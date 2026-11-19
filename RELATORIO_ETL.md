# Relatório de ETL: Radar ENEM

- **Disciplina:** Engenharia de Dados e MLOps, Trabalho II (ETL / Projeto Aplicado)
- **Grupo:** João Paulo Araujo Cappeletti, Matheus Silva da Cruz e Nicolas André Krause de Mello
- **Base:** Microdados do ENEM 2022 e 2023 (INEP)
- **Repositório:** <https://github.com/joaopaulo0611/facilita-enem> (pastas `etl/`, `facilita-backend/` e `facilita-frontend/`)

> Este relatório descreve o processo de ETL e os dados do projeto: a fonte, a
> arquitetura, as transformações de cada camada, as regras de qualidade, a
> modelagem da camada analítica, a volumetria medida e as decisões de engenharia
> que sustentam o pipeline. O [`RELATORIO_GERAL.md`](https://github.com/joaopaulo0611/facilita-enem/blob/main/RELATORIO_GERAL.md) descreve
> o produto inteiro (API e front-end); aqui o foco é o dado.

---

## Sumário

1. [Objetivo e contexto](#1-objetivo-e-contexto)
2. [Arquitetura do pipeline](#2-arquitetura-do-pipeline)
3. [Fonte de dados e ingestão](#3-fonte-de-dados-e-ingestão)
4. [Camada Bronze: ingestão fiel](#4-camada-bronze-ingestão-fiel)
5. [Camada Silver: tipagem e qualidade](#5-camada-silver-tipagem-e-qualidade)
6. [Camada Gold: modelo analítico](#6-camada-gold-modelo-analítico)
7. [Qualidade, validação e governança](#7-qualidade-validação-e-governança)
8. [Orquestração, idempotência e reprodutibilidade](#8-orquestração-idempotência-e-reprodutibilidade)
9. [Volumetria e desempenho](#9-volumetria-e-desempenho)
10. [Linhagem (data lineage)](#10-linhagem-data-lineage)
11. [Consumo: da Gold à aplicação](#11-consumo-da-gold-à-aplicação)
12. [Limitações e trabalhos futuros](#12-limitações-e-trabalhos-futuros)
13. [Como reproduzir](#13-como-reproduzir)

---

## 1. Objetivo e contexto

### 1.1 Problema

O ENEM produz todo ano uma nota por área, mas essa nota, isolada, diz pouco ao
participante: 650 pontos é bom ou ruim? Depende de com quem se compara. O objetivo
do pipeline é transformar os microdados brutos do INEP em uma base analítica
enxuta que permita responder, em tempo de requisição, **onde a nota de um
participante se posiciona**, no Brasil e dentro de recortes socioeconômicos
(renda, tipo de escola, cor/raça, sexo, UF e escolaridade da mãe).

### 1.2 Decisão de arquitetura central

O trabalho pesado (ler milhões de linhas e agregar) acontece **uma vez, offline**,
no pipeline PySpark. A aplicação em produção nunca toca o CSV do INEP: ela lê apenas
a camada Gold, que é um resumo pré-agregado de ~15 MB. Isso desacopla o custo de
processamento (batch, caro, esporádico) do custo de atendimento (online, barato,
constante) e permite hospedar a API em um servidor pequeno.

### 1.3 Escopo

| Item | Decisão | Justificativa |
|---|---|---|
| Edições | 2022 e 2023 | Microdados de 2024+ podem não ligar a nota ao questionário socioeconômico; sem essa ligação os recortes não existem. |
| Granularidade de origem | 1 linha por inscrito/ano | Formato nativo do INEP. |
| Granularidade analítica | 1 linha por (ano, área, recorte, categoria, nota) | Suficiente para percentil exato sem guardar indivíduos. |
| Comparação entre anos | 2022 e 2023 somados numa base única | A nota do ENEM é equalizada por TRI justamente para ser comparável entre edições. |

---

## 2. Arquitetura do pipeline

Arquitetura **medalhão** (Bronze → Silver → Gold) em PySpark, gravando tudo em
Parquet com compressão **zstd**, particionado por ano (`NU_ANO`).

```
microdados do INEP (CSV, ~3,3 GB, 2 arquivos)
        │  etl/  (PySpark, offline, uma vez por base)
        ▼
  ┌──────────┐     ┌──────────┐     ┌──────────┐
  │  BRONZE  │ ──► │  SILVER  │ ──► │   GOLD    │  (≈15 MB)
  │ cópia    │     │ tipagem  │     │ agregação │
  │ fiel     │     │ + QA     │     │ analítica │
  └──────────┘     └────┬─────┘     └────┬─────┘
                        │ rejeitados      │  data/gold/  (versionada no Git)
                        ▼                 ▼
                  auditoria de QA    facilita-backend/ (FastAPI) → front-end
```

**Por que medalhão.** Cada camada tem um contrato claro e pode ser reprocessada a
partir da anterior sem reler a origem:

- **Bronze** isola o projeto do formato bruto do INEP (Latin-1, `;`, tudo texto).
- **Silver** concentra tipagem e regras de qualidade; mudar uma regra reprocessa a
  partir do Parquet da Bronze, muito mais rápido que reler os CSVs.
- **Gold** é o único modelo que a aplicação conhece; mudanças internas de Silver não
  vazam para a API enquanto o contrato da Gold for mantido.

**Por que Parquet + zstd.** Colunar (lê só as colunas necessárias), tipado,
particionável e com compressão forte. Antes de gravar a Gold, as linhas são
ordenadas por grupo e nota, porque valores vizinhos repetidos comprimem melhor:
uma otimização física deliberada do layout em disco.

---

## 3. Fonte de dados e ingestão

### 3.1 Origem

Microdados oficiais do ENEM (INEP), públicos e anonimizados na origem: dois CSVs
(2022 e 2023) somando **~3,3 GB** e **7.410.060 inscritos**. Cada arquivo tem 76
colunas no padrão do INEP (nota por área, presença, situação da redação,
questionário socioeconômico, UF de prova, etc.).

### 3.2 Obtenção automatizada e resiliente (`baixar_microdados.py`, `fontes.json`)

O portal do INEP é instável (ZIPs de cerca de 550 a 620 MB por ano, que viram 3,3 GB de
CSV depois de extraídos, e conexões recusadas com frequência). O pipeline trata a ingestão como uma etapa de engenharia, não como um
download manual:

- **`fontes.json`, o manifesto de origem.** Para cada ano guarda a URL do ZIP no INEP
  e, após a primeira verificação, o **tamanho** e o **SHA-256** do arquivo. Nas
  execuções seguintes esses valores confirmam a integridade e detectam um ZIP
  corrompido ou **republicado** pelo INEP (mudança silenciosa da fonte).
- **Download com robustez.** Até 4 tentativas, retomada de onde parou (HTTP Range),
  cabeçalhos que imitam um navegador (o portal recusa clientes "não-navegador") e,
  em último caso, fallback para o `curl` do sistema. Um ZIP já presente em `public/`
  é reaproveitado.
- **Validação do que foi baixado.** Antes de aceitar o arquivo, o script confere que
  ele é mesmo um ZIP (tamanho mínimo e assinatura `PK\x03\x04`). O portal do INEP às
  vezes responde com um redirect/erro curto (status 200) que seria salvo como se
  fosse o ZIP e só estouraria depois, na extração, com um `BadZipFile` confuso e, pior,
  com um checksum falso registrado no `fontes.json`. Com a validação, um download
  inválido é recusado na hora, com mensagem clara, sem contaminar o manifesto.
- **Verificação de ambiente (`verificar_ambiente.py`).** Antes de subir o Spark,
  confere se a versão do Python é compatível com o PySpark 3.5.3 (suporte oficial
  do 3.8 ao 3.11; o 3.12 passa com aviso). Isso transforma a falha silenciosa da JVM numa
  mensagem objetiva no início, em vez de um pipeline "travado" no meio.

Essas três peças correspondem, na prática, à etapa de **ingestão confiável e
verificação da fonte** que um pipeline de produção exige.

---

## 4. Camada Bronze: ingestão fiel

**Arquivo:** `etl/bronze.py` · **Contrato:** cópia fiel da origem em formato colunar.

- Lê o CSV com as opções exatas do INEP: `header`, separador `;`, encoding
  `ISO-8859-1`, **sem inferência de schema** (tudo entra como texto). Tipar é
  responsabilidade da Silver, não da ingestão.
- **Não altera nenhum valor.** O único enriquecimento é de **rastreabilidade**:
  - `_arquivo_origem`: de qual arquivo a linha veio;
  - `_ingerido_em`: timestamp da ingestão.
- Grava particionado por `NU_ANO`, sobrescrevendo apenas a partição do ano
  reprocessado.

**Resultado:** 7.410.060 linhas · 78 colunas (76 do INEP + 2 de rastreabilidade) ·
**590 MB** (17,6% do CSV, só pela mudança de formato e compressão).

**Por que manter a Bronze.** Ela é a fonte de reprocessamento. Qualquer mudança de
regra na Silver parte do Parquet da Bronze, sem reler 3,3 GB de CSV. É mais rápido e
não depende de a origem continuar disponível.

---

## 5. Camada Silver: tipagem e qualidade

**Arquivo:** `etl/silver.py` · **Contrato:** linhas tipadas, validadas e com média
calculada; nada some sem motivo.

### 5.1 Redução e tipagem

Das 76 colunas do INEP ficam só as **15** que o produto consulta: identificação
(`NU_INSCRICAO`, `NU_ANO`, `IN_TREINEIRO`), as cinco notas, e os seis recortes
(`RENDA` ← `Q006`, `TIPO_ESCOLA` ← `TP_ESCOLA`, `COR_RACA` ← `TP_COR_RACA`,
`SEXO` ← `TP_SEXO`, `UF` ← `SG_UF_PROVA`, `ESCOLARIDADE_MAE` ← `Q002`). Os seis
recortes ganham nomes de domínio aqui, na fronteira; as notas e os identificadores mantêm
os nomes do INEP (`NU_NOTA_CN`, `NU_INSCRICAO` etc.).

Além disso, calcula `NU_NOTA_MEDIA` = média simples das cinco notas, arredondada a
uma casa: a mesma métrica que o participante vê.

### 5.2 Validação com motivo de rejeição

Cada linha recebe um **motivo** (ou fica nula = válida). As válidas vão para
`silver/participantes`; as rejeitadas, para `silver/rejeitados` com inscrição, ano
e motivo. As regras são avaliadas **em ordem de prioridade** (a primeira que falha
define o motivo):

| Ordem | Motivo | Regra | Linhas (2022+2023) |
|---|---|---|---|
| 1 | `AUSENTE_OU_ELIMINADO` | Faltou/eliminado em alguma das 4 provas objetivas | 2.386.973 |
| 2 | `REDACAO_EM_BRANCO` | Redação com situação "em branco" | 77.541 |
| 3 | `NOTA_AUSENTE` | Alguma das 5 notas vazia | 0 |
| 4 | `NOTA_FORA_DA_ESCALA` | Alguma nota fora de 0 a 1000 | 0 |
| 5 | `SEM_QUESTIONARIO` | Sem renda (Q006) → não entra nos recortes | 0 |
| | **Total rejeitado** | | **2.464.514** |

**Decisões de qualidade documentadas:**

- **Nenhum registro é descartado em silêncio.** As rejeitadas ficam auditáveis em
  `silver/rejeitados`. Isso é uma *dead-letter table*: dá para contar e inspecionar
  o que saiu e por quê, em vez de só ver um total encolher.
- **Treineiros não são rejeitados.** Quem fez as provas tem nota válida para
  comparação (904.366 treineiros entre os 4.945.546 válidos).
- **Regras 3 a 5 como rede de proteção.** Não pegaram nenhuma linha em 2022/2023, mas
  permanecem: se o INEP mudar o formato numa edição futura, o problema aparece como
  **rejeição explícita** em vez de virar nota errada na Gold. É um *schema/quality
  guard* contra deriva da fonte.

**Resultado:** 4.945.546 válidos (70 MB, 2,1% do CSV) + 2.464.514 rejeitados (7,7 MB).

---

## 6. Camada Gold: modelo analítico

**Arquivo:** `etl/gold.py` · **Contrato:** distribuições e estatísticas
pré-agregadas por grupo; é a **única** camada que a API lê.

### 6.1 Modelo dimensional

A unidade de análise é o **grupo**: a combinação de quatro chaves.

| Chave | Papel | Domínio |
|---|---|---|
| `NU_ANO` | Dimensão temporal | 2022, 2023 |
| `AREA` | Dimensão de prova | LC, CH, CN, MT, REDACAO, MEDIA |
| `RECORTE` | Dimensão do recorte | GERAL, RENDA, TIPO_ESCOLA, COR_RACA, SEXO, UF, ESCOLARIDADE_MAE, + cruzamentos |
| `CATEGORIA` | Valor do recorte | ex.: `SC`, `B`, `3`, ou `B|E` nos cruzamentos |

Exemplo de grupo: *"2023, Matemática, UF, SC"*.

**Recortes disponíveis:**

- `GERAL`: todo mundo (o "Brasil" de comparação);
- os seis recortes simples: `RENDA`, `TIPO_ESCOLA`, `COR_RACA`, `SEXO`, `UF`,
  `ESCOLARIDADE_MAE`;
- os **cruzamentos** `RENDA_X_ESCOLARIDADE_MAE` (pergunta "família") e
  `COR_RACA_X_TIPO_ESCOLA` (pergunta "origem"). A categoria de um cruzamento junta
  os dois códigos (ex.: `B|E`); quem não respondeu um dos campos fica fora do
  cruzamento.

Os cruzamentos ficam na lista `CRUZAMENTOS` do `etl/config.py`. **Para criar um
novo recorte cruzado, basta acrescentar um par nessa lista e rodar a Gold de novo**.
É extensibilidade guiada por configuração, sem mexer na lógica de agregação.

### 6.2 Duas tabelas por grupo

| Tabela | Grão | Guarda | Serve para |
|---|---|---|---|
| `distribuicao_notas` | 1 linha por (grupo, nota distinta) | contagem de pessoas com aquela nota | **percentil exato** |
| `estatisticas` | 1 linha por grupo | n, média, desvio-padrão, mínimo, quartis (P25/mediana/P75), máximo | **Z-Score** e resumo |

### 6.3 A otimização que torna a Gold pequena

Em vez de guardar 4,9 milhões de indivíduos, a Gold guarda **quantas pessoas
tiraram cada nota** por grupo. Como a nota do ENEM é discreta, a distribuição cabe
em poucas linhas por grupo e ainda permite o percentil **exato** (não amostrado). O
resultado reduz o volume analítico a uma fração mínima do CSV original (ver §9).

**Resultado (código atual, com os dois cruzamentos):** ~6,73 milhões de linhas de
distribuição e **2.616 grupos** de estatísticas, ~**15,5 MB** no total.

> **Rastreabilidade dos números.** O `etl/volumetria.json` versionado foi
> regenerado após a inclusão do segundo cruzamento (`RENDA_X_ESCOLARIDADE_MAE`) e
> hoje registra exatamente estes valores: 2.616 grupos e 6.727.275 linhas de
> distribuição. A evidência no repositório casa com o código atual.

---

## 7. Qualidade, validação e governança

| Dimensão de qualidade | Como é tratada | Onde |
|---|---|---|
| **Completude** | Notas ausentes e questionário faltante viram motivos de rejeição | Silver |
| **Validade** | Notas fora de 0 a 1000 e presença obrigatória nas provas | Silver |
| **Consistência** | Tipagem explícita (texto → `int`/`double`/`long`); contrato fixo da Gold | Silver/Gold |
| **Rastreabilidade** | `_arquivo_origem`, `_ingerido_em`; tabela de rejeitados; manifesto `fontes.json` | Bronze/Silver/ingestão |
| **Integridade da fonte** | SHA-256 + tamanho conferidos a cada download | Ingestão |
| **Confiabilidade estatística** | Grupos com < 100 pessoas não são comparados pela API | Consumo (regra de negócio da Gold) |
| **Testabilidade** | A API tem testes automatizados sobre uma Gold sintética pequena, sem os microdados. O ETL ainda não tem testes próprios (ver §12) | `facilita-backend/tests/` |

O corte de **grupo mínimo (n < 100)** é uma regra de qualidade estatística: abaixo
desse tamanho o percentil deixa de ser confiável, então a API recusa a comparação
em vez de devolver um número enganoso.

---

## 8. Orquestração, idempotência e reprodutibilidade

**Orquestrador:** `etl/run_pipeline.py`.

1. `verificar_ambiente.py`: barra um Python incompatível **antes** de baixar GBs ou
   subir o Spark.
2. `garantir_microdados()`: baixa e extrai de `fontes.json` só o que faltar (pule
   com `--sem-download`).
3. Executa Bronze → Silver → Gold em ordem, **medindo o tempo de cada camada**.
4. `volumetria.py`: mede tamanho/linhas/colunas de cada camada e grava
   `etl/volumetria.json` (evidência do relatório).

**Idempotência.** Cada camada **sobrescreve a própria saída** (`mode("overwrite")`,
particionado por ano). Reexecutar o pipeline com a mesma entrada produz exatamente a
mesma saída: não duplica dados nem depende de estado anterior. Essa propriedade é o
que torna o pipeline seguro de repetir e fácil de depurar.

**Configuração centralizada.** Caminhos, anos, colunas, recortes, cruzamentos e a
sessão Spark (memória, partições de shuffle, timezone) ficam todos em
`etl/config.py`. Mudar escopo (um ano novo, um recorte novo) é mudar configuração,
não lógica.

---

## 9. Volumetria e desempenho

Medições de `etl/volumetria.py`, comparadas ao CSV bruto (~3.345 MB):

| Camada | Tamanho | Linhas | % do CSV |
|---|---:|---:|---:|
| CSV bruto (2 arquivos) | 3.345,3 MB | 7.410.060 | 100% |
| Bronze | 589,9 MB | 7.410.060 | 17,6% |
| Silver: participantes | 69,6 MB | 4.945.546 | 2,1% |
| Silver: rejeitados | 7,7 MB | 2.464.514 | 0,23% |
| Gold: distribuição de notas | 15,4 MB | 6.727.275 | 0,46% |
| Gold: estatísticas | 0,1 MB | 2.616 | 0,002% |

**Leitura do resultado:** a camada que a aplicação consome (Gold) é **~0,46% do
tamanho do CSV original**. A redução vem de três fatores combinados: formato colunar
comprimido (Bronze), descarte de colunas e linhas inválidas (Silver) e agregação por
distribuição de notas (Gold).

**Tempos da última execução de cada camada:** Bronze 53 s · Silver 17 s · Gold 246 s.
Bronze e Silver vêm de uma execução completa do pipeline; a Gold foi rodada de novo
sozinha, depois da troca de cruzamentos, a partir da Silver já gravada.

> A Gold foi executada com 4 GB de memória e 6 núcleos; a configuração padrão do
> `config.py` (6 GB, todos os núcleos) travou um notebook de 16 GB com outros
> programas abertos. Ajustar `spark.driver.memory` e o paralelismo ao hardware é
> parte da operação do pipeline.

---

## 10. Linhagem (data lineage)

Rastro de ponta a ponta de um campo até a resposta da API:

```
INEP: Q006 (texto, CSV)                     ── fonte, verificada por SHA-256
  └─► Bronze: Q006 (texto) + _arquivo_origem, _ingerido_em
        └─► Silver: RENDA (renomeado, validado; nulo → SEM_QUESTIONARIO)
              └─► Gold: grupo (ano, AREA, RENDA, categoria) em
                        distribuicao_notas + estatisticas
                    └─► API: percentil/Z-Score da nota dentro do grupo
                          └─► Front-end: "X% tiveram nota menor que a sua"
```

Cada seta é uma transformação versionada em um arquivo específico (`bronze.py`,
`silver.py`, `gold.py`), e o commit que (re)gera a Gold registra **quando** os dados
mudaram e **por quê**.

**Versionamento dos dados.** Só a **Gold** é versionada (`data/gold/`), porque é
pequena e é tudo o que o deploy precisa. Bronze, Silver e os ZIPs ficam fora do Git
(`.gitignore`), porque são grandes e apenas intermediários. Assim, clonar o repositório já
entrega os dados prontos para a API, sem reprocessar nada.

---

## 11. Consumo: da Gold à aplicação

A API (`facilita-backend/`, FastAPI) carrega a Gold em memória na primeira
requisição (~1,5 s) e a mantém lá. Cada grupo vira dois vetores ordenados (notas e
contagem acumulada).

- **Percentil**: busca binária na distribuição acumulada: % do grupo com nota
  menor que a do usuário. Instantâneo mesmo com milhões de pessoas, porque não
  percorre indivíduos.
- **Z-Score**: `(nota − média) / desvio-padrão` do grupo, a partir de
  `estatisticas`.
- **União de anos**: 2022 e 2023 somados em um único grupo (contagens somadas,
  média e desvio recalculados), coerente com a equalização por TRI.

Isso fecha o propósito da modelagem da Gold: os cálculos online são triviais porque
o custo foi pago no batch.

---

## 12. Limitações e trabalhos futuros

**Limitações conhecidas:**

- **Escopo temporal.** Só 2022 e 2023; incluir 2024+ depende de o INEP manter a
  ligação nota ↔ questionário.
- **UF = local de prova**, não residência (como o INEP registra).
- **ETL sem testes automatizados.** As regras da Silver e a agregação da Gold são
  conferidas pelas contagens e pela volumetria de cada execução, mas não por uma suíte de
  testes. Os testes existentes cobrem a API.
- **Qualidade implícita.** As regras de QA vivem no código da Silver; não há ainda
  um relatório de qualidade publicado a cada execução além da contagem de rejeições.

**Trabalhos futuros (ganchos já existentes no projeto):**

- **Novos recortes cruzados** adicionando pares em `CRUZAMENTOS` (`config.py`).
- **Relatório de qualidade por execução** (ex.: % de rejeição por motivo e por ano
  gravado junto com a volumetria), aproveitando que os rejeitados já são tabela.
- **Assertivas automatizadas de dados** (contagens mínimas por grupo, faixas de
  média esperadas) como *gate* antes de promover a Gold, um passo natural de MLOps/DataOps.
- **Agendamento** do pipeline (cron/CI) condicionado a uma nova publicação do INEP,
  detectável via mudança de SHA-256 em `fontes.json`.

---

## 13. Como reproduzir

Requer Python 3.8 a 3.11 e Java 17 (para o Spark). A partir da raiz do repositório:

```bash
python3 -m venv .venv
. .venv/bin/activate                 # Windows: .\.venv\Scripts\Activate.ps1
pip install -r etl/requirements.txt

python etl/verificar_ambiente.py     # confere a versão do Python
python etl/run_pipeline.py           # baixa o que faltar, verifica (SHA-256) e processa
# ou, se os CSVs já estão extraídos em public/:
python etl/run_pipeline.py --sem-download
```

Ao final, a Gold fica em `data/gold/` e o resumo da execução em
`etl/volumetria.json`. Para publicar, commite `data/gold/`, `etl/fontes.json` e
`etl/volumetria.json`.

---

### Mapa de arquivos do ETL

| Arquivo | Papel |
|---|---|
| `etl/config.py` | Caminhos, anos, colunas, recortes, cruzamentos e sessão Spark |
| `etl/fontes.json` | Manifesto de origem: URL, tamanho e SHA-256 de cada ano |
| `etl/baixar_microdados.py` | Download resiliente, verificação de checksum e extração |
| `etl/verificar_ambiente.py` | Checagem de versão do Python antes do Spark |
| `etl/bronze.py` | CSV do INEP → Parquet, cópia fiel + rastreabilidade |
| `etl/silver.py` | Seleção, tipagem e validação com motivo de rejeição |
| `etl/gold.py` | Distribuição de notas e estatísticas por grupo |
| `etl/volumetria.py` | Mede cada camada → `volumetria.json` |
| `etl/run_pipeline.py` | Orquestra tudo, medindo o tempo de cada camada |

# Relatório Final do Produto de Dados: Radar ENEM

**Instituição:** UniSENAI, Florianópolis
**Curso:** Bacharelado em Ciência de Dados e Inteligência Artificial
**Unidade Curricular:** Projeto Aplicado III, 2026/02
**Docente:** Gustavo Stangherlin Cantarelli
**Avaliação:** AV6, Relatório Final do Produto de Dados (20%)
**Equipe:** Matheus Silva da Cruz (líder), Nicolas André Krause de Mello e João Paulo Araujo Cappeletti
**Repositório:** <https://github.com/joaopaulo0611/facilita-enem>

> **Aplicação web pública (link definitivo):** <https://facilita-enem-eta.vercel.app/>
>
> *A aplicação definitiva está hospedada em nuvem no endereço acima. Documentação
> interativa da API em <https://radar-enem-api.onrender.com/docs>.*

---

## Sumário

1. [Introdução, contextualização e justificativa de impacto social](#1-introdução-contextualização-e-justificativa-de-impacto-social)
2. [Metodologia de engenharia de Big Data aplicada](#2-metodologia-de-engenharia-de-big-data-aplicada)
3. [Metodologia estatística e rigor analítico de backend](#3-metodologia-estatística-e-rigor-analítico-de-backend)
4. [Resultados, conclusões e validação da aplicação em nuvem](#4-resultados-conclusões-e-validação-da-aplicação-em-nuvem)
5. [Conclusão](#5-conclusão)
6. [Referências](#6-referências)

---

## 1. Introdução, contextualização e justificativa de impacto social

### 1.1 O problema

O Exame Nacional do Ensino Médio (ENEM) é a principal porta de entrada ao ensino
superior no Brasil. Todo ano ele produz, para cada participante, uma nota por área
do conhecimento. Mas a nota isolada comunica pouco a quem a recebe: **650 pontos é
um resultado bom ou ruim?** A resposta depende inteiramente de com quem se compara.
O participante recebe o número, mas não recebe o contexto, e é justamente o contexto
que permite interpretar o desempenho e tomar decisões (que curso tentar, em qual
universidade, por qual política de cotas).

Os Microdados do ENEM, publicados pelo INEP, contêm esse contexto: são a base
pública que relaciona a nota de cada inscrito ao seu perfil socioeconômico. O
problema é de acesso. São arquivos de múltiplos gigabytes, em formato bruto, que
exigem conhecimento de engenharia de dados e estatística para serem lidos. Na
prática, essa riqueza fica restrita a pesquisadores e especialistas, longe do
cidadão a quem o dado diz respeito.

### 1.2 A solução: Radar ENEM

O **Radar ENEM** é um produto de dados que fecha essa lacuna. É uma aplicação web
de livre acesso onde qualquer pessoa digita as cinco notas do exame e, opcionalmente,
marca recortes do próprio perfil (renda da família, tipo de escola, cor/raça, UF,
escolaridade da mãe). Em tempo real, a aplicação devolve um diagnóstico estatístico:
em que **percentil** a nota se posiciona, o **Z-Score** (a quantos desvios-padrão da
média o participante está) e como essa posição **muda** conforme o grupo de comparação.

A base do diagnóstico são os microdados oficiais do INEP das edições **2022 e 2023**,
somando **7.410.060 inscritos**, dos quais **4.945.546 participantes válidos**
alimentam as comparações.

### 1.3 Justificativa de impacto social

O valor social do produto está em **democratizar a leitura do próprio dado** e em
**tornar visível a desigualdade educacional** que a nota crua esconde.

Um exemplo concreto, extraído da base real do projeto. Uma média geral de **650
pontos** significa coisas muito diferentes conforme o ponto de partida do
participante:

| Grupo de comparação | Percentil de uma média 650 |
|---|---:|
| Brasil (todos os participantes) | **87,2%** |
| Candidatos de escola pública | **94,4%** |
| Candidatos de escola privada | **65,7%** |
| Renda familiar até 1 salário mínimo | **96,6%** |
| Renda familiar acima de 20 salários mínimos | **49,5%** |

A mesma nota que coloca um estudante de baixa renda entre os **4% melhores** do seu
grupo deixa um estudante de alta renda **abaixo da metade** do grupo dele. O Radar
ENEM mostra isso ao participante de forma direta: evidencia que o esforço individual
acontece sobre pontos de partida desiguais, e dá ao usuário uma régua honesta para
entender sua posição, inclusive diante de políticas afirmativas e de cotas. É um
instrumento de **cidadania informada**, alinhado aos objetivos de formação ética e
socialmente responsável do curso.

Os dados são públicos e anonimizados na origem pelo INEP; a aplicação **não guarda**
as notas digitadas: o cálculo é feito na hora e nada é armazenado, preservando a
privacidade do usuário.

---

## 2. Metodologia de engenharia de Big Data aplicada

### 2.1 Desafio de volumetria e decisão central de arquitetura

Os dois CSVs do INEP somam **3,3 GB** e **7,4 milhões de linhas**. Carregar isso em
memória a cada requisição é inviável em um servidor barato: exatamente o cenário
que a atividade propõe. A decisão de arquitetura central do projeto resolve esse
conflito: **o trabalho pesado (ler milhões de linhas e agregar) acontece uma vez,
offline**, em um pipeline batch; a aplicação em produção nunca toca o CSV, lê apenas
um resumo pré-agregado de cerca de 15 MB. Isso desacopla o custo de processamento
(caro, esporádico) do custo de atendimento (barato, constante).

### 2.2 Arquitetura medalhão em PySpark

O pipeline (`etl/`) segue a arquitetura **medalhão** (Bronze, Silver e Gold) em
PySpark, gravando tudo em **Parquet** (colunar, tipado) com compressão **zstd**,
particionado por ano (`NU_ANO`).

```
microdados do INEP (CSV, 3,3 GB, 2 arquivos)
        |  etl/  (PySpark, offline, uma vez por base)
        v
  +----------+     +----------+     +----------+
  |  BRONZE  | --> |  SILVER  | --> |   GOLD   |  (~15 MB)
  |  copia   |     |  tipagem |     | agregacao|
  |  fiel    |     |  + QA    |     | analitica|
  +----------+     +----+-----+     +----+-----+
                        | rejeitados      |  data/gold/ (versionada no Git)
                        v                 v
                  auditoria de QA    facilita-backend/ --> front-end
```

| Camada | Contrato | Resultado (2022 + 2023) |
|---|---|---|
| **Bronze** (`bronze.py`) | Cópia fiel do CSV em Parquet, tudo como texto, mais duas colunas de rastreabilidade (`_arquivo_origem`, `_ingerido_em`). | 7.410.060 linhas, 78 colunas, 590 MB |
| **Silver** (`silver.py`) | Reduz a 15 colunas úteis, tipa, valida com motivo de rejeição e calcula a média das 5 notas. | 4.945.546 válidas, 70 MB |
| **Gold** (`gold.py`) | Agrega: quantas pessoas tiraram cada nota em cada grupo, mais as estatísticas de cada grupo. Única camada que a API lê. | 6.727.275 linhas de distribuição; 2.616 linhas de estatísticas; 15,5 MB |

**Por que cada camada.** A Bronze isola o projeto do formato bruto do INEP (Latin-1,
separador `;`, tudo texto) e serve de fonte de reprocessamento: mudar uma regra na
Silver parte do Parquet da Bronze, sem reler 3,3 GB de CSV. A Silver concentra
tipagem e qualidade. A Gold é o único modelo que a aplicação conhece; mudanças
internas na Silver não vazam para a API enquanto o contrato da Gold for mantido.

### 2.3 Ingestão confiável e verificação da fonte

O portal do INEP é instável (ZIPs de 550 a 620 MB por ano, conexões recusadas). O
pipeline trata o download como etapa de engenharia:

- **`fontes.json`** é o manifesto de origem: guarda a URL, o tamanho e o **SHA-256**
  de cada ano. Nas execuções seguintes, esses valores confirmam a integridade e
  detectam um arquivo corrompido ou **republicado** pelo INEP.
- **`baixar_microdados.py`** baixa com até 4 tentativas, retoma de onde parou (HTTP
  Range), imita um navegador e, em último caso, usa o `curl` do sistema. **Antes de
  aceitar** o arquivo, valida que ele é mesmo um ZIP (assinatura `PK\x03\x04`),
  evitando que um redirect ou erro curto do portal seja salvo como se fosse o ZIP.
- **`verificar_ambiente.py`** confere, antes de subir o Spark, se a versão do Python
  é compatível com o PySpark 3.5.3, transformando uma falha silenciosa da JVM numa
  mensagem clara logo no início.

### 2.4 Qualidade de dados: nenhuma linha some sem explicação

Na Silver, cada linha fica válida ou recebe um **motivo de rejeição**; as rejeitadas
vão para uma *dead-letter table* (uma tabela de registros descartados, em
`silver/rejeitados`) auditável. As regras são avaliadas em ordem de prioridade:

| Ordem | Motivo | Linhas (2022+2023) |
|---|---|---:|
| 1 | `AUSENTE_OU_ELIMINADO` (faltou ou eliminado em prova objetiva) | 2.386.973 |
| 2 | `REDACAO_EM_BRANCO` | 77.541 |
| 3 | `NOTA_AUSENTE` | 0 |
| 4 | `NOTA_FORA_DA_ESCALA` (fora de 0 a 1000) | 0 |
| 5 | `SEM_QUESTIONARIO` (sem renda Q006) | 0 |
| | **Total rejeitado** | **2.464.514** |

As regras 3 a 5 não pegaram nenhuma linha nesta base, mas permanecem como **rede de
proteção** contra deriva do formato da fonte: se o INEP mudar o layout numa edição
futura, o problema aparece como rejeição explícita em vez de virar nota errada na
Gold. Treineiros **não** são rejeitados (904.366 entre os válidos), pois têm nota
válida para comparação.

### 2.5 A otimização que torna a Gold pequena

Em vez de guardar 4,9 milhões de indivíduos, a Gold guarda **quantas pessoas tiraram
cada nota** por grupo. Como a nota do ENEM é discreta, a distribuição cabe em poucas
linhas por grupo e **ainda permite o percentil exato** (não amostrado). Antes de
gravar, as linhas são ordenadas por grupo e nota, porque valores vizinhos repetidos
comprimem melhor no Parquet.

### 2.6 Volumetria medida

Valores de `etl/volumetria.json`, comparados aos 3.345 MB dos CSVs:

| Camada | Tamanho | Linhas | % do CSV |
|---|---:|---:|---:|
| CSV bruto (2 arquivos) | 3.345,3 MB | 7.410.060 | 100% |
| Bronze | 589,9 MB | 7.410.060 | 17,6% |
| Silver: participantes | 69,6 MB | 4.945.546 | 2,1% |
| Silver: rejeitados | 7,7 MB | 2.464.514 | 0,23% |
| Gold: distribuição de notas | 15,4 MB | 6.727.275 | 0,46% |
| Gold: estatísticas | 0,1 MB | 2.616 | 0,002% |

**A camada que a aplicação consome (Gold) é cerca de 0,46% do CSV original.** Tempos
da última execução: Bronze 53 s, Silver 17 s, Gold 246 s.

### 2.7 Governança, idempotência e versionamento

- **Idempotência:** cada camada sobrescreve a própria saída (`mode("overwrite")`,
  particionado por ano). Reexecutar com a mesma entrada produz exatamente a mesma
  saída: seguro de repetir e fácil de depurar.
- **Configuração centralizada:** caminhos, anos, colunas, recortes, cruzamentos e a
  sessão Spark ficam em `etl/config.py`. Adicionar um recorte ou um ano é mudar
  configuração, não lógica.
- **Versionamento dos dados:** só a **Gold** vai para o Git (`data/gold/`), porque é
  pequena e é tudo o que o deploy precisa. Bronze, Silver e os ZIPs ficam fora
  (`.gitignore`). Clonar o repositório já entrega os dados prontos para a API, sem
  reprocessar nada (foi exatamente assim que a validação deste relatório foi feita,
  ver a seção 4.1).

---

## 3. Metodologia estatística e rigor analítico de backend

### 3.1 Modelo analítico: o grupo

A unidade de análise é o **grupo**, a combinação de quatro chaves: ano, área (LC, CH,
CN, MT, Redação ou a média), recorte e categoria. Exemplo: *"2023, Matemática, UF,
SC"*. Os recortes são `GERAL`, os seis simples (`RENDA`, `TIPO_ESCOLA`, `COR_RACA`,
`SEXO`, `UF`, `ESCOLARIDADE_MAE`) e dois **cruzamentos**:
`COR_RACA_X_TIPO_ESCOLA` (pergunta de origem) e `RENDA_X_ESCOLARIDADE_MAE` (pergunta
de família). A base tem **1.308 grupos**. Na tabela de estatísticas eles somam
**2.616 linhas**, porque cada grupo aparece uma vez para 2022 e outra para 2023.

Para cada grupo a Gold guarda a **distribuição de notas** (uma linha por nota
distinta, com a contagem) e as **estatísticas** (n, média, desvio-padrão, mínimo,
quartis, máximo).

### 3.2 União dos anos coerente com a TRI

A nota do ENEM é calculada pela **Teoria de Resposta ao Item (TRI)** justamente para
ser comparável entre edições. Por isso a API soma 2022 e 2023 em uma base única: as
contagens de cada nota são somadas e a média e o desvio-padrão são **recalculados**
para a base combinada (variância combinada via `E[x²]` dos dois anos menos o quadrado
da média nova). O participante é comparado com todos os anos de uma vez, sem escolher
ano, o que é estatisticamente correto dada a equalização por TRI.

### 3.3 Os cálculos

Cada grupo fica em memória como dois vetores ordenados: as notas e a **contagem
acumulada** até cada nota.

- **Percentil (exato):** porcentagem do grupo com nota estritamente menor que a do
  usuário. Uma **busca binária** (`numpy.searchsorted`) acha a posição da nota e o
  acumulado diz quantas pessoas ficaram abaixo. É **instantâneo mesmo com milhões de
  pessoas**, porque não percorre indivíduos (o custo foi pago no batch). Por ser
  calculado sobre a distribuição completa (e não sobre uma amostra), o percentil é
  exato.
- **Z-Score:** `(nota − média do grupo) / desvio-padrão do grupo`. Diz a quantos
  desvios da média o usuário está.
- **Grupo mínimo (n < 100):** grupos com menos de 100 pessoas **não** são comparados.
  Abaixo desse tamanho o percentil deixa de ser confiável, então a API recusa a
  comparação em vez de devolver um número enganoso. É uma regra deliberada de
  qualidade estatística.

### 3.4 As três perguntas comparativas (escopo individual)

Cada integrante é responsável por um módulo de análise comparativa. Todos seguem o
mesmo princípio: calcular o percentil da nota do usuário **dentro de um grupo** e
contrastá-lo com o percentil **no Brasil todo**, evidenciando o quanto o recorte
"move a régua".

| Pergunta | Responsável | Campos de entrada | Recorte(s) |
|---|---|---|---|
| **Seu estado e o Brasil** | João Paulo Araujo Cappeletti | UF | `UF`, `GERAL` e ranking dos 27 estados |
| **Sua origem** | Nicolas André Krause de Mello | Cor/raça e tipo de escola | `COR_RACA`, `TIPO_ESCOLA` e cruzamento `COR_RACA_X_TIPO_ESCOLA` |
| **Sua família** | Matheus Silva da Cruz | Renda e escolaridade da mãe | `RENDA`, `ESCOLARIDADE_MAE` e cruzamento `RENDA_X_ESCOLARIDADE_MAE` |

Códigos que representam ausência de resposta não são aceitos como grupo de
comparação (cor/raça "não declarada" = 0; tipo de escola "não informou" = 1).

### 3.5 Robustez e validação de entrada

As notas são validadas na fronteira da API: qualquer valor fora de **0 a 1000** é
recusado com **HTTP 422** e mensagem em português, por campo, que o front-end mostra
embaixo do campo certo. Inconsistências entre as duas tabelas da Gold (um grupo numa
e não na outra) geram uma mensagem clara de "Gold inconsistente" em vez de um erro
500 opaco. A API tem **38 testes automatizados** que rodam sobre uma Gold sintética
pequena, sem exigir os microdados: todos passando na validação deste relatório.

---

## 4. Resultados, conclusões e validação da aplicação em nuvem

### 4.1 Validação de que o produto funciona

Para este relatório, o projeto foi **executado novamente** a partir do repositório
limpo, usando a camada Gold versionada (sem reprocessar os 3,3 GB):

1. **Ambiente e dependências:** backend instalado em um ambiente virtual Python a
   partir de `requirements.txt`, sem erros.
2. **Testes automatizados:** `pytest`, **38 testes passaram**.
3. **Carga da Gold:** a API carregou a camada Gold em memória e expôs as rotas.
4. **Rotas validadas end-to-end** (todas com HTTP 200 e dados corretos):
   - `GET /api/metadados` devolve anos `[2022, 2023]` e **4.945.546** participantes;
   - `GET /api/radar` devolve percentil, Z-Score e diferença para a média em cada área;
   - `GET /api/modulos/regional`, `/origem` e `/familia` devolvem comparações por
     recorte e cruzamento;
   - validação de entrada: nota fora de 0 a 1000 retorna **HTTP 422**, como esperado.

Os números abaixo são reais, extraídos dessa execução sobre a base 2022+2023.

### 4.2 Panorama nacional por área

| Área | Média | Desvio-padrão | P25 | Mediana | P75 |
|---|---:|---:|---:|---:|---:|
| Linguagens | 520,9 | 74,7 | 474 | 527 | 574 |
| Humanas | 528,9 | 83,1 | 477 | 534 | 586 |
| Natureza | 496,7 | 80,3 | 441 | 491 | 549 |
| Matemática | 539,2 | 124,3 | 441 | 529 | 628 |
| Redação | 637,5 | 192,7 | 540 | 640 | 780 |
| **Média geral** | **544,7** | **89,8** | **483** | **542** | **606** |

Matemática e Redação têm a maior dispersão (desvio-padrão de 124 e 193), o que
significa que uma mesma diferença de pontos "vale" percentis diferentes conforme a
área: informação que o radar de áreas da aplicação torna visível ao usuário.

### 4.3 O gradiente socioeconômico (média geral, Brasil)

**Renda familiar:** a média cresce de forma monótona com a renda, do piso ao teto:

| Faixa de renda | Participantes | Média geral |
|---|---:|---:|
| Nenhuma renda | 268.259 | 483,4 |
| Até 1 salário mínimo | 1.379.315 | 503,5 |
| De 3 a 4 salários | 343.833 | 578,3 |
| De 10 a 12 salários | 62.623 | 626,6 |
| Mais de 20 salários mínimos | 80.392 | 643,5 |

Da faixa mais baixa à mais alta, a média sobe **160 pontos** (de 503 para 643), quase
dois desvios-padrão de distância.

**Tipo de escola:** privada 613,2 contra pública 520,9, uma diferença de **92 pontos**.

**Escolaridade da mãe:** de "nunca estudou" (476,4) a "pós-graduação" (597,1),
**121 pontos** de diferença.

**Cor/raça:** branca 571,4; amarela 541,1; parda 525,0; preta 517,4; indígena 484,9.

Todos os recortes apontam na mesma direção: **o desempenho no ENEM acompanha o nível
socioeconômico**, e a aplicação permite ao cidadão enxergar onde ele está dentro
desse quadro.

### 4.4 O efeito "régua móvel": a mesma nota, posições diferentes

O resultado mais eloquente do produto. Uma média geral de **650** rende percentis
radicalmente diferentes conforme o grupo de comparação:

| Grupo | Percentil de uma média 650 | n do grupo |
|---|---:|---:|
| Brasil (referência) | 87,2% | 4.945.546 |
| Preta + escola pública | **97,0%** | 185.631 |
| Parda + escola pública | 96,1% | 703.839 |
| Branca + escola pública | 91,5% | 607.827 |
| Parda + escola privada | 73,1% | 97.097 |
| Branca + escola privada | **62,1%** | 283.556 |

E nos cruzamentos de família:

| Grupo | Percentil de uma média 650 |
|---|---:|
| Renda até 1 SM + mãe nunca estudou | **98,8%** |
| Renda até 1 SM + mãe com ensino médio | 95,8% |
| Renda acima de 20 SM + mãe com pós-graduação | **45,5%** |

A mesma nota de 650 coloca um estudante negro de escola pública entre os **3%
melhores** do seu grupo (percentil 97) e deixa um estudante branco de escola privada
**à frente de apenas 62,1%** do grupo dele (percentil 62,1); e, no recorte de família
mais privilegiado, abaixo da mediana. Esse contraste é o cerne do impacto social do
Radar ENEM: o número sozinho não revela o esforço relativo nem a desigualdade de
ponto de partida; o produto revela.

### 4.5 Validação da aplicação em nuvem (link público)

A aplicação está publicada e acessível publicamente, sem instalação:

- **Aplicação web:** <https://facilita-enem-eta.vercel.app/>
- **API e documentação:** <https://radar-enem-api.onrender.com/docs>

**Como foi publicada.** O site React está no Vercel e a API FastAPI está no Render,
ambos no plano gratuito. O site chama a API por `/api/...`, e o `vercel.json` repassa
essas chamadas para o Render, então não foi preciso configurar CORS. O back-end é
descrito no `render.yaml`, o que permite recriar o serviço a partir do repositório.
Como não há banco de dados nem chaves externas (os dados vêm na Gold versionada), não
existe `.env` nem credenciais a proteger.

**Ajuste de memória.** O servidor gratuito do Render tem 512 MB. Ao carregar a Gold,
a API chegava a 659 MB. A leitura foi otimizada (em lotes e com o alocador de memória
do sistema) e o pico caiu para cerca de 410 MB, sem mudar nenhum resultado.

**Validação.** Pelo endereço público, todas as rotas responderam corretamente, com os
mesmos números da execução local, e as consultas voltaram em menos de 1 segundo. A
única limitação é do plano gratuito: depois de 15 minutos sem uso o servidor dorme, e
o primeiro acesso leva até cerca de 50 segundos.

<!-- =========================================================================
     INSERIR PRINT 1 AQUI: captura da APLICAÇÃO WEB funcionando no endereço do
     Vercel (https://facilita-enem-eta.vercel.app/), de preferência já com um
     resultado de radar na tela.
     ========================================================================= -->
> **[INSERIR PRINT 1: aplicação funcionando em https://facilita-enem-eta.vercel.app/]**

<!-- =========================================================================
     INSERIR PRINT 2 AQUI: captura do PAINEL DO RENDER mostrando o serviço
     radar-enem-api com o status "Live".
     ========================================================================= -->
> **[INSERIR PRINT 2: painel do Render com o serviço em "Live"]**

---

## 5. Conclusão

O Radar ENEM cumpre o ciclo completo de um produto de dados: ingestão confiável e
verificada dos microdados do INEP, pipeline medalhão em PySpark que comprime 3,3 GB
em uma camada analítica de 15 MB sem perder exatidão, um backend estatístico que
entrega percentil exato e Z-Score em tempo de requisição, e uma interface web pública
que coloca esse diagnóstico nas mãos do cidadão.

O rigor de engenharia (idempotência, rastreabilidade, *dead-letter table*,
verificação por SHA-256, regra de grupo mínimo) sustenta a confiabilidade dos
números apresentados. E os resultados reais (o gradiente socioeconômico consistente
e o efeito "régua móvel") demonstram que o produto entrega o impacto social a que se
propõe: tornar legível, para quem recebe a nota, a desigualdade que ela sozinha
esconde.

**Limitações e trabalhos futuros.** O escopo cobre 2022 e 2023; incluir 2024 em
diante depende de o INEP manter a ligação entre a nota e o questionário
socioeconômico. A UF é o local de prova, não a residência. O ETL ainda não tem suíte
de testes própria (a API tem). Os ganchos de extensibilidade já existem: novos
recortes cruzados entram por configuração em `etl/config.py`, e o manifesto
`fontes.json` permite detectar uma nova publicação do INEP por mudança de checksum.

---

## 6. Referências

- INEP. **Microdados do ENEM.** Portal de Dados Abertos do Inep. Disponível em:
  <https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados/enem>.
- Repositório do projeto: <https://github.com/joaopaulo0611/facilita-enem>.
- Documentação complementar no repositório: `RELATORIO_GERAL.md` (visão geral do
  produto) e `RELATORIO_ETL.md` (relatório técnico de engenharia de dados).

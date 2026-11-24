# Fase 2 — "Em que eu poderia me inscrever?"

Plano de preparação da Fase 2 do assistente do Radar ENEM. A Fase 1 (assistente
determinístico que explica indicadores e interpreta o resultado) já está na
`main`. Esta fase adiciona a capacidade que motivou o assistente: dizer, a
partir das notas da pessoa, **em quais cursos/programas ela teria tido chance**
em edições passadas — sempre como referência histórica, nunca como garantia.

> **Status:** planejamento. Nenhuma base de corte foi versionada ainda. Este
> documento consolida fontes, licenças, esquema de dados, regras e a arquitetura
> proposta, para a implementação começar com o terreno mapeado.

---

## 1. O que a Fase 2 responde

Três perguntas, por ordem de valor e de dificuldade:

1. **SISU (universidades públicas):** "Com a minha nota, em que cursos eu teria
   passado nas últimas edições?" — comparando a **média ponderada** da pessoa
   (pelos pesos de cada curso) com a **nota de corte** histórica, por modalidade
   (ampla concorrência e cotas).
2. **ProUni (bolsas em faculdades privadas):** "Eu me enquadro no ProUni?" —
   checagem de **elegibilidade** por regra (nota mínima + renda + escola), não
   por nota de corte.
3. **FIES (financiamento):** "Eu me enquadro no FIES?" — mesma lógica de
   elegibilidade por regra.

O Radar já coleta os dados que ProUni/FIES exigem: as cinco notas, a **renda**
(Q006) e o **tipo de escola** (TP_ESCOLA). Isso torna a checagem de
elegibilidade viável sem pedir nada novo à pessoa.

---

## 2. Fontes de dados

### 2.1 SISU — notas de corte (o esforço principal)

| Fonte | O que tem | Formato | Licença / uso |
|---|---|---|---|
| **Dados Abertos do MEC** — `dadosabertos.mec.gov.br/sisu` | Relatórios do processo seletivo por edição, com dicionário de dados | CSV por edição | Dado público do governo federal (fonte oficial) |
| **`maiakanegae/sisu-data`** (GitHub) | Cursos, vagas e **notas de corte** de 2020–2025, mais pesos das provas e lista de aprovados | CSV por ano | **MIT**; coletado das APIs do SISU, sem caráter oficial |
| **Base dos Dados** — dataset `sisu` | SISU tratado e padronizado | BigQuery / download | Verificar licença da tabela antes de usar |

**Recomendação:** começar pela fonte oficial do MEC (procedência e dicionário)
e usar `maiakanegae/sisu-data` como referência de esquema e para preencher anos
que o portal não exponha com facilidade. Registrar a origem exata e a data de
coleta de cada arquivo em `etl/fontes_inscricoes.json` (ver seção 6).

#### Esquema observado em `maiakanegae/sisu-data` (ano 2024)

- **`all_courses.csv`** (sem cabeçalho; `;` como separador, aspas): UF, nome da
  IES, sigla, município, campus, **curso**, grau (Bacharelado/Licenciatura/
  Tecnológico), turno, vagas, **código do curso**.
- **`grades.csv`** (sem cabeçalho): código do curso + metadados do curso +
  **pesos das cinco provas** + blocos repetidos por modalidade, cada bloco com
  `nome_da_modalidade; inscritos; nota_de_corte; bônus; timestamp`. A primeira
  modalidade é sempre "Ampla concorrência"; as demais são as cotas (Lei nº
  12.711/2012 e recortes regionais), com o texto descritivo da modalidade.

Pontos de atenção do esquema:
- **Pesos por curso:** o SISU usa **média ponderada**, não a média simples. Os
  pesos vêm no `grades.csv`, então dá para calcular a nota real da pessoa para
  cada curso. Isso é o diferencial de precisão da Fase 2.
- **Bônus regional:** algumas modalidades aplicam bônus (ex.: 15%) à nota. A
  comparação precisa respeitar isso.
- **Campos vazios:** modalidades sem candidatos têm nota de corte em branco —
  tratar como "sem dado", não como zero.
- **Normalização:** nomes de curso vêm com espaços/caixa irregulares
  ("CIÊNCIAS BIOLÓGICAS "); precisam de limpeza para busca e agrupamento.

### 2.2 ProUni e FIES — regras de elegibilidade (não há "corte")

ProUni e FIES não têm nota de corte por curso: são **regras de elegibilidade**.
Confirmadas em fonte oficial (MEC / gov.br):

**ProUni** (bolsa em instituição privada):
- Média aritmética das 5 áreas do ENEM **≥ 450** e **redação > 0**.
- **Bolsa integral (100%):** renda familiar bruta **per capita ≤ 1,5 salário mínimo**.
- **Bolsa parcial (50%):** renda familiar bruta **per capita ≤ 3 salários mínimos**.
- Além da renda, ao menos uma condição: ensino médio **integralmente em escola
  pública**; ou bolsista integral em escola privada; ou pessoa com deficiência;
  ou professor da rede pública (para licenciatura, sem exigência de renda).

**FIES** (financiamento):
- Mesma nota mínima: média **≥ 450** e **redação > 0** (ENEM a partir de 2010).
- **FIES regular:** renda familiar **per capita ≤ 3 salários mínimos**.
- **FIES Social:** renda **per capita ≤ 0,5 salário mínimo** (CadÚnico), com
  condições mais favoráveis.

> **Importante sobre a renda:** o Radar coleta a renda em **faixas de renda
> familiar total** (Q006, em salários mínimos), não a renda **per capita**. Os
> critérios de ProUni/FIES são **per capita**. Sem o número de pessoas na
> família, não dá para afirmar elegibilidade por renda — só estimar. A Fase 2
> deve: (a) explicar o critério, (b) usar a faixa Q006 como indício, e (c)
> deixar claro que a confirmação depende da renda por pessoa, que o Radar não
> pergunta. Alternativa: adicionar um campo opcional de "pessoas na família" no
> fluxo do assistente, usado só nessa checagem.

As regras mudam a cada edição (salário mínimo, faixas do FIES Social). Versionar
as regras com o **ano de referência** e a fonte, em
`data/inscricoes/regras_prouni_fies.json`.

---

## 3. Modelo de dados proposto (camada "inscrições")

Uma tabela tratada, derivada das fontes de SISU, versionada em
`data/inscricoes/` (Parquet, como a Gold). Uma linha por **curso × modalidade ×
edição**:

| Campo | Tipo | Origem |
|---|---|---|
| `ano` | int | edição do SISU |
| `uf`, `municipio` | texto | `all_courses` / `grades` |
| `ies_nome`, `ies_sigla` | texto | idem |
| `campus` | texto | idem |
| `curso` | texto (normalizado) | idem |
| `grau` | enum (Bacharelado/Licenciatura/Tecnológico) | idem |
| `turno` | enum | idem |
| `vagas` | int | idem |
| `peso_lc`, `peso_ch`, `peso_cn`, `peso_mt`, `peso_redacao` | float | `grades` |
| `modalidade` | texto | `grades` (bloco) |
| `modalidade_tipo` | enum (ampla / cota) | derivado do texto |
| `nota_corte` | float \| nulo | `grades` (bloco) |
| `bonus_pct` | float | `grades` (bloco) |

Decisões a tomar na implementação:
- **Quais anos incluir.** Começar com as 2–3 edições mais recentes disponíveis;
  mais anos aumentam a base versionada.
- **Tamanho.** `grades.csv` de um ano tem ~12 MB em CSV; em Parquet, só com as
  colunas úteis, cai bastante. Fica abaixo do limite do GitHub sem problema.
- **Agrupar modalidades de cota** num conjunto legível (PPI, escola pública,
  renda, PcD) em vez de repassar o texto longo da lei.

---

## 4. Ferramentas novas do assistente (backend)

Seguindo o padrão da Fase 1 (`assistente/ferramentas.py`): cada ferramenta reusa
um serviço oficial, tem parâmetros validados e devolve `Resposta` com evidência.

| Ferramenta | O que faz | Observação |
|---|---|---|
| `cursos_ao_alcance(resultado, filtros)` | Lista cursos cuja nota de corte histórica **≤** a média ponderada da pessoa, por modalidade. Filtros opcionais: UF, grau, nome do curso. | Usa os pesos de cada curso; respeita o bônus de cota. |
| `chance_em_curso(resultado, curso, uf)` | Para um curso específico, mostra a nota de corte por modalidade e compara com a nota da pessoa. | — |
| `elegibilidade_prouni(resultado, renda, escola, pessoas?)` | Aplica as regras do ProUni e diz integral/parcial/não elegível, explicando cada critério. | Renda per capita depende de "pessoas na família". |
| `elegibilidade_fies(resultado, renda, pessoas?)` | Aplica as regras do FIES (regular e Social). | Idem. |
| `explicar_sisu_prouni_fies(termo)` | Verbetes no glossário: o que é cada programa, nota de corte, média ponderada, cotas. | Conteúdo conceitual. |

Novas **intenções** no `provedor.py` (classificador por palavras-chave):
`cursos_ao_alcance`, `chance_em_curso`, `elegibilidade_prouni`,
`elegibilidade_fies`, `explicar_programa`. A intenção `inscricao` da Fase 1 —
que hoje responde "ainda não tenho esses dados" — passa a rotear para essas
ferramentas.

### A mensagem de responsabilidade é parte do produto

Toda resposta que sugerir cursos **precisa** deixar explícito:
- a nota de corte é de **edições passadas** e **muda a cada ano**;
- é **referência**, não garantia de aprovação;
- a classificação final depende da concorrência da edição vigente.

Esse é o mesmo princípio da Fase 1 ("nunca inventa, sempre com evidência"),
agora aplicado a uma decisão de vida real da pessoa — o cuidado tem que ser
maior, não menor.

---

## 5. Interface (frontend)

Reusa o componente de chat da Fase 1 (`componentes/assistente/`). Acréscimos:
- Perguntas rápidas novas: "Em que cursos eu teria passado?", "Eu me enquadro no
  ProUni?", "Qual a nota de corte de Medicina na minha região?".
- Quando a resposta lista cursos, renderizar como **lista/tabela compacta**
  (curso · instituição · modalidade · nota de corte vs. a sua) — provavelmente um
  novo tipo de resposta além de `dado`/`conceito`, com um payload estruturado.
- Campo opcional de **pessoas na família** quando a conversa chega em
  ProUni/FIES, para a checagem de renda per capita.

---

## 6. Pipeline e versionamento

- **Manifesto de fontes:** `etl/fontes_inscricoes.json` (espelha o
  `etl/fontes.json` dos microdados) — URL, ano, licença, `sha256` e data de
  coleta de cada arquivo de origem.
- **ETL:** `etl/inscricoes.py` — baixa/lê os CSVs do SISU, normaliza nomes,
  desdobra os blocos de modalidade em linhas, grava o Parquet em
  `data/inscricoes/`. As regras de ProUni/FIES entram como JSON versionado, não
  como dado derivado.
- **Backend:** `facilita-backend/inscricoes.py` carrega o Parquet em memória (no
  padrão do `gold.py`) e expõe consultas às ferramentas do assistente.
- **Testes:** `tests/test_inscricoes.py` com uma base pequena sintética, como o
  `conftest.py` atual faz para a Gold.

---

## 7. Riscos e decisões em aberto

1. **Renda per capita vs. faixa de renda total.** O maior descompasso. Decidir
   entre estimar (com ressalva) ou pedir "pessoas na família". Recomendação:
   pedir, como campo opcional, só quando a conversa exigir.
2. **Procedência oficial vs. praticidade.** Preferir o portal do MEC pela
   procedência; usar o repositório MIT como apoio. Registrar tudo no manifesto.
3. **Atualização.** As notas de corte são anuais. Definir se a base será
   atualizada a cada edição e documentar que os números são históricos.
4. **Volume versus cobertura.** Quantos anos e se guardar todas as IES ou um
   recorte. Medir o tamanho do Parquet antes de fechar.
5. **Expectativa da pessoa.** "Passar" no SISU depende da concorrência do ano; o
   produto mostra chance histórica. A comunicação tem que segurar essa
   expectativa com clareza.

---

## 8. Fontes consultadas

- MEC — Dados Abertos do SISU e dicionário de dados: <https://dadosabertos.mec.gov.br/sisu>
- MEC — Dados Abertos do FIES (dicionário): <https://dadosabertos.mec.gov.br/fies>
- MEC — ProUni, como funciona e requisitos: <https://prouniportal.mec.gov.br/como-funciona>
- gov.br — Obter bolsa de estudo pelo ProUni (média ≥ 450): <https://www.gov.br/pt-br/servicos/obter-bolsa-de-estudo-do-prouni>
- gov.br — Inscrever-se no SISU: <https://www.gov.br/pt-br/servicos/inscrever-se-no-sisu-sistema-de-selecao-unificada>
- `maiakanegae/sisu-data` (notas de corte 2020–2025, licença MIT): <https://github.com/maiakanegae/sisu-data>
- Base dos Dados — dataset SISU: <https://basedosdados.org/dataset/8326e3d7-9cd2-4144-863f-c380fefef82c>

> Conteúdo das fontes foi parafraseado e resumido para registro; confira os
> editais da edição vigente antes de tratar qualquer regra como definitiva.

# Radar ENEM (Facilita ENEM)

Projeto Aplicado III — Ciência de Dados e IA, UniSENAI 2026/2.

O Radar ENEM mostra ao participante onde a nota dele fica em relação à população
do ENEM e a recortes socioeconômicos (renda, tipo de escola, cor/raça, sexo, UF e
escolaridade da mãe), usando percentil e Z-Score calculados a partir dos
microdados oficiais do INEP (2022 e 2023).

Equipe: Matheus Silva da Cruz (líder), Nicolas André Krause de Mello e João Paulo
Araujo Cappeletti.

## Estrutura

```
etl/                 pipeline PySpark em arquitetura medalhão
  config.py          caminhos, anos, colunas e sessão Spark
  bronze.py          CSV do INEP -> Parquet, sem alterar o conteúdo
  silver.py          seleção de colunas, tipagem e validação com motivo de rejeição
  gold.py            distribuição de notas e estatísticas por recorte (o que a API lê)
  volumetria.py      tamanho e linhas de cada camada -> volumetria.json
  run_pipeline.py    executa as três camadas em ordem e mede o tempo de cada uma
facilita-backend/    API em FastAPI
public/docs/         plano de projeto
```

## Pipeline de dados

1. Baixe os microdados de 2022 e 2023 no portal do INEP e extraia em
   `public/microdados_enem_2022/` e `public/microdados_enem_2023/`
   (não são versionados).
2. Instale e rode (precisa de Java 17 para o Spark):

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r etl/requirements.txt
python etl/run_pipeline.py
```

As camadas são gravadas em `data/` (também não versionada) e o resumo da
execução em `etl/volumetria.json`.

## Back-end

```bash
cd facilita-backend
python3 -m venv venv
. venv/bin/activate
pip install fastapi uvicorn
uvicorn main:app --reload
```

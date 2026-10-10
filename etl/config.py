"""Configuração central do pipeline: caminhos, anos, colunas e sessão Spark."""
from pathlib import Path

from pyspark.sql import SparkSession

RAIZ = Path(__file__).resolve().parent.parent

# Entrada: microdados oficiais do INEP, baixados à mão (não versionados).
ANOS = [2022, 2023]
CSV_BRUTO = {ano: RAIZ / "public" / f"microdados_enem_{ano}" / "DADOS" / f"MICRODADOS_ENEM_{ano}.csv" for ano in ANOS}

# Saída: uma pasta por camada (não versionada, é gerada pelo pipeline).
DADOS = RAIZ / "data"
BRONZE = DADOS / "bronze" / "microdados"
SILVER = DADOS / "silver" / "participantes"
REJEITADOS = DADOS / "silver" / "rejeitados"
GOLD_DISTRIBUICAO = DADOS / "gold" / "distribuicao_notas"
GOLD_ESTATISTICAS = DADOS / "gold" / "estatisticas"
RELATORIO_VOLUMETRIA = RAIZ / "etl" / "volumetria.json"

COMPRESSAO = "zstd"

# Áreas de conhecimento: coluna de nota e coluna de presença no CSV do INEP.
AREAS = {
    "CN": "NU_NOTA_CN",
    "CH": "NU_NOTA_CH",
    "LC": "NU_NOTA_LC",
    "MT": "NU_NOTA_MT",
    "REDACAO": "NU_NOTA_REDACAO",
}
PRESENCAS = ["TP_PRESENCA_CN", "TP_PRESENCA_CH", "TP_PRESENCA_LC", "TP_PRESENCA_MT"]

# Recortes socioeconômicos usados nos módulos comparativos:
# nome do recorte -> coluna de origem no CSV.
RECORTES = {
    "RENDA": "Q006",
    "TIPO_ESCOLA": "TP_ESCOLA",
    "COR_RACA": "TP_COR_RACA",
    "SEXO": "TP_SEXO",
    "UF": "SG_UF_PROVA",
    "ESCOLARIDADE_MAE": "Q002",
}


def criar_spark(nome: str) -> SparkSession:
    """Spark local usando todos os núcleos; memória limitada para caber em notebook comum."""
    return (
        SparkSession.builder.appName(nome)
        .master("local[*]")
        .config("spark.driver.memory", "6g")
        .config("spark.sql.shuffle.partitions", "24")
        .config("spark.sql.session.timeZone", "America/Sao_Paulo")
        .config("spark.ui.showConsoleProgress", "false")
        .getOrCreate()
    )

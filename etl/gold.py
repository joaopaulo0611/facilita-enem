
"""Camada Gold: distribuições de nota pré-agregadas por recorte.

É o que a API consulta. Em vez de milhões de participantes, guarda quantas
pessoas tiraram cada nota em cada grupo (ano, área, recorte, categoria).
Com essas contagens a API calcula o percentil exato de qualquer nota somando
poucas linhas, sem carregar os microdados em memória.
"""
from functools import reduce

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from config import AREAS, COMPRESSAO, GOLD_DISTRIBUICAO, GOLD_ESTATISTICAS, RECORTES, SILVER, criar_spark


def formato_longo(silver: DataFrame) -> DataFrame:
    """Uma linha por participante e área (as 5 provas + a média geral)."""
    areas = {**AREAS, "MEDIA": "NU_NOTA_MEDIA"}
    pares = ", ".join(f"'{nome}', {coluna}" for nome, coluna in areas.items())
    return silver.select(
        "NU_ANO",
        *RECORTES.keys(),
        F.expr(f"stack({len(areas)}, {pares}) as (AREA, NOTA)"),
    )


def por_recorte(longo: DataFrame) -> DataFrame:
    """Empilha a população geral e cada recorte no mesmo formato."""
    partes = [
        longo.select("NU_ANO", "AREA", F.lit("GERAL").alias("RECORTE"), F.lit("TODOS").alias("CATEGORIA"), "NOTA")
    ]
    for recorte in RECORTES:
        partes.append(
            longo.filter(F.col(recorte).isNotNull()).select(
                "NU_ANO", "AREA", F.lit(recorte).alias("RECORTE"), F.col(recorte).cast("string").alias("CATEGORIA"), "NOTA"
            )
        )
    # Cruzamento do módulo de equidade: renda dentro de cada tipo de escola.
    partes.append(
        longo.select(
            "NU_ANO",
            "AREA",
            F.lit("RENDA_X_TIPO_ESCOLA").alias("RECORTE"),
            F.concat_ws("|", "RENDA", F.col("TIPO_ESCOLA").cast("string")).alias("CATEGORIA"),
            "NOTA",
        )
    )
    return reduce(DataFrame.unionByName, partes)


def executar(spark) -> tuple[int, int]:
    base = por_recorte(formato_longo(spark.read.parquet(str(SILVER))))
    grupo = ["NU_ANO", "AREA", "RECORTE", "CATEGORIA"]

    # Distribuição: quantos participantes do grupo tiraram exatamente cada nota.
    (
        base.groupBy(*grupo, "NOTA")
        .agg(F.count("*").alias("QTD"))
        .repartition(1, "NU_ANO")
        .sortWithinPartitions(*grupo, "NOTA")  # valores vizinhos repetidos comprimem melhor
        .write.mode("overwrite")
        .partitionBy("NU_ANO")
        .option("compression", COMPRESSAO)
        .parquet(str(GOLD_DISTRIBUICAO))
    )

    # Estatísticas prontas por grupo: base do Z-Score (média e desvio-padrão).
    (
        base.groupBy(*grupo)
        .agg(
            F.count("*").alias("N"),
            F.round(F.avg("NOTA"), 2).alias("MEDIA"),
            F.round(F.stddev_pop("NOTA"), 2).alias("DESVIO_PADRAO"),
            F.min("NOTA").alias("MINIMO"),
            F.expr("percentile(NOTA, 0.25)").alias("P25"),
            F.expr("percentile(NOTA, 0.50)").alias("MEDIANA"),
            F.expr("percentile(NOTA, 0.75)").alias("P75"),
            F.max("NOTA").alias("MAXIMO"),
        )
        .coalesce(1)
        .sortWithinPartitions(*grupo)
        .write.mode("overwrite")
        .option("compression", COMPRESSAO)
        .parquet(str(GOLD_ESTATISTICAS))
    )

    distribuicao = spark.read.parquet(str(GOLD_DISTRIBUICAO)).count()
    estatisticas = spark.read.parquet(str(GOLD_ESTATISTICAS)).count()
    print(f"[gold] distribuição: {distribuicao:,} linhas | estatísticas: {estatisticas:,} grupos")
    return distribuicao, estatisticas


if __name__ == "__main__":
    spark = criar_spark("enem-gold")
    executar(spark)
    spark.stop()


"""Camada Silver: seleção de colunas, tipagem e validação com motivo de rejeição.

Das 76 colunas do INEP ficam só as que o Radar ENEM consulta. Cada linha
recebe um motivo de rejeição (ou nulo): as válidas vão para `participantes`,
as demais para `rejeitados`, para que nenhum registro suma sem explicação.
"""
from pyspark.sql import functions as F

from config import AREAS, BRONZE, COMPRESSAO, PRESENCAS, RECORTES, REJEITADOS, SILVER, criar_spark


def transformar(bronze):
    notas = [F.col(coluna).cast("double").alias(coluna) for coluna in AREAS.values()]
    recortes = [F.col(coluna).alias(nome) for nome, coluna in RECORTES.items()]
    df = bronze.select(
        F.col("NU_INSCRICAO").cast("long").alias("NU_INSCRICAO"),
        F.col("NU_ANO").cast("int").alias("NU_ANO"),
        F.col("IN_TREINEIRO").cast("int").alias("IN_TREINEIRO"),
        *[F.col(c).cast("int").alias(c) for c in PRESENCAS],
        F.col("TP_STATUS_REDACAO").cast("int").alias("TP_STATUS_REDACAO"),
        *notas,
        *recortes,
    )

    presente_em_tudo = F.lit(True)
    for coluna in PRESENCAS:
        presente_em_tudo = presente_em_tudo & (F.col(coluna) == 1)
    alguma_nota_nula = F.lit(False)
    for coluna in AREAS.values():
        alguma_nota_nula = alguma_nota_nula | F.col(coluna).isNull()
    nota_fora_da_escala = F.lit(False)
    for coluna in AREAS.values():
        nota_fora_da_escala = nota_fora_da_escala | (F.col(coluna) < 0) | (F.col(coluna) > 1000)

    # A primeira regra que falhar define o motivo (ordem = prioridade).
    # Treineiro não é rejeitado: basta ter feito as 4 provas e a redação.
    motivo = (
        F.when(~presente_em_tudo, "AUSENTE_OU_ELIMINADO")
        .when(F.col("TP_STATUS_REDACAO") == 4, "REDACAO_EM_BRANCO")
        .when(alguma_nota_nula, "NOTA_AUSENTE")
        .when(nota_fora_da_escala, "NOTA_FORA_DA_ESCALA")
        .when(F.col("RENDA").isNull(), "SEM_QUESTIONARIO")
    )
    df = df.withColumn("MOTIVO_REJEICAO", motivo)

    # Média simples das cinco notas, com uma casa, como o participante vê.
    soma = sum(F.col(c) for c in AREAS.values())
    return df.withColumn("NU_NOTA_MEDIA", F.round(soma / len(AREAS), 1))


def executar(spark) -> tuple[int, int]:
    df = transformar(spark.read.parquet(str(BRONZE)))

    colunas_validas = ["NU_INSCRICAO", "NU_ANO", "IN_TREINEIRO", *AREAS.values(), "NU_NOTA_MEDIA", *RECORTES.keys()]
    (
        df.filter(F.col("MOTIVO_REJEICAO").isNull())
        .select(*colunas_validas)
        .repartition(4, "NU_ANO")  # poucos arquivos grandes por ano
        .write.mode("overwrite")
        .partitionBy("NU_ANO")
        .option("compression", COMPRESSAO)
        .parquet(str(SILVER))
    )
    (
        df.filter(F.col("MOTIVO_REJEICAO").isNotNull())
        .select("NU_INSCRICAO", "NU_ANO", "MOTIVO_REJEICAO")
        .coalesce(2)
        .write.mode("overwrite")
        .partitionBy("NU_ANO")
        .option("compression", COMPRESSAO)
        .parquet(str(REJEITADOS))
    )

    validos = spark.read.parquet(str(SILVER)).count()
    rejeitados = spark.read.parquet(str(REJEITADOS))
    print(f"[silver] válidos: {validos:,}")
    rejeitados.groupBy("NU_ANO", "MOTIVO_REJEICAO").count().orderBy("NU_ANO", F.desc("count")).show(truncate=False)
    return validos, rejeitados.count()


if __name__ == "__main__":
    spark = criar_spark("enem-silver")
    executar(spark)
    spark.stop()
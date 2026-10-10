"""Camada Bronze: CSV bruto do INEP -> Parquet, sem alterar o conteúdo.

Tudo entra como texto. A Bronze é a cópia fiel da origem em formato colunar:
se uma regra da Silver mudar, reprocessamos daqui sem reler os CSVs.
"""
from pyspark.sql import functions as F

from config import ANOS, BRONZE, COMPRESSAO, CSV_BRUTO, criar_spark


def executar(spark) -> int:
    total = 0
    for ano in ANOS:
        origem = CSV_BRUTO[ano]
        df = (
            spark.read.option("header", True)
            .option("sep", ";")
            .option("encoding", "ISO-8859-1")  # o INEP publica em Latin-1
            .option("inferSchema", False)  # tipagem é responsabilidade da Silver
            .csv(str(origem))
            # Metadados de rastreabilidade: de onde e quando cada linha veio.
            .withColumn("_arquivo_origem", F.lit(origem.name))
            .withColumn("_ingerido_em", F.current_timestamp())
        )
        # Sobrescreve só a partição do ano: reexecutar não duplica dados.
        (
            df.write.mode("overwrite")
            .option("compression", COMPRESSAO)
            .parquet(str(BRONZE / f"NU_ANO={ano}"))
        )
        linhas = spark.read.parquet(str(BRONZE / f"NU_ANO={ano}")).count()
        print(f"[bronze] {ano}: {linhas:,} linhas")
        total += linhas
    return total


if __name__ == "__main__":
    spark = criar_spark("enem-bronze")
    executar(spark)
    spark.stop()

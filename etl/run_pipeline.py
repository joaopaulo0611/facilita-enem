"""Executa o pipeline completo, na ordem, medindo o tempo de cada camada.

Uso: python etl/run_pipeline.py
"""
import time

import bronze
import gold
import silver
import volumetria
from config import criar_spark


def main() -> None:
    spark = criar_spark("enem-pipeline")
    spark.sparkContext.setLogLevel("ERROR")
    tempos = {}
    for nome, etapa in (("bronze", bronze), ("silver", silver), ("gold", gold)):
        inicio = time.perf_counter()
        etapa.executar(spark)
        tempos[nome] = round(time.perf_counter() - inicio, 1)
        print(f"[{nome}] concluída em {tempos[nome]} s")
    volumetria.imprimir(volumetria.medir(spark, tempos))
    spark.stop()


if __name__ == "__main__":
    main()

import json

from pathlib import Path

from config import (

    BRONZE,

    CSV_BRUTO,

    GOLD_DISTRIBUICAO,

    GOLD_ESTATISTICAS,

    REJEITADOS,

    RELATORIO_VOLUMETRIA,

    SILVER,

    criar_spark,

)


def tamanho_bytes(caminho: Path) -> int:

    if caminho.is_file():

        return caminho.stat().st_size

    return sum(f.stat().st_size for f in caminho.rglob("*.parquet"))


def medir(spark, tempos: dict | None = None) -> dict:

    camadas = {

        "bronze": BRONZE,

        "silver_participantes": SILVER,

        "silver_rejeitados": REJEITADOS,

        "gold_distribuicao": GOLD_DISTRIBUICAO,

        "gold_estatisticas": GOLD_ESTATISTICAS,

    }

    bruto_bytes = sum(tamanho_bytes(c) for c in CSV_BRUTO.values())

    relatorio = {"csv_bruto": {"bytes": bruto_bytes, "arquivos": len(CSV_BRUTO)}}

    for nome, caminho in camadas.items():

        df = spark.read.parquet(str(caminho))

        tamanho = tamanho_bytes(caminho)

        relatorio[nome] = {

            "bytes": tamanho,

            "linhas": df.count(),

            "colunas": len(df.columns),

            "arquivos": len(list(caminho.rglob("*.parquet"))),

            "percentual_do_csv": round(100 * tamanho / bruto_bytes, 3),

        }

    if tempos:

        relatorio["tempo_segundos"] = tempos

    RELATORIO_VOLUMETRIA.write_text(json.dumps(relatorio, indent=2, ensure_ascii=False) + "\n")

    return relatorio


def imprimir(relatorio: dict) -> None:

    print(f"\n{'camada':<24}{'tamanho (MB)':>14}{'linhas':>14}{'% do CSV':>10}")

    print(f"{'csv_bruto':<24}{relatorio['csv_bruto']['bytes'] / 1e6:>14,.1f}{'':>14}{100:>10.1f}")

    for nome, m in relatorio.items():

        if nome in ("csv_bruto", "tempo_segundos"):

            continue

        print(f"{nome:<24}{m['bytes'] / 1e6:>14,.1f}{m['linhas']:>14,}{m['percentual_do_csv']:>10.3f}")


if __name__ == "__main__":

    spark = criar_spark("enem-volumetria")

    imprimir(medir(spark))

    spark.stop()

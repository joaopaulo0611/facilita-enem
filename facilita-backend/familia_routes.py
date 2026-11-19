"""Módulo família: quanto a renda da família e a escolaridade da mãe mudam sua posição?

Compara a posição do participante no Brasil todo com a posição dentro de quem
tem a mesma renda familiar, dentro de quem tem a mesma escolaridade da mãe, e
dentro do cruzamento dos dois (mesma renda E mesma escolaridade da mãe). A ideia
é mostrar o quanto esses marcadores familiares deslocam a régua: um mesmo ponto
rende percentis diferentes conforme o grupo de comparação.
"""
from enum import Enum
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from dependencias import exigir_tamanho_minimo, obter_gold
from gold import Gold
from rotulos import AREAS, ESCOLARIDADE_MAE, RENDA

familia_router = APIRouter(prefix="/api/modulos", tags=["modulo familia"])

Area = Enum("Area", {area: area for area in [*AREAS, "MEDIA"]}, type=str)
Renda = Enum("Renda", {codigo: codigo for codigo in RENDA}, type=str)
EscolaridadeMae = Enum("EscolaridadeMae", {codigo: codigo for codigo in ESCOLARIDADE_MAE}, type=str)


@familia_router.get("/familia")
def familia(
    nota: Annotated[float, Query(ge=0, le=1000)],
    renda: Renda,
    escolaridade_mae: EscolaridadeMae,
    area: Area = Area.MEDIA,
    gold: Gold = Depends(obter_gold),
):
    brasil = gold.grupo(area.value)

    def posicao(grupo) -> dict:
        return {
            "percentil": grupo.percentil(nota),
            "zscore": grupo.zscore(nota),
            "media": round(grupo.media, 1),
            "participantes": grupo.n,
        }

    grupo_renda = gold.grupo(area.value, "RENDA", renda.value)
    exigir_tamanho_minimo(grupo_renda, f"com renda {RENDA[renda.value]!r}")
    grupo_mae = gold.grupo(area.value, "ESCOLARIDADE_MAE", escolaridade_mae.value)
    exigir_tamanho_minimo(grupo_mae, f"com escolaridade da mãe {ESCOLARIDADE_MAE[escolaridade_mae.value]!r}")
    grupo_ambos = gold.grupo(area.value, "RENDA_X_ESCOLARIDADE_MAE", f"{renda.value}|{escolaridade_mae.value}")
    exigir_tamanho_minimo(grupo_ambos, "com essa renda e essa escolaridade da mãe")

    return {
        "anos": gold.anos,
        "area": area.value,
        "nota": nota,
        "renda": {"codigo": renda.value, "nome": RENDA[renda.value]},
        "escolaridade_mae": {"codigo": escolaridade_mae.value, "nome": ESCOLARIDADE_MAE[escolaridade_mae.value]},
        "brasil": posicao(brasil),
        "por_renda": posicao(grupo_renda),
        "por_escolaridade_mae": posicao(grupo_mae),
        "por_renda_e_escolaridade_mae": posicao(grupo_ambos),
    }

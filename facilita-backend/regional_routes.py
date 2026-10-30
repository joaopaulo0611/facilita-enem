"""Módulo regional: a mesma nota vale o mesmo em todo o Brasil?

Compara a posição do participante entre quem fez a prova no mesmo estado
com a posição no Brasil todo, e mostra onde essa nota ficaria em cada UF.
A UF é a do local de prova (SG_UF_PROVA), não a de residência.
"""
from enum import Enum
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from dependencias import exigir_tamanho_minimo, obter_gold
from gold import N_MINIMO, Gold
from rotulos import AREAS, UF

regional_router = APIRouter(prefix="/api/modulos", tags=["modulo regional"])

Sigla = Enum("Sigla", {sigla: sigla for sigla in UF}, type=str)
Area = Enum("Area", {area: area for area in [*AREAS, "MEDIA"]}, type=str)


@regional_router.get("/regional")
def regional(
    nota: Annotated[float, Query(ge=0, le=1000)],
    uf: Sigla,
    area: Area = Area.MEDIA,
    gold: Gold = Depends(obter_gold),
):
    estado = gold.grupo(area.value, "UF", uf.value)
    exigir_tamanho_minimo(estado, f"de {uf.value}")
    brasil = gold.grupo(area.value)

    ranking = []
    for sigla in gold.categorias(area.value, "UF"):
        grupo = gold.grupo(area.value, "UF", sigla)
        if grupo.n >= N_MINIMO:
            ranking.append({"uf": sigla, "nome": UF[sigla], "percentil": grupo.percentil(nota), "media": round(grupo.media, 1)})
    ranking.sort(key=lambda linha: linha["percentil"], reverse=True)

    return {
        "anos": gold.anos,
        "area": area.value,
        "nota": nota,
        "uf": uf.value,
        "nome_uf": UF[uf.value],
        "estado": {"percentil": estado.percentil(nota), "zscore": estado.zscore(nota), "media": round(estado.media, 1), "participantes": estado.n},
        "brasil": {"percentil": brasil.percentil(nota), "zscore": brasil.zscore(nota), "media": round(brasil.media, 1), "participantes": brasil.n},
        "ranking": ranking,
    }

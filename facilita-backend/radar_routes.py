"""Radar geral: posição do participante em cada área e na média, no Brasil todo."""
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from dependencias import obter_gold
from gold import Gold
from rotulos import AREAS, RECORTES

radar_router = APIRouter(prefix="/api", tags=["radar"])

Nota = Annotated[float, Query(ge=0, le=1000, description="Nota de 0 a 1000")]

# Faixas do histograma da média geral (quase ninguém fica fora delas).
HISTOGRAMA_INICIO, HISTOGRAMA_FIM, HISTOGRAMA_LARGURA = 300, 850, 25


@radar_router.get("/metadados")
def metadados(gold: Gold = Depends(obter_gold)):
    """Anos que formam a base e opções de cada campo do formulário."""
    return {
        "anos": gold.anos,
        "areas": AREAS,
        "recortes": {nome: [{"codigo": c, "nome": n} for c, n in opcoes.items()] for nome, opcoes in RECORTES.items()},
        "participantes": gold.grupo("MEDIA").n,
    }


@radar_router.get("/radar")
def radar(
    lc: Nota,
    ch: Nota,
    cn: Nota,
    mt: Nota,
    redacao: Nota,
    gold: Gold = Depends(obter_gold),
):
    notas = {"LC": lc, "CH": ch, "CN": cn, "MT": mt, "REDACAO": redacao}

    def posicao(area: str, nota: float) -> dict:
        grupo = gold.grupo(area)
        return {
            "nota": nota,
            "percentil": grupo.percentil(nota),
            "zscore": grupo.zscore(nota),
            "media_participantes": round(grupo.media, 1),
            "diferenca": round(nota - grupo.media, 1),
        }

    media = round(sum(notas.values()) / len(notas), 1)
    geral = gold.grupo("MEDIA")
    return {
        "anos": gold.anos,
        "participantes": geral.n,
        "media_geral": posicao("MEDIA", media),
        "areas": [{"area": area, "nome": AREAS[area], **posicao(area, nota)} for area, nota in notas.items()],
        "histograma": {
            "inicio": HISTOGRAMA_INICIO,
            "largura": HISTOGRAMA_LARGURA,
            "contagens": geral.histograma(HISTOGRAMA_INICIO, HISTOGRAMA_FIM, HISTOGRAMA_LARGURA),
        },
    }

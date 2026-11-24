"""Rotas do assistente do Radar ENEM (Fase 1).

Duas rotas:
- GET  /api/assistente/sugestoes  → perguntas rápidas para começar a conversa.
- POST /api/assistente/pergunta    → a pergunta (e, opcional, o resultado do radar
  que a pessoa já calculou) e devolve a resposta do assistente.

A lógica fica toda no pacote `assistente/`; aqui é só a casca HTTP. A pergunta é
tratada como dado, e o resultado enviado pelo front é opcional — sem ele, as
ferramentas que dependem das notas pedem para a pessoa calcular o radar antes.
"""
from __future__ import annotations

from functools import lru_cache

from fastapi import APIRouter
from pydantic import BaseModel, Field

from assistente.orquestrador import SUGESTOES_INICIAIS, Orquestrador

assistente_router = APIRouter(prefix="/api/assistente", tags=["assistente"])


@lru_cache(maxsize=1)
def _orquestrador() -> Orquestrador:
    """Um orquestrador só, reaproveitado entre requisições (o provedor é sem estado)."""
    return Orquestrador()


class Pergunta(BaseModel):
    """Corpo do POST: a pergunta e, se houver, o resultado já calculado no radar."""
    pergunta: str = Field(..., min_length=1, max_length=2000)
    # Mesmo formato que /api/radar devolve; opcional. Sem ele, o assistente pede
    # para a pessoa calcular o radar antes de interpretar as notas.
    resultado: dict | None = None


@assistente_router.get("/sugestoes")
def sugestoes():
    """Perguntas rápidas que a pessoa pode tocar para começar."""
    return {"sugestoes": list(SUGESTOES_INICIAIS)}


@assistente_router.post("/pergunta")
def pergunta(corpo: Pergunta):
    resposta = _orquestrador().responde(corpo.pergunta, corpo.resultado)
    return resposta.to_dict()

"""Recursos compartilhados pelas rotas: a Gold carregada e as validações comuns."""
from functools import lru_cache

from fastapi import HTTPException

from gold import N_MINIMO, Gold, Grupo


@lru_cache(maxsize=1)
def obter_gold() -> Gold:
    """Carrega a Gold uma vez só, na primeira requisição."""
    return Gold.carregar()


def exigir_tamanho_minimo(grupo: Grupo, descricao: str) -> None:
    if grupo.n < N_MINIMO:
        raise HTTPException(
            422,
            f"O grupo {descricao} tem só {grupo.n} participantes; "
            f"o mínimo para comparar é {N_MINIMO}.",
        )

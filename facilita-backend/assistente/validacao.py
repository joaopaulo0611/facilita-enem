"""Validação e proteção do assistente.

As permissões ficam AQUI, no código, não no texto da pergunta. A camada
conversacional nunca recebe SQL, Python, caminho de arquivo ou nome de
ferramenta livres. A pergunta é tratada como DADO, nunca como instrução.
"""
from __future__ import annotations

import re

MAX_PERGUNTA = 500
MIN_PERGUNTA = 2

# Padrões de tentativa de injeção/abuso. Não travam a conversa: marcam a
# pergunta para o orquestrador responder com a recusa padrão.
_INJECAO = re.compile(
    r"(ignore\s+(as\s+)?(instru|regras|anteriores)|esque[çc]a\s+as\s+instru|"
    r"voc[êe]\s+agora\s+é|aja\s+como|finja\s+ser|system\s+prompt|prompt\s+do\s+sistema|"
    r"revele\s+(suas|as)\s+instru|mostre\s+o\s+prompt|api[_\s-]?key|chave\s+de\s+api|"
    r"senha|credenc|token\s+secreto|\.env|secrets|"
    r"\bSELECT\b.+\bFROM\b|\bDROP\b|\bDELETE\b|\bos\.|subprocess|eval\(|exec\(|import\s+os|"
    r"/etc/|\.\./|sistema\s+de\s+arquivos)",
    re.IGNORECASE | re.DOTALL,
)


class EntradaInvalida(ValueError):
    """Pergunta vazia, longa demais ou malformada."""


def sanitiza_pergunta(texto: str | None) -> str:
    """Normaliza e valida o tamanho da pergunta. Não interpreta o conteúdo."""
    if texto is None:
        raise EntradaInvalida("Escreva uma pergunta.")
    t = " ".join(str(texto).split())  # colapsa espaços e quebras de linha
    if len(t) < MIN_PERGUNTA:
        raise EntradaInvalida("Escreva uma pergunta.")
    if len(t) > MAX_PERGUNTA:
        raise EntradaInvalida(f"Pergunta longa demais (máximo {MAX_PERGUNTA} caracteres).")
    return t


def parece_injecao(texto: str) -> bool:
    """True se a pergunta tenta manipular o assistente, extrair segredos ou rodar código."""
    return bool(_INJECAO.search(texto or ""))

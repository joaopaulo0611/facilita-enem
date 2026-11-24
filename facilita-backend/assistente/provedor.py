"""Provedor do assistente: o 'cérebro' que classifica a intenção.

Fica desacoplado do resto, atrás da interface `classifica`. Trocar o provedor
(simulado → LLM real, no futuro) não exige mexer em ferramentas, orquestrador
nem contratos.

FASE 1: só o `ProvedorSimulado` existe — determinístico, local, SEM custo. Ele
mapeia a pergunta a uma INTENÇÃO (e parâmetros) por palavras-chave. Não gera
texto livre: devolve uma intenção estruturada que o orquestrador transforma em
chamada de ferramenta.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Protocol

from .ferramentas import NOME_AREAS

# Intenções reconhecidas na Fase 1 (cada uma atendida por uma ferramenta controlada).
INTENCOES = (
    "ajuda",                 # "o que você faz", "como funciona"
    "inscricao",             # "em que curso/faculdade posso entrar" (Fase 2 ainda não disponível)
    "limitacoes",            # "quais as limitações dos dados"
    "interpretar_percentil", # "como interpretar meu percentil"
    "resumo_resultado",      # "resuma meu resultado", "como fui"
    "posicao_area",          # "como estou em matemática"
    "explicar_indicador",    # "o que é X", "como calcula X"
    "desconhecida",          # nada reconhecido -> "não sei"
)


@dataclass(frozen=True)
class Intencao:
    nome: str
    parametros: dict = field(default_factory=dict)


def _sem_acento(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


class Provedor(Protocol):
    nome: str

    def classifica(self, pergunta: str) -> Intencao: ...


class ProvedorSimulado:
    """Classificador de intenção determinístico por palavras-chave (Fase 1, sem custo)."""

    nome = "simulado-local"

    # (padrão regex sobre o texto sem acento e em minúsculas, nome da intenção).
    # A ordem importa: a primeira regra que casa vence, da mais específica à mais geral.
    _REGRAS = [
        (r"\b(o que (voce|vc) faz|como (voce|vc) funciona|o que posso perguntar|em que.*ajuda|(me )?ajuda\b|pra que (voce|serve))", "ajuda"),
        (r"\b(curso|faculdade|universidade|federal|medicina|direito|engenharia|sisu|prouni|fies|passar|entrar|me inscrever|inscricao|vaga|nota de corte|carreira|profissao)", "inscricao"),
        (r"\b(limita|restri|confia|margem de erro|precis(a|ao)|os dados valem|de onde vem)", "limitacoes"),
        (r"\b(interpret|entender|o que significa).*percentil|percentil.*(interpret|significa|quer dizer)", "interpretar_percentil"),
        (r"\b(resum|panorama|como (eu )?fui|como foi meu|meu desempenho|minha posicao geral|me saí|como estou no geral)", "resumo_resultado"),
        (r"\b(como (estou|fui|me saí)|minha nota|meu desempenho|posicao).*(em|na|de)\b", "posicao_area"),
        (r"\b(o que (e|significa)|defini|como.*(calcul|interpret)|explic|quer dizer)", "explicar_indicador"),
    ]

    def classifica(self, pergunta: str) -> Intencao:
        p = _sem_acento((pergunta or "").lower().strip())
        for padrao, nome in self._REGRAS:
            if re.search(padrao, p):
                return Intencao(nome=nome, parametros=self._parametros(nome, p, pergunta))
        # Menção direta a uma área ("matemática", "redação") também pede a posição na área.
        area = self._area_citada(p)
        if area:
            return Intencao(nome="posicao_area", parametros={"area": area})
        return Intencao(nome="desconhecida")

    def _parametros(self, nome: str, p: str, pergunta_original: str) -> dict:
        if nome == "explicar_indicador":
            return {"termo": pergunta_original}
        if nome == "posicao_area":
            return {"area": self._area_citada(p)}
        return {}

    def _area_citada(self, p: str) -> str | None:
        """Descobre a qual área (código) a pergunta se refere, por nome ou sinônimo."""
        apelidos = {
            "LC": ("linguagen", "portugues", "ingles", "espanhol", "lingua"),
            "CH": ("humana", "historia", "geografia", "filosofia", "sociologia"),
            "CN": ("natureza", "biologia", "fisica", "quimica"),
            "MT": ("matematica", "exatas", "calculo"),
            "REDACAO": ("redacao", "texto", "dissertacao"),
        }
        for codigo, termos in apelidos.items():
            nome = _sem_acento(NOME_AREAS[codigo].lower())
            if nome in p or any(t in p for t in termos):
                return codigo
        return None

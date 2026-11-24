"""Estrutura das respostas do assistente.

Toda resposta carrega o texto e, quando apresenta número, a EVIDÊNCIA que o
sustenta (fonte, período, abrangência, recorte). Isso torna testável a regra de
que o assistente não inventa dados: se há número, há evidência rastreável; se
não há dado, o tipo da resposta diz isso.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum


class Tipo(str, Enum):
    """Natureza da resposta — diferencia conceito de número e marca ausência de dado/erro."""
    DADO = "dado"              # número real vindo de uma ferramenta/serviço oficial
    CONCEITO = "conceito"      # explicação conceitual (glossário/metodologia), sem número calculado
    SEM_DADOS = "sem_dados"    # não há dado suficiente para responder com segurança
    ERRO = "erro"              # falha controlada (ex.: resultado ausente)


@dataclass(frozen=True)
class Evidencia:
    """Procedência de um número. Campos vazios quando não se aplicam."""
    ferramenta: str = ""
    fonte: str = ""
    periodo: str = ""
    abrangencia: str = ""
    recorte: str = ""
    limitacoes: str = ""

    def preenchida(self) -> bool:
        return any(asdict(self).values())


@dataclass(frozen=True)
class Resposta:
    """O que o orquestrador devolve à interface, pronto para virar JSON."""
    tipo: Tipo
    texto: str                              # markdown leve (negrito, listas)
    evidencia: Evidencia | None = None
    sugestoes: tuple[str, ...] = ()         # próximas perguntas sugeridas

    def to_dict(self) -> dict:
        return {
            "tipo": self.tipo.value,
            "texto": self.texto,
            "evidencia": asdict(self.evidencia) if self.evidencia and self.evidencia.preenchida() else None,
            "sugestoes": list(self.sugestoes),
        }

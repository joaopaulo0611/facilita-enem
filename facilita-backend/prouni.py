"""Elegibilidade ao ProUni a partir das notas, do perfil e do número de pessoas da família.

O ProUni não tem nota de corte por curso nesta base: tem regras de elegibilidade,
versionadas em data/inscricoes/regras_prouni_fies.json (ver docs/FASE2_INSCRICOES.md):
- média aritmética das 5 provas de pelo menos 450 e redação acima de zero;
- renda familiar **por pessoa** de até 1,5 salário mínimo (bolsa integral) ou 3 (parcial);
- ensino médio em escola pública (ou bolsista integral em escola privada, pessoa com
  deficiência ou professor da rede pública, casos que o Radar não pergunta).

O Radar sabe a renda familiar **total**, em faixas (Q006). Com o número de pessoas, a
faixa total vira uma faixa por pessoa: de 3 a 4 SM em 4 pessoas dá de 0,75 a 1 SM por
pessoa. Quando essa faixa cruza um limite, o resultado é "depende do valor exato".
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from math import inf
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
REGRAS = RAIZ / "data" / "inscricoes" / "regras_prouni_fies.json"

ESCOLA_PUBLICA = "2"

# Q006: faixa de renda familiar total, em salários mínimos (mínimo, máximo).
FAIXAS_RENDA = {
    "A": (0, 0), "B": (0, 1), "C": (1, 1.5), "D": (1.5, 2), "E": (2, 2.5), "F": (2.5, 3),
    "G": (3, 4), "H": (4, 5), "I": (5, 6), "J": (6, 7), "K": (7, 8), "L": (8, 9),
    "M": (9, 10), "N": (10, 12), "O": (12, 15), "P": (15, 20), "Q": (20, inf),
}

# Situação da renda por pessoa em relação aos limites do ProUni.
INTEGRAL = "integral"                  # cabe com certeza na bolsa integral
PARCIAL = "parcial"                    # cabe com certeza na parcial, não na integral
INTEGRAL_OU_PARCIAL = "integral_ou_parcial"  # cruza o limite da integral, mas fica dentro da parcial
PARCIAL_OU_NAO = "parcial_ou_nao"      # cruza o limite da parcial
ACIMA = "acima"                        # passa do limite da parcial com certeza


@lru_cache(maxsize=1)
def regras(caminho: Path = REGRAS) -> dict:
    return json.loads(caminho.read_text(encoding="utf-8"))


@dataclass(frozen=True)
class Avaliacao:
    """O que dá para dizer sobre o ProUni com o que o Radar sabe da pessoa."""
    media: float
    redacao: float
    nota_ok: bool
    escola_publica: bool | None        # None: a pessoa não informou a escola
    faixa_por_pessoa: tuple[float, float] | None  # None: falta a renda ou o número de pessoas
    renda: str | None                  # uma das situações acima, ou None
    limite_integral: float
    limite_parcial: float
    nota_minima: float
    ano_referencia: int


def renda_por_pessoa(codigo_renda: str, pessoas: int) -> tuple[float, float]:
    minimo, maximo = FAIXAS_RENDA[codigo_renda]
    return minimo / pessoas, maximo / pessoas


def situacao_da_renda(faixa: tuple[float, float], integral: float, parcial: float) -> str:
    """Compara a faixa de renda por pessoa com os limites. O limite em si ainda conta ("até 1,5")."""
    minimo, maximo = faixa
    if maximo <= integral:
        return INTEGRAL
    if minimo > parcial:
        return ACIMA
    if maximo <= parcial:
        return PARCIAL if minimo > integral else INTEGRAL_OU_PARCIAL
    return PARCIAL_OU_NAO


def avaliar(notas: dict[str, float], escola: str | None, renda: str | None, pessoas: int | None) -> Avaliacao:
    """Aplica as regras do ProUni. `notas` no formato do /api/radar ({"LC": 650, ..., "REDACAO": 740})."""
    r = regras()
    prouni = r["prouni"]
    integral = prouni["bolsa_integral"]["renda_per_capita_max_sm"]
    parcial = prouni["bolsa_parcial"]["renda_per_capita_max_sm"]
    nota_minima = prouni["nota_minima_media"]

    media = sum(notas.values()) / len(notas)
    redacao = notas["REDACAO"]
    nota_ok = media >= nota_minima and (redacao > 0 or not prouni["redacao_maior_que_zero"])

    faixa = renda_por_pessoa(renda, pessoas) if renda in FAIXAS_RENDA and pessoas else None
    return Avaliacao(
        media=media,
        redacao=redacao,
        nota_ok=nota_ok,
        escola_publica=None if not escola else escola == ESCOLA_PUBLICA,
        faixa_por_pessoa=faixa,
        renda=situacao_da_renda(faixa, integral, parcial) if faixa else None,
        limite_integral=integral,
        limite_parcial=parcial,
        nota_minima=nota_minima,
        ano_referencia=r["ano_referencia"],
    )

"""Notas de corte do SISU em memória, para o assistente responder "em que cursos eu teria passado".

Lê data/inscricoes/sisu.parquet, gerado por etl/inscricoes.py: uma linha por
curso × modalidade, com os pesos das provas, as notas mínimas e a nota de corte.
A base é pequena (alguns MB em memória) e só é carregada na primeira pergunta
sobre cursos.

Como a comparação funciona:
- a **média ponderada** da pessoa, com os pesos de cada curso, é comparada com a
  nota de corte, depois de conferir as notas mínimas por prova e a média mínima;
- modalidade sem nota de corte (sem candidatos) nunca conta como "ao alcance";
- sem perfil, só a **ampla concorrência** entra; com o perfil do formulário
  (escola, renda e cor ou raça), entram também as cotas da **Lei de Cotas**
  (Lei nº 12.711/2012) a que a pessoa tem direito;
- ficam de fora as cotas para quilombolas e pessoas com deficiência (o Radar não
  pergunta) e as ações afirmativas próprias de cada instituição (regras variam).
  Nenhuma modalidade da Lei de Cotas tem bônus na base de 2024.
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
SISU = RAIZ / "data" / "inscricoes" / "sisu.parquet"

# Código da área no /api/radar -> sufixo da coluna na base do SISU.
AREAS = {"CN": "cn", "CH": "ch", "LC": "lc", "MT": "mt", "REDACAO": "redacao"}
TEXTO = ["curso", "grau", "turno", "campus", "municipio", "uf", "ies_nome", "ies_sigla", "modalidade", "modalidade_tipo", "modalidade_grupo"]
AMPLA = "Ampla concorrência"
LEI_DE_COTAS = "Lei de Cotas"

# Códigos do formulário (os mesmos do INEP).
ESCOLA_PUBLICA = "2"            # TP_ESCOLA
RENDA_ATE_1_SM = {"A", "B"}     # Q006: nenhuma renda ou até 1 salário mínimo (renda familiar TOTAL)
PRETOS_PARDOS = {"2", "3"}      # TP_COR_RACA
INDIGENAS = {"5"}


@dataclass(frozen=True)
class Perfil:
    """O que o formulário do Radar diz sobre a pessoa e importa para as cotas."""
    escola: str | None = None     # código de TP_ESCOLA
    renda: str | None = None      # código de Q006 (faixa de renda familiar total)
    cor_raca: str | None = None   # código de TP_COR_RACA

    @classmethod
    def dos_campos(cls, campos: dict | None) -> Perfil:
        campos = campos or {}
        return cls(
            escola=campos.get("tipo_escola") or None,
            renda=campos.get("renda") or None,
            cor_raca=campos.get("cor_raca") or None,
        )

    @property
    def completo(self) -> bool:
        return bool(self.escola and self.renda and self.cor_raca)

    @property
    def escola_publica(self) -> bool:
        return self.escola == ESCOLA_PUBLICA

    @property
    def renda_ate_1_sm(self) -> bool:
        # Renda TOTAL de até 1 SM garante renda POR PESSOA de até 1 SM, qualquer que seja a família.
        return self.renda in RENDA_ATE_1_SM


@dataclass(frozen=True)
class Consulta:
    """Resultado de uma busca: os cursos ao alcance (já ordenados) e o contexto da busca."""
    cursos: pd.DataFrame      # uma linha por curso ao alcance, com a modalidade que dá a vaga
    total: int                # cursos ao alcance, considerando as modalidades do perfil
    total_ampla: int          # cursos ao alcance só pela ampla concorrência
    avaliados: int            # cursos com nota de corte em alguma modalidade considerada
    ano: int
    com_cotas: bool           # se alguma cota da Lei de Cotas entrou na comparação
    mais_proximo: pd.Series | None = None  # fora do alcance com a menor distância até a nota de corte


@lru_cache(maxsize=1)
def carregar(caminho: Path = SISU) -> pd.DataFrame:
    """Lê a base uma vez: ampla concorrência e Lei de Cotas, com texto como categoria."""
    df = pd.read_parquet(caminho)
    grupo = df["modalidade_grupo"].astype(str)
    df = df[(df["modalidade_tipo"] == "ampla") | grupo.str.startswith(LEI_DE_COTAS)].reset_index(drop=True)
    return preparar(df)


def preparar(df: pd.DataFrame) -> pd.DataFrame:
    """Tipos compactos, nome de curso para busca e o que cada cota exige, a partir do grupo."""
    for coluna in TEXTO:
        df[coluna] = df[coluna].astype("category")
    df["curso_busca"] = df["curso"].astype(str).map(sem_acento).astype("category")
    grupo = df["modalidade_grupo"].astype(str)
    df["exige_renda"] = grupo.str.contains("renda até 1 SM", regex=False)
    df["exige_ppi"] = grupo.str.contains("pretos, pardos ou indígenas", regex=False)
    df["exige_pp"] = grupo.str.contains("pretos ou pardos", regex=False) & ~df["exige_ppi"]
    df["exige_indigena"] = grupo.str.endswith(", indígenas")
    df["exige_nao_perguntado"] = grupo.str.contains("quilombolas|pessoas com deficiência")
    return df


def sem_acento(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn")


def nomes_de_curso(base: pd.DataFrame) -> list[str]:
    """Nomes de curso distintos (sem acento), do mais longo ao mais curto, para achar o citado na pergunta."""
    return sorted(base["curso_busca"].cat.categories, key=len, reverse=True)


def modalidades_do_perfil(df: pd.DataFrame, perfil: Perfil | None) -> np.ndarray:
    """Quais linhas (modalidades) a pessoa pode disputar. Sem perfil completo, só a ampla."""
    ampla = (df["modalidade_tipo"] == "ampla").to_numpy()
    if perfil is None or not perfil.completo or not perfil.escola_publica:
        return ampla
    cor = perfil.cor_raca
    cota = (
        ~df["exige_nao_perguntado"]
        & (~df["exige_renda"] | perfil.renda_ate_1_sm)
        & (~df["exige_ppi"] | (cor in (PRETOS_PARDOS | INDIGENAS)))
        & (~df["exige_pp"] | (cor in PRETOS_PARDOS))
        & (~df["exige_indigena"] | (cor in INDIGENAS))
    ).to_numpy()
    return ampla | (cota & ~ampla)


def cursos_ao_alcance(
    notas: dict[str, float],
    base: pd.DataFrame,
    perfil: Perfil | None = None,
    uf: str | None = None,
    curso: str | None = None,
    familia: bool = False,
    limite: int = 8,
) -> Consulta:
    """Cursos em que a pessoa teria alcançado a nota de corte, na ampla ou numa cota do perfil.

    `notas` vem no formato {"LC": 650, "CH": 700, "CN": 630, "MT": 810, "REDACAO": 740}.
    `curso` (sem acento) filtra pelo nome exato; com `familia=True`, pelo começo do nome
    ("engenharia" pega todas as engenharias, "medicina" exato não pega "medicina veterinária").
    Para cada curso vale a ampla concorrência, se ela basta; senão, a cota de menor nota de corte.
    """
    df = base
    if uf:
        df = df[df["uf"] == uf]
    if curso:
        nomes = df["curso_busca"].astype(str)
        df = df[nomes.str.startswith(curso) if familia else nomes == curso]
    df = df[df["nota_corte"].notna()]
    df = df[modalidades_do_perfil(df, perfil)]

    pesos = df[[f"peso_{s}" for s in AREAS.values()]].to_numpy(dtype=np.float64)
    vetor = np.array([notas[a] for a in AREAS], dtype=np.float64)
    media = (pesos @ vetor) / pesos.sum(axis=1) if len(df) else np.zeros(0)

    atende_minimos = np.ones(len(df), dtype=bool)
    for posicao, sufixo in enumerate(AREAS.values()):
        atende_minimos &= vetor[posicao] >= df[f"nota_min_{sufixo}"].fillna(0).to_numpy()
    atende_minimos &= media >= df["media_minima"].fillna(0).to_numpy()
    alcance = atende_minimos & (media >= df["nota_corte"].to_numpy())

    df = df.assign(sua_nota=media, ao_alcance=alcance, cota=(df["modalidade_tipo"] != "ampla").to_numpy())
    alcancados = df[df["ao_alcance"]]
    # Uma linha por curso: a ampla, se bastar; senão, a cota de menor nota de corte.
    por_curso = alcancados.sort_values(["codigo_curso", "cota", "nota_corte"]).drop_duplicates("codigo_curso")
    por_curso = por_curso.sort_values("nota_corte", ascending=False)

    mais_proximo = None
    fora = df[~df["ao_alcance"]].assign(falta=lambda x: x["nota_corte"] - x["sua_nota"])
    fora = fora[fora["falta"] > 0]  # quem ficou de fora só pela nota mínima de uma prova não conta
    if len(fora):
        mais_proximo = fora.loc[fora["falta"].idxmin()]

    return Consulta(
        cursos=por_curso.head(limite),
        total=len(por_curso),
        total_ampla=int(alcancados.loc[~alcancados["cota"], "codigo_curso"].nunique()),
        avaliados=int(df["codigo_curso"].nunique()),
        ano=int(base["ano"].max()) if len(base) else 0,
        com_cotas=bool(df["cota"].any()),
        mais_proximo=mais_proximo,
    )

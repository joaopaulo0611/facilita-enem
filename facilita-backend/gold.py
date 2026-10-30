"""Leitura da camada Gold em memória e cálculo de percentil e Z-Score.

A Gold guarda, para cada grupo (ano, área, recorte, categoria), quantas
pessoas tiraram cada nota. Ao carregar, cada grupo vira dois vetores
ordenados: as notas e a contagem acumulada até cada uma. O percentil de
qualquer nota sai de uma busca binária nesses vetores, sem varrer os
microdados.

Os anos são somados numa base só: a nota do ENEM é calculada pela TRI para
ser comparável entre edições, então o participante é comparado com todos
os anos disponíveis, e não com um ano escolhido.
"""
from dataclasses import dataclass
from math import sqrt
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

RAIZ = Path(__file__).resolve().parent.parent
GOLD = RAIZ / "data" / "gold"

# Abaixo disso o grupo é pequeno demais para o percentil ser confiável.
N_MINIMO = 100

CHAVE = ["NU_ANO", "AREA", "RECORTE", "CATEGORIA"]


@dataclass(frozen=True)
class Grupo:
    notas: np.ndarray
    acumulado: np.ndarray
    media: float
    desvio: float

    @property
    def n(self) -> int:
        return int(self.acumulado[-1])

    def percentil(self, nota: float) -> float:
        """Percentual do grupo com nota estritamente menor que a informada."""
        abaixo = np.searchsorted(self.notas, nota, side="left")
        quantos = self.acumulado[abaixo - 1] if abaixo > 0 else 0
        return round(100 * quantos / self.n, 1)

    def zscore(self, nota: float) -> float:
        return round((nota - self.media) / self.desvio, 2)

    def histograma(self, inicio: float, fim: float, largura: float) -> list[int]:
        """Contagem de pessoas por faixa de nota [inicio, fim)."""
        bordas = np.arange(inicio, fim + largura, largura)
        acumulado_nas_bordas = [
            self.acumulado[i - 1] if i > 0 else 0
            for i in np.searchsorted(self.notas, bordas, side="left")
        ]
        return [int(b - a) for a, b in zip(acumulado_nas_bordas, acumulado_nas_bordas[1:])]

    def somar(self, outro: "Grupo") -> "Grupo":
        """Junta dois anos do mesmo grupo numa distribuição só."""
        notas, posicao = np.unique(np.concatenate([self.notas, outro.notas]), return_inverse=True)
        qtd = np.concatenate([np.diff(self.acumulado, prepend=0), np.diff(outro.acumulado, prepend=0)])
        acumulado = np.bincount(posicao, weights=qtd).astype(np.int64).cumsum()
        n = self.n + outro.n
        media = (self.n * self.media + outro.n * outro.media) / n
        # Variância combinada: E[x²] dos dois anos menos o quadrado da média nova.
        quadrados = self.n * (self.desvio**2 + self.media**2) + outro.n * (outro.desvio**2 + outro.media**2)
        return Grupo(notas=notas, acumulado=acumulado, media=media, desvio=sqrt(quadrados / n - media**2))


class GrupoInexistente(LookupError):
    pass


class Gold:
    def __init__(self, estatisticas: pd.DataFrame):
        self.estatisticas = estatisticas.set_index(CHAVE)
        self.grupos: dict[tuple[str, str, str], Grupo] = {}
        self.anos: list[int] = []

    @classmethod
    def carregar(cls, pasta: Path = GOLD) -> "Gold":
        """Um ano por vez, com o texto lido como dicionário, para o pico de memória caber num servidor pequeno."""
        gold = cls(pd.read_parquet(pasta / "estatisticas"))
        for pasta_ano in sorted((pasta / "distribuicao_notas").glob("NU_ANO=*")):
            ano = int(pasta_ano.name.split("=")[1])
            gold.adicionar_ano(ano, pq.read_table(pasta_ano, read_dictionary=CHAVE[1:]))
            pa.default_memory_pool().release_unused()
        return gold

    def adicionar_ano(self, ano: int, distribuicao: pa.Table) -> None:
        """Ordena o ano uma vez e soma cada grupo ao que já veio dos anos anteriores."""
        codigos, rotulos = [], []
        for coluna in CHAVE[1:]:
            dicionario = distribuicao[coluna]
            if not pa.types.is_dictionary(dicionario.type):
                dicionario = pc.dictionary_encode(dicionario)
            dicionario = dicionario.unify_dictionaries().combine_chunks()
            codigos.append(dicionario.indices.to_numpy().astype(np.int32))
            rotulos.append(dicionario.dictionary.to_pylist())
        nota = distribuicao["NOTA"].to_numpy()
        qtd = distribuicao["QTD"].to_numpy()

        ordem = np.lexsort((nota, *reversed(codigos)))
        nota, acumulado = nota[ordem], qtd[ordem].cumsum()
        chave = np.stack([c[ordem] for c in codigos])
        del ordem, codigos
        inicios = np.flatnonzero(np.r_[True, (chave[:, 1:] != chave[:, :-1]).any(axis=0)])
        fins = np.r_[inicios[1:], len(nota)]

        for inicio, fim in zip(inicios, fins):
            area, recorte, categoria = (rotulos[i][chave[i, inicio]] for i in range(3))
            est = self.estatisticas.loc[(ano, area, recorte, categoria)]
            antes = acumulado[inicio - 1] if inicio > 0 else 0
            novo = Grupo(
                notas=nota[inicio:fim],
                acumulado=acumulado[inicio:fim] - antes,
                media=float(est["MEDIA"]),
                desvio=float(est["DESVIO_PADRAO"]),
            )
            chave_grupo = (area, recorte, categoria)
            anterior = self.grupos.get(chave_grupo)
            self.grupos[chave_grupo] = anterior.somar(novo) if anterior else novo
        self.anos = sorted({*self.anos, ano})

    def grupo(self, area: str, recorte: str = "GERAL", categoria: str = "TODOS") -> Grupo:
        try:
            return self.grupos[(area, recorte, categoria)]
        except KeyError:
            raise GrupoInexistente(f"Não há dados para {recorte}={categoria} em {area}.") from None

    def categorias(self, area: str, recorte: str) -> list[str]:
        return sorted(c for (ar, r, c) in self.grupos if ar == area and r == recorte)

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
from collections.abc import Iterable
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

# Linhas lidas do Parquet por vez ao carregar a Gold.
LOTE = 250_000
# Bits reservados para o número de cada texto da chave (até ~1 milhão de valores distintos).
BITS_ROTULO = 20


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
        """Um ano por vez e em lotes, para o pico de memória caber no plano grátis do Render (512 MB)."""
        gold = cls(pd.read_parquet(pasta / "estatisticas"))
        for pasta_ano in sorted((pasta / "distribuicao_notas").glob("NU_ANO=*")):
            ano = int(pasta_ano.name.split("=")[1])
            lotes = (
                lote
                for arquivo in sorted(pasta_ano.glob("*.parquet"))
                for lote in pq.ParquetFile(arquivo, read_dictionary=CHAVE[1:]).iter_batches(
                    batch_size=LOTE, columns=[*CHAVE[1:], "NOTA", "QTD"], use_threads=False
                )
            )
            gold.adicionar_ano(ano, lotes)
            pa.default_memory_pool().release_unused()
        return gold

    def adicionar_ano(self, ano: int, distribuicao: pa.Table | Iterable[pa.RecordBatch]) -> None:
        """Soma cada grupo do ano ao que já veio dos anos anteriores.

        Cada lote vira na hora três vetores compactos (grupo, nota e quantidade) e é
        descartado, então a tabela do ano inteiro nunca fica em memória de uma vez.
        """
        lotes = distribuicao.to_batches() if isinstance(distribuicao, pa.Table) else distribuicao
        # Cada texto (área, recorte, categoria) ganha um número; o grupo vira um único inteiro
        # com os três números, para separar e ordenar sem guardar o texto de cada linha.
        rotulos: list[dict[str, int]] = [{}, {}, {}]
        partes_grupo, partes_nota, partes_qtd = [], [], []
        for lote in lotes:
            grupo = np.zeros(lote.num_rows, np.int64)
            for posicao, coluna in enumerate(CHAVE[1:]):
                valores = lote.column(coluna)
                if not pa.types.is_dictionary(valores.type):
                    valores = pc.dictionary_encode(valores)
                numeros = rotulos[posicao]
                traducao = np.array([numeros.setdefault(t, len(numeros)) for t in valores.dictionary.to_pylist()], np.int64)
                grupo = (grupo << BITS_ROTULO) | traducao[valores.indices.to_numpy()]
            partes_grupo.append(grupo)
            partes_nota.append(lote.column("NOTA").to_numpy())
            partes_qtd.append(lote.column("QTD").to_numpy().astype(np.int64))
        if not partes_nota:
            return
        grupo, nota, qtd = (np.concatenate(p) for p in (partes_grupo, partes_nota, partes_qtd))
        del partes_grupo, partes_nota, partes_qtd
        textos = [list(numeros) for numeros in rotulos]

        # O ETL já grava cada ano ordenado por grupo e nota; só reordena se não vier assim.
        inicios = np.flatnonzero(np.r_[True, grupo[1:] != grupo[:-1]])
        contiguo = len(inicios) == len(np.unique(grupo[inicios]))
        if not (contiguo and np.all((np.diff(nota) > 0) | (np.diff(grupo) != 0))):
            ordem = np.lexsort((nota, grupo))
            grupo, nota, qtd = grupo[ordem], nota[ordem], qtd[ordem]
            del ordem
            inicios = np.flatnonzero(np.r_[True, grupo[1:] != grupo[:-1]])
        fins = np.r_[inicios[1:], len(nota)]
        mascara = (1 << BITS_ROTULO) - 1

        for inicio, fim in zip(inicios, fins):
            numero = int(grupo[inicio])
            area, recorte, categoria = (
                textos[0][numero >> 2 * BITS_ROTULO],
                textos[1][(numero >> BITS_ROTULO) & mascara],
                textos[2][numero & mascara],
            )
            try:
                est = self.estatisticas.loc[(ano, area, recorte, categoria)]
            except KeyError as erro:
                # distribuicao_notas e estatisticas saíram de execuções diferentes
                # do ETL: há um grupo numa tabela e não na outra. Mensagem clara
                # em vez de um 500 opaco em toda rota (inclusive /metadados).
                raise RuntimeError(
                    f"Gold inconsistente: o grupo {(ano, area, recorte, categoria)} está em "
                    "distribuicao_notas mas não em estatisticas. Rode o ETL (etl/gold.py) de novo "
                    "para regerar as duas tabelas juntas."
                ) from erro
            # Cópias próprias de cada grupo: assim os vetores do ano inteiro são liberados.
            novo = Grupo(
                notas=nota[inicio:fim].copy(),
                acumulado=qtd[inicio:fim].cumsum(),
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

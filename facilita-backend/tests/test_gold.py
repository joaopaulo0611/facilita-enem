"""Cálculo de percentil, Z-Score e histograma sobre a distribuição pré-agregada."""
import numpy as np
import pandas as pd
import pyarrow as pa
import pytest

from gold import Gold, Grupo, GrupoInexistente


def test_percentil_conta_quem_ficou_estritamente_abaixo(gold):
    brasil = gold.grupo("MT")
    assert brasil.percentil(400.0) == 0.0     # ninguém abaixo da menor nota
    assert brasil.percentil(402.0) == 1.0     # só o 400 está abaixo
    assert brasil.percentil(650.0) == 50.0    # 400..645 = 50 pessoas
    assert brasil.percentil(1000.0) == 100.0


def test_percentil_e_monotono(gold):
    brasil = gold.grupo("MT")
    valores = [brasil.percentil(n) for n in range(0, 1001, 10)]
    assert valores == sorted(valores)


def test_zscore_na_media_e_zero(gold):
    brasil = gold.grupo("MT")
    assert brasil.zscore(brasil.media) == 0.0
    assert brasil.zscore(brasil.media + brasil.desvio) == 1.0


def test_histograma_soma_o_total_do_intervalo(gold):
    brasil = gold.grupo("MEDIA")
    contagens = brasil.histograma(400, 900, 50)
    assert len(contagens) == 10
    assert sum(contagens) == brasil.n


def test_grupo_inexistente(gold):
    with pytest.raises(GrupoInexistente):
        gold.grupo("MT", "UF", "XX")


def _ano(ano, notas_e_qtd):
    """Gold de um ano só, com um único grupo GERAL de MT."""
    distribuicao = pd.DataFrame(
        [{"AREA": "MT", "RECORTE": "GERAL", "CATEGORIA": "TODOS", "NOTA": n, "QTD": q} for n, q in notas_e_qtd]
    )
    notas = distribuicao["NOTA"].repeat(distribuicao["QTD"])
    estatisticas = {"NU_ANO": ano, "AREA": "MT", "RECORTE": "GERAL", "CATEGORIA": "TODOS",
                    "MEDIA": notas.mean(), "DESVIO_PADRAO": notas.std(ddof=0)}
    return estatisticas, pa.Table.from_pandas(distribuicao, preserve_index=False)


def test_anos_sao_somados_numa_base_so():
    est_2022, dist_2022 = _ano(2022, [(400.0, 2), (600.0, 1)])
    est_2023, dist_2023 = _ano(2023, [(600.0, 1), (800.0, 4)])
    gold = Gold(pd.DataFrame([est_2022, est_2023]))
    gold.adicionar_ano(2022, dist_2022)
    gold.adicionar_ano(2023, dist_2023)

    mt = gold.grupo("MT")
    juntas = np.repeat([400.0, 600.0, 800.0], [2, 2, 4])
    assert gold.anos == [2022, 2023]
    assert mt.n == 8
    assert list(mt.notas) == [400.0, 600.0, 800.0]   # o 600 dos dois anos vira uma nota só
    assert mt.percentil(700.0) == 50.0                # 2 + 2 de 8 abaixo
    assert mt.media == pytest.approx(juntas.mean())
    assert mt.desvio == pytest.approx(juntas.std())


def test_soma_e_igual_nas_duas_ordens():
    a = Grupo(notas=np.array([1.0, 3.0]), acumulado=np.array([2, 5]), media=1.0, desvio=1.0)
    b = Grupo(notas=np.array([2.0, 3.0]), acumulado=np.array([1, 2]), media=2.0, desvio=0.5)
    ab, ba = a.somar(b), b.somar(a)
    assert list(ab.acumulado) == list(ba.acumulado) == [2, 3, 7]
    assert ab.media == pytest.approx(ba.media)
    assert ab.desvio == pytest.approx(ba.desvio)

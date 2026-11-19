"""Gold sintética e pequena, montada em memória, para os testes não dependerem dos microdados."""
import sys
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dependencias import obter_gold  # noqa: E402
from gold import Gold  # noqa: E402
from main import app  # noqa: E402

AREAS = ["LC", "CH", "CN", "MT", "REDACAO", "MEDIA"]


def _grupo(area, recorte, categoria, notas_e_qtd):
    return [{"AREA": area, "RECORTE": recorte, "CATEGORIA": categoria, "NOTA": n, "QTD": q} for n, q in notas_e_qtd]


@pytest.fixture(scope="session")
def gold() -> Gold:
    # Brasil: 100 pessoas, uma em cada nota 400, 405, ..., 895.
    brasil = [(400.0 + 5 * i, 1) for i in range(100)]
    # SC tem notas mais altas que AM; RR é pequena demais para comparar.
    sc = [(600.0 + 2 * i, 1) for i in range(150)]
    am = [(400.0 + 2 * i, 1) for i in range(150)]
    rr = [(500.0, 10)]
    # Recortes socioeconômicos: renda alta (Q) tira mais que renda baixa (B);
    # escola privada (3) mais que pública (2). Grupos pequenos (10 pessoas)
    # servem para testar a recusa por tamanho mínimo.
    renda_b = [(400.0 + 2 * i, 1) for i in range(150)]
    renda_q = [(600.0 + 2 * i, 1) for i in range(150)]
    escola_2 = [(420.0 + 2 * i, 1) for i in range(150)]
    escola_3 = [(620.0 + 2 * i, 1) for i in range(150)]
    # mãe com ensino médio (E) tira menos que com pós (G);
    # cor/raça 3 (parda) tem notas mais baixas que 1 (branca).
    mae_e = [(400.0 + 2 * i, 1) for i in range(150)]
    mae_g = [(600.0 + 2 * i, 1) for i in range(150)]
    cor_1 = [(620.0 + 2 * i, 1) for i in range(150)]
    cor_3 = [(420.0 + 2 * i, 1) for i in range(150)]
    cor_5 = [(500.0, 10)]
    # Módulo origem: cruzamento cor/raça x tipo de escola. 3|2 é parda em escola
    # pública; 3|3 é pequeno demais para comparar.
    cruz_cor_escola_32 = [(410.0 + 2 * i, 1) for i in range(150)]
    cruz_cor_escola_33 = [(500.0, 10)]
    # Módulo família: cruzamento renda x escolaridade da mãe. B|E é renda baixa
    # com mãe no ensino médio; B|G é pequeno demais para comparar.
    cruz_renda_mae_be = [(415.0 + 2 * i, 1) for i in range(150)]
    cruz_renda_mae_bg = [(500.0, 10)]
    linhas = []
    for area in AREAS:
        linhas += _grupo(area, "GERAL", "TODOS", brasil)
        linhas += _grupo(area, "UF", "SC", sc)
        linhas += _grupo(area, "UF", "AM", am)
        linhas += _grupo(area, "UF", "RR", rr)
        linhas += _grupo(area, "RENDA", "B", renda_b)
        linhas += _grupo(area, "RENDA", "Q", renda_q)
        linhas += _grupo(area, "TIPO_ESCOLA", "2", escola_2)
        linhas += _grupo(area, "TIPO_ESCOLA", "3", escola_3)
        linhas += _grupo(area, "ESCOLARIDADE_MAE", "E", mae_e)
        linhas += _grupo(area, "ESCOLARIDADE_MAE", "G", mae_g)
        linhas += _grupo(area, "COR_RACA", "1", cor_1)
        linhas += _grupo(area, "COR_RACA", "3", cor_3)
        linhas += _grupo(area, "COR_RACA", "5", cor_5)
        linhas += _grupo(area, "COR_RACA_X_TIPO_ESCOLA", "3|2", cruz_cor_escola_32)
        linhas += _grupo(area, "COR_RACA_X_TIPO_ESCOLA", "3|3", cruz_cor_escola_33)
        linhas += _grupo(area, "RENDA_X_ESCOLARIDADE_MAE", "B|E", cruz_renda_mae_be)
        linhas += _grupo(area, "RENDA_X_ESCOLARIDADE_MAE", "B|G", cruz_renda_mae_bg)
    distribuicao = pd.DataFrame(linhas)

    estatisticas = []
    for (area, recorte, categoria), grupo in distribuicao.groupby(["AREA", "RECORTE", "CATEGORIA"]):
        notas = grupo["NOTA"].repeat(grupo["QTD"])
        estatisticas.append({
            "NU_ANO": 2023, "AREA": area, "RECORTE": recorte, "CATEGORIA": categoria,
            "MEDIA": notas.mean(), "DESVIO_PADRAO": notas.std(ddof=0) or 1.0,
        })
    gold = Gold(pd.DataFrame(estatisticas))
    gold.adicionar_ano(2023, pa.Table.from_pandas(distribuicao, preserve_index=False))
    return gold


@pytest.fixture
def cliente(gold):
    app.dependency_overrides[obter_gold] = lambda: gold
    yield TestClient(app)
    app.dependency_overrides.clear()

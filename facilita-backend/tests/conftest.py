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
    linhas = []
    for area in AREAS:
        linhas += _grupo(area, "GERAL", "TODOS", brasil)
        linhas += _grupo(area, "UF", "SC", sc)
        linhas += _grupo(area, "UF", "AM", am)
        linhas += _grupo(area, "UF", "RR", rr)
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

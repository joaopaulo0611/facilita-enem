"""Módulo regional: regras de negócio e validação das entradas."""
PARAMS = {"nota": 700, "uf": "SC", "area": "MT"}


def test_compara_estado_com_brasil(cliente):
    corpo = cliente.get("/api/modulos/regional", params=PARAMS).json()
    assert corpo["estado"]["percentil"] == 33.3   # 600..698 = 50 de 150
    assert corpo["brasil"]["percentil"] == 60.0   # 400..695 = 60 de 100
    assert corpo["nome_uf"] == "Santa Catarina"


def test_ranking_ordenado_e_sem_ufs_pequenas(cliente):
    ranking = cliente.get("/api/modulos/regional", params=PARAMS).json()["ranking"]
    assert [linha["uf"] for linha in ranking] == ["AM", "SC"]
    assert ranking[0]["percentil"] >= ranking[1]["percentil"]


def test_area_padrao_e_a_media(cliente):
    corpo = cliente.get("/api/modulos/regional", params={"nota": 700, "uf": "SC"}).json()
    assert corpo["area"] == "MEDIA"


def test_uf_inexistente_e_recusada(cliente):
    assert cliente.get("/api/modulos/regional", params={**PARAMS, "uf": "XX"}).status_code == 422


def test_uf_em_minusculas_e_recusada(cliente):
    assert cliente.get("/api/modulos/regional", params={**PARAMS, "uf": "sc"}).status_code == 422


def test_area_inexistente_e_recusada(cliente):
    assert cliente.get("/api/modulos/regional", params={**PARAMS, "area": "FISICA"}).status_code == 422


def test_estado_com_poucos_participantes_e_recusado(cliente):
    resposta = cliente.get("/api/modulos/regional", params={**PARAMS, "uf": "RR"})
    assert resposta.status_code == 422
    assert "mínimo" in resposta.json()["detail"]


def test_uf_valida_sem_dados_retorna_404(cliente):
    resposta = cliente.get("/api/modulos/regional", params={**PARAMS, "uf": "BA"})
    assert resposta.status_code == 404


def test_uf_invalida_lista_as_opcoes(cliente):
    campos = cliente.get("/api/modulos/regional", params={**PARAMS, "uf": "XX"}).json()["campos"]
    assert campos["uf"].startswith("não é válido; use um destes:")
    assert "'SC'" in campos["uf"]

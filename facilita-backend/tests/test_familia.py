"""Módulo família: posição por renda, por escolaridade da mãe e no cruzamento dos dois."""
PARAMS = {"nota": 600, "renda": "B", "escolaridade_mae": "E", "area": "MT"}


def test_compara_brasil_renda_escolaridade_e_cruzamento(cliente):
    corpo = cliente.get("/api/modulos/familia", params=PARAMS).json()
    # Brasil (400..895 de 5 em 5): 40 de 100 abaixo de 600.
    assert corpo["brasil"]["percentil"] == 40.0
    # Renda B (400..698 de 2 em 2): 100 de 150 abaixo de 600.
    assert corpo["por_renda"]["percentil"] == 66.7
    # Escolaridade E (400..698 de 2 em 2): 100 de 150 abaixo de 600.
    assert corpo["por_escolaridade_mae"]["percentil"] == 66.7
    # Cruzamento B|E (415..713 de 2 em 2): 93 de 150 abaixo de 600.
    assert corpo["por_renda_e_escolaridade_mae"]["percentil"] == 62.0


def test_nomes_legiveis_na_resposta(cliente):
    corpo = cliente.get("/api/modulos/familia", params=PARAMS).json()
    assert corpo["renda"] == {"codigo": "B", "nome": "Até 1 salário mínimo"}
    assert corpo["escolaridade_mae"] == {"codigo": "E", "nome": "Ensino médio completo"}


def test_area_padrao_e_a_media(cliente):
    corpo = cliente.get("/api/modulos/familia", params={k: v for k, v in PARAMS.items() if k != "area"}).json()
    assert corpo["area"] == "MEDIA"


def test_renda_inexistente_e_recusada(cliente):
    assert cliente.get("/api/modulos/familia", params={**PARAMS, "renda": "Z"}).status_code == 422


def test_escolaridade_inexistente_e_recusada(cliente):
    assert cliente.get("/api/modulos/familia", params={**PARAMS, "escolaridade_mae": "Z"}).status_code == 422


def test_grupo_pequeno_no_cruzamento_e_recusado(cliente):
    # B|G tem só 10 participantes na Gold sintética (abaixo do mínimo).
    resposta = cliente.get("/api/modulos/familia", params={**PARAMS, "escolaridade_mae": "G", "renda": "B"})
    assert resposta.status_code == 422
    assert "mínimo" in resposta.json()["detail"]


def test_renda_invalida_lista_as_opcoes(cliente):
    campos = cliente.get("/api/modulos/familia", params={**PARAMS, "renda": "Z"}).json()["campos"]
    assert campos["renda"].startswith("não é válido; use um destes:")
    assert "'B'" in campos["renda"]

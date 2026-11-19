"""Módulo origem: posição por cor/raça, por tipo de escola e no cruzamento dos dois."""
PARAMS = {"nota": 600, "cor_raca": "3", "tipo_escola": "2", "area": "MT"}


def test_compara_brasil_cor_escola_e_cruzamento(cliente):
    corpo = cliente.get("/api/modulos/origem", params=PARAMS).json()
    # Brasil (400..895 de 5 em 5): 40 de 100 abaixo de 600.
    assert corpo["brasil"]["percentil"] == 40.0
    # Cor/raça 3 (420..718 de 2 em 2): 90 de 150 abaixo de 600.
    assert corpo["por_cor_raca"]["percentil"] == 60.0
    # Escola 2 (420..718 de 2 em 2): 90 de 150 abaixo de 600.
    assert corpo["por_escola"]["percentil"] == 60.0
    # Cruzamento 3|2 (410..708 de 2 em 2): 95 de 150 abaixo de 600.
    assert corpo["por_cor_raca_e_escola"]["percentil"] == 63.3


def test_nomes_legiveis_na_resposta(cliente):
    corpo = cliente.get("/api/modulos/origem", params=PARAMS).json()
    assert corpo["cor_raca"] == {"codigo": "3", "nome": "Parda"}
    assert corpo["tipo_escola"] == {"codigo": "2", "nome": "Pública"}


def test_area_padrao_e_a_media(cliente):
    corpo = cliente.get("/api/modulos/origem", params={k: v for k, v in PARAMS.items() if k != "area"}).json()
    assert corpo["area"] == "MEDIA"


def test_cor_raca_inexistente_e_recusada(cliente):
    assert cliente.get("/api/modulos/origem", params={**PARAMS, "cor_raca": "9"}).status_code == 422


def test_cor_raca_nao_declarada_e_recusada(cliente):
    # O código 0 ("não declarada") não é opção válida de comparação.
    assert cliente.get("/api/modulos/origem", params={**PARAMS, "cor_raca": "0"}).status_code == 422


def test_tipo_escola_nao_informado_e_recusado(cliente):
    # O código 1 ("não informou") não é opção válida de comparação.
    assert cliente.get("/api/modulos/origem", params={**PARAMS, "tipo_escola": "1"}).status_code == 422


def test_grupo_pequeno_no_cruzamento_e_recusado(cliente):
    # 3|3 tem só 10 participantes na Gold sintética (abaixo do mínimo).
    resposta = cliente.get("/api/modulos/origem", params={**PARAMS, "tipo_escola": "3", "cor_raca": "3"})
    assert resposta.status_code == 422
    assert "mínimo" in resposta.json()["detail"]


def test_cor_raca_invalida_lista_as_opcoes(cliente):
    campos = cliente.get("/api/modulos/origem", params={**PARAMS, "cor_raca": "9"}).json()["campos"]
    assert campos["cor_raca"].startswith("não é válido; use um destes:")
    assert "'3'" in campos["cor_raca"]

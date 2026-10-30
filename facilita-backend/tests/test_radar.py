"""Rota /api/radar: entradas válidas e resiliência contra entradas inválidas."""
NOTAS = {"lc": 650, "ch": 700, "cn": 600, "mt": 750, "redacao": 900}


def test_radar_responde_cada_area_e_a_media(cliente):
    resposta = cliente.get("/api/radar", params=NOTAS)
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert [a["area"] for a in corpo["areas"]] == ["LC", "CH", "CN", "MT", "REDACAO"]
    assert corpo["media_geral"]["nota"] == 720.0
    assert corpo["participantes"] == 100
    mt = next(a for a in corpo["areas"] if a["area"] == "MT")
    assert mt["percentil"] == 70.0


def test_nota_acima_de_1000_e_recusada(cliente):
    resposta = cliente.get("/api/radar", params={**NOTAS, "mt": 1001})
    assert resposta.status_code == 422


def test_nota_negativa_e_recusada(cliente):
    assert cliente.get("/api/radar", params={**NOTAS, "lc": -1}).status_code == 422


def test_nota_que_nao_e_numero_e_recusada(cliente):
    assert cliente.get("/api/radar", params={**NOTAS, "cn": "abc"}).status_code == 422


def test_nota_faltando_e_recusada(cliente):
    sem_redacao = {k: v for k, v in NOTAS.items() if k != "redacao"}
    assert cliente.get("/api/radar", params=sem_redacao).status_code == 422


def test_metadados_lista_anos_e_opcoes(cliente):
    corpo = cliente.get("/api/metadados").json()
    assert corpo["anos"] == [2023]
    assert corpo["participantes"] == 100
    assert {"codigo": "1", "nome": "Não informou"} in corpo["recortes"]["TIPO_ESCOLA"]


def test_erros_de_validacao_saem_em_portugues_por_campo(cliente):
    resposta = cliente.get("/api/radar", params={**NOTAS, "mt": 1001, "cn": "abc"})
    campos = resposta.json()["campos"]
    assert campos["mt"] == "deve ser no máximo 1000"
    assert campos["cn"] == "precisa ser um número"

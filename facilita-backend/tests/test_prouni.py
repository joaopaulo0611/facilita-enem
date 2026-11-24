"""ProUni: regra de elegibilidade com a renda por pessoa estimada pela faixa e pelo número de pessoas."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import prouni as P  # noqa: E402
from assistente.ferramentas import pessoas_citadas  # noqa: E402
from assistente.orquestrador import Orquestrador  # noqa: E402
from assistente.resposta import Tipo  # noqa: E402

NOTAS = {"LC": 650.0, "CH": 700.0, "CN": 630.0, "MT": 810.0, "REDACAO": 740.0}
RESULTADO = {"areas": [{"area": a, "nome": a, "nota": n} for a, n in NOTAS.items()]}
PUBLICA = "2"


@pytest.mark.parametrize(
    ("renda", "pessoas", "esperado"),
    [
        ("G", 4, P.INTEGRAL),             # 3 a 4 SM / 4 = 0,75 a 1
        ("E", 1, P.PARCIAL),              # 2 a 2,5 SM / 1: acima de 1,5 e até 3
        ("D", 1, P.INTEGRAL_OU_PARCIAL),  # 1,5 a 2 SM / 1: começa exatamente no limite da integral
        ("G", 2, P.INTEGRAL_OU_PARCIAL),  # 1,5 a 2: o limite da integral (1,5) ainda conta
        ("H", 2, P.PARCIAL),              # 4 a 5 / 2 = 2 a 2,5
        ("N", 3, P.ACIMA),                # 10 a 12 / 3 = 3,33 a 4
        ("Q", 1, P.ACIMA),                # mais de 20
        ("A", 1, P.INTEGRAL),             # nenhuma renda
    ],
)
def test_situacao_da_renda_por_pessoa(renda, pessoas, esperado):
    assert P.avaliar(NOTAS, PUBLICA, renda, pessoas).renda == esperado


def test_faixa_que_cruza_o_limite_da_parcial():
    # 6 a 7 SM / 2 = 3 a 3,5: com exatamente 3 ainda entra na parcial; acima, não.
    assert P.avaliar(NOTAS, PUBLICA, "J", 2).renda == P.PARCIAL_OU_NAO


def test_nota_abaixo_de_450_ou_redacao_zero_nao_atende():
    assert not P.avaliar({**NOTAS, "LC": 100, "CH": 100, "CN": 100, "MT": 100, "REDACAO": 900}, PUBLICA, "B", 1).nota_ok
    assert not P.avaliar({**NOTAS, "REDACAO": 0}, PUBLICA, "B", 1).nota_ok


@pytest.mark.parametrize(
    ("pergunta", "pessoas"),
    [("Moramos em 4 pessoas", 4), ("somos três em casa", 3), ("moro sozinha", 1), ("família de 5", 5),
     ("Eu me enquadro no ProUni?", None), ("tenho 2 irmãos", None)],
)
def test_numero_de_pessoas_na_pergunta(pergunta, pessoas):
    assert pessoas_citadas(pergunta) == pessoas


def test_chat_responde_bolsa_integral_com_criterios():
    r = Orquestrador().responde("Eu me enquadro no ProUni? Moramos em 4 pessoas.", RESULTADO, {"tipo_escola": PUBLICA, "renda": "G"})
    assert r.tipo is Tipo.DADO and "bolsa integral (100%)" in r.texto
    assert "de 0,75 a 1 salário mínimo" in r.texto and r.evidencia.preenchida()


def test_chat_pergunta_o_numero_de_pessoas_quando_falta():
    r = Orquestrador().responde("Eu me enquadro no ProUni?", RESULTADO, {"tipo_escola": PUBLICA, "renda": "G"})
    assert "Quantas pessoas moram na sua casa" in r.texto


def test_chat_escola_privada_explica_a_excecao():
    r = Orquestrador().responde("ProUni? Somos 4 pessoas", RESULTADO, {"tipo_escola": "3", "renda": "B"})
    assert "bolsista integral" in r.texto


def test_chat_sem_radar_pede_as_notas():
    r = Orquestrador().responde("Eu me enquadro no ProUni?")
    assert r.tipo is Tipo.SEM_DADOS

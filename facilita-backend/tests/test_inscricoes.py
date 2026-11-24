"""Fase 2 (SISU): cursos ao alcance com uma base sintética pequena, sem depender do Parquet real."""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import inscricoes as I  # noqa: E402
from assistente import ferramentas as F  # noqa: E402
from assistente.resposta import Tipo  # noqa: E402

NOTAS = {"LC": 600.0, "CH": 600.0, "CN": 600.0, "MT": 800.0, "REDACAO": 700.0}
RESULTADO = {"areas": [{"area": a, "nome": a, "nota": n} for a, n in NOTAS.items()]}


def _curso(codigo, curso, uf, corte, pesos=(1, 1, 1, 1, 1), minimos=(0, 0, 0, 0, 0), media_minima=0.0, grupo="Ampla concorrência"):
    linha = {
        "ano": 2024, "codigo_curso": codigo, "curso": curso, "grau": "Bacharelado", "turno": "Integral",
        "campus": "Campus", "municipio": "Cidade", "uf": uf, "ies_nome": "Universidade", "ies_sigla": "UNI",
        "modalidade": grupo, "modalidade_tipo": "ampla" if grupo == "Ampla concorrência" else "cota",
        "modalidade_grupo": grupo,
        "nota_corte": corte, "media_minima": media_minima,
    }
    for area, peso, minimo in zip(["cn", "ch", "lc", "mt", "redacao"], pesos, minimos):
        linha[f"peso_{area}"], linha[f"nota_min_{area}"] = float(peso), float(minimo)
    return linha


@pytest.fixture
def base():
    linhas = [
        _curso(1, "MEDICINA", "SC", 700.0),                          # média simples 660 < 700: fora
        _curso(2, "MEDICINA VETERINÁRIA", "SC", 640.0),              # 660 >= 640: dentro
        _curso(3, "ENGENHARIA CIVIL", "SC", 700.0, pesos=(1, 1, 1, 4, 1)),  # ponderada 712,5 >= 700: dentro
        _curso(4, "ENGENHARIA ELÉTRICA", "RS", 650.0),               # 660 >= 650: dentro
        _curso(5, "DIREITO", "SC", 600.0, minimos=(0, 0, 0, 0, 750)),  # redação mínima 750 > 700: fora
        _curso(6, "LETRAS", "SC", None),                              # sem nota de corte: nunca conta
        # Cotas da Medicina (código 1): média simples da pessoa é 660.
        _curso(1, "MEDICINA", "SC", 680.0, grupo="Lei de Cotas: escola pública"),
        _curso(1, "MEDICINA", "SC", 650.0, grupo="Lei de Cotas: escola pública, renda até 1 SM, pretos, pardos ou indígenas"),
        _curso(1, "MEDICINA", "SC", 640.0, grupo="Lei de Cotas: escola pública, pessoas com deficiência"),
    ]
    return I.preparar(pd.DataFrame(linhas))


PARDA_BAIXA_RENDA = I.Perfil(escola="2", renda="B", cor_raca="3")


def test_media_ponderada_usa_os_pesos_do_curso(base):
    consulta = I.cursos_ao_alcance(NOTAS, base, curso="engenharia civil")
    assert consulta.total == 1
    assert consulta.cursos.iloc[0]["sua_nota"] == pytest.approx(712.5)  # (600*3 + 800*4 + 700) / 8 = 5700 / 8


def test_nota_minima_da_prova_tira_o_curso(base):
    consulta = I.cursos_ao_alcance(NOTAS, base, curso="direito")
    assert consulta.total == 0


def test_sem_nota_de_corte_nunca_esta_ao_alcance(base):
    consulta = I.cursos_ao_alcance(NOTAS, base, curso="letras")
    assert consulta.avaliados == 0 and consulta.total == 0


def test_ordena_pela_nota_de_corte_e_filtra_por_uf(base):
    consulta = I.cursos_ao_alcance(NOTAS, base, uf="SC")
    assert list(consulta.cursos["curso"]) == ["ENGENHARIA CIVIL", "MEDICINA VETERINÁRIA"]


def test_mais_proximo_quando_nada_esta_ao_alcance(base):
    consulta = I.cursos_ao_alcance(NOTAS, base, curso="medicina")
    assert consulta.total == 0
    assert consulta.mais_proximo["curso"] == "MEDICINA"
    assert consulta.mais_proximo["falta"] == pytest.approx(40.0)


def test_ferramenta_medicina_e_exato_e_engenharia_e_familia(base):
    r = F.cursos_ao_alcance(RESULTADO, "Dá pra passar em Medicina?", base=base)
    assert "não" in r.texto and "MEDICINA VETERINÁRIA" not in r.texto
    r = F.cursos_ao_alcance(RESULTADO, "Quais engenharias eu alcançaria?", base=base)
    assert "ENGENHARIA CIVIL" in r.texto and "ENGENHARIA ELÉTRICA" in r.texto


def test_ferramenta_responde_com_evidencia_e_aviso(base):
    r = F.cursos_ao_alcance(RESULTADO, "Em que cursos eu teria passado em Santa Catarina?", base=base)
    assert r.tipo is Tipo.DADO
    assert r.evidencia.periodo == "SISU 2024" and "SC" in r.evidencia.recorte
    assert "não garantia" in r.texto


def test_preposicao_para_nao_vira_o_estado_do_para(base):
    r = F.cursos_ao_alcance(RESULTADO, "Quero um curso para mim", base=base)
    assert "Pará" not in r.texto


# ---------------------------------------------------------------- cotas pelo perfil

def test_sem_perfil_so_ampla(base):
    consulta = I.cursos_ao_alcance(NOTAS, base, curso="medicina")
    assert consulta.total == 0 and not consulta.com_cotas


def test_cota_ppi_com_renda_ate_1_sm_da_a_vaga(base):
    consulta = I.cursos_ao_alcance(NOTAS, base, perfil=PARDA_BAIXA_RENDA, curso="medicina")
    assert consulta.total == 1 and consulta.total_ampla == 0
    assert "pretos, pardos ou indígenas" in str(consulta.cursos.iloc[0]["modalidade_grupo"])


def test_cota_de_renda_exige_renda_total_ate_1_sm(base):
    # Renda total de 3 a 4 SM: a cota de renda fica de fora; a de escola pública (corte 680) não basta.
    perfil = I.Perfil(escola="2", renda="G", cor_raca="3")
    consulta = I.cursos_ao_alcance(NOTAS, base, perfil=perfil, curso="medicina")
    assert consulta.total == 0 and consulta.com_cotas
    assert "escola pública" in str(consulta.mais_proximo["modalidade_grupo"])


def test_cota_ppi_nao_vale_para_quem_e_branco(base):
    perfil = I.Perfil(escola="2", renda="B", cor_raca="1")
    assert I.cursos_ao_alcance(NOTAS, base, perfil=perfil, curso="medicina").total == 0


def test_escola_privada_nao_usa_cotas(base):
    perfil = I.Perfil(escola="3", renda="B", cor_raca="3")
    consulta = I.cursos_ao_alcance(NOTAS, base, perfil=perfil, curso="medicina")
    assert consulta.total == 0 and not consulta.com_cotas


def test_cota_de_pcd_nunca_entra_porque_o_radar_nao_pergunta(base):
    # A cota PcD (corte 640) daria a vaga, mas o Radar não sabe se a pessoa tem deficiência.
    perfil = I.Perfil(escola="2", renda="G", cor_raca="1")
    assert I.cursos_ao_alcance(NOTAS, base, perfil=perfil, curso="medicina").total == 0


def test_ampla_tem_prioridade_quando_basta(base):
    consulta = I.cursos_ao_alcance(NOTAS, base, perfil=PARDA_BAIXA_RENDA, uf="SC")
    linha = consulta.cursos[consulta.cursos["curso"] == "MEDICINA VETERINÁRIA"].iloc[0]
    assert not linha["cota"]


def test_ferramenta_explica_as_cotas(base):
    campos = {"tipo_escola": "2", "renda": "G", "cor_raca": "3"}
    r = F.cursos_ao_alcance(RESULTADO, "Dá pra passar em Medicina?", campos, base=base)
    assert "por pessoa" in r.texto and "Lei de Cotas" in r.evidencia.recorte
    r = F.cursos_ao_alcance(RESULTADO, "Dá pra passar em Medicina?", None, base=base)
    assert "Para incluir as cotas" in r.texto

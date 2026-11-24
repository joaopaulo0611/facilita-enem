"""Glossário do assistente: a fonte única de definições e metodologia.

Cada termo traz nome, definição, como ler e (quando faz sentido) a fórmula e as
limitações. O assistente não duplica esses textos em outro lugar: as respostas
conceituais vêm todas daqui, e o resolvedor de termos liga o que a pessoa
escreveu a um id conhecido.
"""
from __future__ import annotations

FONTE = "Microdados do ENEM, INEP"
PERIODO = "edições de 2022 e 2023"
ABRANGENCIA = "participantes do ENEM no Brasil"

# Cada indicador: nome legível, definição, como interpretar e limitações.
INDICADORES: dict[str, dict] = {
    "percentil": {
        "nome": "Percentil",
        "definicao": (
            "O percentil diz quantos participantes, em cada 100, tiveram nota **menor** que a sua. "
            "Um percentil de 80 significa que você ficou à frente de 80% de quem fez a prova."
        ),
        "como_ler": "Quanto maior o percentil, melhor a sua posição em relação aos demais.",
        "formula": "percentil = (participantes com nota menor que a sua ÷ total do grupo) × 100",
        "limitacoes": "É uma posição relativa ao grupo comparado; muda conforme o recorte (estado, renda etc.).",
    },
    "media_geral": {
        "nome": "Média geral",
        "definicao": (
            "A média geral é a média simples das suas cinco notas (Linguagens, Humanas, Natureza, "
            "Matemática e Redação), todas com o mesmo peso."
        ),
        "como_ler": "É um resumo do seu desempenho; cada curso pode dar pesos diferentes às áreas.",
        "formula": "média geral = (LC + CH + CN + MT + Redação) ÷ 5",
        "limitacoes": "Os pesos reais variam por curso e seleção (SISU, ProUni); a média simples é só uma referência.",
    },
    "media_participantes": {
        "nome": "Média dos participantes",
        "definicao": "É a nota média de todos os participantes do grupo comparado, numa área ou na média geral.",
        "como_ler": "Serve de linha de referência: a sua diferença para ela mostra se você ficou acima ou abaixo.",
        "formula": "soma das notas do grupo ÷ número de participantes",
        "limitacoes": "Uma média esconde a dispersão; duas pessoas com a mesma média podem ter perfis bem diferentes.",
    },
    "zscore": {
        "nome": "Z-score",
        "definicao": (
            "O z-score mede quantos desvios-padrão a sua nota está acima ou abaixo da média do grupo. "
            "Zero é exatamente a média; +1 é um desvio acima."
        ),
        "como_ler": "Positivo: acima da média. Negativo: abaixo. Quanto maior o módulo, mais distante da média.",
        "formula": "z = (sua nota − média do grupo) ÷ desvio-padrão do grupo",
        "limitacoes": "Supõe uma distribuição razoavelmente simétrica; em caudas extremas é menos intuitivo.",
    },
    "nota": {
        "nome": "Nota do ENEM",
        "definicao": (
            "As notas das provas objetivas vêm da Teoria de Resposta ao Item (TRI), não do total de acertos: "
            "a TRI pesa a dificuldade e a coerência das respostas. A redação vai de 0 a 1.000."
        ),
        "como_ler": "Por ser calculada pela TRI, a nota é comparável entre edições diferentes do exame.",
        "formula": "",
        "limitacoes": "Duas pessoas com o mesmo número de acertos podem ter notas diferentes pela TRI.",
    },
}

# Sinônimos e palavras que apontam para um indicador do glossário.
_APELIDOS: dict[str, tuple[str, ...]] = {
    "percentil": ("percentil", "posicao", "posição", "ranking", "lugar", "frente"),
    "media_geral": ("media geral", "média geral", "media das notas", "media simples"),
    "media_participantes": ("media dos participantes", "média dos participantes", "media do grupo", "media geral dos outros"),
    "zscore": ("zscore", "z-score", "z score", "desvio padrao", "desvio-padrão", "desvios"),
    "nota": ("tri", "teoria de resposta", "como a nota", "como e calculada a nota", "calculo da nota", "nota do enem"),
}

# Notas de metodologia reutilizadas por várias respostas.
NOTAS = {
    "base": (
        "Os números vêm dos microdados oficiais do ENEM (INEP), somando as edições de 2022 e 2023. "
        "As notas são comparáveis entre anos porque a TRI as coloca na mesma escala."
    ),
    "estatistico": (
        "Os resultados são **estatísticos** e descrevem o conjunto de participantes; não substituem o "
        "boletim individual oficial nem preveem aprovação em nenhuma seleção."
    ),
    "grupo_minimo": (
        "Comparações por recorte (estado, renda etc.) só aparecem quando o grupo tem participantes "
        "suficientes; grupos muito pequenos não permitem um percentil confiável."
    ),
}


def resolve_id(texto: str) -> str | None:
    """Liga o que a pessoa escreveu a um id de indicador conhecido, ou None."""
    t = (texto or "").lower()
    # Casa o apelido mais específico (texto mais longo) primeiro.
    achado, tamanho = None, 0
    for id_, apelidos in _APELIDOS.items():
        for apelido in apelidos:
            if apelido in t and len(apelido) > tamanho:
                achado, tamanho = id_, len(apelido)
    return achado


def explicar(id_: str) -> dict | None:
    """Devolve o verbete do indicador, ou None se o id não existir."""
    return INDICADORES.get(id_)

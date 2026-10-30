"""Nomes legíveis para os códigos do INEP, usados nas respostas da API."""

AREAS = {
    "LC": "Linguagens",
    "CH": "Humanas",
    "CN": "Natureza",
    "MT": "Matemática",
    "REDACAO": "Redação",
}

# Q006: renda familiar mensal, em salários mínimos.
RENDA = {
    "A": "Nenhuma renda",
    "B": "Até 1 salário mínimo",
    "C": "De 1 a 1,5 salário",
    "D": "De 1,5 a 2 salários",
    "E": "De 2 a 2,5 salários",
    "F": "De 2,5 a 3 salários",
    "G": "De 3 a 4 salários",
    "H": "De 4 a 5 salários",
    "I": "De 5 a 6 salários",
    "J": "De 6 a 7 salários",
    "K": "De 7 a 8 salários",
    "L": "De 8 a 9 salários",
    "M": "De 9 a 10 salários",
    "N": "De 10 a 12 salários",
    "O": "De 12 a 15 salários",
    "P": "De 15 a 20 salários",
    "Q": "Mais de 20 salários",
}

# TP_ESCOLA: o código 1 é quem não respondeu, não "escola pública".
TIPO_ESCOLA = {
    "1": "Não informou",
    "2": "Pública",
    "3": "Privada",
}

COR_RACA = {
    "0": "Não declarada",
    "1": "Branca",
    "2": "Preta",
    "3": "Parda",
    "4": "Amarela",
    "5": "Indígena",
}

# Q002: até onde a mãe (ou responsável) estudou.
ESCOLARIDADE_MAE = {
    "A": "Nunca estudou",
    "B": "Fundamental I incompleto",
    "C": "Fundamental I completo",
    "D": "Fundamental II completo",
    "E": "Ensino médio completo",
    "F": "Ensino superior completo",
    "G": "Pós-graduação",
    "H": "Não sei",
}

UF = {
    "AC": "Acre", "AL": "Alagoas", "AM": "Amazonas", "AP": "Amapá", "BA": "Bahia",
    "CE": "Ceará", "DF": "Distrito Federal", "ES": "Espírito Santo", "GO": "Goiás",
    "MA": "Maranhão", "MG": "Minas Gerais", "MS": "Mato Grosso do Sul", "MT": "Mato Grosso",
    "PA": "Pará", "PB": "Paraíba", "PE": "Pernambuco", "PI": "Piauí", "PR": "Paraná",
    "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte", "RO": "Rondônia", "RR": "Roraima",
    "RS": "Rio Grande do Sul", "SC": "Santa Catarina", "SE": "Sergipe", "SP": "São Paulo",
    "TO": "Tocantins",
}

RECORTES = {
    "UF": UF,
    "RENDA": RENDA,
    "TIPO_ESCOLA": TIPO_ESCOLA,
    "COR_RACA": COR_RACA,
    "ESCOLARIDADE_MAE": ESCOLARIDADE_MAE,
}

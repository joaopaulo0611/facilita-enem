"""Ferramentas controladas do assistente.

Cada ferramenta recebe parâmetros já validados e devolve texto + evidência,
reutilizando o glossário e o resultado que a pessoa já calculou no radar (o
mesmo formato que /api/radar retorna). Nenhuma ferramenta executa SQL ou código
livre; quando o dado não está disponível, devolve uma resposta SEM_DADOS.

O `resultado` é opcional: se a pessoa ainda não calculou o radar, as ferramentas
que dependem das notas pedem, com gentileza, que ela preencha o formulário.
"""
from __future__ import annotations

import re

import inscricoes as I
import prouni as P
from rotulos import AREAS, RENDA, UF

from . import glossario as G
from .resposta import Evidencia, Resposta, Tipo

_PEDIR_RADAR = (
    "Para isso eu preciso das suas notas. Preencha as cinco notas no formulário e toque em "
    "**Ver meu radar**; depois é só perguntar de novo."
)


def _num(valor, casas: int = 1) -> str:
    """Formata número no padrão brasileiro (vírgula decimal)."""
    texto = f"{valor:,.{casas}f}"
    return texto.replace(",", "·").replace(".", ",").replace("·", ".")


def _com_sinal(valor) -> str:
    return ("+" if valor >= 0 else "−") + _num(abs(valor))


def _evidencia(ferramenta: str, recorte: str = "", limitacoes: str = "") -> Evidencia:
    return Evidencia(
        ferramenta=ferramenta,
        fonte=G.FONTE,
        periodo=G.PERIODO,
        abrangencia=G.ABRANGENCIA,
        recorte=recorte,
        limitacoes=limitacoes,
    )


def explicar_indicador(termo: str) -> Resposta:
    """Explica um indicador do glossário (percentil, média, z-score, nota)."""
    id_ = G.resolve_id(termo)
    verbete = G.explicar(id_) if id_ else None
    if not verbete:
        return Resposta(
            Tipo.SEM_DADOS,
            "Não encontrei esse termo no glossário. Posso explicar, por exemplo: **percentil**, "
            "**média geral**, **média dos participantes**, **z-score** ou como a **nota do ENEM** é calculada.",
            sugestoes=("O que é percentil?", "Como a nota do ENEM é calculada?"),
        )
    partes = [f"**{verbete['nome']}**", "", verbete["definicao"], "", f"**Como ler:** {verbete['como_ler']}"]
    if verbete.get("formula"):
        partes.append(f"**Cálculo:** {verbete['formula']}")
    if verbete.get("limitacoes"):
        partes.append(f"**Atenção:** {verbete['limitacoes']}")
    return Resposta(Tipo.CONCEITO, "\n".join(partes))


def resumo_do_resultado(resultado: dict | None) -> Resposta:
    """Lê o resultado do radar e resume a posição da pessoa (média geral e destaque)."""
    if not resultado:
        return Resposta(Tipo.SEM_DADOS, _PEDIR_RADAR)
    media = resultado.get("media_geral") or {}
    areas = resultado.get("areas") or []
    if not media or not areas:
        return Resposta(Tipo.SEM_DADOS, _PEDIR_RADAR)
    percentil = round(media.get("percentil", 0))
    maior = max(areas, key=lambda a: a.get("nota", 0))
    texto = (
        f"Sua **média geral** é {_num(media['nota'])} pts, {_com_sinal(media['diferenca'])} pts em relação "
        f"à média dos participantes ({_num(media['media_participantes'])}). Isso coloca você no "
        f"**percentil {percentil}**: {percentil} em cada 100 participantes tiveram média menor que a sua. "
        f"Sua maior nota é em **{maior['nome']}** ({_num(maior['nota'])} pts)."
    )
    return Resposta(
        Tipo.DADO,
        texto,
        evidencia=_evidencia("radar.media_geral", recorte="Brasil", limitacoes=G.NOTAS["estatistico"]),
        sugestoes=("O que é percentil?", "Como estou em cada área?"),
    )


def posicao_por_area(resultado: dict | None, area: str | None) -> Resposta:
    """Mostra a posição da pessoa por área (uma específica ou todas)."""
    if not resultado or not resultado.get("areas"):
        return Resposta(Tipo.SEM_DADOS, _PEDIR_RADAR)
    areas = resultado["areas"]
    if area:
        alvo = next((a for a in areas if a["area"] == area), None)
        if not alvo:
            return Resposta(Tipo.SEM_DADOS, _PEDIR_RADAR)
        percentil = round(alvo.get("percentil", 0))
        texto = (
            f"Em **{alvo['nome']}** sua nota é {_num(alvo['nota'])} pts ({_com_sinal(alvo['diferenca'])} pts "
            f"em relação à média de {_num(alvo['media_participantes'])}). Você está no **percentil {percentil}** "
            f"dessa área."
        )
    else:
        linhas = [
            f"- **{a['nome']}:** {_num(a['nota'])} pts · percentil {round(a.get('percentil', 0))} "
            f"({_com_sinal(a['diferenca'])} vs. média {_num(a['media_participantes'])})"
            for a in areas
        ]
        texto = "Sua posição em cada área:\n\n" + "\n".join(linhas)
    return Resposta(
        Tipo.DADO,
        texto,
        evidencia=_evidencia("radar.areas", recorte="Brasil", limitacoes=G.NOTAS["estatistico"]),
        sugestoes=("O que é percentil?", "Qual foi minha maior nota?"),
    )


def como_interpretar_percentil(resultado: dict | None) -> Resposta:
    """Explica o percentil usando, se houver, o número da própria pessoa."""
    verbete = G.explicar("percentil")
    base = f"**{verbete['nome']}**\n\n{verbete['definicao']}\n\n**Como ler:** {verbete['como_ler']}"
    media = (resultado or {}).get("media_geral") or {}
    if media:
        p = round(media.get("percentil", 0))
        base += f"\n\nNo seu caso, a média geral está no **percentil {p}** — à frente de {p}% dos participantes."
        return Resposta(
            Tipo.DADO,
            base,
            evidencia=_evidencia("radar.media_geral", recorte="Brasil", limitacoes=G.NOTAS["estatistico"]),
        )
    return Resposta(Tipo.CONCEITO, base)


def limitacoes() -> Resposta:
    texto = (
        "Pontos a ter em mente sobre os números do Radar ENEM:\n\n"
        f"- {G.NOTAS['base']}\n"
        f"- {G.NOTAS['estatistico']}\n"
        f"- {G.NOTAS['grupo_minimo']}"
    )
    return Resposta(Tipo.CONCEITO, texto)


def ajuda() -> Resposta:
    texto = (
        "Eu sou o assistente do **Radar ENEM**. Respondo com base nos dados e na metodologia do próprio "
        "projeto, sem inventar números. Posso:\n\n"
        "- **Explicar indicadores:** percentil, média geral, z-score, como a nota é calculada;\n"
        "- **Interpretar o seu resultado:** sua posição na média e em cada área (depois que você calcula o radar);\n"
        "- Dizer em que **cursos do SISU** você teria passado, comparando a sua nota com as notas de corte "
        "de 2024 (ampla concorrência), com filtro por curso e por estado;\n"
        "- Esclarecer as **limitações** dos dados.\n\n"
        "- Dizer se você se enquadra no **ProUni**, a partir da sua nota, da escola e da renda por pessoa da família.\n\n"
        "Ainda **não** sei avaliar o FIES; isso fica para uma próxima versão."
    )
    return Resposta(Tipo.CONCEITO, texto)


def fora_de_escopo_inscricao() -> Resposta:
    """FIES: ainda não avaliamos."""
    texto = (
        "Ainda **não** sei avaliar o **FIES** (financiamento). Já consigo dizer se você se enquadra no "
        "**ProUni** (bolsas em faculdades privadas) e em que cursos do **SISU** você teria passado."
    )
    return Resposta(
        Tipo.SEM_DADOS,
        texto,
        sugestoes=("Eu me enquadro no ProUni? Moramos em 4 pessoas.", "Em que cursos eu teria passado?"),
    )


def _uf_citada(pergunta: str) -> str | None:
    """Estado citado na pergunta: sigla em maiúsculas ("SC") ou nome por extenso ("Santa Catarina")."""
    for sigla in UF:
        if re.search(rf"\b{sigla}\b", pergunta):
            return sigla
    texto = I.sem_acento(pergunta)
    # Do nome mais longo ao mais curto: "mato grosso do sul" antes de "mato grosso".
    for sigla, nome in sorted(UF.items(), key=lambda par: len(par[1]), reverse=True):
        if sigla == "PA":
            # "para" sem acento é preposição; só aceita "Pará" escrito com acento.
            if re.search(r"\bpará\b", pergunta.lower()):
                return sigla
            continue
        if re.search(rf"\b{I.sem_acento(nome)}\b", texto):
            return sigla
    return None


def _curso_citado(pergunta: str, base) -> tuple[str | None, bool]:
    """Curso citado na pergunta: (nome sem acento, é família?). "medicina" é exato; "engenharia" é família."""
    texto = I.sem_acento(pergunta)
    nomes = I.nomes_de_curso(base)
    ofertas = base["curso_busca"].astype(str).value_counts()
    for nome in nomes:
        if re.search(rf"\b{re.escape(nome)}\b", texto):
            # Se o nome exato é minoria entre os cursos que começam com ele, a pessoa quis a
            # família: "engenharia" (existe um curso só "ENGENHARIA") vira todas as engenharias,
            # mas "medicina" continua exato e não traz "medicina veterinária".
            na_familia = ofertas[ofertas.index.str.startswith(nome + " ")].sum()
            return nome, bool(na_familia > ofertas.get(nome, 0))
    familias = sorted({nome.split()[0] for nome in nomes if len(nome.split()[0]) >= 5}, key=len, reverse=True)
    for familia in familias:
        if re.search(rf"\b{re.escape(familia)}", texto):
            return familia, True
    return None, False


def _linha_curso(c) -> str:
    via = "" if not c["cota"] else f" · pela cota *{str(c['modalidade_grupo']).removeprefix('Lei de Cotas: ')}*"
    return (
        f"- **{c['curso']}** ({c['grau']}, {c['turno']}) · {c['ies_sigla']}, {c['municipio']}/{c['uf']} · "
        f"nota de corte {_num(c['nota_corte'], 2)} · sua média ponderada {_num(c['sua_nota'], 2)}{via}"
    )


def _sobre_as_cotas(perfil: I.Perfil, consulta) -> str:
    """Explica por que as cotas entraram (ou não) na comparação."""
    if not perfil.completo:
        return (
            "Considerei só a **ampla concorrência**. Para incluir as cotas, marque as perguntas **Sua origem** "
            "(cor ou raça e escola) e **Sua família** (renda), calcule o radar de novo e pergunte outra vez."
        )
    if not perfil.escola_publica:
        return (
            "Considerei só a **ampla concorrência**: as cotas da Lei de Cotas são para quem cursou todo o "
            "ensino médio em escola pública, e você informou outro tipo de escola."
        )
    texto = (
        f"Considerei a ampla concorrência e as cotas da **Lei de Cotas** que o seu perfil permite. "
        f"Só pela ampla concorrência seriam **{_num(consulta.total_ampla, 0)}** cursos."
    )
    if not perfil.renda_ate_1_sm:
        texto += (
            " As cotas de renda exigem até 1 salário mínimo **por pessoa** da família; como o Radar só sabe a "
            "renda total, deixei essas cotas de fora. Se a renda por pessoa da sua família for de até 1 salário "
            "mínimo, você também pode concorrer a elas."
        )
    return texto


def cursos_ao_alcance(resultado: dict | None, pergunta: str, perfil: dict | None = None, base=None) -> Resposta:
    """Cursos do SISU em que a pessoa teria alcançado a nota de corte, na ampla ou nas cotas do perfil."""
    notas = {a["area"]: a["nota"] for a in (resultado or {}).get("areas") or []}
    if set(notas) != set(I.AREAS):
        return Resposta(
            Tipo.SEM_DADOS,
            "Para comparar com as notas de corte do SISU eu preciso das suas cinco notas. "
            "Preencha o formulário e toque em **Ver meu radar**; depois é só perguntar de novo.",
        )
    base = I.carregar() if base is None else base
    perfil_ = I.Perfil.dos_campos(perfil)
    uf = _uf_citada(pergunta)
    curso, familia = _curso_citado(pergunta, base)
    consulta = I.cursos_ao_alcance(notas, base, perfil=perfil_, uf=uf, curso=curso, familia=familia)
    modalidades = "a ampla concorrência e as cotas do seu perfil" if consulta.com_cotas else "a **ampla concorrência**"

    filtros = []
    if curso:
        # Nome como está na base (com acento); a família usa só a palavra citada.
        exemplo = base.loc[base["curso_busca"] == curso, "curso"]
        nome = str(exemplo.iloc[0]).title() if len(exemplo) and not familia else curso.title()
        filtros.append(f"de **{nome}**" + (" (todos os cursos que começam assim)" if familia else ""))
    if uf:
        filtros.append(f"em **{UF[uf]}**")
    onde = "".join(f" {f}" for f in filtros)  # já com o espaço da frente, ou vazio
    recorte = ("Ampla concorrência e Lei de Cotas (perfil)" if consulta.com_cotas else "Ampla concorrência") + (
        f", {curso}" if curso else ""
    ) + (f", {uf}" if uf else "")

    if consulta.avaliados == 0:
        return Resposta(
            Tipo.SEM_DADOS,
            f"Não encontrei cursos{onde} com nota de corte no SISU {consulta.ano}. "
            "Confira o nome do curso ou tente sem o estado.",
            sugestoes=("Em que cursos eu teria passado?",),
        )

    if consulta.total:
        partes = [
            f"Com as suas notas, considerando {modalidades}, você teria alcançado a nota de corte em "
            f"**{_num(consulta.total, 0)} de {_num(consulta.avaliados, 0)} cursos**{onde} no SISU {consulta.ano}. "
            "Os de nota de corte mais alta:",
            "",
            *(_linha_curso(c) for _, c in consulta.cursos.iterrows()),
        ]
    else:
        partes = [f"Com as suas notas, considerando {modalidades}, você **não** teria alcançado a nota de corte{onde} no SISU {consulta.ano}."]
        if consulta.mais_proximo is not None:
            c = consulta.mais_proximo
            via = "" if not c["cota"] else f", pela cota *{str(c['modalidade_grupo']).removeprefix('Lei de Cotas: ')}*"
            partes += [
                "",
                f"O mais perto foi **{c['curso']}** na {c['ies_sigla']} ({c['municipio']}/{c['uf']}){via}: nota de corte "
                f"{_num(c['nota_corte'], 2)}, faltaram {_num(c['falta'], 2)} pontos na sua média ponderada.",
            ]
    partes += [
        "",
        _sobre_as_cotas(perfil_, consulta),
        "",
        "**Atenção:** a nota de corte é de uma edição passada e muda todo ano, conforme a concorrência. "
        "É uma referência, não garantia de vaga. Cada curso usa pesos diferentes para as provas, por isso "
        "a sua média ponderada muda de um curso para outro.",
    ]
    return Resposta(
        Tipo.DADO,
        "\n".join(partes),
        evidencia=Evidencia(
            ferramenta="sisu.cursos_ao_alcance",
            fonte="Notas de corte do SISU, coletadas das APIs do MEC pelo projeto aberto maiakanegae/sisu-data (licença MIT)",
            periodo=f"SISU {consulta.ano}",
            abrangencia=f"{_num(consulta.avaliados, 0)} cursos com nota de corte" + (f" em {UF[uf]}" if uf else " no Brasil"),
            recorte=recorte,
            limitacoes=(
                "Nota de corte histórica. Não inclui cotas para quilombolas e pessoas com deficiência, as ações "
                "afirmativas próprias de cada instituição, bônus regionais nem a concorrência da próxima edição."
            ),
        ),
        sugestoes=("Quais cursos de Medicina eu alcançaria?", "Em que cursos eu teria passado em Santa Catarina?"),
    )


_NUMEROS = {"um": 1, "uma": 1, "dois": 2, "duas": 2, "tres": 3, "quatro": 4, "cinco": 5, "seis": 6,
            "sete": 7, "oito": 8, "nove": 9, "dez": 10}


def pessoas_citadas(pergunta: str) -> int | None:
    """Número de pessoas da família citado na pergunta ("moramos em 4 pessoas", "somos três", "moro sozinho")."""
    texto = I.sem_acento(pergunta)
    if re.search(r"\b(moro|vivo) sozinh[oa]\b", texto):
        return 1
    numero = r"(\d{1,2}|" + "|".join(_NUMEROS) + r")"
    padroes = (
        rf"\b{numero}\s+(pessoas?|moradores?|integrantes?|membros?)\b",
        rf"\b(somos|moramos|vivemos)\s+(em\s+)?{numero}\b",
        rf"\bfamilia\s+de\s+{numero}\b",
    )
    for padrao in padroes:
        achado = re.search(padrao, texto)
        if achado:
            valor = next(g for g in achado.groups() if g and (g.isdigit() or g in _NUMEROS))
            pessoas = int(valor) if valor.isdigit() else _NUMEROS[valor]
            return pessoas if 1 <= pessoas <= 30 else None
    return None


def _sm(valor: float) -> str:
    """Salários mínimos com até duas casas, sem zeros sobrando: 1,5 e 0,75."""
    return _num(valor, 2).rstrip("0").rstrip(",")


def elegibilidade_prouni(resultado: dict | None, pergunta: str, perfil: dict | None = None) -> Resposta:
    """Diz se a pessoa se enquadra no ProUni (integral, parcial ou não), critério por critério."""
    notas = {a["area"]: a["nota"] for a in (resultado or {}).get("areas") or []}
    if set(notas) != set(I.AREAS):
        return Resposta(Tipo.SEM_DADOS, _PEDIR_RADAR)
    perfil = perfil or {}
    pessoas = pessoas_citadas(pergunta)
    av = P.avaliar(notas, perfil.get("tipo_escola") or None, perfil.get("renda") or None, pessoas)

    nota = (
        f"- **Nota:** média das 5 provas {_num(av.media)} pts e redação {_num(av.redacao)}. "
        + ("Atende (mínimo de 450 e redação acima de zero)." if av.nota_ok else "**Não atende**: o mínimo é média 450 e redação acima de zero.")
    )
    if av.escola_publica is None:
        escola = "- **Escola:** não sei. Marque a pergunta **Sua origem** no formulário para informar o tipo de escola."
    elif av.escola_publica:
        escola = "- **Escola:** pública. Atende (o ProUni exige ensino médio todo em escola pública ou como bolsista integral)."
    else:
        escola = (
            "- **Escola:** privada. Só atende se você foi **bolsista integral** da escola, ou se é pessoa com "
            "deficiência ou professor da rede pública, casos que o Radar não pergunta."
        )

    renda_total = perfil.get("renda")
    if not renda_total:
        renda = "- **Renda:** não sei. Marque a pergunta **Sua família** no formulário para informar a renda."
    elif not pessoas:
        renda = (
            f"- **Renda:** a sua família ganha {RENDA[renda_total].lower()} no total, mas o ProUni olha a renda "
            "**por pessoa**. Quantas pessoas moram na sua casa, contando você? Pergunte de novo dizendo, por "
            "exemplo: *Eu me enquadro no ProUni? Moramos em 4 pessoas.*"
        )
    else:
        minimo, maximo = av.faixa_por_pessoa
        faixa = f"mais de {_sm(minimo)}" if maximo == float("inf") else (
            f"até {_sm(maximo)}" if minimo == 0 else f"de {_sm(minimo)} a {_sm(maximo)}"
        )
        unidade = "salário mínimo" if maximo <= 1 else "salários mínimos"
        renda = (
            f"- **Renda por pessoa:** a renda total da família ({RENDA[renda_total].lower()}) dividida por "
            f"{pessoas} {'pessoa' if pessoas == 1 else 'pessoas'} dá **{faixa} {unidade}** por pessoa. Limites: até "
            f"{_sm(av.limite_integral)} para a bolsa integral e até {_sm(av.limite_parcial)} para a parcial."
        )

    if not av.nota_ok:
        conclusao = "Pela nota, você **não** poderia concorrer ao ProUni."
    elif av.escola_publica is False:
        conclusao = "Pela escola, você só poderia concorrer se foi bolsista integral no ensino médio (ou nos outros casos acima)."
    elif av.escola_publica is None or av.renda is None:
        conclusao = "A nota atende. Para eu dizer se você se enquadra, faltam as informações acima."
    else:
        conclusao = {
            P.INTEGRAL: "Pelo que o Radar sabe, você poderia concorrer à **bolsa integral (100%)**.",
            P.PARCIAL: "Pelo que o Radar sabe, você poderia concorrer à **bolsa parcial (50%)**, mas não à integral.",
            P.INTEGRAL_OU_PARCIAL: (
                f"Você poderia concorrer pelo menos à **bolsa parcial (50%)**. A **integral** depende do valor exato: "
                f"vale se a renda por pessoa for de até {_sm(av.limite_integral)} salário mínimo."
            ),
            P.PARCIAL_OU_NAO: (
                f"Depende do valor exato da renda: com até {_sm(av.limite_parcial)} salários mínimos por pessoa, "
                f"você poderia concorrer à bolsa parcial (ou à integral, com até {_sm(av.limite_integral)}); acima disso, não."
            ),
            P.ACIMA: "Pela renda por pessoa, você **não** se enquadraria no ProUni.",
        }[av.renda]

    texto = "\n".join([
        f"**ProUni** (bolsas em faculdades privadas), pelas regras de {av.ano_referencia}:",
        "",
        nota,
        escola,
        renda,
        "",
        conclusao,
        "",
        "**Atenção:** também não pode ter diploma de curso superior, e treineiros não concorrem. Cada curso tem "
        "uma nota de corte própria no ProUni, que o Radar ainda não tem. Confira as regras no edital da edição.",
    ])
    return Resposta(
        Tipo.DADO,
        texto,
        evidencia=Evidencia(
            ferramenta="prouni.elegibilidade",
            fonte="Regras do ProUni (MEC: prouniportal.mec.gov.br e gov.br), versionadas em data/inscricoes/regras_prouni_fies.json",
            periodo=f"regras de {av.ano_referencia}",
            abrangencia="Programa Universidade para Todos (bolsas em instituições privadas)",
            recorte="Nota do radar, escola e renda do formulário" + (f", {pessoas} pessoas na família" if pessoas else ""),
            limitacoes="A renda vem em faixas; a renda por pessoa é estimada pela faixa dividida pelo número de pessoas.",
        ),
        sugestoes=("Eu me enquadro no ProUni? Moramos em 4 pessoas.", "Em que cursos eu teria passado?"),
    )


def nao_sei() -> Resposta:
    texto = (
        "Ainda não sei responder isso. Eu consigo explicar os indicadores do Radar ENEM e interpretar o "
        "seu resultado. Experimente perguntar sobre **percentil**, **média geral** ou peça um **resumo** do "
        "seu resultado."
    )
    return Resposta(
        Tipo.SEM_DADOS,
        texto,
        sugestoes=("O que é percentil?", "Resuma o meu resultado", "O que você faz?"),
    )


# Nome legível de cada área, para a classificação da intenção localizar a área citada.
NOME_AREAS = AREAS

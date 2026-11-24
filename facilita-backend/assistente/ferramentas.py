"""Ferramentas controladas do assistente.

Cada ferramenta recebe parâmetros já validados e devolve texto + evidência,
reutilizando o glossário e o resultado que a pessoa já calculou no radar (o
mesmo formato que /api/radar retorna). Nenhuma ferramenta executa SQL ou código
livre; quando o dado não está disponível, devolve uma resposta SEM_DADOS.

O `resultado` é opcional: se a pessoa ainda não calculou o radar, as ferramentas
que dependem das notas pedem, com gentileza, que ela preencha o formulário.
"""
from __future__ import annotations

from rotulos import AREAS

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
        "- Esclarecer as **limitações** dos dados.\n\n"
        "Ainda **não** sei dizer em que cursos ou universidades você poderia se inscrever — isso depende de "
        "dados de notas de corte (SISU, ProUni) que ainda vamos adicionar."
    )
    return Resposta(Tipo.CONCEITO, texto)


def fora_de_escopo_inscricao() -> Resposta:
    """Pergunta sobre cursos/inscrição: ainda não temos esses dados (será a Fase 2)."""
    texto = (
        "Essa é a pergunta que mais queremos responder, mas ainda **não** tenho os dados de notas de corte "
        "(SISU, ProUni, FIES) para dizer em que cursos ou universidades você poderia se inscrever. Por "
        "enquanto, posso te ajudar a **entender a sua nota** e a sua **posição** em relação aos outros "
        "participantes — e isso já é um bom ponto de partida."
    )
    return Resposta(
        Tipo.SEM_DADOS,
        texto,
        sugestoes=("Resuma o meu resultado", "O que é percentil?"),
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

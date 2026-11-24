"""Orquestração do assistente.

Fluxo: sanitiza a pergunta → checa injeção → classifica a intenção (provedor) →
executa a ferramenta controlada → devolve a Resposta com evidência. A interface
nunca consulta dados direto; o provedor nunca executa código. Todo número vem de
uma ferramenta que reutiliza o resultado oficial do radar.
"""
from __future__ import annotations

from . import ferramentas as F
from . import validacao as V
from .provedor import Provedor, ProvedorSimulado
from .resposta import Resposta, Tipo

RECUSA_INJECAO = (
    "Só consigo responder sobre as notas, os indicadores e a metodologia do Radar ENEM. Não executo "
    "comandos, não acesso arquivos e não compartilho configurações internas."
)

SUGESTOES_INICIAIS = (
    "O que você faz?",
    "O que é percentil?",
    "Resuma o meu resultado",
    "Como estou em Matemática?",
    "Como a nota do ENEM é calculada?",
    "Quais são as limitações dos dados?",
    "Em que cursos eu teria passado?",
    "Quais cursos de Medicina eu alcançaria?",
)


class Orquestrador:
    """Coordena uma pergunta. Recebe um provedor (injetável para testes)."""

    def __init__(self, provedor: Provedor | None = None):
        self.provedor = provedor or ProvedorSimulado()

    def responde(self, pergunta: str, resultado: dict | None = None, perfil: dict | None = None) -> Resposta:
        # 1) sanitização + limite de tamanho
        try:
            texto = V.sanitiza_pergunta(pergunta)
        except V.EntradaInvalida as e:
            return Resposta(Tipo.ERRO, str(e), sugestoes=SUGESTOES_INICIAIS[:4])

        # 2) proteção contra injeção/abuso (aplicada no código, não no prompt)
        if V.parece_injecao(texto):
            return Resposta(Tipo.CONCEITO, RECUSA_INJECAO, sugestoes=SUGESTOES_INICIAIS[:4])

        # 3) intenção (provedor) + 4) ferramenta controlada
        intent = self.provedor.classifica(texto)
        try:
            return self._executa(intent, resultado, perfil)
        except Exception:
            # falha controlada: nunca vaza stack nem caminho interno
            return Resposta(Tipo.ERRO, "Não consegui responder agora. Tente reformular a pergunta.")

    def _executa(self, intent, resultado: dict | None, perfil: dict | None = None) -> Resposta:
        nome = intent.nome
        if nome == "ajuda":
            return F.ajuda()
        if nome == "programas":
            return F.fora_de_escopo_inscricao()
        if nome == "cursos_ao_alcance":
            return F.cursos_ao_alcance(resultado, intent.parametros.get("pergunta", ""), perfil)
        if nome == "limitacoes":
            return F.limitacoes()
        if nome == "interpretar_percentil":
            return F.como_interpretar_percentil(resultado)
        if nome == "resumo_resultado":
            return F.resumo_do_resultado(resultado)
        if nome == "posicao_area":
            return F.posicao_por_area(resultado, intent.parametros.get("area"))
        if nome == "explicar_indicador":
            return F.explicar_indicador(intent.parametros.get("termo", ""))
        return F.nao_sei()

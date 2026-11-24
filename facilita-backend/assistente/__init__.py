"""Assistente do Radar ENEM (Fase 1).

Um assistente determinístico, local e sem custo, no mesmo padrão do Assistente
Pulso (projeto datathon): a pergunta vira uma INTENÇÃO (classificada por
palavras-chave) que o orquestrador transforma na chamada de uma FERRAMENTA
controlada. As ferramentas reutilizam os cálculos oficiais (a camada Gold e o
glossário documentado); o assistente nunca inventa número, fonte ou conclusão.

Nesta fase não há IA generativa nem chamada a nenhuma API externa. A arquitetura
fica pronta para, no futuro, plugar um provedor de LLM com a mesma interface,
sem reescrever interface, ferramentas, contexto ou contratos.
"""

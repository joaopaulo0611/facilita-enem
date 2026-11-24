/** Chamadas ao back-end. Todo erro vira ErroApi com uma mensagem pronta para mostrar. */

export class ErroApi extends Error {
  constructor(mensagem, campos = {}) {
    super(mensagem)
    this.campos = campos
  }
}

async function buscar(caminho, parametros = {}) {
  const consulta = new URLSearchParams(parametros).toString()
  let resposta
  try {
    resposta = await fetch(`/api/${caminho}${consulta ? `?${consulta}` : ''}`)
  } catch {
    throw new ErroApi('Não foi possível falar com o servidor. Confira sua conexão e tente de novo.')
  }
  const corpo = await resposta.json().catch(() => null)
  if (!resposta.ok) {
    const mensagem = typeof corpo?.detail === 'string' ? corpo.detail : 'O servidor não conseguiu calcular agora. Tente de novo em instantes.'
    throw new ErroApi(mensagem, corpo?.campos)
  }
  return corpo
}

export const buscarMetadados = () => buscar('metadados')
export const buscarRadar = (notas) => buscar('radar', notas)
export const buscarRegional = (parametros) => buscar('modulos/regional', parametros)
export const buscarOrigem = (parametros) => buscar('modulos/origem', parametros)
export const buscarFamilia = (parametros) => buscar('modulos/familia', parametros)

export const buscarSugestoesAssistente = () => buscar('assistente/sugestoes')

/** Envia a pergunta e, se houver, o resultado do radar e os campos do perfil (usados nas cotas do SISU). */
export async function perguntarAssistente(pergunta, resultado = null, perfil = null) {
  let resposta
  try {
    resposta = await fetch('/api/assistente/pergunta', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pergunta, resultado, perfil }),
    })
  } catch {
    throw new ErroApi('Não foi possível falar com o assistente. Confira sua conexão e tente de novo.')
  }
  const corpo = await resposta.json().catch(() => null)
  if (!resposta.ok) {
    const mensagem = typeof corpo?.detail === 'string' ? corpo.detail : 'O assistente não conseguiu responder agora. Tente de novo.'
    throw new ErroApi(mensagem)
  }
  return corpo
}

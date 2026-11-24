import { List, Text } from '@chakra-ui/react'

/**
 * Renderiza o markdown leve que o assistente devolve: parágrafos, listas com
 * "- " e trechos em **negrito**. É proposital que seja mínimo — o texto vem do
 * nosso próprio backend, não de conteúdo arbitrário, então não precisamos de um
 * parser completo de markdown (e evitamos a dependência).
 */

/** Quebra uma linha em pedaços de texto normal e em negrito (**assim**). */
function comNegrito(linha, chave) {
  const partes = linha.split(/(\*\*[^*]+\*\*)/g).filter(Boolean)
  return partes.map((parte, i) =>
    parte.startsWith('**') && parte.endsWith('**') ? (
      <Text as="strong" fontWeight="semibold" key={`${chave}-${i}`}>
        {parte.slice(2, -2)}
      </Text>
    ) : (
      <Text as="span" key={`${chave}-${i}`}>
        {parte}
      </Text>
    ),
  )
}

export default function TextoResposta({ texto }) {
  const linhas = texto.split('\n')
  const blocos = []
  let i = 0
  let chave = 0
  while (i < linhas.length) {
    const linha = linhas[i]
    if (linha.trim() === '') {
      i += 1
      continue
    }
    if (linha.trimStart().startsWith('- ')) {
      // Agrupa linhas consecutivas de lista num único <ul>.
      const itens = []
      while (i < linhas.length && linhas[i].trimStart().startsWith('- ')) {
        itens.push(linhas[i].trimStart().slice(2))
        i += 1
      }
      blocos.push(
        <List.Root key={`b-${chave}`} gap="1" ps="4">
          {itens.map((item, j) => (
            <List.Item key={`li-${chave}-${j}`}>{comNegrito(item, `li-${chave}-${j}`)}</List.Item>
          ))}
        </List.Root>,
      )
      chave += 1
      continue
    }
    blocos.push(
      <Text key={`p-${chave}`}>{comNegrito(linha, `p-${chave}`)}</Text>,
    )
    chave += 1
    i += 1
  }
  return blocos
}

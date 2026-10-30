import { HStack, Text } from '@chakra-ui/react'
import ConstructionOutlined from '@mui/icons-material/ConstructionOutlined'
import Cartao from './Cartao'
import Icone from './Icone'

export default function CartaoEmConstrucao({ modulo }) {
  return (
    <Cartao titulo={modulo.titulo} subtitulo={<Text as="span" fontStyle="italic" color="fg">{modulo.pergunta}</Text>}>
      <HStack gap="2" textStyle="sm" color="fg.muted">
        <Icone de={ConstructionOutlined} tamanho={18} />
        <Text>Esta comparação chega na próxima versão.</Text>
      </HStack>
    </Cartao>
  )
}

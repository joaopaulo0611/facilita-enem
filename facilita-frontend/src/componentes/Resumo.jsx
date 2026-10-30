import { Card, Flex, SimpleGrid, Stat } from '@chakra-ui/react'
import EmojiEventsOutlined from '@mui/icons-material/EmojiEventsOutlined'
import GroupsOutlined from '@mui/icons-material/GroupsOutlined'
import InsightsOutlined from '@mui/icons-material/InsightsOutlined'
import * as f from '../formato'
import Icone from './Icone'

function Indicador({ icone, rotulo, valor, unidade, detalhe, destaque = false }) {
  return (
    <Card.Root bg={destaque ? 'colorPalette.solid' : undefined} borderColor={destaque ? 'colorPalette.solid' : undefined}>
      <Card.Body>
        <Stat.Root>
          <Flex justify="space-between" gap="2">
            <Stat.Label color={destaque ? 'whiteAlpha.800' : 'fg.muted'}>{rotulo}</Stat.Label>
            <Icone de={icone} color={destaque ? 'whiteAlpha.800' : 'colorPalette.fg'} />
          </Flex>
          <Stat.ValueText mt="2" textStyle="4xl" fontWeight="bold" color={destaque ? 'white' : 'fg'} fontVariantNumeric="tabular-nums">
            {valor}
            {unidade && (
              <Stat.ValueUnit textStyle="md" color={destaque ? 'whiteAlpha.800' : 'fg.muted'}>
                {unidade}
              </Stat.ValueUnit>
            )}
          </Stat.ValueText>
          <Stat.HelpText mt="2" textStyle="sm" color={destaque ? 'whiteAlpha.900' : 'fg.muted'}>
            {detalhe}
          </Stat.HelpText>
        </Stat.Root>
      </Card.Body>
    </Card.Root>
  )
}

export default function Resumo({ resultado }) {
  const { media_geral: media, areas } = resultado
  const maior = areas.reduce((a, b) => (b.nota > a.nota ? b : a))
  const abaixo = Math.round(media.percentil)
  return (
    <SimpleGrid columns={{ base: 1, sm: 3 }} gap="4">
      <Indicador
        destaque
        icone={InsightsOutlined}
        rotulo="Sua média geral"
        valor={f.nota(media.nota)}
        unidade="pts"
        detalhe={`${f.diferenca(media.diferenca)} pts em relação à média dos participantes (${f.nota(media.media_participantes)})`}
      />
      <Indicador
        icone={GroupsOutlined}
        rotulo="Percentil da média geral"
        valor={`${abaixo}%`}
        detalhe={`${abaixo} em cada 100 participantes tiveram média menor que a sua`}
      />
      <Indicador
        icone={EmojiEventsOutlined}
        rotulo="Sua maior nota"
        valor={f.nota(maior.nota)}
        unidade="pts"
        detalhe={`${maior.nome} é o seu destaque`}
      />
    </SimpleGrid>
  )
}

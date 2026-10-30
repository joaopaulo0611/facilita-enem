import { Badge, Box, SimpleGrid, Text } from '@chakra-ui/react'
import ArrowDownward from '@mui/icons-material/ArrowDownward'
import ArrowUpward from '@mui/icons-material/ArrowUpward'
import * as f from '../formato'
import Cartao from './Cartao'

export default function AreaAArea({ resultado }) {
  return (
    <Cartao titulo="Área a área" subtitulo="Sua nota, a média dos participantes e o percentil em cada prova.">
      <SimpleGrid as="ul" listStyleType="none" columns={{ base: 2, sm: 3, lg: 5 }} columnGap="4" rowGap="5">
        {resultado.areas.map((a) => {
          const acima = a.diferenca >= 0
          return (
            <Box as="li" key={a.area} borderLeftWidth="2px" pl="3" fontVariantNumeric="tabular-nums">
              <Text textStyle="sm" color="fg.muted">{a.nome}</Text>
              <Text mt="1" textStyle="2xl" fontWeight="bold" color="fg">{f.nota(a.nota)}</Text>
              <Text textStyle="xs" color="fg.muted">média {f.nota(a.media_participantes)}</Text>
              <Badge mt="2" rounded="full" colorPalette={acima ? 'green' : 'gray'} variant="subtle" gap="0.5">
                {acima ? <ArrowUpward sx={{ fontSize: 13 }} aria-hidden /> : <ArrowDownward sx={{ fontSize: 13 }} aria-hidden />}
                {f.diferenca(Math.round(a.diferenca)).replace(',0', '')} pts
              </Badge>
              <Text mt="1" textStyle="xs" color="fg">percentil {f.percentual(a.percentil)}</Text>
            </Box>
          )
        })}
      </SimpleGrid>
      <Text mt="5" textStyle="xs" color="fg.muted">
        A média geral é a média simples das cinco provas, todas com o mesmo peso. O percentil diz quantos participantes, em cada 100, tiveram nota menor que a sua.
      </Text>
    </Cartao>
  )
}

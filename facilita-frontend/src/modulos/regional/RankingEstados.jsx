import { Box, HStack, Text } from '@chakra-ui/react'
import { useState } from 'react'
import Dica from '../../componentes/Dica'
import * as f from '../../formato'
import { cor, textoSvg } from '../../svg'

const LINHA = 15
const ROTULO = 30
const LARGURA = 360
const MARGEM_TOPO = 22

/** Gráfico de pontos: o percentil da mesma nota em cada UF, com o Brasil como referência. */
export default function RankingEstados({ dados }) {
  const [ativo, setAtivo] = useState(null)
  const { ranking, uf, brasil } = dados
  const valores = [...ranking.map((r) => r.percentil), brasil.percentil]
  let minimo = Math.floor(Math.min(...valores) / 5) * 5
  let maximo = Math.ceil(Math.max(...valores) / 5) * 5
  if (maximo - minimo < 10) minimo = Math.max(0, maximo - 10)
  if (maximo === minimo) maximo = minimo + 10
  const ticks = [minimo, (minimo + maximo) / 2, maximo]

  const larguraUtil = LARGURA - ROTULO - 12
  const x = (valor) => ROTULO + ((valor - minimo) / (maximo - minimo)) * larguraUtil
  const altura = MARGEM_TOPO + ranking.length * LINHA + 6
  const xBrasil = x(brasil.percentil)

  return (
    <Box as="figure" position="relative">
      <Text as="figcaption" mb="1" textStyle="sm" color="fg.muted">Percentil da mesma nota em cada estado</Text>
      <svg viewBox={`0 0 ${LARGURA} ${altura}`} width="100%" role="img" aria-label={`Percentil da sua nota em cada estado, de ${f.percentual(ranking[0].percentil)} em ${ranking[0].nome} a ${f.percentual(ranking.at(-1).percentil)} em ${ranking.at(-1).nome}.`}>
        {ticks.map((tick) => (
          <g key={tick}>
            <line x1={x(tick)} x2={x(tick)} y1={MARGEM_TOPO - 4} y2={altura - 4} stroke={cor('grade')} />
            <text x={x(tick)} y={10} textAnchor="middle" {...textoSvg(10)}>
              {f.percentual(tick)}
            </text>
          </g>
        ))}
        <line x1={xBrasil} x2={xBrasil} y1={MARGEM_TOPO - 4} y2={altura - 4} stroke={cor('fg')} strokeOpacity="0.5" />
        <text x={xBrasil} y={MARGEM_TOPO - 7} textAnchor="middle" {...textoSvg(10, 'fg')}>
          Brasil
        </text>

        {ranking.map((linha, i) => {
          const y = MARGEM_TOPO + i * LINHA + LINHA / 2
          const eu = linha.uf === uf
          return (
            <g key={linha.uf} onMouseEnter={() => setAtivo(i)} onMouseLeave={() => setAtivo(null)}>
              <rect x="0" y={y - LINHA / 2} width={LARGURA} height={LINHA} fill={ativo === i ? cor('fundo') : 'transparent'} />
              <text x={ROTULO - 8} y={y + 3.5} textAnchor="end" {...textoSvg(10, 'fg', { fontWeight: eu ? 'bold' : 'normal' })}>
                {linha.uf}
              </text>
              <circle
                cx={x(linha.percentil)}
                cy={y}
                r={eu ? 5.5 : 4}
                fill={eu ? cor('voce') : cor('media')}
                fillOpacity={eu ? 1 : 0.75}
                stroke="white"
                strokeWidth="2"
              />
            </g>
          )
        })}
      </svg>

      {ativo !== null && (
        <Dica right="0" top={`${((MARGEM_TOPO + ativo * LINHA) / altura) * 100}%`}>
          <Text fontWeight="bold" color="fg">{ranking[ativo].nome}</Text>
          <Text color="fg">percentil {f.percentual(ranking[ativo].percentil)}</Text>
          <Text color="fg.muted">média do estado {f.nota(ranking[ativo].media)}</Text>
        </Dica>
      )}
      <HStack as="ul" listStyleType="none" mt="1" gap="4" textStyle="xs" color="fg">
        <HStack as="li" gap="1.5">
          <Box boxSize="2.5" rounded="full" bg="voce" aria-hidden /> Seu estado
        </HStack>
        <HStack as="li" gap="1.5">
          <Box boxSize="2.5" rounded="full" bg="media" opacity="0.75" aria-hidden /> Outros estados
        </HStack>
      </HStack>
    </Box>
  )
}

import { Alert, Box, HStack, Text } from '@chakra-ui/react'
import TrendingUp from '@mui/icons-material/TrendingUp'
import { useState } from 'react'
import * as f from '../formato'
import { cor, textoSvg } from '../svg'
import Cartao from './Cartao'
import Dica from './Dica'

const LARGURA = 420
const ALTURA = 340
const CX = LARGURA / 2
const CY = ALTURA / 2
const RAIO = 118
const ANEIS = [200, 400, 600, 800, 1000]

// Linguagens no topo e as demais em sentido horário, como no boletim.
function ponto(indice, total, valor) {
  const angulo = -Math.PI / 2 + (indice * 2 * Math.PI) / total
  const r = (valor / 1000) * RAIO
  return [CX + r * Math.cos(angulo), CY + r * Math.sin(angulo)]
}

const poligono = (valores) => valores.map((v, i) => ponto(i, valores.length, v).join(',')).join(' ')

function Legenda() {
  return (
    <HStack as="ul" listStyleType="none" justify="center" gap="5" textStyle="xs" color="fg">
      <HStack as="li" gap="1.5">
        <svg width="18" height="8" aria-hidden>
          <line x1="1" y1="4" x2="17" y2="4" stroke={cor('voce')} strokeWidth="2" strokeLinecap="round" />
        </svg>
        Você
      </HStack>
      <HStack as="li" gap="1.5">
        <svg width="18" height="8" aria-hidden>
          <line x1="1" y1="4" x2="17" y2="4" stroke={cor('media')} strokeWidth="2" strokeDasharray="4 3" />
        </svg>
        Média dos participantes
      </HStack>
    </HStack>
  )
}

export default function MapaDeNotas({ resultado }) {
  const { areas } = resultado
  const [ativo, setAtivo] = useState(null)
  const total = areas.length
  const acima = areas.filter((a) => a.diferenca > 0).length
  const maisPerto = areas.reduce((a, b) => (b.diferenca < a.diferenca ? b : a))

  return (
    <Cartao titulo="Seu mapa de notas" subtitulo="Cada ponta é uma área, de 0 no centro a 1.000 na borda.">
      <Box position="relative">
        <svg viewBox={`0 0 ${LARGURA} ${ALTURA}`} width="100%" role="img" aria-label="Gráfico radar comparando suas notas com a média dos participantes em cada área">
          {ANEIS.map((anel) => (
            <polygon key={anel} points={poligono(areas.map(() => anel))} fill="none" stroke={cor('grade')} strokeWidth="1" />
          ))}
          {areas.map((_, i) => {
            const [x, y] = ponto(i, total, 1000)
            return <line key={i} x1={CX} y1={CY} x2={x} y2={y} stroke={cor('grade')} strokeWidth="1" />
          })}

          <polygon
            points={poligono(areas.map((a) => a.media_participantes))}
            fill="none"
            stroke={cor('media')}
            strokeWidth="2"
            strokeDasharray="5 4"
            strokeLinejoin="round"
          />
          <g className="radar-abrindo" key={areas.map((a) => a.nota).join()}>
            <polygon
              points={poligono(areas.map((a) => a.nota))}
              fill={cor('voce')}
              fillOpacity="0.12"
              stroke={cor('voce')}
              strokeWidth="2"
              strokeLinejoin="round"
            />
            {areas.map((a, i) => {
              const [x, y] = ponto(i, total, a.nota)
              return <circle key={a.area} cx={x} cy={y} r="5" fill={cor('voce')} stroke="white" strokeWidth="2" />
            })}
          </g>

          {areas.map((a, i) => {
            const [x, y] = ponto(i, total, 1000)
            const dx = x - CX
            const ancora = Math.abs(dx) < 5 ? 'middle' : dx > 0 ? 'start' : 'end'
            const desloc = Math.abs(dx) < 5 ? 0 : dx > 0 ? 10 : -10
            const topo = y < CY - RAIO + 5
            const ly = topo ? y - 22 : y + (y > CY ? 14 : -4)
            return (
              <text key={a.area} x={x + desloc} y={ly} textAnchor={ancora} {...textoSvg(12, 'fg')}>
                <tspan x={x + desloc}>{a.nome}</tspan>
                <tspan x={x + desloc} dy="14" fill={cor('fg')} style={{ fontWeight: 'bold' }}>
                  {f.nota(a.nota)}
                </tspan>
              </text>
            )
          })}

          {/* Alvos de foco e hover maiores que os pontos, um por área. */}
          {areas.map((a, i) => {
            const [x, y] = ponto(i, total, a.nota)
            return (
              <circle
                key={a.area}
                cx={x}
                cy={y}
                r="16"
                fill="transparent"
                tabIndex={0}
                role="button"
                aria-label={`${a.nome}: sua nota ${f.nota(a.nota)}, média ${f.nota(a.media_participantes)}`}
                onMouseEnter={() => setAtivo(i)}
                onMouseLeave={() => setAtivo(null)}
                onFocus={() => setAtivo(i)}
                onBlur={() => setAtivo(null)}
                style={{ cursor: 'pointer', outline: 'none' }}
              />
            )
          })}
        </svg>

        {ativo !== null && (() => {
          const a = areas[ativo]
          const [x, y] = ponto(ativo, total, a.nota)
          return (
            <Dica left={`${(x / LARGURA) * 100}%`} top={`${(y / ALTURA) * 100}%`} transform="translate(-50%, calc(-100% - 14px))" w="48">
              <Text textStyle="sm" fontWeight="semibold" color="fg">{a.nome}</Text>
              <Box as="dl" mt="1" display="grid" gridTemplateColumns="1fr auto" columnGap="3" rowGap="0.5">
                <Text as="dt" color="fg.muted">Sua nota</Text>
                <Text as="dd" textAlign="right" fontWeight="bold" color="fg">{f.nota(a.nota)}</Text>
                <Text as="dt" color="fg.muted">Média</Text>
                <Text as="dd" textAlign="right" color="fg">{f.nota(a.media_participantes)}</Text>
                <Text as="dt" color="fg.muted">Percentil</Text>
                <Text as="dd" textAlign="right" color="fg">{f.percentual(a.percentil)}</Text>
              </Box>
            </Dica>
          )
        })()}
      </Box>

      <Legenda />

      <Alert.Root mt="4" status={acima === total ? 'success' : 'info'}>
        <Alert.Indicator>
          <TrendingUp sx={{ fontSize: 18 }} />
        </Alert.Indicator>
        <Alert.Title fontWeight="normal">
          {acima === total
            ? 'Você está acima da média dos participantes em todas as áreas.'
            : `Você está acima da média em ${acima} de ${total} áreas. ${maisPerto.nome} é onde há mais espaço para crescer.`}
        </Alert.Title>
      </Alert.Root>
    </Cartao>
  )
}

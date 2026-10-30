import { Box, HStack, Progress, Text } from '@chakra-ui/react'
import { useState } from 'react'
import * as f from '../formato'
import { cor, textoSvg, tituloSvg } from '../svg'
import Cartao from './Cartao'
import Dica from './Dica'

const LARGURA = 420
const ALTURA = 190
const MARGEM = { topo: 30, base: 22, lado: 8 }

// Topo arredondado de 4px e base reta, apoiada no eixo.
function coluna(x, y, largura, altura) {
  const r = Math.min(4, largura / 2, altura)
  const base = y + altura
  return `M${x},${base} V${y + r} Q${x},${y} ${x + r},${y} H${x + largura - r} Q${x + largura},${y} ${x + largura},${y + r} V${base} Z`
}

export default function OndeVoceEsta({ resultado }) {
  const { media_geral: media, histograma, participantes, anos } = resultado
  const [ativo, setAtivo] = useState(null)
  const { inicio, largura: passo, contagens } = histograma
  const fim = inicio + passo * contagens.length

  const areaX = LARGURA - 2 * MARGEM.lado
  const areaY = ALTURA - MARGEM.topo - MARGEM.base
  const x = (valor) => MARGEM.lado + ((Math.min(Math.max(valor, inicio), fim) - inicio) / (fim - inicio)) * areaX
  const maior = Math.max(...contagens)
  const faixa = areaX / contagens.length
  const larguraColuna = Math.min(24, faixa - 2)
  const xVoce = x(media.nota)
  const acima = Math.max(0, 100 - media.percentil)

  return (
    <Cartao titulo="Onde você está" subtitulo={`Médias gerais de ${f.pessoas(participantes)} participações no ENEM ${f.anos(anos)}.`}>
      <HStack align="baseline" gap="2">
        <Text textStyle="4xl" fontWeight="bold" color="fg">
          Top {f.percentual(acima)}
        </Text>
        <Text textStyle="sm" color="fg.muted">pela média geral</Text>
      </HStack>

      <Box position="relative" mt="2">
        <svg viewBox={`0 0 ${LARGURA} ${ALTURA}`} width="100%" role="img" aria-label={`Histograma das médias gerais. Sua média, ${f.nota(media.nota)}, fica à frente de ${f.percentual(media.percentil)} dos participantes.`}>
          {contagens.map((qtd, i) => {
            const altura = (qtd / maior) * areaY
            const x0 = MARGEM.lado + i * faixa + (faixa - larguraColuna) / 2
            const limite = inicio + (i + 1) * passo
            return (
              <path
                key={i}
                d={coluna(x0, MARGEM.topo + areaY - altura, larguraColuna, altura)}
                fill={limite <= media.nota ? cor('media') : cor('barra')}
                fillOpacity={limite <= media.nota ? 0.55 : 1}
                opacity={ativo === null || ativo === i ? 1 : 0.5}
              />
            )
          })}
          <line x1={MARGEM.lado} x2={LARGURA - MARGEM.lado} y1={MARGEM.topo + areaY} y2={MARGEM.topo + areaY} stroke={cor('linha')} />
          {Array.from({ length: Math.floor((fim - inicio) / 100) + 1 }, (_, i) => inicio + i * 100).map((tick) => (
            <text key={tick} x={x(tick)} y={ALTURA - 6} textAnchor="middle" {...textoSvg(11)}>
              {tick}
            </text>
          ))}

          <line x1={xVoce} x2={xVoce} y1={MARGEM.topo - 6} y2={MARGEM.topo + areaY} stroke={cor('voce')} strokeWidth="2" />
          <g transform={`translate(${Math.min(Math.max(xVoce, 30), LARGURA - 30)}, ${MARGEM.topo - 16})`}>
            <rect x="-26" y="-11" width="52" height="20" rx="10" fill={cor('voce')} />
            <text textAnchor="middle" y="3.5" {...tituloSvg(12, 'white')}>
              Você
            </text>
          </g>

          {contagens.map((_, i) => (
            <rect
              key={i}
              x={MARGEM.lado + i * faixa}
              y={MARGEM.topo}
              width={faixa}
              height={areaY}
              fill="transparent"
              onMouseEnter={() => setAtivo(i)}
              onMouseLeave={() => setAtivo(null)}
            />
          ))}
        </svg>

        {ativo !== null && (
          <Dica left={`${((MARGEM.lado + (ativo + 0.5) * faixa) / LARGURA) * 100}%`} top="0" transform="translateX(-50%)" whiteSpace="nowrap">
            <Text fontWeight="bold" color="fg">
              {inicio + ativo * passo} a {inicio + (ativo + 1) * passo} pts
            </Text>
            <Text color="fg.muted">{f.pessoas(contagens[ativo])} participantes</Text>
          </Dica>
        )}
      </Box>

      <Progress.Root mt="3" value={media.percentil} size="sm" shape="full" aria-label="Participantes abaixo de você">
        <Progress.Track>
          <Progress.Range />
        </Progress.Track>
      </Progress.Root>
      <HStack mt="1.5" justify="space-between" textStyle="xs" fontVariantNumeric="tabular-nums">
        <Text fontWeight="bold" color="colorPalette.fg">{f.percentual(media.percentil)} abaixo de você</Text>
        <Text color="fg.muted">{f.percentual(acima)} à frente</Text>
      </HStack>
    </Cartao>
  )
}

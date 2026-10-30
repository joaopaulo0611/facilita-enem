import { Alert, Box, Button, Grid, HStack, SimpleGrid, Spinner, Text, Wrap } from '@chakra-ui/react'
import PlaceOutlined from '@mui/icons-material/PlaceOutlined'
import { useEffect, useState } from 'react'
import { buscarRegional } from '../../api'
import { AREAS } from '../../campos'
import * as f from '../../formato'
import Cartao from '../../componentes/Cartao'
import Icone from '../../componentes/Icone'
import RankingEstados from './RankingEstados'

const OPCOES_AREA = [{ codigo: 'MEDIA', nome: 'Média geral' }, ...AREAS]

function Posicao({ rotulo, dados, destaque }) {
  return (
    <Box p="4" rounded="l3" bg={destaque ? 'colorPalette.subtle' : 'bg.muted'} fontVariantNumeric="tabular-nums">
      <Text textStyle="sm" color="fg.muted">{rotulo}</Text>
      <Text mt="1" textStyle="3xl" fontWeight="bold" color="fg">
        {f.percentual(dados.percentil)}
      </Text>
      <Text textStyle="xs" color="fg">
        tiveram nota menor · média {f.nota(dados.media)} · {f.pessoas(dados.participantes)} pessoas
      </Text>
    </Box>
  )
}

function frase(dados) {
  const diferenca = dados.estado.percentil - dados.brasil.percentil
  if (Math.abs(diferenca) < 0.5) return `Em ${dados.nome_uf}, sua posição é praticamente a mesma que no Brasil todo.`
  const pontos = f.nota(Math.abs(diferenca)).replace(',0', '')
  return diferenca > 0
    ? `Em ${dados.nome_uf}, sua nota rende uma posição ${pontos} pontos percentuais melhor que no Brasil todo.`
    : `Em ${dados.nome_uf}, a concorrência é mais forte: sua posição fica ${pontos} pontos percentuais abaixo da nacional.`
}

export default function CartaoRegional({ modulo, perfil, resultado }) {
  const [area, setArea] = useState('MEDIA')
  const [estado, setEstado] = useState({ dados: null, erro: null })
  const nota = area === 'MEDIA' ? resultado.media_geral.nota : perfil.notas[AREAS.find((a) => a.codigo === area).id]
  const uf = perfil.campos.uf

  useEffect(() => {
    let atual = true
    buscarRegional({ area, nota, uf })
      .then((dados) => atual && setEstado({ dados, erro: null }))
      .catch((erro) => atual && setEstado({ dados: null, erro: erro.message }))
    return () => {
      atual = false
    }
  }, [area, nota, uf])

  const { dados, erro } = estado
  const carregando = !erro && dados?.uf !== uf

  return (
    <Cartao titulo={modulo.titulo} subtitulo={modulo.pergunta} acao={<Icone de={PlaceOutlined} color="colorPalette.fg" />}>
      <Wrap role="radiogroup" aria-label="Área comparada" gap="1.5" mt="-1" mb="4">
        {OPCOES_AREA.map((opcao) => {
          const marcada = area === opcao.codigo
          return (
            <Button
              key={opcao.codigo}
              role="radio"
              aria-checked={marcada}
              onClick={() => setArea(opcao.codigo)}
              size="xs"
              rounded="full"
              variant={marcada ? 'solid' : 'outline'}
            >
              {opcao.nome}
            </Button>
          )
        })}
      </Wrap>

      {erro && (
        <Alert.Root status="error">
          <Alert.Indicator />
          <Alert.Title fontWeight="normal">{erro}</Alert.Title>
        </Alert.Root>
      )}
      {!erro && !dados && (
        <HStack gap="2" textStyle="sm" color="fg.muted">
          <Spinner size="sm" />
          <Text>Calculando…</Text>
        </HStack>
      )}
      {dados && (
        <Grid templateColumns={{ base: '1fr', lg: 'minmax(0,5fr) minmax(0,6fr)' }} gap="6" opacity={carregando ? 0.6 : 1} aria-busy={carregando}>
          <div>
            <Text textStyle="sm" color="fg">
              Com <Text as="strong" color="fg" fontVariantNumeric="tabular-nums">{f.nota(dados.nota)} pts</Text> em{' '}
              {OPCOES_AREA.find((a) => a.codigo === dados.area).nome.toLowerCase()}:
            </Text>
            <SimpleGrid mt="3" columns={2} gap="3">
              <Posicao rotulo={`Em ${dados.nome_uf}`} dados={dados.estado} destaque />
              <Posicao rotulo="No Brasil" dados={dados.brasil} />
            </SimpleGrid>
            <Text mt="4" textStyle="md" color="fg">{frase(dados)}</Text>
            <Text mt="2" textStyle="sm" color="fg">
              A mesma nota ficaria mais bem posicionada em <strong>{dados.ranking[0].nome}</strong> ({f.percentual(dados.ranking[0].percentil)}) e menos em{' '}
              <strong>{dados.ranking.at(-1).nome}</strong> ({f.percentual(dados.ranking.at(-1).percentil)}).
            </Text>
            <Text mt="4" textStyle="xs" color="fg.muted">O estado considerado é onde a prova foi feita, como registra o INEP.</Text>
          </div>
          <RankingEstados dados={dados} />
        </Grid>
      )}
    </Cartao>
  )
}

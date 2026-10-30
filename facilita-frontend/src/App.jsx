import { Box, Container, EmptyState, Flex, Heading, SimpleGrid, Stack, Text, VisuallyHidden } from '@chakra-ui/react'
import QueryStatsOutlined from '@mui/icons-material/QueryStatsOutlined'
import { useEffect, useRef, useState } from 'react'
import { buscarMetadados, buscarRadar } from './api'
import { AREAS, CAMPOS_PERGUNTA } from './campos'
import AreaAArea from './componentes/AreaAArea'
import Cabecalho from './componentes/Cabecalho'
import Comparativos from './componentes/Comparativos'
import FormularioPerfil from './componentes/FormularioPerfil'
import MapaDeNotas from './componentes/MapaDeNotas'
import OndeVoceEsta from './componentes/OndeVoceEsta'
import Resumo from './componentes/Resumo'
import * as f from './formato'
import { MODULOS } from './modulos'

const NOTAS_VAZIAS = Object.fromEntries(AREAS.map((a) => [a.id, '']))
const CAMPOS_VAZIOS = Object.fromEntries(CAMPOS_PERGUNTA.map((c) => [c.id, '']))

/** Confere as notas antes de chamar a API; devolve as notas em número e os erros por campo. */
function validarNotas(notas) {
  const valores = {}
  const erros = {}
  for (const area of AREAS) {
    const texto = notas[area.id]
    const valor = f.lerNota(texto)
    if (String(texto).trim() === '') erros[area.id] = `Informe a nota de ${area.nome}.`
    else if (valor === null) erros[area.id] = 'Use só números, como 680 ou 680,5.'
    else if (valor > 1000) erros[area.id] = 'A nota vai de 0 a 1.000.'
    else valores[area.id] = valor
  }
  return { valores, erros }
}

/** Cada pergunta marcada precisa dos campos dela preenchidos. */
function validarPerguntas(perguntas, campos) {
  const erros = {}
  for (const modulo of MODULOS.filter((m) => perguntas.includes(m.id))) {
    for (const id of modulo.campos) {
      if (!campos[id]) erros[id] = 'Escolha uma opção para responder esta pergunta.'
    }
  }
  return erros
}

const semCampo = (id) => (atual) => {
  const resto = { ...atual }
  delete resto[id]
  return resto
}

function Introducao() {
  return (
    <Container maxW="6xl" px={{ base: 4, sm: 6 }} pt="8">
      <Heading as="h1" mt="2" maxW="2xl" size={{ base: '3xl', sm: '4xl' }} color="fg" lineHeight="shorter">
        Descubra onde você está em relação aos outros candidatos
      </Heading>
    </Container>
  )
}

function Vazio({ metadados }) {
  const participantes = metadados?.participantes
  return (
    <EmptyState.Root borderWidth="1px" borderStyle="dashed" rounded="l3">
      <EmptyState.Content>
        <EmptyState.Indicator>
          <QueryStatsOutlined sx={{ fontSize: 48 }} />
        </EmptyState.Indicator>
        <Stack textAlign="center" gap="1">
          <EmptyState.Title as="h2" textStyle="xl" color="fg">
            Seu radar aparece aqui
          </EmptyState.Title>
          <EmptyState.Description maxW="sm" color="fg">
            Preencha as cinco notas e toque em <strong>Ver meu radar</strong>
            {participantes ? ` para ver sua posição entre ${f.pessoas(participantes)} participantes.` : '.'}
          </EmptyState.Description>
        </Stack>
      </EmptyState.Content>
    </EmptyState.Root>
  )
}

export default function App() {
  const [metadados, setMetadados] = useState(null)
  const [notas, setNotas] = useState(NOTAS_VAZIAS)
  const [perguntas, setPerguntas] = useState([])
  const [campos, setCampos] = useState(CAMPOS_VAZIOS)
  const [erros, setErros] = useState({})
  const [erroGeral, setErroGeral] = useState(null)
  const [calculando, setCalculando] = useState(false)
  const [enviado, setEnviado] = useState(null)
  const painel = useRef(null)

  useEffect(() => {
    buscarMetadados()
      .then((dados) => {
        setMetadados(dados)
      })
      .catch((erro) => setErroGeral(erro.message))
  }, [])

  async function verRadar() {
    const { valores, erros: errosNotas } = validarNotas(notas)
    const novosErros = { ...errosNotas, ...validarPerguntas(perguntas, campos) }
    setErros(novosErros)
    setErroGeral(null)
    if (Object.keys(novosErros).length) {
      document.getElementById(Object.keys(novosErros)[0])?.focus()
      return
    }
    setCalculando(true)
    try {
      const resultado = await buscarRadar(valores)
      setEnviado({ notas: valores, perguntas, campos, resultado })
      painel.current?.scrollIntoView({ behavior: 'smooth' })
    } catch (erro) {
      setErros(erro.campos ?? {})
      setErroGeral(erro.message)
    } finally {
      setCalculando(false)
    }
  }

  return (
    <Box minH="100vh">
      <Cabecalho />
      <main>
        <Introducao />

        <Container maxW="6xl" px={{ base: 4, sm: 6 }} py="6">
          <Stack gap="6">
            <FormularioPerfil
              metadados={metadados}
              notas={notas}
              perguntas={perguntas}
              campos={campos}
              erros={erros}
              erroGeral={erroGeral}
              calculando={calculando}
              aoMudarNota={(id, valor) => {
                setNotas((atual) => ({ ...atual, [id]: valor }))
                setErros(semCampo(id))
              }}
              aoMarcarPergunta={(id) => {
                const desmarcando = perguntas.includes(id)
                setPerguntas(desmarcando ? perguntas.filter((p) => p !== id) : [...perguntas, id])
                if (desmarcando) MODULOS.find((m) => m.id === id).campos.forEach((campo) => setErros(semCampo(campo)))
              }}
              aoMudarCampo={(id, valor) => {
                setCampos((atual) => ({ ...atual, [id]: valor }))
                setErros(semCampo(id))
              }}
              aoEnviar={verRadar}
            />

            <Stack ref={painel} gap="6" minW="0" scrollMarginTop="4" aria-live="polite">
              <VisuallyHidden as="h2">Resultado</VisuallyHidden>
              {!enviado ? (
                <Vazio metadados={metadados} />
              ) : (
                <>
                  <Stack as="section" aria-labelledby="radar-titulo" gap="4">
                    <Flex wrap="wrap" align="baseline" justify="space-between" gap="2">
                      <Heading as="h2" id="radar-titulo" size="xl" color="fg">
                        Seu radar
                      </Heading>
                      <Text textStyle="sm" color="fg.muted">ENEM {f.anos(enviado.resultado.anos)} · Brasil</Text>
                    </Flex>
                    <Resumo resultado={enviado.resultado} />
                    <SimpleGrid columns={{ base: 1, lg: 2 }} gap="4">
                      <MapaDeNotas resultado={enviado.resultado} />
                      <OndeVoceEsta resultado={enviado.resultado} />
                    </SimpleGrid>
                    <AreaAArea resultado={enviado.resultado} />
                  </Stack>
                  {enviado.perguntas.length > 0 && (
                    <Comparativos perguntas={enviado.perguntas} perfil={{ notas: enviado.notas, campos: enviado.campos }} resultado={enviado.resultado} />
                  )}
                </>
              )}
            </Stack>
          </Stack>
        </Container>
      </main>

      <Box as="footer" borderTopWidth="1px">
        <Container maxW="6xl" px={{ base: 4, sm: 6 }} py="6">
          <Flex direction={{ base: 'column', sm: 'row' }} justify="space-between" gap="1" textStyle="xs" color="fg.muted">
            <Text>
              <Text as="span" textStyle="sm" fontWeight="semibold" color="fg">Radar ENEM</Text> · Projeto Aplicado III, Ciência de Dados e IA, UniSENAI
            </Text>
            <Text>Fonte: microdados do ENEM 2022 e 2023, INEP. Os resultados são estatísticos e não substituem o boletim oficial.</Text>
          </Flex>
        </Container>
      </Box>
    </Box>
  )
}

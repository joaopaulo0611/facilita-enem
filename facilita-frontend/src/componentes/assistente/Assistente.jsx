import {
  Box,
  Button,
  Flex,
  HStack,
  IconButton,
  Input,
  Popover,
  Portal,
  Spinner,
  Stack,
  Text,
  VisuallyHidden,
} from '@chakra-ui/react'
import ChatBubbleOutlineOutlined from '@mui/icons-material/ChatBubbleOutlineOutlined'
import CloseOutlined from '@mui/icons-material/CloseOutlined'
import SendOutlined from '@mui/icons-material/SendOutlined'
import SmartToyOutlined from '@mui/icons-material/SmartToyOutlined'
import { useEffect, useRef, useState } from 'react'
import { buscarSugestoesAssistente, ErroApi, perguntarAssistente } from '../../api'
import Icone from '../Icone'
import TextoResposta from './TextoResposta'

const MAX_MENSAGENS = 40 // mantém só as últimas mensagens da sessão

/** Rodapé com a procedência de uma resposta que traz número. */
function Evidencia({ evidencia }) {
  const partes = [
    evidencia.fonte && `Fonte: ${evidencia.fonte}`,
    evidencia.periodo && `Período: ${evidencia.periodo}`,
    evidencia.recorte && `Recorte: ${evidencia.recorte}`,
  ].filter(Boolean)
  if (!partes.length) return null
  return (
    <Text mt="1.5" textStyle="xs" color="fg.muted">
      {partes.join(' · ')}
    </Text>
  )
}

/** Uma bolha de mensagem (da pessoa ou do assistente). */
function Mensagem({ papel, conteudo }) {
  const daPessoa = papel === 'user'
  return (
    <Flex justify={daPessoa ? 'flex-end' : 'flex-start'}>
      <Box
        maxW="85%"
        px="3"
        py="2"
        rounded="l2"
        bg={daPessoa ? 'colorPalette.solid' : 'bg.muted'}
        color={daPessoa ? 'colorPalette.contrast' : 'fg'}
        textStyle="sm"
      >
        {daPessoa ? (
          <Text>{conteudo}</Text>
        ) : (
          <Stack gap="2">
            <TextoResposta texto={conteudo.texto} />
            {conteudo.tipo === 'dado' && conteudo.evidencia && <Evidencia evidencia={conteudo.evidencia} />}
          </Stack>
        )}
      </Box>
    </Flex>
  )
}

/**
 * Assistente do Radar ENEM: botão flutuante que abre uma janela de conversa.
 * A interface não calcula nada — envia a pergunta (e o resultado já calculado,
 * se houver) ao backend e mostra a resposta. O histórico vive só nesta sessão.
 */
export default function Assistente({ resultado }) {
  const [aberto, setAberto] = useState(false)
  const [historico, setHistorico] = useState([])
  const [texto, setTexto] = useState('')
  const [sugestoes, setSugestoes] = useState([])
  const [carregando, setCarregando] = useState(false)
  const fim = useRef(null)
  // Mantém o resultado atual acessível ao enviar, sem recriar o callback.
  const resultadoRef = useRef(resultado)
  useEffect(() => {
    resultadoRef.current = resultado
  }, [resultado])

  useEffect(() => {
    buscarSugestoesAssistente()
      .then((d) => setSugestoes(d.sugestoes ?? []))
      .catch(() => setSugestoes([]))
  }, [])

  useEffect(() => {
    if (aberto) fim.current?.scrollIntoView({ behavior: 'smooth' })
  }, [historico, carregando, aberto])

  async function enviar(pergunta) {
    const limpa = pergunta.trim()
    if (!limpa || carregando) return
    setTexto('')
    setHistorico((h) => [...h, { papel: 'user', conteudo: limpa }].slice(-MAX_MENSAGENS))
    setCarregando(true)
    try {
      const resposta = await perguntarAssistente(limpa, resultadoRef.current ?? null)
      setHistorico((h) => [...h, { papel: 'assistente', conteudo: resposta }].slice(-MAX_MENSAGENS))
    } catch (erro) {
      const mensagem = erro instanceof ErroApi ? erro.message : 'Não consegui responder agora. Tente de novo.'
      setHistorico((h) => [...h, { papel: 'assistente', conteudo: { tipo: 'erro', texto: mensagem } }].slice(-MAX_MENSAGENS))
    } finally {
      setCarregando(false)
    }
  }

  // Sugestões da última resposta do assistente, para continuar a conversa.
  const ultima = historico.at(-1)
  const sugestoesAtivas =
    historico.length === 0 ? sugestoes.slice(0, 4) : ultima?.papel === 'assistente' ? ultima.conteudo.sugestoes ?? [] : []

  return (
    <Popover.Root open={aberto} onOpenChange={(e) => setAberto(e.open)} positioning={{ placement: 'top-end', gutter: 12 }}>
      <Box position="fixed" bottom={{ base: 4, sm: 6 }} right={{ base: 4, sm: 6 }} zIndex="docked">
        <Popover.Trigger asChild>
          <Button rounded="full" size="lg" shadow="lg" gap="2" colorPalette="brand">
            <Icone de={aberto ? CloseOutlined : ChatBubbleOutlineOutlined} tamanho={20} />
            <Text as="span" hideBelow="sm">
              {aberto ? 'Fechar' : 'Tirar dúvidas'}
            </Text>
          </Button>
        </Popover.Trigger>
      </Box>

      <Portal>
        <Popover.Positioner>
          <Popover.Content
            width={{ base: 'calc(100vw - 2rem)', sm: '380px' }}
            maxW="380px"
            maxH={{ base: '70vh', sm: '540px' }}
            display="flex"
            flexDirection="column"
            overflow="hidden"
          >
            <Popover.Header borderBottomWidth="1px" py="3">
              <HStack gap="2.5">
                <Flex boxSize="9" rounded="full" bg="colorPalette.subtle" color="colorPalette.fg" align="center" justify="center">
                  <Icone de={SmartToyOutlined} tamanho={20} />
                </Flex>
                <Box>
                  <Text textStyle="sm" fontWeight="bold" color="fg">
                    Assistente do Radar ENEM
                  </Text>
                  <Text textStyle="xs" color="fg.muted">
                    Tira dúvidas sobre a sua nota · gratuito
                  </Text>
                </Box>
              </HStack>
            </Popover.Header>

            <Popover.Body flex="1" overflowY="auto" py="3">
              <Stack gap="3">
                {historico.length === 0 && (
                  <Text textStyle="sm" color="fg.muted">
                    Posso explicar os indicadores (como o percentil) e interpretar o seu resultado. Toque numa
                    pergunta ou escreva a sua.
                  </Text>
                )}
                {historico.map((msg, i) => (
                  <Mensagem key={i} papel={msg.papel} conteudo={msg.conteudo} />
                ))}
                {carregando && (
                  <HStack color="fg.muted" textStyle="sm" gap="2">
                    <Spinner size="sm" />
                    <Text>Consultando os dados…</Text>
                  </HStack>
                )}

                {sugestoesAtivas.length > 0 && !carregando && (
                  <Stack gap="1.5" pt="1">
                    {sugestoesAtivas.map((s) => (
                      <Button
                        key={s}
                        variant="outline"
                        size="xs"
                        justifyContent="flex-start"
                        textAlign="start"
                        whiteSpace="normal"
                        height="auto"
                        py="1.5"
                        onClick={() => enviar(s)}
                      >
                        {s}
                      </Button>
                    ))}
                  </Stack>
                )}
                <div ref={fim} />
              </Stack>
            </Popover.Body>

            <Box
              as="form"
              borderTopWidth="1px"
              p="2.5"
              onSubmit={(e) => {
                e.preventDefault()
                enviar(texto)
              }}
            >
              <HStack gap="2">
                <VisuallyHidden as="label" htmlFor="assistente-pergunta">
                  Escreva sua pergunta
                </VisuallyHidden>
                <Input
                  id="assistente-pergunta"
                  size="sm"
                  placeholder="Escreva sua pergunta…"
                  value={texto}
                  maxLength={500}
                  onChange={(e) => setTexto(e.target.value)}
                  autoComplete="off"
                />
                <IconButton
                  type="submit"
                  size="sm"
                  colorPalette="brand"
                  aria-label="Enviar pergunta"
                  disabled={!texto.trim() || carregando}
                >
                  <Icone de={SendOutlined} tamanho={18} />
                </IconButton>
              </HStack>
              <Text mt="1.5" textStyle="xs" color="fg.muted">
                Respostas vêm de consultas aos dados do projeto. Não há IA generativa nesta versão.
              </Text>
            </Box>
          </Popover.Content>
        </Popover.Positioner>
      </Portal>
    </Popover.Root>
  )
}

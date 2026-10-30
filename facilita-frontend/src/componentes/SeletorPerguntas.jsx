import { Box, CheckboxCard, createListCollection, Field, Heading, Portal, Select, SimpleGrid, Stack, Text, VisuallyHidden } from '@chakra-ui/react'
import { useMemo } from 'react'
import { campoPorId } from '../campos'
import { MODULOS } from '../modulos'
import Icone from './Icone'

// A lista abre sempre para baixo do campo, com altura limitada e rolagem.
const POSICAO_LISTA = { placement: 'bottom-start', flip: false, sameWidth: true, gutter: 4 }

// O card inteiro é um <label>; por isso o rótulo do campo é texto comum e o
// gatilho do select recebe o nome por aria-label, sem <label> dentro de <label>.
function CampoPergunta({ campo, opcoes, valor, erro, aoMudar }) {
  const colecao = useMemo(
    () =>
      createListCollection({
        items: opcoes.filter((opcao) => !campo.ocultar?.includes(opcao.codigo)).map((opcao) => ({ label: opcao.nome, value: opcao.codigo })),
      }),
    [opcoes, campo],
  )
  return (
    <Field.Root invalid={Boolean(erro)} gap="1">
      <Text textStyle="sm" fontWeight="medium" color="fg">
        {campo.rotulo}
      </Text>
      <Select.Root
        collection={colecao}
        size="sm"
        value={valor ? [valor] : []}
        onValueChange={(e) => aoMudar(campo.id, e.value[0] ?? '')}
        positioning={POSICAO_LISTA}
        ids={{ trigger: campo.id }}
        invalid={Boolean(erro)}
      >
        <Select.HiddenSelect />
        <Select.Control>
          <Select.Trigger aria-label={campo.rotulo}>
            <Select.ValueText placeholder="Selecione" />
          </Select.Trigger>
          <Select.IndicatorGroup>
            <Select.Indicator />
          </Select.IndicatorGroup>
        </Select.Control>
        <Portal>
          <Select.Positioner>
            <Select.Content maxH="48" overflowY="auto">
              {colecao.items.map((item) => (
                <Select.Item item={item} key={item.value}>
                  {item.label}
                  <Select.ItemIndicator />
                </Select.Item>
              ))}
            </Select.Content>
          </Select.Positioner>
        </Portal>
      </Select.Root>
      <Field.ErrorText>{erro}</Field.ErrorText>
    </Field.Root>
  )
}

/** Um card por pergunta; marcar o card mostra os campos de que ela precisa. */
export default function SeletorPerguntas({ metadados, marcadas, valores, erros, aoMarcar, aoMudar }) {
  return (
    <Box as="fieldset" mt="5" pt="4" borderTopWidth="1px">
      <VisuallyHidden as="legend">Perguntas</VisuallyHidden>
      <Heading as="h3" size="md" color="fg">
        O que você quer descobrir?
      </Heading>
      <Text textStyle="sm" color="fg.muted">
        Escolha uma ou mais perguntas. Sem nenhuma, você vê só a sua posição no Brasil.
      </Text>

      <SimpleGrid mt="3" columns={{ base: 1, lg: 3 }} gap="3" alignItems="start">
        {MODULOS.map((modulo) => {
          const marcada = marcadas.includes(modulo.id)
          return (
            <CheckboxCard.Root key={modulo.id} checked={marcada} onCheckedChange={() => aoMarcar(modulo.id)} align="start">
              <CheckboxCard.HiddenInput />
              <CheckboxCard.Control>
                <Icone de={modulo.icone} tamanho={22} color="colorPalette.fg" />
                <CheckboxCard.Content>
                  <CheckboxCard.Label>{modulo.titulo}</CheckboxCard.Label>
                  <CheckboxCard.Description>{modulo.pergunta}</CheckboxCard.Description>
                </CheckboxCard.Content>
                <CheckboxCard.Indicator />
              </CheckboxCard.Control>

              {marcada && (
                <CheckboxCard.Addon
                  // Clicar no espaço em volta dos campos não deve desmarcar a pergunta.
                  onClick={(e) => e.target.closest('button') || e.preventDefault()}
                >
                  <Stack gap="3" py="1">
                    {modulo.campos.map((id) => {
                      const campo = campoPorId(id)
                      return (
                        <CampoPergunta
                          key={id}
                          campo={campo}
                          opcoes={metadados?.recortes[campo.recorte] ?? []}
                          valor={valores[id]}
                          erro={erros[id]}
                          aoMudar={aoMudar}
                        />
                      )
                    })}
                  </Stack>
                </CheckboxCard.Addon>
              )}
            </CheckboxCard.Root>
          )
        })}
      </SimpleGrid>
    </Box>
  )
}

import { Alert, Button, Card, Field, Flex, Heading, HStack, Input, InputGroup, SimpleGrid, Text, VisuallyHidden } from '@chakra-ui/react'
import ArrowForward from '@mui/icons-material/ArrowForward'
import LockOutlined from '@mui/icons-material/LockOutlined'
import RadarOutlined from '@mui/icons-material/RadarOutlined'
import TuneOutlined from '@mui/icons-material/TuneOutlined'
import { AREAS } from '../campos'
import * as f from '../formato'
import Icone from './Icone'
import SeletorPerguntas from './SeletorPerguntas'

// Enquanto digita: só números de até 1000, com no máximo uma casa decimal.
const PARCIAL = /^\d{0,4}([.,]\d?)?$/
const aceitaNota = (texto) => PARCIAL.test(texto) && !(f.lerNota(texto) > 1000)

function CampoNota({ area, valor, erro, aoMudar }) {
  return (
    <Field.Root invalid={Boolean(erro)} gridColumn={area.id === 'redacao' ? { base: 'span 2', sm: 'auto' } : undefined}>
      <Field.Label fontWeight="bold" color="fg">
        {area.nome}
      </Field.Label>
      <InputGroup endElement={<Text textStyle="xs" color="fg.muted">pts</Text>}>
        <Input
          id={area.id}
          inputMode="decimal"
          autoComplete="off"
          placeholder="0 a 1000"
          value={valor}
          onChange={(e) => aceitaNota(e.target.value) && aoMudar(area.id, e.target.value)}
         
         
          fontVariantNumeric="tabular-nums"
        />
      </InputGroup>
      <Field.ErrorText>{erro}</Field.ErrorText>
    </Field.Root>
  )
}

export default function FormularioPerfil({ metadados, notas, perguntas, campos, erros, erroGeral, calculando, aoMudarNota, aoMarcarPergunta, aoMudarCampo, aoEnviar }) {
  return (
    <Card.Root
      as="form"
      noValidate
      onSubmit={(e) => {
        e.preventDefault()
        aoEnviar()
      }}
      variant="outline"
     
     
     
    >
      <Card.Body>
        <Heading as="h2" size="lg" color="fg" display="flex" alignItems="center" gap="2">
          <Icone de={TuneOutlined} color="colorPalette.fg" />
          Suas notas
        </Heading>
        <Text mt="1" textStyle="sm" color="fg.muted">
          Use as notas do seu boletim, de 0 a 1.000, de qualquer edição do ENEM. Dá para editar e comparar de novo.
        </Text>

        <SimpleGrid as="fieldset" mt="4" columns={{ base: 2, sm: 3, lg: 5 }} gap="3">
          <VisuallyHidden as="legend">Notas por área</VisuallyHidden>
          {AREAS.map((area) => (
            <CampoNota key={area.id} area={area} valor={notas[area.id]} erro={erros[area.id]} aoMudar={aoMudarNota} />
          ))}
        </SimpleGrid>

        <SeletorPerguntas
          metadados={metadados}
          marcadas={perguntas}
          valores={campos}
          erros={erros}
          aoMarcar={aoMarcarPergunta}
          aoMudar={aoMudarCampo}
        />

        {erroGeral && (
          <Alert.Root status="error" mt="4">
            <Alert.Indicator />
            <Alert.Title>{erroGeral}</Alert.Title>
          </Alert.Root>
        )}
      </Card.Body>

      <Card.Footer borderTopWidth="1px" pt="4">
        <Flex w="full" direction={{ base: 'column-reverse', sm: 'row' }} align={{ sm: 'center' }} justify="space-between" gap="3">
          <HStack gap="1" textStyle="xs" color="fg.muted">
            <Icone de={LockOutlined} tamanho={14} />
            <Text>Sem cadastro. Suas notas não são guardadas.</Text>
          </HStack>
          <Button type="submit" size="lg" loading={calculando} loadingText="Calculando…">
            <RadarOutlined sx={{ fontSize: 20 }} aria-hidden />
            Ver meu radar
            <ArrowForward sx={{ fontSize: 18 }} aria-hidden />
          </Button>
        </Flex>
      </Card.Footer>
    </Card.Root>
  )
}

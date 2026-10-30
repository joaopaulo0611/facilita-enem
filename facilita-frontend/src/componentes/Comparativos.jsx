import { Heading, Stack } from '@chakra-ui/react'
import { MODULOS } from '../modulos'
import CartaoEmConstrucao from './CartaoEmConstrucao'

/** A resposta de cada pergunta marcada no formulário, na mesma ordem dos cards. */
export default function Comparativos({ perguntas, perfil, resultado }) {
  const marcados = MODULOS.filter((modulo) => perguntas.includes(modulo.id))
  return (
    <Stack as="section" aria-labelledby="comparativos-titulo" gap="3">
      <Heading as="h2" id="comparativos-titulo" size="xl" color="fg">
        {marcados.length > 1 ? 'Suas perguntas' : 'Sua pergunta'}
      </Heading>
      {marcados.map((modulo) =>
        modulo.Componente ? (
          <modulo.Componente key={modulo.id} modulo={modulo} perfil={perfil} resultado={resultado} />
        ) : (
          <CartaoEmConstrucao key={modulo.id} modulo={modulo} />
        ),
      )}
    </Stack>
  )
}

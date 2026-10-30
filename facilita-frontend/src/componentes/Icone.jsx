import { Box } from '@chakra-ui/react'

/** Ícone do Material UI com a cor e o espaçamento vindos das props do Chakra. */
export default function Icone({ de: Componente, tamanho = 20, ...props }) {
  return (
    <Box as="span" display="inline-flex" flexShrink={0} aria-hidden {...props}>
      <Componente sx={{ fontSize: tamanho }} />
    </Box>
  )
}

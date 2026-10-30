import { Box } from '@chakra-ui/react'

/** Caixa flutuante dos gráficos, posicionada sobre o ponto em foco. */
export default function Dica({ children, ...props }) {
  return (
    <Box
      position="absolute"
      zIndex="1"
      pointerEvents="none"
     
      bg="bg.panel"
      borderWidth="1px"
      rounded="l2"
     
     
      shadow="lg"
      px="3"
      py="2"
      textStyle="xs"
      fontVariantNumeric="tabular-nums"
      {...props}
    >
      {children}
    </Box>
  )
}

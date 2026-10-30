import { Badge, Box, Container, Flex, Image, Link, Text } from '@chakra-ui/react'
import VerifiedOutlined from '@mui/icons-material/VerifiedOutlined'
import Icone from './Icone'

export default function Cabecalho() {
  return (
    <Box as="header" borderBottomWidth="1px">
      <Container maxW="6xl" px={{ base: 4, sm: 6 }} py="3">
        <Flex align="center" justify="space-between" gap="4">
          <Link href="/" display="flex" alignItems="center" gap="2.5" _hover={{ textDecoration: 'none' }}>
            <Image src="/logo.svg" alt="" boxSize="9" />
            <Text as="span" textStyle="xl" fontWeight="bold" color="fg">
              Radar ENEM
            </Text>
          </Link>
          <Badge colorPalette="green" variant="subtle" rounded="full" px="3" py="1" gap="1.5" fontWeight="normal">
            <Icone de={VerifiedOutlined} tamanho={16} />
            <Text as="span" hideBelow="sm">Microdados oficiais do INEP</Text>
            <Text as="span" hideFrom="sm">Dados INEP</Text>
          </Badge>
        </Flex>
      </Container>
    </Box>
  )
}

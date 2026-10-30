import { Card, Flex, Heading, Text } from '@chakra-ui/react'

/** Superfície branca usada por todos os blocos do painel. */
export default function Cartao({ titulo, subtitulo, acao, children, ...props }) {
  return (
    <Card.Root as="section" {...props}>
      {titulo && (
        <Card.Header pb="0">
          <Flex align="start" justify="space-between" gap="3">
            <div>
              <Heading as="h3" size="lg" color="fg" lineHeight="short">
                {titulo}
              </Heading>
              {subtitulo && (
                <Text mt="0.5" textStyle="sm" color="fg.muted">
                  {subtitulo}
                </Text>
              )}
            </div>
            {acao}
          </Flex>
        </Card.Header>
      )}
      <Card.Body>{children}</Card.Body>
    </Card.Root>
  )
}

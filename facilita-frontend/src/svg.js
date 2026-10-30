/**
 * Cores e texto do tema para usar dentro dos gráficos em SVG.
 *
 * Fonte e tamanho vão em `style`: o reset do Chakra aplica `font: inherit`
 * em todo elemento, o que passaria por cima dos atributos do SVG.
 */
export const cor = (nome) => `var(--chakra-colors-${nome.replace('.', '-')})`

export const textoSvg = (tamanho, nomeCor = 'fg.muted', { fontWeight = 'normal' } = {}) => ({
  fill: cor(nomeCor),
  style: { font: `${fontWeight} ${tamanho}px var(--chakra-fonts-body)`, fontVariantNumeric: 'tabular-nums' },
})

export const tituloSvg = (tamanho, nomeCor = 'fg') => ({
  fill: cor(nomeCor),
  style: { font: `600 ${tamanho}px var(--chakra-fonts-heading)` },
})

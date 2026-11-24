/**
 * Tema do Chakra UI: os componentes usam a aparência padrão da biblioteca,
 * com a fonte Stack Sans Text e o azul do protótipo como cor principal (`brand`).
 *
 * As outras cores do protótipo ficam como tokens para os gráficos em SVG
 * (`var(--chakra-colors-voce)`), que o Chakra não desenha.
 *
 * Cada cor é um token semântico com valor para o modo claro e para o `_dark`.
 * Assim os gráficos em SVG (que leem a variável CSS da cor) e os componentes
 * trocam de cor junto com o modo escolhido, mantendo o contraste.
 */
import { createSystem, defaultConfig, defineConfig } from '@chakra-ui/react'

// Cada token tem a cor do modo claro e a do modo escuro (`_dark`).
const cores = {
  tinta: { base: '#1b2a4a', _dark: '#eef2f9' },
  texto: { base: '#3a4a66', _dark: '#c4cde0' },
  suave: { base: '#6b7891', _dark: '#92a0bb' },
  marinho: { base: '#1d3b6f', _dark: '#9db8ef' },
  primaria: { base: '#2a5bd7', _dark: '#6f9bff' },
  'primaria-escura': { base: '#1f48b3', _dark: '#5b8af7' },
  voce: { base: '#e36e2c', _dark: '#ff9a52' },
  'voce-texto': { base: '#b4501a', _dark: '#ffb27a' },
  media: { base: '#3f6ad8', _dark: '#6f9bff' },
  barra: { base: '#c9d7f5', _dark: '#3a4f7a' },
  fundo: { base: '#f3f6fb', _dark: '#1a2338' },
  linha: { base: '#e1e7f0', _dark: '#2c3a57' },
  grade: { base: '#edf1f7', _dark: '#27334d' },
  info: { base: '#eaf1fd', _dark: '#1c2c4d' },
  positivo: { base: '#1b7f4a', _dark: '#4cc585' },
  'positivo-fundo': { base: '#e6f4ec', _dark: '#13331f' },
  erro: { base: '#b42318', _dark: '#f87166' },
  'erro-fundo': { base: '#fdecea', _dark: '#3a1715' },
}

const brand = {
  50: '#eaf1fd',
  100: '#d5e2fb',
  200: '#c9d7f5',
  300: '#93aff0',
  400: '#5f86e3',
  500: '#2a5bd7',
  600: '#1f48b3',
  700: '#1d3b6f',
  800: '#172f59',
  900: '#12244a',
  950: '#0c1833',
}

const config = defineConfig({
  theme: {
    tokens: {
      fonts: {
        heading: { value: '"Stack Sans Text Variable", system-ui, sans-serif' },
        body: { value: '"Stack Sans Text Variable", system-ui, sans-serif' },
      },
      colors: {
        brand: Object.fromEntries(Object.entries(brand).map(([passo, valor]) => [passo, { value: valor }])),
      },
    },
    semanticTokens: {
      colors: {
        // Tokens do protótipo que trocam de cor conforme o modo (claro/escuro).
        ...Object.fromEntries(
          Object.entries(cores).map(([nome, { base, _dark }]) => [nome, { value: { base, _dark } }]),
        ),
        brand: {
          solid: { value: '{colors.brand.500}' },
          contrast: { value: 'white' },
          fg: { value: { base: '{colors.brand.600}', _dark: '{colors.brand.300}' } },
          muted: { value: { base: '{colors.brand.200}', _dark: '{colors.brand.800}' } },
          subtle: { value: { base: '{colors.brand.50}', _dark: '{colors.brand.950}' } },
          emphasized: { value: { base: '{colors.brand.300}', _dark: '{colors.brand.700}' } },
          focusRing: { value: { base: '{colors.brand.500}', _dark: '{colors.brand.400}' } },
        },
      },
    },
  },
  globalCss: {
    html: { colorPalette: 'brand' },
  },
})

export const sistema = createSystem(defaultConfig, config)

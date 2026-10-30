/**
 * Tema do Chakra UI: os componentes usam a aparência padrão da biblioteca,
 * com a fonte Stack Sans Text e o azul do protótipo como cor principal (`brand`).
 *
 * As outras cores do protótipo ficam como tokens para os gráficos em SVG
 * (`var(--chakra-colors-voce)`), que o Chakra não desenha.
 */
import { createSystem, defaultConfig, defineConfig } from '@chakra-ui/react'

const cores = {
  tinta: '#1b2a4a',
  texto: '#3a4a66',
  suave: '#6b7891',
  marinho: '#1d3b6f',
  primaria: '#2a5bd7',
  'primaria-escura': '#1f48b3',
  voce: '#e36e2c',
  'voce-texto': '#b4501a',
  media: '#3f6ad8',
  barra: '#c9d7f5',
  fundo: '#f3f6fb',
  linha: '#e1e7f0',
  grade: '#edf1f7',
  info: '#eaf1fd',
  positivo: '#1b7f4a',
  'positivo-fundo': '#e6f4ec',
  erro: '#b42318',
  'erro-fundo': '#fdecea',
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
        ...Object.fromEntries(Object.entries(cores).map(([nome, valor]) => [nome, { value: valor }])),
        brand: Object.fromEntries(Object.entries(brand).map(([passo, valor]) => [passo, { value: valor }])),
      },
    },
    semanticTokens: {
      colors: {
        brand: {
          solid: { value: '{colors.brand.500}' },
          contrast: { value: 'white' },
          fg: { value: '{colors.brand.600}' },
          muted: { value: '{colors.brand.200}' },
          subtle: { value: '{colors.brand.50}' },
          emphasized: { value: '{colors.brand.300}' },
          focusRing: { value: '{colors.brand.500}' },
        },
      },
    },
  },
  globalCss: {
    html: { colorPalette: 'brand' },
  },
})

export const sistema = createSystem(defaultConfig, config)

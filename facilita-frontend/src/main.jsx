import { ChakraProvider } from '@chakra-ui/react'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '@fontsource-variable/stack-sans-text'
import './index.css'
import App from './App.jsx'
import { ProvedorModoCor } from './componentes/modo-cor'
import { sistema } from './tema'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ChakraProvider value={sistema}>
      <ProvedorModoCor defaultTheme="light">
        <App />
      </ProvedorModoCor>
    </ChakraProvider>
  </StrictMode>,
)

/**
 * Componentes do modo claro/escuro: o provedor que guarda a preferência e o
 * botão de alternância (ícone de lua para ir ao escuro, de sol para o claro).
 *
 * A lógica do modo (hook `useModoCor`) fica em `../modo-cor.js`.
 */
import { ClientOnly, IconButton, Skeleton } from '@chakra-ui/react'
import DarkModeOutlined from '@mui/icons-material/DarkModeOutlined'
import LightModeOutlined from '@mui/icons-material/LightModeOutlined'
import { ThemeProvider } from 'next-themes'
import { useModoCor } from '../modo-cor'
import Icone from './Icone'

export function ProvedorModoCor(props) {
  return <ThemeProvider attribute="class" disableTransitionOnChange {...props} />
}

/**
 * Botão que troca entre modo claro e escuro. Mostra o ícone de lua no modo
 * claro (para ir ao escuro) e o de sol no modo escuro (para voltar ao claro).
 */
export function BotaoModoCor(props) {
  const { modoCor, alternarModoCor } = useModoCor()
  const paraEscuro = modoCor !== 'dark'
  return (
    <ClientOnly fallback={<Skeleton boxSize="9" rounded="md" />}>
      <IconButton
        onClick={alternarModoCor}
        variant="ghost"
        aria-label={paraEscuro ? 'Ativar modo escuro' : 'Ativar modo claro'}
        title={paraEscuro ? 'Modo escuro' : 'Modo claro'}
        size="sm"
        {...props}
      >
        <Icone de={paraEscuro ? DarkModeOutlined : LightModeOutlined} tamanho={20} />
      </IconButton>
    </ClientOnly>
  )
}

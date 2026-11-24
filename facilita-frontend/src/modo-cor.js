/**
 * Lógica do modo claro/escuro (sem componentes).
 *
 * O Chakra UI v3 usa a biblioteca `next-themes` para guardar a preferência de
 * cor e aplicar a classe `.light`/`.dark` no `<html>`, que é o seletor que a
 * condição `_dark` dos tokens do tema enxerga.
 */
import { useTheme } from 'next-themes'

/** Lê o modo atual e expõe funções para definir ou alternar entre claro e escuro. */
export function useModoCor() {
  const { resolvedTheme, setTheme, forcedTheme } = useTheme()
  const modoCor = forcedTheme || resolvedTheme
  const alternarModoCor = () => setTheme(modoCor === 'dark' ? 'light' : 'dark')
  return { modoCor, definirModoCor: setTheme, alternarModoCor }
}

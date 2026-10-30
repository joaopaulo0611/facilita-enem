const umaCasa = new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })
const inteiro = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 0 })

export const nota = (valor) => umaCasa.format(valor)
export const pessoas = (valor) => inteiro.format(valor)

/** Lista de anos por extenso: "2022 e 2023". */
export const anos = (lista) => (lista.length > 1 ? `${lista.slice(0, -1).join(', ')} e ${lista.at(-1)}` : String(lista[0] ?? ''))

/** Percentil com uma casa, sem ",0" quando é redondo: 98,4% / 85%. */
export const percentual = (valor) =>
  `${new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 1 }).format(valor)}%`

/** Diferença com sinal explícito: +42,0 / −12,5. */
export const diferenca = (valor) => `${valor >= 0 ? '+' : '−'}${umaCasa.format(Math.abs(valor))}`

/** Aceita "680", "680,5" ou "680.5"; devolve null se não for número. */
export function lerNota(texto) {
  const limpo = String(texto).trim().replace(',', '.')
  if (limpo === '' || !/^\d+(\.\d+)?$/.test(limpo)) return null
  return Number(limpo)
}

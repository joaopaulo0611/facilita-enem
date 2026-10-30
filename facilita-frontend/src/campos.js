/** Campos do formulário: as cinco notas, pedidas sempre, e os que cada pergunta pede. */

export const AREAS = [
  { id: 'lc', codigo: 'LC', nome: 'Linguagens' },
  { id: 'ch', codigo: 'CH', nome: 'Humanas' },
  { id: 'cn', codigo: 'CN', nome: 'Natureza' },
  { id: 'mt', codigo: 'MT', nome: 'Matemática' },
  { id: 'redacao', codigo: 'REDACAO', nome: 'Redação' },
]

// `recorte` é a chave da lista de opções em /api/metadados. `ocultar` tira códigos
// que, para quem está preenchendo, equivalem a deixar o campo em branco.
export const CAMPOS_PERGUNTA = [
  { id: 'uf', recorte: 'UF', rotulo: 'Estado onde fez a prova' },
  { id: 'renda', recorte: 'RENDA', rotulo: 'Renda familiar mensal' },
  { id: 'tipo_escola', recorte: 'TIPO_ESCOLA', rotulo: 'Escola no ensino médio', ocultar: ['1'] },
  { id: 'escolaridade_mae', recorte: 'ESCOLARIDADE_MAE', rotulo: 'Até onde sua mãe estudou' },
  { id: 'cor_raca', recorte: 'COR_RACA', rotulo: 'Cor ou raça', ocultar: ['0'] },
]

export const campoPorId = (id) => CAMPOS_PERGUNTA.find((campo) => campo.id === id)

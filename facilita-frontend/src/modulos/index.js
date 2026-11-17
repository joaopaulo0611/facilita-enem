/**
 * Perguntas comparativas, uma por integrante.
 *
 * No formulário, cada pergunta é um card que o usuário marca; ao marcar,
 * aparecem os `campos` que ela pede. No resultado, `Componente` recebe
 * { modulo, perfil, resultado }; sem ele, o cartão mostra "em construção".
 */
import FamilyRestroomOutlined from '@mui/icons-material/FamilyRestroomOutlined'
import PlaceOutlined from '@mui/icons-material/PlaceOutlined'
import SchoolOutlined from '@mui/icons-material/SchoolOutlined'
import CartaoRegional from './regional/CartaoRegional'

export const MODULOS = [
  {
    id: 'regional',
    titulo: 'Seu estado e o Brasil',
    pergunta: 'A mesma nota vale o mesmo em todo o país?',
    campos: ['uf'],
    icone: PlaceOutlined,
    Componente: CartaoRegional,
  },
  {
    id: 'origem',
    titulo: 'Sua origem',
    pergunta: 'Quanto a cor ou raça e a escola pesam na sua posição?',
    campos: ['cor_raca', 'tipo_escola'],
    icone: SchoolOutlined,
    Componente: null,
  },
  {
    id: 'familia',
    titulo: 'Sua família',
    pergunta: 'Quanto a renda da família e a escolaridade da mãe mudam sua posição?',
    campos: ['renda', 'escolaridade_mae'],
    icone: FamilyRestroomOutlined,
    Componente: null,
  },
]

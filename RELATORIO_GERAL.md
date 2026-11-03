# Como o Radar ENEM funciona

Visão geral de cada parte do projeto: o que ela faz e por que foi feita assim.
Para instalar e rodar, veja o [README](README.md).

```
microdados do INEP (CSV, 3,3 GB)
        │  etl/  (PySpark, roda offline, uma vez)
        ▼
Bronze ──► Silver ──► Gold (11 MB)
                        │  facilita-backend/  (FastAPI)
                        ▼
                API: percentil e Z-Score
                        │  /api/...
                        ▼
              facilita-frontend/  (React + Chakra UI)
```

A ideia central: o trabalho pesado (ler milhões de linhas) acontece **uma vez, offline**.
A API só consulta um resumo pequeno, então responde na hora e cabe num servidor barato.

## 1. Pipeline de dados (`etl/`)

Arquitetura medalhão em PySpark, com as edições de **2022 e 2023**. Anos de 2024 em
diante ficaram de fora porque os microdados novos podem não ligar a nota ao
questionário socioeconômico.

| Camada | O que faz | Resultado (2022 + 2023) |
|---|---|---|
| **Bronze** (`bronze.py`) | Copia o CSV do INEP para Parquet, tudo como texto, sem mudar nada. Guarda de qual arquivo e quando cada linha veio. | 7.410.060 linhas, 590 MB (17,6% do CSV) |
| **Silver** (`silver.py`) | Escolhe só as colunas usadas, converte os tipos, valida e calcula a média das 5 notas. | 4.945.546 válidos, 70 MB (2,1% do CSV) |
| **Gold** (`gold.py`) | Conta quantas pessoas tiraram cada nota em cada grupo e calcula as estatísticas de cada grupo. | 11 MB (0,33% do CSV) |

**Validação na Silver.** Nenhuma linha some sem explicação: cada uma recebe um motivo de
rejeição ou fica válida. As rejeitadas (2.464.514) vão para uma pasta separada com o motivo:

1. `AUSENTE_OU_ELIMINADO`: faltou ou foi eliminado em alguma prova;
2. `REDACAO_EM_BRANCO`;
3. `NOTA_AUSENTE`;
4. `NOTA_FORA_DA_ESCALA`: fora de 0 a 1000;
5. `SEM_QUESTIONARIO`: sem a renda, então não entra nos recortes.

Treineiros não são rejeitados: quem fez as provas tem nota válida para comparação.

**Grupos na Gold.** Um grupo é a combinação de ano, área (LC, CH, CN, MT, Redação ou a
média), recorte e categoria. Por exemplo: "2023, Matemática, UF, SC". Os recortes são:

- `GERAL` (todo mundo);
- `RENDA`, `TIPO_ESCOLA`, `COR_RACA`, `SEXO`, `UF` (estado onde fez a prova) e `ESCOLARIDADE_MAE`;
- `RENDA_X_TIPO_ESCOLA`, um cruzamento pronto para a pergunta de origem.

Para cada grupo a Gold guarda duas tabelas:

- `distribuicao_notas`: uma linha por nota distinta, com quantas pessoas tiraram aquela nota;
- `estatisticas`: tamanho do grupo, média, desvio-padrão, mínimo, quartis e máximo.

**Por que a Gold fica tão pequena.** Em vez de guardar 4,9 milhões de pessoas, guarda a
contagem por nota. Isso basta para o percentil exato e reduz o volume a 0,33% do CSV.

`run_pipeline.py` roda as três camadas em ordem e mede o tempo de cada uma
(última execução: Bronze 47 s, Silver 22 s, Gold 131 s). `volumetria.py` grava o tamanho e
as linhas de cada camada em `etl/volumetria.json`, que serve de evidência no relatório.

## 2. API (`facilita-backend/`)

FastAPI. Ao receber a primeira requisição, carrega a Gold na memória (cerca de 1,4 s) e
mantém ela lá.

### Os anos viram uma base só

A nota do ENEM é calculada pela TRI justamente para ser comparável entre edições. Por isso
a API soma 2022 e 2023 em um único grupo e o usuário é comparado com todos os anos de uma
vez, sem escolher ano. Ao juntar dois anos, as contagens de cada nota são somadas, e a
média e o desvio-padrão são recalculados para a base combinada.

### Os cálculos

Cada grupo fica em memória como dois vetores ordenados: as notas e a **contagem acumulada**
até cada nota. Exemplo com um grupo de 10 pessoas:

| Nota | Pessoas | Acumulado |
|---|---|---|
| 500 | 2 | 2 |
| 600 | 3 | 5 |
| 700 | 5 | 10 |

- **Percentil**: porcentagem do grupo com nota **menor** que a do usuário. Uma busca binária
  acha a posição da nota no vetor e o acumulado diz quantas pessoas ficaram abaixo.
  Com 650 no exemplo: abaixo ficam 5 de 10, então **50%**. A busca é instantânea mesmo
  com milhões de pessoas, porque não percorre ninguém.
- **Z-Score**: `(nota − média do grupo) / desvio-padrão do grupo`. Diz a quantos desvios
  da média o usuário está (0 é na média, +1 é um desvio acima).
- **Média geral do usuário**: média simples das cinco notas, a mesma usada na Gold.
- **Grupo mínimo**: grupos com menos de 100 pessoas não são comparados, porque o percentil
  deixa de ser confiável.

### Rotas

| Rota | O que devolve |
|---|---|
| `GET /api/metadados` | Anos da base, áreas, opções de cada campo do formulário e total de participantes |
| `GET /api/radar` | Para cada área e para a média: nota, percentil, Z-Score, média dos participantes e diferença; mais o histograma da média geral |
| `GET /api/modulos/regional` | Posição no estado e no Brasil e o ranking dos estados para a mesma nota |

Erros de entrada voltam em português e por campo (por exemplo, nota acima de 1000), e o
front-end mostra a mensagem embaixo do campo certo. Documentação interativa em `/docs`.

Os testes (`tests/`) usam uma Gold sintética pequena, então rodam sem os microdados.

## 3. Front-end (`facilita-frontend/`)

React 19 com Vite. Os componentes visuais (botões, cards, campos, selects, alertas) são da
biblioteca **Chakra UI**, no visual padrão dela; os ícones são do Material UI e a fonte é
Stack Sans Text. Os gráficos são desenhados à mão em SVG, usando as cores do tema do Chakra.

### Fluxo da tela

1. O usuário digita as **cinco notas**. O campo não aceita valor acima de 1000.
2. Marca as **perguntas** que quer responder. Cada card mostra os campos que aquela
   pergunta precisa (estado, renda, escola, etc.).
3. Ao clicar em **Ver meu radar**, o front-end valida tudo, chama `/api/radar` e mostra:
   - **Resumo**: média geral e posição;
   - **Mapa de notas**: radar com as cinco áreas, comparando com a média dos participantes;
   - **Onde você está**: histograma da média geral com o marcador "Você";
   - **Área a área**: diferença para a média em cada prova;
   - uma resposta para cada pergunta marcada.

As notas não são guardadas em lugar nenhum: o cálculo é feito na hora e nada é salvo.

### Organização do código

| Arquivo | Papel |
|---|---|
| `src/App.jsx` | Estado da tela, validação e chamada da API |
| `src/api.js` | Chamadas ao back-end; todo erro vira uma mensagem pronta para mostrar |
| `src/campos.js` | Áreas e campos que as perguntas pedem |
| `src/tema.js` | Tema do Chakra: fonte, cor principal e cores dos gráficos |
| `src/componentes/` | Peças da tela (formulário, gráficos, cartões) |
| `src/modulos/` | Uma pasta por pergunta comparativa |

## 4. As perguntas comparativas

Cada integrante responde uma pergunta. Todas seguem o mesmo modelo: calcular o percentil
da nota do usuário dentro de um grupo e comparar com o percentil no Brasil todo.

| Pergunta | Responsável | Campos | Situação |
|---|---|---|---|
| **Seu estado e o Brasil**: a mesma nota vale o mesmo em todo o país? | João Paulo | Estado | Pronta |
| **Sua origem**: quanto a renda da família e a escola pesam na sua posição? | Matheus | Renda e tipo de escola | Em construção (a Gold já tem o cruzamento) |
| **Sua família**: quanto a escolaridade da mãe e a cor ou raça mudam sua posição? | Nicolas | Escolaridade da mãe e cor/raça | Em construção (precisa de um cruzamento novo na Gold) |

**Como a pergunta regional funciona.** Para a nota escolhida (média geral ou uma área), a API
calcula o percentil no grupo do estado e no grupo do Brasil e diz se a posição melhora ou
piora no estado. Também calcula o percentil da mesma nota em todos os estados e ordena do
melhor para o pior. O estado é o **local de prova**, como o INEP registra, e não onde a
pessoa mora.

**Como acrescentar uma pergunta.**

1. Na API, criar uma rota que use `gold.grupo(area, recorte, categoria)`.
2. No front-end, criar o cartão em `src/modulos/<pergunta>/`.
3. Ligar o cartão em `src/modulos/index.js`, no campo `Componente`.

O formulário e a validação dos campos já estão prontos.

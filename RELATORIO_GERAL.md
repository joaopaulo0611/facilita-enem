# Como o Radar ENEM funciona

Visão geral de cada parte do projeto: o que ela faz e por que foi feita assim.
Para instalar e rodar, veja o [README](README.md).

```
microdados do INEP (CSV, 3,3 GB)
        │  etl/  (PySpark, roda offline, uma vez)
        ▼
Bronze ──► Silver ──► Gold (15,5 MB)
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

### 1.1 Fonte e escopo

A base são os microdados oficiais do ENEM publicados pelo INEP, edições **2022 e 2023**:
dois CSVs que somam 3,3 GB e 7.410.060 inscritos. Os dados são públicos e anonimizados pelo
INEP. Anos de 2024 em diante ficaram de fora porque os microdados novos podem não ligar a
nota ao questionário socioeconômico, e sem essa ligação os recortes não funcionam.

O pipeline segue a arquitetura medalhão em PySpark e roda **offline**, uma vez por base. Ele
grava tudo em Parquet com compressão zstd, separado por ano (`NU_ANO`).

### 1.2 Camadas

| Camada | O que faz | Resultado (2022 + 2023) |
|---|---|---|
| **Bronze** (`bronze.py`) | Copia o CSV do INEP para Parquet sem mudar nada, com todas as colunas como texto. Acrescenta duas colunas de rastreabilidade: o arquivo de origem (`_arquivo_origem`) e o momento da ingestão (`_ingerido_em`). | 7.410.060 linhas, 78 colunas, 590 MB |
| **Silver** (`silver.py`) | Fica só com as 15 colunas usadas, converte os tipos, valida cada linha e calcula a média das 5 notas. Separa as linhas válidas das rejeitadas. | 4.945.546 válidas, 70 MB |
| **Gold** (`gold.py`) | Conta quantas pessoas tiraram cada nota em cada grupo e calcula as estatísticas de cada grupo. É a única camada que a API lê. | 6.727.275 linhas e 2.616 grupos, 15,5 MB |

A Bronze existe para que uma mudança de regra na Silver não exija ler os CSVs de novo: o
reprocessamento parte do Parquet, que é bem mais rápido.

### 1.3 Validação na Silver

Nenhuma linha some sem explicação: cada uma fica válida ou recebe um motivo de rejeição. As
rejeitadas vão para `silver/rejeitados`, com o número de inscrição, o ano e o motivo. As
regras são testadas nesta ordem, e a primeira que falhar define o motivo:

| Ordem | Motivo | Regra | Linhas na base atual |
|---|---|---|---|
| 1 | `AUSENTE_OU_ELIMINADO` | Faltou ou foi eliminado em alguma das 4 provas objetivas | 2.386.973 |
| 2 | `REDACAO_EM_BRANCO` | Redação com situação "em branco" | 77.541 |
| 3 | `NOTA_AUSENTE` | Alguma das 5 notas vazia | 0 |
| 4 | `NOTA_FORA_DA_ESCALA` | Alguma nota fora de 0 a 1000 | 0 |
| 5 | `SEM_QUESTIONARIO` | Sem a renda (Q006), então não entra nos recortes | 0 |
| | **Total rejeitado** | | **2.464.514** |

As regras 3 a 5 não pegaram nenhuma linha em 2022 e 2023, mas continuam no pipeline como
proteção: se o INEP mudar o formato numa edição futura, o problema aparece como motivo de
rejeição em vez de virar nota errada na Gold.

Treineiros não são rejeitados: quem fez todas as provas tem nota válida para comparação. Na
base atual são 904.366 treineiros entre os 4.945.546 válidos.

### 1.4 Modelagem da Gold

Um **grupo** é a combinação de ano, área (LC, CH, CN, MT, Redação ou a média), recorte e
categoria. Por exemplo: "2023, Matemática, UF, SC". Os recortes são:

- `GERAL` (todo mundo);
- `RENDA`, `TIPO_ESCOLA`, `COR_RACA`, `SEXO`, `UF` (estado onde fez a prova) e `ESCOLARIDADE_MAE`;
- os cruzamentos `RENDA_X_ESCOLARIDADE_MAE` (pergunta de família) e `COR_RACA_X_TIPO_ESCOLA`
  (pergunta de origem). A categoria de um cruzamento junta os dois códigos, por exemplo `E|F`.
  Quem não respondeu um dos dois campos fica fora do cruzamento.

Os cruzamentos ficam na lista `CRUZAMENTOS` do `etl/config.py`. Para criar um novo, basta
acrescentar um par de recortes nessa lista e rodar a Gold de novo.

Para cada grupo, a Gold guarda duas tabelas:

- `distribuicao_notas`: uma linha por nota distinta, com quantas pessoas tiraram aquela nota
  (6.727.275 linhas). É o que permite o percentil exato;
- `estatisticas`: tamanho do grupo, média, desvio-padrão, mínimo, quartis e máximo (2.616
  grupos). É a base do Z-Score.

**Por que a Gold fica tão pequena.** Em vez de guardar 4,9 milhões de pessoas, ela guarda
quantas pessoas tiraram cada nota. Isso basta para o percentil exato e reduz o volume a 0,46%
do CSV. Antes de gravar, as linhas são ordenadas por grupo e nota, porque valores vizinhos
repetidos comprimem melhor no Parquet.

### 1.5 Execução

`run_pipeline.py` orquestra tudo:

1. checa a versão do Python (`verificar_ambiente.py`);
2. garante que os microdados estão no lugar, baixando e extraindo o que faltar
   (`baixar_microdados.py`). A flag `--sem-download` pula esta etapa quando os CSVs já
   estão extraídos;
3. roda Bronze, Silver e Gold em ordem, medindo o tempo de cada uma;
4. mede a volumetria de cada camada e grava em `etl/volumetria.json` (`volumetria.py`).

Cada camada sobrescreve a própria saída. Por isso rodar o pipeline de novo não duplica dados:
o resultado é sempre o mesmo para a mesma entrada.

Tempos da última execução: Bronze 53 s, Silver 17 s e Gold 246 s. A Gold rodou com 4 GB de
memória e 6 núcleos, porque a configuração padrão do `etl/config.py` (6 GB e todos os
núcleos) travou um notebook de 16 GB com outros programas abertos.

### 1.6 Obtenção dos microdados

Os microdados do INEP são pesados (ZIPs de cerca de 2 GB por ano) e o portal às vezes recusa
a conexão. Por isso o download é automatizado e resiliente:

- `fontes.json` é o manifesto de origem. Para cada ano, guarda a URL do ZIP no INEP e o
  tamanho e o SHA-256 do ZIP, registrados na primeira verificação bem-sucedida. Nas
  execuções seguintes, esses valores confirmam a integridade e detectam arquivo corrompido
  ou republicado pelo INEP. Na base atual os dois anos (2022 e 2023) já estão com o checksum
  preenchido; um campo `null` significa apenas que aquele ano ainda não foi verificado.
- `baixar_microdados.py` baixa, confere o checksum e extrai cada ano. O download faz até 4
  tentativas, retoma de onde parou e, se nada disso bastar, usa o `curl` do sistema. Um ZIP
  que já está em `public/` é reaproveitado. **Antes de aceitar qualquer download**, o script
  valida que o arquivo é mesmo um ZIP (tamanho mínimo e assinatura `PK\x03\x04`): o portal do
  INEP às vezes responde com um redirect/erro curto (status 200) que seria salvo como se
  fosse o ZIP e só estouraria depois, na extração, com um `BadZipFile` confuso. Com a
  validação, um download inválido é recusado na hora, com uma mensagem clara e sem registrar
  um checksum falso no `fontes.json`.
- `verificar_ambiente.py` confere, antes de subir o Spark, se a versão do Python é
  compatível com o PySpark 3.5.3. Se não for, interrompe logo no começo com uma orientação
  clara, em vez de falhar no meio do pipeline sem mensagem.

### 1.7 Volumetria

Valores de `etl/volumetria.json`, comparados com os 3.345 MB dos dois CSVs:

| Camada | Tamanho | Linhas | % do CSV |
|---|---|---|---|
| CSV bruto (2 arquivos) | 3.345,3 MB | 7.410.060 | 100% |
| Bronze | 589,9 MB | 7.410.060 | 17,6% |
| Silver: participantes | 69,6 MB | 4.945.546 | 2,1% |
| Silver: rejeitados | 7,7 MB | 2.464.514 | 0,23% |
| Gold: distribuição de notas | 15,4 MB | 6.727.275 | 0,46% |
| Gold: estatísticas | 0,1 MB | 2.616 | 0,002% |

A API em produção nunca lê o CSV do INEP: ela lê só a Gold, que é 0,46% do tamanho original.

### 1.8 Versionamento dos dados

A Gold é versionada no repositório (`data/gold/`), então rodar a API **não** exige baixar
nem reprocessar nada, e o servidor do deploy só precisa do repositório. Cada vez que a Gold
é gerada de novo, o commit registra quando os dados mudaram e por quê. Bronze e Silver ficam
fora do Git (`.gitignore`), porque são grandes e só servem para gerar a Gold. O download dos
microdados só é necessário para regenerar a Gold.

## 2. API (`facilita-backend/`)

FastAPI. Ao receber a primeira requisição, carrega a Gold na memória (cerca de 1,5 s) e
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
| `GET /api/modulos/origem` | Posição no Brasil, na mesma cor/raça, no mesmo tipo de escola e no cruzamento cor/raça × escola |
| `GET /api/modulos/familia` | Posição no Brasil, na mesma renda, na mesma escolaridade da mãe e no cruzamento renda × escolaridade da mãe |

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
| **Sua origem**: quanto a cor ou raça e a escola pesam na sua posição? | Matheus Cruz | Cor/raça e tipo de escola | Pronta (cruzamento `COR_RACA_X_TIPO_ESCOLA`) |
| **Sua família**: quanto a renda da família e a escolaridade da mãe mudam sua posição? | Nicolas Mello | Renda e escolaridade da mãe | Pronta (cruzamento `RENDA_X_ESCOLARIDADE_MAE`) |

**Como a pergunta regional funciona.** Para a nota escolhida (média geral ou uma área), a API
calcula o percentil no grupo do estado e no grupo do Brasil e diz se a posição melhora ou
piora no estado. Também calcula o percentil da mesma nota em todos os estados e ordena do
melhor para o pior. O estado é o **local de prova**, como o INEP registra, e não onde a
pessoa mora.

**Como a pergunta de origem funciona.** Para a nota escolhida, a API calcula o percentil em
quatro grupos: no Brasil todo, dentro de quem declarou a mesma cor/raça, dentro de quem
estudou no mesmo tipo de escola e no cruzamento dos dois (mesma cor/raça **e** mesma escola),
usando o recorte `COR_RACA_X_TIPO_ESCOLA` já pronto na Gold. Mostra o quanto a origem
"move a régua": o mesmo ponto rende percentis diferentes conforme o grupo de comparação. O
código 0 de cor/raça ("não declarada") e o código 1 de tipo de escola ("não informou") não
são aceitos como grupo de comparação.

**Como a pergunta de família funciona.** Para a nota escolhida, a API calcula o percentil em
quatro grupos: no Brasil todo, dentro de quem tem a mesma renda familiar, dentro de quem tem
a mesma escolaridade da mãe e no cruzamento dos dois (mesma renda **e** mesma escolaridade da
mãe), usando o recorte `RENDA_X_ESCOLARIDADE_MAE` já pronto na Gold. Mostra o quanto esses
marcadores familiares deslocam a régua: o mesmo ponto rende percentis diferentes conforme o
grupo de comparação.

**Como acrescentar uma pergunta.**

1. Na API, criar uma rota que use `gold.grupo(area, recorte, categoria)`.
2. No front-end, criar o cartão em `src/modulos/<pergunta>/`.
3. Ligar o cartão em `src/modulos/index.js`, no campo `Componente`.

O formulário e a validação dos campos já estão prontos.

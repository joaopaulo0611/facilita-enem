# Deploy gratuito do Radar ENEM

Guia passo a passo para publicar a aplicação **de graça**, em nuvem, com link
público. A arquitetura é dividida em duas partes, cada uma no serviço gratuito que
melhor a atende:

| Parte | O que é | Onde hospedar (grátis) |
|---|---|---|
| **Back-end** | API FastAPI (`facilita-backend/`) que lê a Gold e calcula percentil/Z-Score | **Render** (Web Service free) |
| **Front-end** | Site React + Vite (`facilita-frontend/`), arquivos estáticos | **Vercel** (Hobby free) |

**Por que assim.** O front-end chama a API por caminhos **relativos** (`/api/...`).
Para não precisar mexer no código nem lidar com CORS, o Vercel é configurado para
**reescrever** `/api/...` para o endereço do back-end no Render. Para o navegador,
tudo parece vir do mesmo domínio.

```
navegador ──►  https://SEU-SITE.vercel.app          (front-end, Vercel)
                   │  /api/...  (rewrite do vercel.json)
                   ▼
               https://SEU-BACKEND.onrender.com/api/...   (API, Render)
```

> **Pré-requisitos:** o repositório já está no GitHub e a camada Gold está
> versionada em `data/gold/` (já está). Você vai precisar de uma conta no
> [Render](https://render.com) e outra no [Vercel](https://vercel.com) — as duas
> permitem entrar com o próprio GitHub e são gratuitas.

---

## Parte 0 — Dois arquivos de configuração (commitar antes de publicar)

Esses dois arquivos deixam o deploy reproduzível e sem cliques manuais de
configuração. **Crie e commite os dois antes de começar.**

### 0.1 `render.yaml` (raiz do repositório)

Descreve o serviço para o Render e já está na raiz do repositório. Pontos importantes:

- **Sem Root Directory.** A API lê a Gold em `data/gold/`, que fica fora de
  `facilita-backend/`. Por isso o serviço usa o repositório inteiro, e os comandos
  entram na pasta da API:
  - build: `pip install -r facilita-backend/requirements.txt`
  - start: `cd facilita-backend && uvicorn main:app --host 0.0.0.0 --port $PORT`
- **Variáveis de memória.** O plano Free tem 512 MB. `ARROW_DEFAULT_MEMORY_POOL=system`
  e `MALLOC_ARENA_MAX=2` baixam o pico ao carregar a Gold para cerca de 400 MB.
- **Python 3.12.3**, a mesma versão dos testes locais (`PYTHON_VERSION`).
- O Render injeta a porta em `$PORT`, por isso o start não fixa `8001`.

### 0.2 `facilita-frontend/vercel.json`

Faz o Vercel (a) servir o site estático e (b) reescrever `/api/...` para o Render.
Coloque dentro de `facilita-frontend/`:

```json
{
  "rewrites": [
    { "source": "/api/:path*", "destination": "https://SEU-BACKEND.onrender.com/api/:path*" }
  ]
}
```

> Troque `SEU-BACKEND.onrender.com` pela URL real **depois** de criar o back-end
> (Parte 1). Você volta aqui, edita e commita de novo.

---

## Parte 1: back-end no Render

Use o **Blueprint**, que lê o `render.yaml` com todas as configurações acima.

1. Entre em <https://render.com> com sua conta do GitHub.
2. No painel, clique em **New +** → **Blueprint**.
3. Conecte o repositório `facilita-enem` (autorize o GitHub se for a primeira vez)
   e escolha a branch `main`.
4. O Render mostra o serviço `radar-enem-api` lido do `render.yaml`, no plano Free.
   Clique em **Apply** (ou **Deploy Blueprint**).
5. Espere o primeiro build (alguns minutos). Quando aparecer **Live**, copie a URL
   pública, algo como `https://radar-enem-api.onrender.com`.
6. **Teste** no navegador:
   - `https://radar-enem-api.onrender.com/` deve responder `["Facilita ENEM"]`;
   - `https://radar-enem-api.onrender.com/docs` abre a documentação interativa;
   - `https://radar-enem-api.onrender.com/api/metadados` traz os anos `[2022, 2023]`
     e o total de participantes. É a primeira rota que carrega a Gold, então pode
     levar alguns segundos.

**Se preferir criar à mão** (New + → Web Service), deixe o **Root Directory vazio**,
use o build e o start da seção 0.1, escolha o plano **Free** e, em **Environment**,
adicione as três variáveis: `PYTHON_VERSION=3.12.3`,
`ARROW_DEFAULT_MEMORY_POOL=system` e `MALLOC_ARENA_MAX=2`.

> **Importante sobre o plano Free do Render:** o serviço "dorme" após ~15 minutos
> sem acesso. A requisição seguinte acorda a API, e essa primeira resposta demora
> ~30 a 60 segundos (cold start). Depois disso fica rápido. Para a banca, **acesse
> o site 1–2 minutos antes** para "esquentar" a API. (Opcional: um monitor gratuito
> como UptimeRobot pingando a URL a cada 10 min mantém a API acordada.)

---

## Parte 2 — Ligar o front-end ao back-end

Agora que você tem a URL do Render, atualize o `vercel.json`:

1. Abra `facilita-frontend/vercel.json`.
2. Troque `https://SEU-BACKEND.onrender.com` pela URL real do passo 1.6
   (ex.: `https://radar-enem-api.onrender.com`). **Mantenha** o `/api/:path*` no fim.
3. Commite e faça push dessa mudança para a `main`.

---

## Parte 3 — Front-end no Vercel

1. Entre em <https://vercel.com> com sua conta do GitHub.
2. Clique em **Add New...** → **Project** e importe o repositório `facilita-enem`.
3. Nas configurações do projeto:
   - **Root Directory:** `facilita-frontend` (clique em *Edit* e selecione a pasta).
   - **Framework Preset:** **Vite** (o Vercel costuma detectar sozinho).
   - **Build Command:** `npm run build` (padrão).
   - **Output Directory:** `dist` (padrão do Vite).
   - **Install Command:** `npm install` (padrão).
4. Clique em **Deploy**. Em um ou dois minutos o site fica no ar.
5. Copie a URL pública, algo como `https://facilita-enem.vercel.app`. **Esse é o
   link definitivo que vai no relatório.**

---

## Parte 4 — Validar a aplicação publicada

Abra `https://SEU-SITE.vercel.app` e confirme, de ponta a ponta:

1. A tela do Radar ENEM carrega (os campos de nota aparecem).
2. Digite as cinco notas (ex.: 600, 650, 580, 720, 800) e marque uma ou mais
   perguntas comparativas (estado, origem, família).
3. Clique em **Ver meu radar**. Devem aparecer o resumo, o mapa de notas, o
   histograma e as respostas das perguntas marcadas.
   - Se a primeira tentativa demorar ou falhar, é o cold start do Render: espere
     ~1 minuto e tente de novo.
4. Confirme que a documentação da API responde em
   `https://SEU-BACKEND.onrender.com/docs`.

Se tudo isso funciona, a aplicação está validada em nuvem e pronta para o
relatório.

---

## Parte 5 — Levar os links para o relatório final

Com o site no ar, me passe os dois endereços:

- **Front-end (link público definitivo):** `https://SEU-SITE.vercel.app`
- **API / docs:** `https://SEU-BACKEND.onrender.com/docs`

Eu preencho os marcadores do `RELATORIO_FINAL.md` (topo e seção 4.5), regenero o
PDF e fecho a entrega.

---

## Alternativas gratuitas (caso prefira)

- **Back-end:** [Railway](https://railway.app) (crédito mensal grátis),
  [Fly.io](https://fly.io) ou [Hugging Face Spaces](https://huggingface.co/spaces)
  também rodam FastAPI. Em qualquer um, o comando de start é o mesmo
  (`uvicorn main:app --host 0.0.0.0 --port $PORT`) e você só precisa apontar o
  `vercel.json` para a nova URL.
- **Front-end:** [Netlify](https://netlify.com) funciona igual ao Vercel. O rewrite
  equivalente vai em um arquivo `facilita-frontend/netlify.toml`:

  ```toml
  [[redirects]]
    from = "/api/*"
    to = "https://SEU-BACKEND.onrender.com/api/:splat"
    status = 200
    force = true

  [[redirects]]
    from = "/*"
    to = "/index.html"
    status = 200
  ```

- **Tudo em um só serviço (sem rewrite):** dá para servir o front-end estático pela
  própria API FastAPI (montando o `dist/` com `StaticFiles`) e publicar só no
  Render. Fica um único link, mas exige uma pequena mudança no `main.py` e rodar o
  `npm run build` no deploy. O caminho com Vercel + rewrite acima é mais simples e
  não mexe no código.

## Resumo rápido

1. Commite `render.yaml` (raiz) e `facilita-frontend/vercel.json`.
2. **Render:** New + → Blueprint → repositório `facilita-enem` → Apply → copie a URL.
3. Atualize o `vercel.json` com a URL do Render e dê push.
4. **Vercel:** Import Project → root `facilita-frontend` → preset Vite → Deploy →
   copie a URL.
5. Teste o site e me mande os dois links para fechar o relatório.

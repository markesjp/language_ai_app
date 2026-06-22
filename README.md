# LinguaFlow AI

App web para aprendizado de línguas com IA conversacional, RAG, voz opcional, analytics e auditoria de latência/tokens.

## O que já está implementado

- Backend FastAPI em `/api/v1`.
- Frontend Next.js responsivo.
- Docker Compose com Nginx, Postgres/pgvector, PgBouncer, Redis e Prometheus.
- Chat textual com providers `mock`, `gemini` e `ollama`.
- RAG admin documental com chunking, embeddings, fontes, confiança e auditoria.
- Busca vetorial com pgvector quando o banco é PostgreSQL, com fallback JSON/cosseno para ambientes simples.
- Login admin com senha mestre hasheada no banco e cookie HTTP-only.
- Painel de configurações para IA, RAG, sistema e segurança.

## Desenvolvimento rapido com hot reload

Para ver mudancas com velocidade, use o modo hibrido: Postgres, PgBouncer, Redis e Prometheus ficam no Docker; backend e frontend rodam direto no Windows com reload automatico.

Rode um unico script:

```powershell
.\scripts\dev-fast.ps1
```

Ele cria o `.venv` do backend se faltar, instala dependencias, sobe backend e frontend em janelas separadas, espera os servicos responderem e abre `http://localhost:3000`.

Para subir somente o essencial, sem Prometheus:

```powershell
.\scripts\dev-fast.ps1 -SkipPrometheus
```

Para pular instalacao de dependencias quando voce sabe que nada mudou:

```powershell
.\scripts\dev-fast.ps1 -NoInstall
```

Se nao quiser abrir o navegador automaticamente:

```powershell
.\scripts\dev-fast.ps1 -NoBrowser
```

Se quiser pular o aquecimento dos modelos do Ollama:

```powershell
.\scripts\dev-fast.ps1 -NoWarmOllama
```

Para prender os logs do Docker Compose no terminal atual:

```powershell
.\scripts\dev-fast.ps1 -Attached
```

Fallback manual para o backend:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Fallback manual para o frontend:

```powershell
cd frontend
npm install
npm run dev
```

Depois acesse:

- Web dev: `http://localhost:3000`
- API dev: `http://localhost:8000/api/v1/health`
- Swagger/OpenAPI dev: `http://localhost:8000/docs`
- Prometheus: `http://localhost:9090`

O frontend ja usa `http://localhost:8000/api/v1` por padrao quando `NEXT_PUBLIC_API_BASE_URL` nao esta definido.
No modo rapido, o backend usa Postgres direto em `localhost:5432` para evitar problemas de startup/DDL via PgBouncer.

Se voce tiver `make` instalado, tambem pode subir a infraestrutura rapida com:

```powershell
make dev-fast
```

## Rodar localmente com Docker completo

Use este fluxo para validar a stack completa com Nginx e imagens Docker, mais proximo de producao.

Pré-requisito recomendado para IA local: Ollama rodando no Windows host.

```powershell
ollama serve
ollama pull llama3.2
ollama pull nomic-embed-text
```

Depois, na raiz do projeto, use o comando mais compatível com Windows:

```powershell
.\scripts\dev-up.ps1
```

Para rodar em segundo plano:

```powershell
.\scripts\dev-up.ps1 -Detached
```

Se você tiver `make` instalado, também pode usar:

```powershell
make up
```

Fallback manual:

```powershell
docker compose up --build
```

Depois acesse:

- Web: `http://localhost`
- Login do aluno: `http://localhost/login`
- Chat: `http://localhost/chat`
- Login admin: `http://localhost/admin/login`
- Senha admin inicial: `admin123`
- Configurações admin: `http://localhost/admin/settings`
- Health da API: `http://localhost/api/v1/health`
- Swagger/OpenAPI: `http://localhost/docs`
- Prometheus: `http://localhost:9090`

Fluxo do aluno:

- `http://localhost` valida a sessão automaticamente.
- Sem sessão, vai para `/login`.
- Primeiro acesso vai para `/onboarding`.
- Sessão ativa e onboarding completo vai para `/chat`.

Para login com Google, configure no `.env`:

```env
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://localhost/api/v1/auth/google/callback
FRONTEND_POST_LOGIN_URL=http://localhost/chat
FRONTEND_ONBOARDING_URL=http://localhost/onboarding
```

## Ollama com GPU

### Opção padrão: Ollama no Windows host

Este é o caminho mais simples para usar sua GPU NVIDIA.

```powershell
nvidia-smi
ollama serve
ollama pull llama3.2
ollama pull nomic-embed-text
Invoke-RestMethod http://localhost:11434/api/tags
```

O `.env` deve manter:

```env
DEFAULT_LLM_PROVIDER=ollama
DEFAULT_EMBEDDING_PROVIDER=ollama
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_LLM_MODEL=llama3.2
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
```

### Opção avançada: Ollama em Docker com GPU

Use apenas se o Docker Desktop/WSL já estiver configurado com suporte NVIDIA.

```powershell
make up-ollama-docker
make ollama-docker-pull
```

No Windows sem `make`, use:

```powershell
.\scripts\dev-up.ps1 -OllamaDocker
```

Fallback manual:

```powershell
docker compose -f docker-compose.yml -f docker-compose.ollama.yml --profile ollama-gpu up --build
docker compose -f docker-compose.yml -f docker-compose.ollama.yml --profile ollama-gpu exec ollama ollama pull llama3.2
docker compose -f docker-compose.yml -f docker-compose.ollama.yml --profile ollama-gpu exec ollama ollama pull nomic-embed-text
```

## Builds sem acúmulo de espaço

Use rebuild seguro, sem apagar volumes do banco:

```powershell
make rebuild
```

No Windows sem `make`:

```powershell
.\scripts\rebuild.ps1
```

Para limpar imagens dangling e cache antigo sem apagar `postgres_data`, `redis_data` ou modelos Ollama:

```powershell
make clean-docker
```

No Windows sem `make`:

```powershell
.\scripts\clean-docker.ps1
```

Fallback sem `make`:

```powershell
docker compose build frontend backend worker
docker compose up -d --force-recreate frontend backend worker nginx
docker image prune -f
docker builder prune -f --filter "until=24h"
docker system df
```

Evite `docker system prune --volumes`, porque isso pode apagar dados do banco e modelos locais.

Para diagnosticar GPU, Ollama, containers e espaço:

```powershell
.\scripts\status.ps1
```

## Desenvolvimento backend sem Docker

O backend sem Docker espera Postgres/PgBouncer em `localhost:6432` e Redis em `localhost:6379`.

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Testes e build

```powershell
python -m pytest -q
npm --prefix frontend run build
docker compose config --quiet
```

## Providers de IA

O projeto também aceita Gemini, mas para uso local gratuito o fluxo recomendado é Ollama.

```env
DEFAULT_LLM_PROVIDER=gemini
DEFAULT_EMBEDDING_PROVIDER=gemini
GEMINI_API_KEY=sua_chave
GEMINI_LLM_MODEL=gemini-3.5-flash
GEMINI_EMBEDDING_MODEL=gemini-embedding-001
```

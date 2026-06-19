# LinguaFlow AI

App web para aprendizado de línguas com IA conversacional, RAG, voz opcional, analytics e auditoria de latência/tokens.

## O que já está implementado

- Backend FastAPI em `/api/v1`.
- Frontend Next.js responsivo.
- Docker Compose com Nginx, Postgres/pgvector, PgBouncer, Redis e Prometheus.
- Chat textual com provider mock plugável.
- RAG admin documental com chunking, embeddings mock, fontes, confiança e auditoria.
- Dashboard agregado sem PII.
- Ledger de uso para tokens/custos estimados.
- Métricas de latência por turno.
- Registro dos módulos MCP-style em `backend/app/mcp_servers/registry.py`.

## Rodar localmente

```bash
cd language_ai_app
copy .env.example .env
docker compose up --build
```

Depois acesse:

- Web: `http://localhost`
- API docs: `http://localhost/api/v1` via OpenAPI em `http://localhost/docs` quando acessando backend diretamente na porta `8000`
- Prometheus: `http://localhost:9090`

## Desenvolvimento backend sem Docker

```bash
cd language_ai_app/backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Próximos passos recomendados

1. Adicionar autenticação JWT/session e RBAC real para admin.
2. Trocar embeddings mock por provider real ou local.
3. Implementar WebSocket/SSE streaming para chat e voz.
4. Migrar `embedding_json` para coluna `vector` com queries pgvector nativas.
5. Criar ETL para `analytics` schema com agregações LGPD-safe.
6. Adicionar adapters reais de STT/TTS.

# LinguaFlow AI Architecture

## Goals

LinguaFlow AI is a web-first language learning app with a mobile-ready backend. It separates conversation, speech, RAG, analytics, gamification, auditability and provider routing into MCP-style modules so each capability can evolve independently.

## Runtime

- Frontend: Next.js responsive PWA-ready app.
- Backend: FastAPI async with `/api/v1` REST contracts and future WebSocket/SSE streaming.
- Data: PostgreSQL through PgBouncer, Redis for cache/queues/rate limits and pgvector for vector search.
- Observability: Prometheus metrics endpoint plus trace IDs stored in each conversational turn.
- Deployment: Docker Compose for the first EC2 deployment.

## RAG Boundaries

- Learner RAG stores per-user memory and must always filter by learner ownership before retrieval.
- Admin RAG only sees indexed documents and aggregate analytics.
- Admin RAG must not query operational PII, private conversations or raw audio.
- Every admin answer should include sources, filters, confidence and origin.

## Latency Audit

Each conversational flow records:

- `time_to_first_transcript`
- `stt_duration`
- `rag_duration`
- `time_to_first_token`
- `llm_duration`
- `time_to_first_audio`
- `tts_duration`
- `total_turn_duration`

## Cost Audit

The usage ledger records LLM tokens, cached tokens, embeddings, STT seconds, TTS characters, provider, model, feature and estimated cost. Provider pricing should stay configurable and versioned as real adapters are added.

## Hermes Inspiration

Hermes Agent is treated as an architectural reference for persistent memory, MCP-like tool boundaries, voice mode and learning loops. It is not a required runtime dependency in v1.

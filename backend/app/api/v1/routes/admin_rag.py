from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.observability import LatencyTracker, TraceContext, timed_step
from app.db.session import get_session
from app.schemas.common import UsageSummary
from app.schemas.rag import AdminRagAnswer, AdminRagQuestion, DocumentIngestRequest, DocumentIngestResponse
from app.services.ai_providers.router import provider_router
from app.services.audit.ledger import record_llm_usage
from app.services.rag.vector_store import RagVectorStore, citation_from_chunk

router = APIRouter()


@router.post("/documents", response_model=DocumentIngestResponse)
async def ingest_document(
    payload: DocumentIngestRequest,
    session: AsyncSession = Depends(get_session),
) -> DocumentIngestResponse:
    store = RagVectorStore(session, provider_router.get_embeddings())
    document_id, chunks_indexed = await store.ingest_document(
        domain="admin-docs",
        title=payload.title,
        source_uri=payload.source_uri,
        language=payload.language,
        content=payload.content,
        metadata=payload.metadata,
    )
    await session.commit()
    return DocumentIngestResponse(document_id=document_id, chunks_indexed=chunks_indexed)


@router.post("/ask", response_model=AdminRagAnswer)
async def ask_admin_rag(
    payload: AdminRagQuestion,
    session: AsyncSession = Depends(get_session),
) -> AdminRagAnswer:
    trace = TraceContext()
    tracker = LatencyTracker()
    llm = provider_router.get_llm()
    store = RagVectorStore(session, provider_router.get_embeddings())

    async with timed_step(tracker, "rag_duration"):
        matches = await store.search(domain="admin-docs", query=payload.question, limit=5)

    citations = [citation_from_chunk(chunk, score) for chunk, score in matches if score > 0.35]
    evidence = "\n\n".join(chunk.content for chunk, score in matches if score > 0.35)
    guardrail = (
        "Responda apenas usando documentos indexados e analytics agregados. "
        "Não tente consultar PII, conversas privadas ou banco operacional de usuários. "
        f"Admin RAG pode acessar PII? {settings.admin_rag_allow_operational_pii}."
    )
    prompt = (
        f"Pergunta: {payload.question}\n"
        f"Evidências documentais:\n{evidence or 'Nenhuma evidência documental relevante encontrada.'}\n"
        "Se não houver evidência suficiente, diga isso claramente e sugira indexar documentos."
    )

    async with timed_step(tracker, "llm_duration"):
        result = await llm.complete(guardrail, prompt)

    latency = tracker.finish()
    await record_llm_usage(
        session,
        trace_id=trace.trace_id,
        user_id=None,
        feature="admin.rag.ask",
        usage=result.usage,
    )
    await session.commit()

    return AdminRagAnswer(
        trace_id=trace.trace_id,
        answer=result.text,
        sources=citations,
        filters_used={"domain": "admin-docs", "language": payload.language, "include_analytics": payload.include_analytics},
        confidence=max([source.confidence for source in citations], default=0),
        origin="documents+analytics-aggregate" if payload.include_analytics else "documents",
        latency_ms=latency,
        usage=UsageSummary(**result.usage.__dict__),
    )

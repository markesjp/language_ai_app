import math

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import RagChunk, RagDocument
from app.schemas.common import SourceCitation
from app.services.ai_providers.base import EmbeddingProvider, RerankProvider
from app.services.ai_providers.mock import NoopRerankProvider
from app.services.rag.chunking import chunk_text


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right:
        return 0
    total = sum(a * b for a, b in zip(left, right, strict=False))
    left_mag = math.sqrt(sum(a * a for a in left)) or 1
    right_mag = math.sqrt(sum(b * b for b in right)) or 1
    return total / (left_mag * right_mag)


class RagVectorStore:
    def __init__(self, session: AsyncSession, embeddings: EmbeddingProvider, reranker: RerankProvider | None = None):
        self.session = session
        self.embeddings = embeddings
        self.reranker = reranker or NoopRerankProvider()

    async def ingest_document(
        self,
        *,
        domain: str,
        title: str,
        source_uri: str,
        language: str,
        content: str,
        metadata: dict,
    ) -> tuple[str, int]:
        document = RagDocument(
            domain=domain,
            title=title,
            source_uri=source_uri,
            language=language,
            metadata_json=metadata,
        )
        self.session.add(document)
        await self.session.flush()

        chunks = chunk_text(content)
        for index, chunk in enumerate(chunks):
            embedding = await self.embeddings.embed(chunk)
            vector = embedding if len(embedding) == 64 else None
            self.session.add(
                RagChunk(
                    document_id=document.id,
                    domain=domain,
                    content=chunk,
                    metadata_json={**metadata, "chunk_index": index, "title": title, "source_uri": source_uri},
                    embedding_json=embedding,
                    embedding_vector=vector,
                )
            )
        return document.id, len(chunks)

    async def search(self, *, domain: str, query: str, limit: int = 5) -> list[tuple[RagChunk, float]]:
        existing_chunk = await self.session.scalar(select(RagChunk.id).where(RagChunk.domain == domain).limit(1))
        if not existing_chunk:
            return []

        query_embedding = await self.embeddings.embed(query)
        candidate_limit = max(limit, limit * 3)
        if self.session.bind and self.session.bind.dialect.name == "postgresql" and len(query_embedding) == 64:
            distance = RagChunk.embedding_vector.cosine_distance(query_embedding)
            result = await self.session.execute(
                select(RagChunk, distance.label("distance"))
                .where(RagChunk.domain == domain, RagChunk.embedding_vector.is_not(None))
                .order_by(distance)
                .limit(candidate_limit)
            )
            rows = result.all()
            if rows:
                scored = [(chunk, max(0, min(1, 1 - float(distance)))) for chunk, distance in rows]
                return await self._maybe_rerank(query=query, candidates=scored, limit=limit)

        result = await self.session.execute(select(RagChunk).where(RagChunk.domain == domain))
        scored = [
            (chunk, cosine_similarity(query_embedding, chunk.embedding_json))
            for chunk in result.scalars().all()
        ]
        candidates = sorted(scored, key=lambda item: item[1], reverse=True)[:candidate_limit]
        return await self._maybe_rerank(query=query, candidates=candidates, limit=limit)

    async def _maybe_rerank(self, *, query: str, candidates: list[tuple[RagChunk, float]], limit: int) -> list[tuple[RagChunk, float]]:
        if not candidates or self.reranker.name in {"none", "mock"}:
            return candidates[:limit]

        reranked = await self.reranker.rerank(query, [chunk.content for chunk, score in candidates], top_n=limit)
        by_index = {index: score for index, score in reranked}
        ordered = [
            (candidates[index][0], max(0, min(1, score)))
            for index, score in reranked
            if 0 <= index < len(candidates)
        ]
        if len(ordered) < limit:
            ordered.extend((chunk, score) for index, (chunk, score) in enumerate(candidates) if index not in by_index)
        return ordered[:limit]


def citation_from_chunk(chunk: RagChunk, score: float) -> SourceCitation:
    return SourceCitation(
        title=chunk.metadata_json.get("title", "Documento indexado"),
        source_uri=chunk.metadata_json.get("source_uri", "unknown://source"),
        chunk_id=chunk.id,
        confidence=max(0, min(1, round(score, 3))),
    )

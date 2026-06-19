import math

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import RagChunk, RagDocument
from app.schemas.common import SourceCitation
from app.services.ai_providers.base import EmbeddingProvider
from app.services.rag.chunking import chunk_text


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right:
        return 0
    total = sum(a * b for a, b in zip(left, right, strict=False))
    left_mag = math.sqrt(sum(a * a for a in left)) or 1
    right_mag = math.sqrt(sum(b * b for b in right)) or 1
    return total / (left_mag * right_mag)


class RagVectorStore:
    def __init__(self, session: AsyncSession, embeddings: EmbeddingProvider):
        self.session = session
        self.embeddings = embeddings

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
            self.session.add(
                RagChunk(
                    document_id=document.id,
                    domain=domain,
                    content=chunk,
                    metadata_json={**metadata, "chunk_index": index, "title": title, "source_uri": source_uri},
                    embedding_json=await self.embeddings.embed(chunk),
                )
            )
        return document.id, len(chunks)

    async def search(self, *, domain: str, query: str, limit: int = 5) -> list[tuple[RagChunk, float]]:
        query_embedding = await self.embeddings.embed(query)
        result = await self.session.execute(select(RagChunk).where(RagChunk.domain == domain))
        scored = [
            (chunk, cosine_similarity(query_embedding, chunk.embedding_json))
            for chunk in result.scalars().all()
        ]
        return sorted(scored, key=lambda item: item[1], reverse=True)[:limit]


def citation_from_chunk(chunk: RagChunk, score: float) -> SourceCitation:
    return SourceCitation(
        title=chunk.metadata_json.get("title", "Documento indexado"),
        source_uri=chunk.metadata_json.get("source_uri", "unknown://source"),
        chunk_id=chunk.id,
        confidence=max(0, min(1, round(score, 3))),
    )

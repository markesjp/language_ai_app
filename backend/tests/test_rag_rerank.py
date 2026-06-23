import pytest

from app.models import RagChunk
from app.services.ai_providers.base import RerankProvider
from app.services.ai_providers.mock import NoopRerankProvider
from app.services.rag.vector_store import RagVectorStore, cosine_similarity


class ReverseRerankProvider(RerankProvider):
    name = "reverse"
    model = "reverse-test"

    async def rerank(self, query: str, documents: list[str], top_n: int | None = None) -> list[tuple[int, float]]:
        indexes = list(reversed(range(len(documents))))
        return [(index, 0.9 - position * 0.1) for position, index in enumerate(indexes[: top_n or len(indexes)])]


def _chunk(content: str) -> RagChunk:
    return RagChunk(domain="test", document_id="doc", content=content, metadata_json={}, embedding_json=[1.0])


@pytest.mark.asyncio
async def test_rag_without_rerank_keeps_similarity_order():
    store = RagVectorStore.__new__(RagVectorStore)
    store.reranker = NoopRerankProvider()
    candidates = [(_chunk("first"), 0.9), (_chunk("second"), 0.8)]

    result = await store._maybe_rerank(query="q", candidates=candidates, limit=2)

    assert [chunk.content for chunk, score in result] == ["first", "second"]


@pytest.mark.asyncio
async def test_rag_with_rerank_reorders_only_candidates():
    store = RagVectorStore.__new__(RagVectorStore)
    store.reranker = ReverseRerankProvider()
    candidates = [(_chunk("first"), 0.9), (_chunk("second"), 0.8), (_chunk("third"), 0.7)]

    result = await store._maybe_rerank(query="q", candidates=candidates, limit=2)

    assert [chunk.content for chunk, score in result] == ["third", "second"]
    assert len(result) == 2


def test_cosine_similarity_handles_non_64_dimension_vectors():
    assert cosine_similarity([1.0, 0.0, 0.0], [1.0, 0.0, 0.0]) == 1.0

from pydantic import BaseModel, Field

from app.schemas.common import SourceCitation, UsageSummary


class DocumentIngestRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    source_uri: str = Field(default="manual://admin")
    language: str = "pt"
    content: str = Field(min_length=20)
    metadata: dict = {}


class DocumentIngestResponse(BaseModel):
    document_id: str
    chunks_indexed: int


class AdminRagQuestion(BaseModel):
    question: str = Field(min_length=3, max_length=4000)
    language: str = "pt"
    include_analytics: bool = True


class AdminRagAnswer(BaseModel):
    trace_id: str
    answer: str
    sources: list[SourceCitation]
    filters_used: dict
    confidence: float
    origin: str
    latency_ms: dict[str, float]
    usage: UsageSummary

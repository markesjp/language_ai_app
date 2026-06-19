from pydantic import BaseModel, Field


SUPPORTED_LANGUAGES = {"pt", "en", "es", "fr"}


class SourceCitation(BaseModel):
    title: str
    source_uri: str
    chunk_id: str | None = None
    confidence: float = Field(ge=0, le=1, default=0.5)


class UsageSummary(BaseModel):
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    estimated_cost_usd: float = 0

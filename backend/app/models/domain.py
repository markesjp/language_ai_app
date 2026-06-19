import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


def uuid_str() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(120))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    profile: Mapped["LearnerProfile"] = relationship(back_populates="user", uselist=False)


class LearnerProfile(Base):
    __tablename__ = "learner_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    native_language: Mapped[str] = mapped_column(String(16), default="pt")
    target_language: Mapped[str] = mapped_column(String(16), default="en")
    proficiency_level: Mapped[str] = mapped_column(String(32), default="beginner")
    age_range: Mapped[str | None] = mapped_column(String(32), nullable=True)
    gender: Mapped[str | None] = mapped_column(String(32), nullable=True)
    correction_preference: Mapped[str] = mapped_column(String(32), default="friendly")
    voice_preference: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    user: Mapped[User] = relationship(back_populates="profile")


class ConversationSession(Base):
    __tablename__ = "conversation_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    topic: Mapped[str] = mapped_column(String(160))
    mode: Mapped[str] = mapped_column(String(16), default="text")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class ConversationTurn(Base):
    __tablename__ = "conversation_turns"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    trace_id: Mapped[str] = mapped_column(String(36), index=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("conversation_sessions.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    user_message: Mapped[str] = mapped_column(Text)
    assistant_message: Mapped[str] = mapped_column(Text)
    feedback: Mapped[dict] = mapped_column(JSON, default=dict)
    latency_ms: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class UsageLedger(Base):
    __tablename__ = "usage_ledger"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    trace_id: Mapped[str] = mapped_column(String(36), index=True)
    user_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    feature: Mapped[str] = mapped_column(String(64))
    provider: Mapped[str] = mapped_column(String(64))
    model: Mapped[str] = mapped_column(String(120))
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cached_tokens: Mapped[int] = mapped_column(Integer, default=0)
    audio_seconds: Mapped[float] = mapped_column(Float, default=0)
    tts_characters: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class RagDocument(Base):
    __tablename__ = "rag_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    domain: Mapped[str] = mapped_column(String(32), index=True)
    title: Mapped[str] = mapped_column(String(255))
    source_uri: Mapped[str] = mapped_column(String(512))
    language: Mapped[str] = mapped_column(String(16), default="pt")
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class RagChunk(Base):
    __tablename__ = "rag_chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    document_id: Mapped[str] = mapped_column(ForeignKey("rag_documents.id"), index=True)
    domain: Mapped[str] = mapped_column(String(32), index=True)
    content: Mapped[str] = mapped_column(Text)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    embedding_json: Mapped[list[float]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class AnalyticsSnapshot(Base):
    __tablename__ = "analytics_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    metric_name: Mapped[str] = mapped_column(String(120), index=True)
    dimensions: Mapped[dict] = mapped_column(JSON, default=dict)
    value: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

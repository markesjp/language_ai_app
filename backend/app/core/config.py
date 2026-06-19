from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "development"
    database_url: str = "postgresql+asyncpg://language_user:language_pass@localhost:6432/language_ai"
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    auto_create_schema: bool = True

    default_llm_provider: str = "mock"
    default_stt_provider: str = "mock"
    default_tts_provider: str = "mock"
    default_embedding_provider: str = "mock"

    admin_rag_allow_operational_pii: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

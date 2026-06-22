from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), env_file_encoding="utf-8", extra="ignore")

    environment: str = "development"
    database_url: str = "postgresql+asyncpg://language_user:language_pass@localhost:6432/language_ai"
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    auto_create_schema: bool = True

    default_llm_provider: str = "mock"
    default_stt_provider: str = "mock"
    default_tts_provider: str = "mock"
    default_embedding_provider: str = "mock"
    embedding_dimension: int = 64

    gemini_api_key: str | None = None
    gemini_api_base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    gemini_llm_model: str = "gemini-3.5-flash"
    gemini_embedding_model: str = "gemini-embedding-001"

    ollama_base_url: str = "http://localhost:11434"
    ollama_llm_model: str = "llama3.2"
    ollama_embedding_model: str = "nomic-embed-text"

    admin_rag_allow_operational_pii: bool = False
    admin_master_password: str | None = None
    admin_session_secret: str = "development-admin-session-secret-change-me"
    admin_session_cookie: str = "linguaflow_admin"
    admin_session_ttl_seconds: int = 60 * 60 * 12
    admin_cookie_secure: bool = False

    user_session_secret: str = "development-user-session-secret-change-me"
    user_session_cookie: str = "linguaflow_user"
    user_session_ttl_seconds: int = 60 * 60 * 24 * 14
    password_reset_ttl_seconds: int = 60 * 30

    google_client_id: str | None = None
    google_client_secret: str | None = None
    google_redirect_uri: str = "http://localhost/api/v1/auth/google/callback"
    frontend_post_login_url: str = "http://localhost/chat"
    frontend_onboarding_url: str = "http://localhost/onboarding"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

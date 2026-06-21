from collections.abc import Callable

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_session
from app.schemas.admin import AdminSettingItem, AdminSettingsResponse, AdminSettingsUpdate
from app.services.rbac import require_permission
from app.services.runtime_settings import get_runtime_setting, load_runtime_settings, save_runtime_settings

router = APIRouter(dependencies=[Depends(require_permission("admin.settings:read"))])

PROVIDER_OPTIONS = ["mock", "gemini", "ollama"]
SECRET_KEYS = {"gemini_api_key"}


def _mask(value: object | None) -> str:
    if value in (None, ""):
        return "não configurado"
    text = str(value)
    if len(text) <= 8:
        return "••••"
    return f"{text[:4]}••••{text[-4:]}"


def _mask_url(value: str) -> str:
    if "://" not in value or "@" not in value:
        return value
    protocol, rest = value.split("://", 1)
    _, tail = rest.split("@", 1)
    return f"{protocol}://••••:••••@{tail}"


def _effective(key: str, fallback: object) -> object:
    return get_runtime_setting(key, fallback)


def _setting(
    key: str,
    label: str,
    category: str,
    fallback: object,
    description: str,
    *,
    editable: bool = False,
    secret: bool = False,
    options: list[str] | None = None,
    requires_restart: bool = False,
    mask: Callable[[object], str] | None = None,
) -> AdminSettingItem:
    value = _effective(key, fallback)
    return AdminSettingItem(
        key=key,
        label=label,
        category=category,
        value=None if secret else value,
        masked_value=_mask(value) if secret else (mask(value) if mask else None),
        editable=editable,
        secret=secret,
        requires_restart=requires_restart,
        description=description,
        options=options or [],
    )


def _settings_payload() -> AdminSettingsResponse:
    items = [
        _setting("default_llm_provider", "Provider LLM", "ia", settings.default_llm_provider, "Modelo conversacional usado no chat e no RAG administrativo.", editable=True, options=PROVIDER_OPTIONS),
        _setting("default_embedding_provider", "Provider de embeddings", "ia", settings.default_embedding_provider, "Motor usado para gerar vetores de documentos e consultas RAG.", editable=True, options=PROVIDER_OPTIONS),
        _setting("gemini_api_key", "Gemini API key", "ia", settings.gemini_api_key, "Chave mascarada usada pelos adapters Gemini.", editable=True, secret=True),
        _setting("gemini_llm_model", "Modelo Gemini LLM", "ia", settings.gemini_llm_model, "Modelo Gemini para respostas conversacionais.", editable=True),
        _setting("gemini_embedding_model", "Modelo Gemini embeddings", "ia", settings.gemini_embedding_model, "Modelo Gemini para embeddings.", editable=True),
        _setting("ollama_base_url", "URL Ollama", "ia", settings.ollama_base_url, "Endpoint HTTP do Ollama local.", editable=True),
        _setting("ollama_llm_model", "Modelo Ollama LLM", "ia", settings.ollama_llm_model, "Modelo local para conversa.", editable=True),
        _setting("ollama_embedding_model", "Modelo Ollama embeddings", "ia", settings.ollama_embedding_model, "Modelo local para embeddings.", editable=True),
        _setting("admin_rag_allow_operational_pii", "RAG pode acessar PII?", "rag", settings.admin_rag_allow_operational_pii, "Flag de segurança do guardrail administrativo.", editable=True),
        _setting("embedding_dimension", "Dimensão dos embeddings", "rag", settings.embedding_dimension, "Dimensão atual do vetor pgvector; mudar exige migração.", requires_restart=True),
        _setting("environment", "Ambiente", "sistema", settings.environment, "Ambiente ativo da aplicação."),
        _setting("database_url", "Banco de dados", "sistema", settings.database_url, "URL do banco mascarada.", mask=lambda value: _mask_url(str(value))),
        _setting("redis_url", "Redis", "sistema", settings.redis_url, "URL do Redis."),
        _setting("cors_origins", "CORS", "sistema", settings.cors_origins, "Origens permitidas para chamadas web."),
        _setting("admin_session_ttl_seconds", "Duração da sessão", "seguranca", settings.admin_session_ttl_seconds, "Tempo de validade do cookie admin."),
        _setting("admin_cookie_secure", "Cookie secure", "seguranca", settings.admin_cookie_secure, "Indica se cookies admin exigem HTTPS."),
    ]
    return AdminSettingsResponse(
        settings=items,
        warnings=[
            "Configurações críticas de infraestrutura são exibidas em modo leitura.",
            "Mudanças de dimensão de embedding exigem migração da coluna vector(64).",
        ],
    )


def _normalize_value(key: str, value: object) -> object:
    if key in {"default_llm_provider", "default_embedding_provider"}:
        if value not in PROVIDER_OPTIONS:
            raise HTTPException(status_code=422, detail=f"Unsupported provider for {key}")
        return value
    if key == "admin_rag_allow_operational_pii":
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in {"1", "true", "yes", "on"}
        return bool(value)
    if key in {
        "gemini_api_key",
        "gemini_llm_model",
        "gemini_embedding_model",
        "ollama_base_url",
        "ollama_llm_model",
        "ollama_embedding_model",
    }:
        return "" if value is None else str(value).strip()
    raise HTTPException(status_code=422, detail=f"Setting is not editable: {key}")


@router.get("", response_model=AdminSettingsResponse)
async def read_settings() -> AdminSettingsResponse:
    return _settings_payload()


@router.patch("", response_model=AdminSettingsResponse)
async def update_settings(
    payload: AdminSettingsUpdate,
    _user=Depends(require_permission("admin.settings:write")),
    session: AsyncSession = Depends(get_session),
) -> AdminSettingsResponse:
    normalized = {key: _normalize_value(key, value) for key, value in payload.values.items()}
    await save_runtime_settings(session, normalized, secret_keys=SECRET_KEYS)
    await session.commit()
    await load_runtime_settings(session)
    return _settings_payload()

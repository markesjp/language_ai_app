from collections.abc import Callable

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_session
from app.schemas.admin import AdminSettingItem, AdminSettingsResponse, AdminSettingsUpdate
from app.services.rbac import require_permission
from app.services.runtime_settings import get_runtime_setting, load_runtime_settings, save_runtime_settings

router = APIRouter(dependencies=[Depends(require_permission("admin.settings:read"))])

LLM_PROVIDER_OPTIONS = ["mock", "gemini", "ollama", "groq", "nvidia_nim"]
EMBEDDING_PROVIDER_OPTIONS = ["mock", "gemini", "ollama", "cohere", "nvidia_nim"]
RERANK_PROVIDER_OPTIONS = ["none", "cohere", "nvidia_nim"]
STT_PROVIDER_OPTIONS = ["mock", "groq", "deepgram"]
TTS_PROVIDER_OPTIONS = ["mock", "deepgram", "elevenlabs"]
SECRET_KEYS = {"gemini_api_key", "groq_api_key", "nvidia_nim_api_key", "cohere_api_key", "deepgram_api_key", "elevenlabs_api_key"}


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
        _setting("default_llm_provider", "Provider LLM", "ia", settings.default_llm_provider, "Modelo conversacional usado no chat e no RAG administrativo.", editable=True, options=LLM_PROVIDER_OPTIONS),
        _setting("default_embedding_provider", "Provider de embeddings", "ia", settings.default_embedding_provider, "Motor usado para gerar vetores de documentos e consultas RAG.", editable=True, options=EMBEDDING_PROVIDER_OPTIONS),
        _setting("default_rerank_provider", "Provider de rerank", "ia", settings.default_rerank_provider, "Reclassificador opcional aplicado depois da busca vetorial.", editable=True, options=RERANK_PROVIDER_OPTIONS),
        _setting("default_stt_provider", "Provider STT", "ia", settings.default_stt_provider, "Motor usado para transcrever audio enviado ao backend.", editable=True, options=STT_PROVIDER_OPTIONS),
        _setting("default_tts_provider", "Provider TTS", "ia", settings.default_tts_provider, "Motor usado para sintetizar audio no backend.", editable=True, options=TTS_PROVIDER_OPTIONS),
        _setting("gemini_api_key", "Gemini API key", "ia", settings.gemini_api_key, "Chave mascarada usada pelos adapters Gemini.", editable=True, secret=True),
        _setting("gemini_llm_model", "Modelo Gemini LLM", "ia", settings.gemini_llm_model, "Modelo Gemini para respostas conversacionais.", editable=True),
        _setting("gemini_embedding_model", "Modelo Gemini embeddings", "ia", settings.gemini_embedding_model, "Modelo Gemini para embeddings.", editable=True),
        _setting("groq_api_key", "Groq API key", "ia", settings.groq_api_key, "Chave mascarada usada pelos adapters Groq.", editable=True, secret=True),
        _setting("groq_api_base_url", "URL Groq", "ia", settings.groq_api_base_url, "Endpoint OpenAI-compatible da Groq.", editable=True),
        _setting("groq_llm_model", "Modelo Groq LLM", "ia", settings.groq_llm_model, "Modelo Groq para respostas conversacionais.", editable=True),
        _setting("groq_stt_model", "Modelo Groq STT", "ia", settings.groq_stt_model, "Modelo Groq para transcricao Whisper.", editable=True),
        _setting("nvidia_nim_api_key", "NVIDIA NIM API key", "ia", settings.nvidia_nim_api_key, "Chave mascarada usada pelos adapters NVIDIA NIM.", editable=True, secret=True),
        _setting("nvidia_nim_api_base_url", "URL NVIDIA NIM", "ia", settings.nvidia_nim_api_base_url, "Endpoint OpenAI-compatible da NVIDIA NIM.", editable=True),
        _setting("nvidia_nim_llm_model", "Modelo NVIDIA LLM", "ia", settings.nvidia_nim_llm_model, "Modelo NVIDIA NIM para conversa.", editable=True),
        _setting("nvidia_nim_embedding_model", "Modelo NVIDIA embeddings", "ia", settings.nvidia_nim_embedding_model, "Modelo NVIDIA NIM para embeddings.", editable=True),
        _setting("nvidia_nim_rerank_model", "Modelo NVIDIA rerank", "ia", settings.nvidia_nim_rerank_model, "Modelo NVIDIA NIM para reclassificacao RAG.", editable=True),
        _setting("cohere_api_key", "Cohere API key", "ia", settings.cohere_api_key, "Chave mascarada usada por embeddings e rerank Cohere.", editable=True, secret=True),
        _setting("cohere_api_base_url", "URL Cohere", "ia", settings.cohere_api_base_url, "Endpoint HTTP da Cohere.", editable=True),
        _setting("cohere_embedding_model", "Modelo Cohere embeddings", "ia", settings.cohere_embedding_model, "Modelo Cohere para embeddings.", editable=True),
        _setting("cohere_rerank_model", "Modelo Cohere rerank", "ia", settings.cohere_rerank_model, "Modelo Cohere para reclassificacao RAG.", editable=True),
        _setting("deepgram_api_key", "Deepgram API key", "ia", settings.deepgram_api_key, "Chave mascarada usada por STT/TTS Deepgram.", editable=True, secret=True),
        _setting("deepgram_api_base_url", "URL Deepgram", "ia", settings.deepgram_api_base_url, "Endpoint HTTP da Deepgram.", editable=True),
        _setting("deepgram_stt_model", "Modelo Deepgram STT", "ia", settings.deepgram_stt_model, "Modelo Deepgram para transcricao.", editable=True),
        _setting("deepgram_tts_model", "Modelo Deepgram TTS", "ia", settings.deepgram_tts_model, "Modelo/voz Deepgram Aura para sintese.", editable=True),
        _setting("elevenlabs_api_key", "ElevenLabs API key", "ia", settings.elevenlabs_api_key, "Chave mascarada usada por TTS ElevenLabs.", editable=True, secret=True),
        _setting("elevenlabs_api_base_url", "URL ElevenLabs", "ia", settings.elevenlabs_api_base_url, "Endpoint HTTP da ElevenLabs.", editable=True),
        _setting("elevenlabs_tts_model", "Modelo ElevenLabs TTS", "ia", settings.elevenlabs_tts_model, "Modelo ElevenLabs para sintese.", editable=True),
        _setting("elevenlabs_default_voice_id", "Voz ElevenLabs padrao", "ia", settings.elevenlabs_default_voice_id, "Voice ID usado quando o payload nao informar voz.", editable=True),
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
    option_groups = {
        "default_llm_provider": LLM_PROVIDER_OPTIONS,
        "default_embedding_provider": EMBEDDING_PROVIDER_OPTIONS,
        "default_rerank_provider": RERANK_PROVIDER_OPTIONS,
        "default_stt_provider": STT_PROVIDER_OPTIONS,
        "default_tts_provider": TTS_PROVIDER_OPTIONS,
    }
    if key in option_groups:
        if value not in option_groups[key]:
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
        "groq_api_key",
        "groq_api_base_url",
        "groq_llm_model",
        "groq_stt_model",
        "nvidia_nim_api_key",
        "nvidia_nim_api_base_url",
        "nvidia_nim_llm_model",
        "nvidia_nim_embedding_model",
        "nvidia_nim_rerank_model",
        "cohere_api_key",
        "cohere_api_base_url",
        "cohere_embedding_model",
        "cohere_rerank_model",
        "deepgram_api_key",
        "deepgram_api_base_url",
        "deepgram_stt_model",
        "deepgram_tts_model",
        "elevenlabs_api_key",
        "elevenlabs_api_base_url",
        "elevenlabs_tts_model",
        "elevenlabs_default_voice_id",
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

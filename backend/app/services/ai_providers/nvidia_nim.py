from app.core.config import settings
from app.services.ai_providers.openai_compatible import (
    OpenAiCompatibleEmbeddingProvider,
    OpenAiCompatibleLlmProvider,
    OpenAiCompatibleRerankProvider,
)
from app.services.runtime_settings import get_runtime_str


class NvidiaNimLlmProvider(OpenAiCompatibleLlmProvider):
    def __init__(self) -> None:
        super().__init__(
            name="nvidia_nim",
            model=get_runtime_str("nvidia_nim_llm_model", settings.nvidia_nim_llm_model) or settings.nvidia_nim_llm_model,
            api_key=get_runtime_str("nvidia_nim_api_key", settings.nvidia_nim_api_key),
            base_url=get_runtime_str("nvidia_nim_api_base_url", settings.nvidia_nim_api_base_url) or settings.nvidia_nim_api_base_url,
            missing_key_message="NVIDIA_NIM_API_KEY is required when DEFAULT_LLM_PROVIDER=nvidia_nim",
        )


class NvidiaNimEmbeddingProvider(OpenAiCompatibleEmbeddingProvider):
    def __init__(self) -> None:
        super().__init__(
            name="nvidia_nim",
            model=get_runtime_str("nvidia_nim_embedding_model", settings.nvidia_nim_embedding_model) or settings.nvidia_nim_embedding_model,
            api_key=get_runtime_str("nvidia_nim_api_key", settings.nvidia_nim_api_key),
            base_url=get_runtime_str("nvidia_nim_api_base_url", settings.nvidia_nim_api_base_url) or settings.nvidia_nim_api_base_url,
            missing_key_message="NVIDIA_NIM_API_KEY is required when DEFAULT_EMBEDDING_PROVIDER=nvidia_nim",
        )


class NvidiaNimRerankProvider(OpenAiCompatibleRerankProvider):
    def __init__(self) -> None:
        super().__init__(
            name="nvidia_nim",
            model=get_runtime_str("nvidia_nim_rerank_model", settings.nvidia_nim_rerank_model) or settings.nvidia_nim_rerank_model,
            api_key=get_runtime_str("nvidia_nim_api_key", settings.nvidia_nim_api_key),
            base_url=get_runtime_str("nvidia_nim_api_base_url", settings.nvidia_nim_api_base_url) or settings.nvidia_nim_api_base_url,
            missing_key_message="NVIDIA_NIM_API_KEY is required when DEFAULT_RERANK_PROVIDER=nvidia_nim",
        )

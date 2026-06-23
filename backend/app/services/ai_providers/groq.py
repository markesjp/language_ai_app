from app.core.config import settings
from app.services.ai_providers.openai_compatible import OpenAiCompatibleLlmProvider
from app.services.runtime_settings import get_runtime_str


class GroqLlmProvider(OpenAiCompatibleLlmProvider):
    def __init__(self) -> None:
        super().__init__(
            name="groq",
            model=get_runtime_str("groq_llm_model", settings.groq_llm_model) or settings.groq_llm_model,
            api_key=get_runtime_str("groq_api_key", settings.groq_api_key),
            base_url=get_runtime_str("groq_api_base_url", settings.groq_api_base_url) or settings.groq_api_base_url,
            missing_key_message="GROQ_API_KEY is required when DEFAULT_LLM_PROVIDER=groq",
        )

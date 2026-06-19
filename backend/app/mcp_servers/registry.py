MCP_MODULES = {
    "conversation": "Owns chat orchestration, streaming, correction and turn persistence.",
    "stt": "Owns speech-to-text adapters, partial transcripts and audio usage audit.",
    "tts": "Owns text-to-speech adapters, voice selection and time-to-first-audio metrics.",
    "provider-router": "Routes LLM, STT, TTS and embeddings across local/free/API providers.",
    "memory-rag": "Owns learner memory retrieval without exposing cross-user data.",
    "admin-rag": "Owns document and aggregate-analytics RAG with no operational PII access.",
    "learning-feedback": "Owns grammar, fluency, pronunciation and exercise feedback rubrics.",
    "gamification": "Owns streaks, XP, achievements and spaced repetition.",
    "usage-audit": "Owns token, audio, TTS and cost ledgers.",
    "latency-audit": "Owns per-step latency measurements and trace correlation.",
    "analytics": "Owns PII-free aggregate insight tables and dashboard metrics.",
}


def list_mcp_modules() -> dict[str, str]:
    return MCP_MODULES

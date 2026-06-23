import pytest
from fastapi import HTTPException

from app.api.v1.routes.admin_settings import _normalize_value, _settings_payload


def test_admin_settings_exposes_modular_provider_options():
    settings = {item.key: item for item in _settings_payload().settings}

    assert "groq" in settings["default_llm_provider"].options
    assert "nvidia_nim" in settings["default_llm_provider"].options
    assert "cohere" in settings["default_embedding_provider"].options
    assert settings["default_rerank_provider"].options == ["none", "cohere", "nvidia_nim"]
    assert "deepgram" in settings["default_stt_provider"].options
    assert "elevenlabs" in settings["default_tts_provider"].options


def test_admin_settings_masks_new_secret_keys():
    settings = {item.key: item for item in _settings_payload().settings}

    for key in ["groq_api_key", "nvidia_nim_api_key", "cohere_api_key", "deepgram_api_key", "elevenlabs_api_key"]:
        assert settings[key].secret is True
        assert settings[key].value is None


def test_admin_settings_rejects_invalid_provider():
    with pytest.raises(HTTPException):
        _normalize_value("default_llm_provider", "bad-provider")

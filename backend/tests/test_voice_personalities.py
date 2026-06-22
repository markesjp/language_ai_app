import pytest
from pydantic import ValidationError

from app.schemas.conversation import ChatRequest
from app.schemas.practice import VoicePersonalityCreate, VoicePresetCreate
from app.services.practice_catalog import LANGUAGES, PERSONALITY_BLUEPRINTS, VOICE_BLUEPRINTS


def test_default_voice_blueprints_include_male_and_female_for_each_language():
    genders = {blueprint[1] for blueprint in VOICE_BLUEPRINTS}

    assert {"female", "male"}.issubset(genders)
    assert len(LANGUAGES) == 4


def test_default_personalities_include_male_and_female():
    genders = {blueprint["gender"] for blueprint in PERSONALITY_BLUEPRINTS}

    assert {"female", "male"}.issubset(genders)


def test_voice_preset_rejects_unknown_gender():
    with pytest.raises(ValidationError):
        VoicePresetCreate(name="Invalid", gender="robot")


def test_voice_personality_schema_accepts_admin_fields():
    personality = VoicePersonalityCreate(
        name="Marina",
        gender="female",
        age=32,
        profession="professora",
        hobbies="música",
        description="Paciente",
        tone="gentil",
        prompt_instructions="Corrija com cuidado.",
        target_language="pt",
    )

    assert personality.gender == "female"
    assert personality.prompt_instructions


def test_chat_request_accepts_voice_personality_id():
    request = ChatRequest(user_id="user-1", message="hello", voice_personality_id="personality-1")

    assert request.voice_personality_id == "personality-1"

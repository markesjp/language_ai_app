from datetime import UTC, datetime

from app.models import ConversationSession, ConversationTurn
from app.schemas.conversation import ChatRequest
from app.services.conversation.service import ConversationService


def test_recent_turns_are_formatted_and_truncated():
    service = ConversationService(session=None)  # type: ignore[arg-type]
    turns = [
        ConversationTurn(
            id=f"turn-{index}",
            trace_id=f"trace-{index}",
            session_id="session-1",
            user_id="user-1",
            user_message=f"Learner said: mensagem {index}",
            assistant_message=f"resposta {index}",
            feedback={},
            latency_ms={},
            created_at=datetime.now(UTC),
        )
        for index in range(2)
    ]

    history = service._format_recent_turns(turns)

    assert "Aluno: mensagem 0" in history
    assert "Tutor: resposta 0" in history
    assert "Aluno: mensagem 1" in history


def test_system_prompt_includes_memory_layers():
    service = ConversationService(session=None)  # type: ignore[arg-type]
    request = ChatRequest(
        user_id="user-1",
        native_language="pt",
        target_language="en",
        topic="restaurant",
        message="I want coffee",
    )
    conversation_session = ConversationSession(
        id="session-1",
        user_id="user-1",
        topic="restaurant",
        mode="text",
        summary="O aluno se chama Pedro e está treinando restaurante.",
        summary_turn_count=4,
        last_user_intent="Pedir café",
        open_question="What would you like to order?",
    )

    prompt = service._build_system_prompt(
        request=request,
        conversation_session=conversation_session,
        practice_context="Cenário: restaurante",
        personality_context="Nome: Marina; gênero: female; profissão: professora",
        memory_context="Pedro prefere praticar pedidos em cafeteria.",
        history_context="Aluno: I want coffee\nTutor: Sure, what size?",
    )

    assert "Resumo compacto da sessão: O aluno se chama Pedro" in prompt
    assert "Personalidade de voz/IA: Nome: Marina" in prompt
    assert "Memórias persistentes relevantes: Pedro prefere praticar" in prompt
    assert "Últimos turnos: Aluno: I want coffee" in prompt
    assert "Não reinicie o assunto" in prompt


def test_memory_domain_is_scoped_by_user():
    service = ConversationService(session=None)  # type: ignore[arg-type]

    assert service._memory_domain("user-1") == "learner-memory:user-1"
    assert service._memory_domain("user-2") != service._memory_domain("user-1")


def test_truncate_compacts_context_budget():
    text = "palavra " * 500

    compacted = ConversationService._truncate(text, 120)

    assert len(compacted) <= 120
    assert compacted.endswith("…")

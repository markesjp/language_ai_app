from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.core.observability import LatencyTracker, TraceContext, timed_step
from app.models import ConversationSession, ConversationTurn, LearnerProfile, PracticeScenario, PracticeSkill, User
from app.schemas.common import UsageSummary
from app.schemas.conversation import ChatRequest, ChatResponse, PedagogicalFeedback
from app.services.ai_providers.router import provider_router
from app.services.audit.ledger import record_llm_usage
from app.services.rag.vector_store import RagVectorStore


class ConversationService:
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _extract_learner_message(message: str) -> str:
        marker = "Learner said:"
        if marker not in message:
            return message
        return message.rsplit(marker, 1)[-1].strip() or message

    async def chat(self, request: ChatRequest) -> ChatResponse:
        trace = TraceContext()
        tracker = LatencyTracker()
        learner_message = self._extract_learner_message(request.message)

        await self.session.execute(
            insert(User)
            .values(
                id=request.user_id,
                email=f"{request.user_id}@demo.local",
                display_name="Demo learner",
            )
            .on_conflict_do_nothing(index_elements=[User.id])
        )
        user = await self.session.scalar(select(User).where(User.id == request.user_id))
        if not user:
            await self.session.flush()
            user = await self.session.scalar(select(User).where(User.id == request.user_id))

        await self.session.execute(
            insert(LearnerProfile)
            .values(
                user_id=user.id,
                native_language=request.native_language,
                target_language=request.target_language,
            )
            .on_conflict_do_nothing(index_elements=[LearnerProfile.user_id])
        )

        session_id = request.session_id
        if not session_id:
            conversation_session = ConversationSession(user_id=request.user_id, topic=request.topic, mode=request.mode)
            self.session.add(conversation_session)
            await self.session.flush()
            session_id = conversation_session.id

        llm = provider_router.get_llm()
        embeddings = provider_router.get_embeddings()
        rag_store = RagVectorStore(self.session, embeddings)

        async with timed_step(tracker, "rag_duration"):
            memories = await rag_store.search(domain="learner-memory", query=learner_message, limit=3)

        memory_context = "\n".join(chunk.content for chunk, score in memories if score > 0.55)
        system_prompt = (
            "Você é uma IA professora de línguas, humana, gentil e objetiva. "
            "Converse no idioma-alvo, corrija sem humilhar e explique brevemente. "
            f"Idioma nativo: {request.native_language}. Idioma-alvo: {request.target_language}. "
            f"Tópico: {request.topic}. Memória relevante: {memory_context or 'sem memória relevante'}."
        )
        if request.voice_enabled or request.mode == "voice":
            system_prompt += (
                " Modo voz ativo: responda com no maximo 35 palavras em ate duas frases curtas, sem listas, "
                "sem Markdown, sem varias alternativas, e termine com uma pergunta simples."
            )
        practice_context = await self._build_practice_context(request)
        if practice_context:
            system_prompt += f" Contexto de prática: {practice_context}"
        if request.voice_enabled or request.mode == "voice":
            system_prompt = (
                "You are a concise live language tutor. "
                f"Native={request.native_language}. Target={request.target_language}. Scenario={request.topic}. "
                f"Memory={memory_context or 'none'}. Practice={practice_context or 'none'}. "
                "Reply only in the target language with at most 30 words, no Markdown, no lists, and ask one simple follow-up."
            )
        user_prompt = learner_message

        async with timed_step(tracker, "llm_duration"):
            max_output_tokens = 48 if request.voice_enabled or request.mode == "voice" else 192
            llm_result = await llm.complete(system_prompt, user_prompt, max_output_tokens=max_output_tokens)

        tracker.measurements_ms.setdefault("time_to_first_token", tracker.measurements_ms["llm_duration"])

        feedback = PedagogicalFeedback(
            corrected_text=None,
            explanation="Correção amigável gerada junto da conversa. Em providers reais, este campo deve usar rubrica estruturada.",
            focus_points=["fluência", "vocabulário", "naturalidade"],
            encouragement="Boa! Continue praticando um pouco todos os dias.",
        )
        latency = tracker.finish()
        turn = ConversationTurn(
            id=trace.conversation_turn_id,
            trace_id=trace.trace_id,
            session_id=session_id,
            user_id=request.user_id,
            user_message=request.message,
            assistant_message=llm_result.text,
            feedback=feedback.model_dump(),
            latency_ms=latency,
        )
        self.session.add(turn)
        await record_llm_usage(
            self.session,
            trace_id=trace.trace_id,
            user_id=request.user_id,
            feature="conversation.chat",
            usage=llm_result.usage,
        )
        await self.session.commit()

        return ChatResponse(
            trace_id=trace.trace_id,
            conversation_turn_id=trace.conversation_turn_id,
            session_id=session_id,
            answer=llm_result.text,
            feedback=feedback,
            latency_ms=latency,
            usage=UsageSummary(**llm_result.usage.__dict__),
        )

    async def _build_practice_context(self, request: ChatRequest) -> str:
        parts: list[str] = []
        if request.scenario_id:
            scenario = await self.session.get(PracticeScenario, request.scenario_id)
            if scenario and scenario.is_active:
                parts.append(f"Cenário: {scenario.title}. {scenario.description}. Instrução: {scenario.prompt_template}")
        if request.custom_scenario:
            parts.append(f"Cenário customizado: {request.custom_scenario}")

        skill_names: list[str] = []
        if request.skill_ids:
            result = await self.session.execute(select(PracticeSkill).where(PracticeSkill.id.in_(request.skill_ids)))
            skill_names.extend(skill.name for skill in result.scalars().all() if skill.is_active)
        if request.custom_skills:
            skill_names.append(request.custom_skills)
        if skill_names:
            parts.append(f"Skills para treinar: {', '.join(skill_names)}")

        if request.voice_preset_id or request.voice_speed:
            speed = f"{request.voice_speed:.2f}" if request.voice_speed else "padrão"
            parts.append(f"Preferência de voz: preset={request.voice_preset_id or 'não informado'}, velocidade={speed}")

        return " ".join(parts)

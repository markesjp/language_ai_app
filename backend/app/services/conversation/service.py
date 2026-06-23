from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.observability import LatencyTracker, TraceContext, timed_step
from app.models import ConversationSession, ConversationTurn, LearnerProfile, PracticeScenario, PracticeSkill, User, VoicePersonality
from app.schemas.common import UsageSummary
from app.schemas.conversation import ChatRequest, ChatResponse, MemoryDebug, PedagogicalFeedback
from app.services.ai_providers.router import provider_router
from app.services.audit.ledger import record_llm_usage
from app.services.rag.vector_store import RagVectorStore


class ConversationService:
    RECENT_TURN_LIMIT = 6
    SUMMARY_INTERVAL_TURNS = 4
    SUMMARY_MAX_CHARS = 1200
    RECENT_HISTORY_MAX_CHARS = 2200
    PERSISTENT_MEMORY_LIMIT = 3

    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _extract_learner_message(message: str) -> str:
        marker = "Learner said:"
        if marker not in message:
            return message
        return message.rsplit(marker, 1)[-1].strip() or message

    @staticmethod
    def _truncate(text: str, max_chars: int) -> str:
        normalized = " ".join(text.split())
        if len(normalized) <= max_chars:
            return normalized
        return f"{normalized[: max_chars - 1].rstrip()}…"

    async def chat(self, request: ChatRequest) -> ChatResponse:
        trace = TraceContext()
        tracker = LatencyTracker()
        learner_message = self._extract_learner_message(request.message)

        await self._ensure_demo_user(request)
        conversation_session = await self._resolve_session(request)
        if not conversation_session:
            conversation_session = ConversationSession(user_id=request.user_id, topic=request.topic, mode=request.mode)
            self.session.add(conversation_session)
            await self.session.flush()
        session_id = conversation_session.id

        llm = provider_router.get_llm()
        embeddings = provider_router.get_embeddings()
        rag_store = RagVectorStore(self.session, embeddings, provider_router.get_rerank())
        memory_domain = self._memory_domain(request.user_id)

        async with timed_step(tracker, "history_duration"):
            recent_turns = await self._load_recent_turns(session_id)

        async with timed_step(tracker, "memory_duration"):
            memories = await rag_store.search(domain=memory_domain, query=learner_message, limit=self.PERSISTENT_MEMORY_LIMIT)

        practice_context = await self._build_practice_context(request)
        personality_context = await self._build_personality_context(request)
        memory_context = "\n".join(self._truncate(chunk.content, 420) for chunk, score in memories if score > 0.55)
        system_prompt = self._build_system_prompt(
            request=request,
            conversation_session=conversation_session,
            practice_context=practice_context,
            personality_context=personality_context,
            memory_context=memory_context,
            history_context=self._format_recent_turns(recent_turns),
        )

        async with timed_step(tracker, "llm_duration"):
            max_output_tokens = 48 if request.voice_enabled or request.mode == "voice" else 192
            llm_result = await llm.complete(system_prompt, learner_message, max_output_tokens=max_output_tokens)

        tracker.measurements_ms.setdefault("time_to_first_token", tracker.measurements_ms["llm_duration"])

        feedback = PedagogicalFeedback(
            corrected_text=None,
            explanation="Correção amigável gerada junto da conversa. Em providers reais, este campo deve usar rubrica estruturada.",
            focus_points=["fluência", "vocabulário", "naturalidade"],
            encouragement="Boa! Continue praticando um pouco todos os dias.",
        )
        turn = ConversationTurn(
            id=trace.conversation_turn_id,
            trace_id=trace.trace_id,
            session_id=session_id,
            user_id=request.user_id,
            user_message=request.message,
            assistant_message=llm_result.text,
            feedback=feedback.model_dump(),
            latency_ms={},
        )
        self.session.add(turn)
        await self.session.flush()
        await record_llm_usage(
            self.session,
            trace_id=trace.trace_id,
            user_id=request.user_id,
            feature="conversation.chat",
            usage=llm_result.usage,
        )

        async with timed_step(tracker, "summary_duration"):
            await self._maybe_update_compacted_memory(
                conversation_session=conversation_session,
                llm=llm,
                rag_store=rag_store,
                memory_domain=memory_domain,
                recent_turns=[*recent_turns, turn],
                learner_message=learner_message,
                assistant_message=llm_result.text,
            )

        latency = tracker.finish()
        turn.latency_ms = latency
        await self.session.commit()

        return ChatResponse(
            trace_id=trace.trace_id,
            conversation_turn_id=trace.conversation_turn_id,
            session_id=session_id,
            answer=llm_result.text,
            feedback=feedback,
            latency_ms=latency,
            usage=UsageSummary(**llm_result.usage.__dict__),
            memory=MemoryDebug(
                summary_used=bool(conversation_session.summary),
                recent_turns_used=len(recent_turns),
                persistent_memories_used=len(memories),
            ),
        )

    async def _ensure_demo_user(self, request: ChatRequest) -> User:
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
        return user

    def _build_system_prompt(
        self,
        *,
        request: ChatRequest,
        conversation_session: ConversationSession,
        practice_context: str,
        personality_context: str,
        memory_context: str,
        history_context: str,
    ) -> str:
        summary_context = self._truncate(conversation_session.summary or "", self.SUMMARY_MAX_CHARS)
        open_question = self._truncate(conversation_session.open_question or "", 320)
        last_user_intent = self._truncate(conversation_session.last_user_intent or "", 240)
        voice_instruction = ""
        if request.voice_enabled or request.mode == "voice":
            voice_instruction = (
                "Modo voz: responda em no máximo 30 palavras, sem Markdown, sem listas, "
                "mas preserve o assunto ativo e termine com uma pergunta simples."
            )

        return (
            "Você é uma IA professora de línguas, humana, gentil e objetiva. "
            "Converse no idioma-alvo, corrija com leveza e mantenha continuidade. "
            "Não reinicie o assunto se houver resumo, pergunta aberta ou histórico recente.\n"
            f"Perfil: idioma nativo={request.native_language}; idioma-alvo={request.target_language}; tópico={request.topic}.\n"
            f"Contexto de prática: {practice_context or 'não informado'}.\n"
            f"Personalidade de voz/IA: {personality_context or 'personalidade padrão do tutor'}.\n"
            "A personalidade influencia estilo e vocabulário, mas nunca sobrescreve idioma-alvo, correção pedagógica ou regras de segurança.\n"
            f"Resumo compacto da sessão: {summary_context or 'ainda sem resumo'}.\n"
            f"Última intenção do aluno: {last_user_intent or 'não registrada'}.\n"
            f"Pergunta aberta/pendência: {open_question or 'nenhuma'}.\n"
            f"Memórias persistentes relevantes: {memory_context or 'nenhuma recuperada'}.\n"
            f"Últimos turnos: {history_context or 'sem turnos anteriores'}.\n"
            f"{voice_instruction}"
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

    async def _build_personality_context(self, request: ChatRequest) -> str:
        if not request.voice_personality_id:
            return ""
        personality = await self.session.get(VoicePersonality, request.voice_personality_id)
        if not personality or not personality.is_active:
            return ""
        if personality.target_language and personality.target_language != request.target_language:
            return ""
        parts = [
            f"Nome: {personality.name}",
            f"gênero: {personality.gender}",
            f"idade: {personality.age if personality.age is not None else 'não informada'}",
            f"profissão: {personality.profession or 'não informada'}",
            f"hobbies: {personality.hobbies or 'não informados'}",
            f"tom: {personality.tone or 'amigável'}",
            f"descrição: {personality.description or 'sem descrição'}",
            f"instruções: {personality.prompt_instructions or 'sem instruções extras'}",
        ]
        return "; ".join(parts)

    async def _resolve_session(self, request: ChatRequest) -> ConversationSession | None:
        if not request.session_id:
            return None

        conversation_session = await self.session.get(ConversationSession, request.session_id)
        if not conversation_session or conversation_session.user_id != request.user_id:
            return None

        return conversation_session

    async def _load_recent_turns(self, session_id: str) -> list[ConversationTurn]:
        result = await self.session.execute(
            select(ConversationTurn)
            .where(ConversationTurn.session_id == session_id)
            .order_by(ConversationTurn.created_at.desc())
            .limit(self.RECENT_TURN_LIMIT)
        )
        return list(reversed(result.scalars().all()))

    def _format_recent_turns(self, turns: list[ConversationTurn]) -> str:
        lines: list[str] = []
        for turn in turns:
            learner_text = self._truncate(self._extract_learner_message(turn.user_message), 220)
            assistant_text = self._truncate(turn.assistant_message, 260)
            lines.append(f"Aluno: {learner_text}\nTutor: {assistant_text}")
        return self._truncate("\n".join(lines), self.RECENT_HISTORY_MAX_CHARS)

    def _memory_domain(self, user_id: str) -> str:
        return f"learner-memory:{user_id}"

    async def _maybe_update_compacted_memory(
        self,
        *,
        conversation_session: ConversationSession,
        llm: Any,
        rag_store: RagVectorStore,
        memory_domain: str,
        recent_turns: list[ConversationTurn],
        learner_message: str,
        assistant_message: str,
    ) -> None:
        turn_count = await self.session.scalar(
            select(func.count()).select_from(ConversationTurn).where(ConversationTurn.session_id == conversation_session.id)
        )
        turn_count = int(turn_count or 0)
        conversation_session.last_user_intent = self._truncate(learner_message, 240)
        conversation_session.open_question = self._extract_open_question(assistant_message)

        should_summarize = (
            turn_count == 1
            or turn_count - (conversation_session.summary_turn_count or 0) >= self.SUMMARY_INTERVAL_TURNS
        )
        if not should_summarize:
            return

        system_prompt = (
            "Compacte memória conversacional para uma IA professora de idiomas. "
            "Retorne somente um resumo curto em português, sem Markdown, com no máximo 1200 caracteres. "
            "Preserve: assunto ativo, objetivo da prática, fatos úteis do aluno, erros recorrentes e próxima pendência. "
            "Não invente fatos."
        )
        user_prompt = (
            f"Resumo anterior: {conversation_session.summary or 'nenhum'}\n"
            f"Turnos recentes:\n{self._format_recent_turns(recent_turns)}\n"
            f"Última intenção: {learner_message}\n"
            f"Última resposta do tutor: {assistant_message}"
        )

        try:
            summary_result = await llm.complete(system_prompt, user_prompt, max_output_tokens=220)
            summary = self._truncate(summary_result.text, self.SUMMARY_MAX_CHARS)
            conversation_session.summary = summary
            conversation_session.summary_turn_count = turn_count
            await rag_store.ingest_document(
                domain=memory_domain,
                title="Resumo de sessão do aluno",
                source_uri=f"conversation-session://{conversation_session.id}",
                language="pt",
                content=summary,
                metadata={
                    "user_id": conversation_session.user_id,
                    "session_id": conversation_session.id,
                    "kind": "session_summary",
                    "turn_count": turn_count,
                },
            )
        except Exception:
            return

    def _extract_open_question(self, assistant_message: str) -> str:
        if "?" in assistant_message:
            before_last_question = assistant_message.rsplit("?", 1)[0]
            candidate = before_last_question.rsplit(".", 1)[-1].strip()
            if candidate:
                return self._truncate(f"{candidate}?", 320)

        sentences = [part.strip() for part in assistant_message.replace("!", ".").split(".") if part.strip()]
        if sentences:
            return self._truncate(sentences[-1], 320)
        return ""

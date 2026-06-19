from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.observability import LatencyTracker, TraceContext, timed_step
from app.models import ConversationSession, ConversationTurn, LearnerProfile, User
from app.schemas.common import UsageSummary
from app.schemas.conversation import ChatRequest, ChatResponse, PedagogicalFeedback
from app.services.ai_providers.router import provider_router
from app.services.audit.ledger import record_llm_usage
from app.services.rag.vector_store import RagVectorStore


class ConversationService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def chat(self, request: ChatRequest) -> ChatResponse:
        trace = TraceContext()
        tracker = LatencyTracker()

        user = await self.session.scalar(select(User).where(User.id == request.user_id))
        if not user:
            user = User(
                id=request.user_id,
                email=f"{request.user_id}@demo.local",
                display_name="Demo learner",
            )
            self.session.add(user)
            await self.session.flush()
            self.session.add(
                LearnerProfile(
                    user_id=user.id,
                    native_language=request.native_language,
                    target_language=request.target_language,
                )
            )
            await self.session.flush()

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
            memories = await rag_store.search(domain="learner-memory", query=request.message, limit=3)

        memory_context = "\n".join(chunk.content for chunk, score in memories if score > 0.55)
        system_prompt = (
            "Você é uma IA professora de línguas, humana, gentil e objetiva. "
            "Converse no idioma-alvo, corrija sem humilhar e explique brevemente. "
            f"Idioma nativo: {request.native_language}. Idioma-alvo: {request.target_language}. "
            f"Tópico: {request.topic}. Memória relevante: {memory_context or 'sem memória relevante'}."
        )
        user_prompt = request.message

        async with timed_step(tracker, "llm_duration"):
            llm_result = await llm.complete(system_prompt, user_prompt)

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

import asyncio
import time
from app.db.session import AsyncSessionLocal
from app.schemas.conversation import ChatRequest
from app.services.conversation.service import ConversationService
from app.core.config import settings

async def main():
    print(f"Loaded LLM Provider from config: {settings.default_llm_provider}")
    print(f"Loaded OLLAMA URL: {settings.ollama_base_url}")
    
    async with AsyncSessionLocal() as session:
        service = ConversationService(session)
        req = ChatRequest(
            user_id="test_id",
            message="hello",
            native_language="pt",
            target_language="en",
            topic="greetings",
            voice_enabled=True,
            mode="voice"
        )
        try:
            start_time = time.time()
            print("Sending request to LLM...")
            res = await service.chat(req)
            elapsed = time.time() - start_time
            print(f"Response ({elapsed:.2f}s):", res.answer)
        except Exception as e:
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(main())

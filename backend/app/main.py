from contextlib import asynccontextmanager
import asyncio
import contextlib

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from app.api.v1.router import api_router
from app.core.config import settings
from app.db.session import AsyncSessionLocal, create_schema
from app.services.admin_auth import bootstrap_admin_credential
from app.services.practice_catalog import bootstrap_practice_catalog
from app.services.rbac import bootstrap_rbac
from app.services.runtime_settings import load_runtime_settings
from app.services.ai_providers.router import provider_router


async def warm_ollama_llm() -> None:
    with contextlib.suppress(Exception):
        llm = provider_router.get_llm("ollama")
        await llm.complete("Warm up. Reply with one word.", "ok", max_output_tokens=1)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.auto_create_schema:
        await create_schema()
    async with AsyncSessionLocal() as session:
        await bootstrap_admin_credential(session)
        await bootstrap_rbac(session)
        await bootstrap_practice_catalog(session)
        await load_runtime_settings(session)
    with contextlib.suppress(Exception):
        await asyncio.wait_for(warm_ollama_llm(), timeout=45)
    yield


app = FastAPI(
    title="Language AI Learning Platform",
    version="0.1.0",
    description="Web-first language learning platform with MCP-style modules, RAG, speech, analytics, and audited AI usage.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")
app.mount("/metrics", make_asgi_app())


@app.get("/")
async def root() -> dict[str, str]:
    return {"name": "Language AI Learning Platform", "status": "ok"}

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from app.api.v1.router import api_router
from app.core.config import settings
from app.db.session import create_schema


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.auto_create_schema:
        await create_schema()
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

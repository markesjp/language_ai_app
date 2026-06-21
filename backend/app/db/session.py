import asyncio

from sqlalchemy.exc import OperationalError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.base import Base

engine = create_async_engine(settings.database_url, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session():
    async with AsyncSessionLocal() as session:
        yield session


async def create_schema() -> None:
    attempts = 30
    for attempt in range(1, attempts + 1):
        try:
            async with engine.begin() as connection:
                if engine.dialect.name == "postgresql":
                    await connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                await connection.run_sync(Base.metadata.create_all)
                if engine.dialect.name == "postgresql":
                    await connection.execute(
                        text("ALTER TABLE IF EXISTS rag_chunks ADD COLUMN IF NOT EXISTS embedding_vector vector(64)")
                    )
                    await connection.execute(text("ALTER TABLE IF EXISTS users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(256)"))
                    await connection.execute(text("ALTER TABLE IF EXISTS users ADD COLUMN IF NOT EXISTS salt VARCHAR(128)"))
                    await connection.execute(
                        text("ALTER TABLE IF EXISTS users ADD COLUMN IF NOT EXISTS iterations INTEGER DEFAULT 210000")
                    )
                    await connection.execute(
                        text("ALTER TABLE IF EXISTS learner_profiles ADD COLUMN IF NOT EXISTS learning_goal VARCHAR(64)")
                    )
                    await connection.execute(
                        text("ALTER TABLE IF EXISTS learner_profiles ADD COLUMN IF NOT EXISTS practice_preference VARCHAR(64)")
                    )
                    await connection.execute(
                        text(
                            "ALTER TABLE IF EXISTS learner_profiles "
                            "ADD COLUMN IF NOT EXISTS onboarding_completed BOOLEAN DEFAULT false"
                        )
                    )
                    await connection.execute(
                        text("ALTER TABLE IF EXISTS learner_profiles ADD COLUMN IF NOT EXISTS recommended_scenario_id VARCHAR(36)")
                    )
            return
        except (ConnectionRefusedError, OSError, OperationalError):
            if attempt == attempts:
                raise
            await asyncio.sleep(1)

from contextlib import asynccontextmanager
from typing import Optional
from urllib.parse import quote

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from configs.settings import get_settings


class Base(DeclarativeBase):
    pass


def get_postgres_url(is_async: bool = True) -> str:
    user = get_settings().POSTGRES_USER
    password = quote(get_settings().POSTGRES_PASSWORD)
    host = get_settings().POSTGRES_HOST
    port = get_settings().POSTGRES_PORT
    db = get_settings().POSTGRES_DB

    if is_async:
        return f"postgresql+psycopg_async://{user}:{password}@{host}:{port}/{db}"
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db}"


engine: Optional[AsyncEngine] = None
SessionLocal: Optional[async_sessionmaker[AsyncSession]] = None


def init_engine() -> None:
    global engine, SessionLocal
    if engine is None:
        engine = create_async_engine(
            url=get_postgres_url(is_async=True),
            echo=False,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=2,
            pool_recycle=300,
            pool_use_lifo=True,
        )
        SessionLocal = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )


async def get_db():
    global SessionLocal
    if SessionLocal is None:
        raise RuntimeError("Database engine is not initialized")
    async with SessionLocal() as session:
        yield session


@asynccontextmanager
async def use_db_session():
    global SessionLocal
    if SessionLocal is None:
        raise RuntimeError("Database engine is not initialized")
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def shutdown_engine() -> None:
    global engine, SessionLocal
    if engine is not None:
        await engine.dispose()
    engine = None
    SessionLocal = None

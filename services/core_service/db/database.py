import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text
from services.core_service.db.models import Base
from shared.utils.logger import setup_logger

logger = setup_logger("core_service.database")

POSTGRES_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/education"
)
SQLITE_URL = os.getenv("SQLITE_URL", "sqlite+aiosqlite:///./core.db")

active_engine = None
active_session_maker = None
is_sqlite_fallback = False


async def init_db() -> bool:
    """
    Инициализирует подключение к БД.
    Сначала пытается подключиться к PostgreSQL. При недоступности прозрачно
    переключается на локальный SQLite для защиты демо (Demo-Resilience).
    """
    global active_engine, active_session_maker, is_sqlite_fallback

    # 1. Попытка подключения к PostgreSQL
    try:
        engine = create_async_engine(
            POSTGRES_URL,
            echo=False,
            pool_pre_ping=True,
            connect_args={"timeout": 3}
        )
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        
        active_engine = engine
        active_session_maker = async_sessionmaker(active_engine, expire_on_commit=False, class_=AsyncSession)
        is_sqlite_fallback = False
        logger.info("Подключение к PostgreSQL успешно установлено")
        
        # Создаем таблицы если их нет
        async with active_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        return True
    except Exception as e:
        logger.warning(f"PostgreSQL недоступен ({e}). Переключение на резервный SQLite (Demo-Resilience)...")

    # 2. Резервный SQLite
    try:
        engine = create_async_engine(SQLITE_URL, echo=False)
        active_engine = engine
        active_session_maker = async_sessionmaker(active_engine, expire_on_commit=False, class_=AsyncSession)
        is_sqlite_fallback = True

        async with active_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Резервная БД SQLite успешно инициализирована")
        return True
    except Exception as e:
        logger.critical(f"Критическая ошибка инициализации БД: {e}")
        return False


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    if active_session_maker is None:
        await init_db()
    async with active_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

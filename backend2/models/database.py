from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from core.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_timeout=60,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False
)

async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

Base = declarative_base()

async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session

async def get_session_local() -> AsyncSession:
    """Создает сессию для локального использования (не через FastAPI)"""
    return async_session()

async def init_db():
    """
    Создание всех таблиц в базе данных
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def drop_db():
    """
    Удаление всех таблиц из базы данных
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
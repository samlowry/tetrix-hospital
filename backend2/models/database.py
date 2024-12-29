# Database configuration and session management module
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from core.config import get_settings

# Get application settings
settings = get_settings()

# Configure the database engine with connection pooling settings
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=10,          # Maximum number of database connections in the pool
    max_overflow=20,       # Maximum number of connections that can be created beyond pool_size
    pool_timeout=60,       # Seconds to wait before timing out on getting a connection from the pool
    pool_pre_ping=True,    # Enables connection health checks before each use
    pool_recycle=3600,     # Seconds after which a connection is recycled
    echo=False            # Disable SQL query logging
)

# Create an async session factory
async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# Base class for all database models
Base = declarative_base()

async def get_session() -> AsyncSession:
    """
    FastAPI dependency that provides an async database session.
    Yields a session and automatically closes it after use.
    """
    async with async_session() as session:
        yield session

async def get_session_local() -> AsyncSession:
    """
    Creates a database session for local use (not through FastAPI).
    Returns an async session instance.
    """
    return async_session()

async def init_db():
    """
    Initializes the database by creating all defined tables.
    Should be called when setting up the application.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def drop_db():
    """
    Drops all tables from the database.
    Use with caution - this will delete all data.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
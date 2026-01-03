import logging

from app.core.config import get_settings
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import text
from sqlmodel.ext.asyncio.session import AsyncSession

logger = logging.getLogger(__name__)

settings = get_settings()

# Create async engine
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    future=True,
    pool_pre_ping=True,  # Verify connections before using
    pool_size=10,
    max_overflow=20,
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def check_db_connection():
    """
    Check database connectivity (doesn't create tables!)

    Just verifies we can connect to the database.
    Table creation is handled by Alembic migrations.
    """
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection successful")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise


async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

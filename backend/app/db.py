from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .config import settings

engine = create_async_engine(
    settings.async_database_url,
    pool_pre_ping=True,
    pool_size=settings.database_pool_size,
    max_overflow=0,
    pool_recycle=settings.database_pool_recycle_seconds,
)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session():
    async with SessionLocal() as session:
        yield session

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from price_tracker.core.config import get_settings


def make_engine(url: str | None = None) -> AsyncEngine:
    return create_async_engine(url or get_settings().database_url)


def make_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)

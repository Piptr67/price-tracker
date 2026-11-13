import asyncio
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from price_tracker.core.config import get_settings
from price_tracker.db.session import make_engine

ROOT = Path(__file__).resolve().parents[2]
TEST_DB = "price_tracker_test"


async def _recreate_database(admin_url: str) -> None:
    engine = create_async_engine(admin_url, isolation_level="AUTOCOMMIT")
    async with engine.connect() as conn:
        await conn.execute(text(f'DROP DATABASE IF EXISTS "{TEST_DB}" WITH (FORCE)'))
        await conn.execute(text(f'CREATE DATABASE "{TEST_DB}"'))
    await engine.dispose()


@pytest.fixture(scope="session")
def test_database_url() -> str:
    base = make_url(get_settings().database_url)
    admin_url = base.set(database="postgres").render_as_string(hide_password=False)
    test_url = base.set(database=TEST_DB).render_as_string(hide_password=False)

    asyncio.run(_recreate_database(admin_url))

    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("DATABASE_URL", test_url)
        get_settings.cache_clear()
        command.upgrade(config, "head")
    get_settings.cache_clear()
    return test_url


@pytest.fixture
async def session(test_database_url: str) -> AsyncIterator[AsyncSession]:
    engine = make_engine(test_database_url)
    async with engine.connect() as conn:
        outer = await conn.begin()
        factory = async_sessionmaker(
            bind=conn,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        async with factory() as db_session:
            yield db_session
        await outer.rollback()
    await engine.dispose()

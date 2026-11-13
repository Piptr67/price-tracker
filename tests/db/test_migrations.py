from typing import Any

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy.engine import Connection

from price_tracker.db.models import Base
from price_tracker.db.session import make_engine


async def test_migration_matches_models(test_database_url: str) -> None:
    def diff(sync_conn: Connection) -> list[Any]:
        result: list[Any] = compare_metadata(
            MigrationContext.configure(sync_conn), Base.metadata
        )
        return result

    engine = make_engine(test_database_url)
    async with engine.connect() as conn:
        differences = await conn.run_sync(diff)
    await engine.dispose()

    assert differences == []

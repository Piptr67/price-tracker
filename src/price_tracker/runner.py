import asyncio
import logging
from collections import defaultdict

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from price_tracker.db import repository
from price_tracker.db.models import Listing
from price_tracker.db.session import make_engine, make_session_factory
from price_tracker.scrapers.base import BaseScraper
from price_tracker.scrapers.exceptions import ScraperError
from price_tracker.scrapers.registry import SCRAPERS

log = logging.getLogger(__name__)


async def check_listing(
    session: AsyncSession, scraper: BaseScraper, listing: Listing
) -> None:
    data = await scraper.scrape(listing.url)
    await repository.record_snapshot(session, listing.id, data)
    await session.commit()


async def check_store(
    session: AsyncSession, scraper: BaseScraper, listings: list[Listing]
) -> int:
    failures = 0
    for listing in listings:
        try:
            await check_listing(session, scraper, listing)
        except ScraperError as e:
            log.warning("%s: %s", type(e).__name__, listing.url)
            failures += 1
        else:
            log.info("ok: %s", listing.url)
    return failures


async def run_pass(factory: async_sessionmaker[AsyncSession]) -> int:
    async with factory() as session:
        listings = await repository.list_active_listings(session)

    by_store: defaultdict[str, list[Listing]] = defaultdict(list)
    for listing in listings:
        by_store[listing.store].append(listing)

    failures = 0
    for store, store_listings in by_store.items():
        async with factory() as session, SCRAPERS[store]() as scraper:
            failures += await check_store(session, scraper, store_listings)

    log.info("checked %d listings, %d failed", len(listings), failures)
    return failures


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )

    async def run() -> int:
        engine = make_engine()
        try:
            return await run_pass(make_session_factory(engine))
        finally:
            await engine.dispose()

    if asyncio.run(run()):
        raise SystemExit(1)

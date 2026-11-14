import random
from asyncio import Lock, sleep
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from time import monotonic

from price_tracker.scrapers.exceptions import ScraperRateLimit


class RateLimiter:
    """Serialises requests to one site and enforces a gap between them.

    State is per instance, so each site needs exactly one scraper instance.
    Two instances for the same site would exceed the intended rate.
    """

    def __init__(self, min_delay: float, jitter: float, max_wait: float = 60.0) -> None:
        self._min_delay = min_delay
        self._jitter = jitter
        self._max_wait = max_wait
        self._lock = Lock()
        self._ready_at = 0.0

    @asynccontextmanager
    async def slot(self, url: str) -> AsyncGenerator[None]:
        async with self._lock:
            wait = self._ready_at - monotonic()
            if wait > self._max_wait:
                raise ScraperRateLimit(url, retry_after=wait)
            if wait > 0:
                await sleep(wait)

            try:
                yield
            finally:
                self.delay_next(self._min_delay + random.uniform(0, self._jitter))

    def delay_next(self, seconds: float) -> None:
        self._ready_at = max(self._ready_at, monotonic() + seconds)

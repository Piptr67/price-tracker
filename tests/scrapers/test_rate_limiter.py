import asyncio

import pytest

from price_tracker.scrapers.exceptions import ScraperRateLimit
from price_tracker.scrapers.rate_limiter import RateLimiter

URL = "https://shop.example/product"


@pytest.fixture
def limiter(sleeps: list[float]) -> RateLimiter:
    return RateLimiter(min_delay=2.0, jitter=0.0)


async def test_requests_are_spaced(limiter: RateLimiter, sleeps: list[float]) -> None:
    async with limiter.slot(URL):
        pass
    assert sleeps == []

    async with limiter.slot(URL):
        pass
    assert sleeps == [2.0]


async def test_penalty_delays_next_request(
    limiter: RateLimiter, sleeps: list[float]
) -> None:
    async with limiter.slot(URL):
        pass
    limiter.penalize(30.0)
    async with limiter.slot(URL):
        pass

    assert sleeps == [30.0]


async def test_wait_over_cap_raises_instead_of_sleeping(
    limiter: RateLimiter, sleeps: list[float]
) -> None:
    limiter.penalize(120.0)

    with pytest.raises(ScraperRateLimit) as exc_info:
        async with limiter.slot(URL):
            pass

    assert exc_info.value.retry_after == 120.0
    assert sleeps == []


async def test_concurrent_tasks_never_overlap(limiter: RateLimiter) -> None:
    events: list[str] = []

    async def worker() -> None:
        async with limiter.slot(URL):
            events.append("in")
            await asyncio.sleep(0)
            events.append("out")

    await asyncio.gather(worker(), worker(), worker())

    assert events == ["in", "out"] * 3

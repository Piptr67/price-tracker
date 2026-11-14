import asyncio

import pytest

from price_tracker.scrapers import rate_limiter


@pytest.fixture
def sleeps(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    slept: list[float] = []

    async def sleep(seconds: float) -> None:
        slept.append(seconds)
        await asyncio.sleep(0)

    monkeypatch.setattr(rate_limiter, "monotonic", lambda: 1000.0 + sum(slept))
    monkeypatch.setattr(rate_limiter, "sleep", sleep)
    return slept

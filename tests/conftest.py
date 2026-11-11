import asyncio
from types import SimpleNamespace

import pytest

from price_tracker.scrapers import rate_limiter


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0
        self.slept: list[float] = []

    def monotonic(self) -> float:
        return self.now

    async def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds
        await asyncio.sleep(0)


@pytest.fixture
def sleeps(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    clock = FakeClock()
    monkeypatch.setattr(
        rate_limiter, "time", SimpleNamespace(monotonic=clock.monotonic)
    )
    monkeypatch.setattr(
        rate_limiter, "asyncio", SimpleNamespace(sleep=clock.sleep, Lock=asyncio.Lock)
    )
    return clock.slept

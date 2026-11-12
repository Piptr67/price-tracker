from abc import ABC, abstractmethod
from typing import NoReturn, Self

import httpx
from bs4 import BeautifulSoup

from price_tracker.models.product import ProductData
from price_tracker.scrapers.exceptions import (
    ScraperBlocked,
    ScraperConnectionError,
    ScraperError,
    ScraperNotFound,
    ScraperRateLimit,
    ScraperServerError,
    ScraperTimeout,
)
from price_tracker.scrapers.rate_limiter import RateLimiter

DEFAULT_HEADERS: dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/157.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Upgrade-Insecure-Requests": "1",
}

DEFAULT_COOLDOWN = 30.0


class BaseScraper(ABC):
    """Base for per-site scrapers. Use as `async with`; one instance per site."""

    headers: dict[str, str] = DEFAULT_HEADERS
    timeout: httpx.Timeout | float = httpx.Timeout(10.0)
    min_delay: float = 2.0
    jitter: float = 1.0

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._limiter = RateLimiter(self.min_delay, self.jitter)

    async def __aenter__(self) -> Self:
        self._client = httpx.AsyncClient(
            headers=self.headers, timeout=self.timeout, follow_redirects=True
        )
        return self

    async def __aexit__(self, *exc: object) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def fetch(self, url: str) -> BeautifulSoup:
        if self._client is None:
            raise RuntimeError(
                f"Scraper must be used as an async context manager. Cannot fetch {url}."
            )

        async with self._limiter.slot(url):
            try:
                response = await self._client.get(url)
            except httpx.TimeoutException as e:
                raise ScraperTimeout(url) from e
            except httpx.RequestError as e:
                raise ScraperConnectionError(url) from e

        status = response.status_code

        if response.is_success:
            if self._is_not_found(response):
                raise ScraperNotFound(url)
            return BeautifulSoup(response.content, "lxml")
        if status in (404, 410):
            raise ScraperNotFound(url)
        if status == 429:
            self._raise_rate_limited(url, response)
        if status in (401, 403) or (
            status == 503 and "cloudflare" in response.headers.get("server", "").lower()
        ):
            raise ScraperBlocked(url)
        if status >= 500:
            raise ScraperServerError(url)
        raise ScraperError(url, f"Unexpected status {status} at {url}")

    @staticmethod
    def _parse_retry_after(value: str | None) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except ValueError:
            return None

    def _raise_rate_limited(self, url: str, response: httpx.Response) -> NoReturn:
        retry_after = self._parse_retry_after(response.headers.get("retry-after"))
        cooldown = DEFAULT_COOLDOWN if retry_after is None else retry_after
        self._limiter.penalize(cooldown)
        raise ScraperRateLimit(url, retry_after=retry_after)

    def _is_not_found(self, response: httpx.Response) -> bool:
        """Hook for sites that signal a missing product with a redirect or a 200."""
        return False

    @abstractmethod
    async def scrape(self, url: str) -> ProductData: ...

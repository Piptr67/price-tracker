from abc import ABC, abstractmethod
from typing import Self

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

DEFAULT_HEADERS: dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/157.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Upgrade-Insecure-Requests": "1",
}


class BaseScraper(ABC):
    headers: dict[str, str] = DEFAULT_HEADERS
    timeout: httpx.Timeout | float = httpx.Timeout(10.0)

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

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

        try:
            response = await self._client.get(url)
        except httpx.TimeoutException as e:
            raise ScraperTimeout(url) from e
        except httpx.RequestError as e:
            raise ScraperConnectionError(url) from e

        status = response.status_code
        server_header = response.headers.get("server", "").lower()

        if response.is_success:
            return BeautifulSoup(response.text, "lxml")
        if status in (404, 410):
            raise ScraperNotFound(url)
        if status == 429:
            retry_after = self._parse_retry_after(response.headers.get("retry-after"))
            raise ScraperRateLimit(url, retry_after=retry_after)
        if status in (401, 403) or (status == 503 and "cloudflare" in server_header):
            raise ScraperBlocked(url)
        if status >= 500:
            raise ScraperServerError(url)
        raise ScraperError(url, f"Unexpected status {status} at {url}")

    @staticmethod
    def _parse_retry_after(value: str | None) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except ValueError:
            return None

    @abstractmethod
    async def scrape(self, url: str) -> ProductData: ...

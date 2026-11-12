import httpx
import pytest
import respx

from price_tracker.models.product import ProductData
from price_tracker.scrapers.base import BaseScraper
from price_tracker.scrapers.exceptions import (
    ScraperBlocked,
    ScraperConnectionError,
    ScraperError,
    ScraperNotFound,
    ScraperRateLimit,
    ScraperServerError,
    ScraperTimeout,
)

URL = "https://shop.example/product"


class DummyScraper(BaseScraper):
    store = "dummy"
    min_delay = 0.0
    jitter = 0.0

    async def scrape(self, url: str) -> ProductData:
        raise NotImplementedError


class MissingProductScraper(DummyScraper):
    def _is_not_found(self, response: httpx.Response) -> bool:
        return True


async def test_fetch_returns_parsed_html(respx_mock: respx.MockRouter) -> None:
    respx_mock.get(URL).respond(200, text="<html><title>Shop</title></html>")

    async with DummyScraper() as scraper:
        soup = await scraper.fetch(URL)

    assert soup.title is not None
    assert soup.title.string == "Shop"


@pytest.mark.parametrize(
    ("status", "headers", "expected"),
    [
        (404, {}, ScraperNotFound),
        (410, {}, ScraperNotFound),
        (401, {}, ScraperBlocked),
        (403, {}, ScraperBlocked),
        (503, {"server": "cloudflare"}, ScraperBlocked),
        (503, {}, ScraperServerError),
        (500, {}, ScraperServerError),
        (418, {}, ScraperError),
    ],
)
async def test_status_maps_to_exception(
    respx_mock: respx.MockRouter,
    status: int,
    headers: dict[str, str],
    expected: type[ScraperError],
) -> None:
    respx_mock.get(URL).respond(status, headers=headers)

    async with DummyScraper() as scraper:
        with pytest.raises(ScraperError) as exc_info:
            await scraper.fetch(URL)

    assert type(exc_info.value) is expected


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (httpx.ReadTimeout("slow"), ScraperTimeout),
        (httpx.ConnectError("refused"), ScraperConnectionError),
    ],
)
async def test_network_errors_map_to_exception(
    respx_mock: respx.MockRouter,
    error: httpx.RequestError,
    expected: type[ScraperError],
) -> None:
    respx_mock.get(URL).mock(side_effect=error)

    async with DummyScraper() as scraper:
        with pytest.raises(ScraperError) as exc_info:
            await scraper.fetch(URL)

    assert type(exc_info.value) is expected


@pytest.mark.parametrize(
    ("headers", "expected"),
    [
        ({"retry-after": "30"}, 30.0),
        ({}, None),
        ({"retry-after": "Wed, 21 Oct 2015 07:28:00 GMT"}, None),
    ],
)
async def test_retry_after_is_parsed(
    respx_mock: respx.MockRouter,
    headers: dict[str, str],
    expected: int | None,
) -> None:
    respx_mock.get(URL).respond(429, headers=headers)

    async with DummyScraper() as scraper:
        with pytest.raises(ScraperRateLimit) as exc_info:
            await scraper.fetch(URL)

    assert exc_info.value.retry_after == expected


async def test_fetch_outside_context_manager_raises() -> None:
    with pytest.raises(RuntimeError):
        await DummyScraper().fetch(URL)


async def test_429_delays_next_request(
    respx_mock: respx.MockRouter, sleeps: list[float]
) -> None:
    respx_mock.get(URL).mock(
        side_effect=[
            httpx.Response(429, headers={"retry-after": "30"}),
            httpx.Response(200, text="<html></html>"),
        ]
    )

    async with DummyScraper() as scraper:
        with pytest.raises(ScraperRateLimit):
            await scraper.fetch(URL)
        await scraper.fetch(URL)

    assert sleeps == [30.0]


async def test_not_found_hook_raises(respx_mock: respx.MockRouter) -> None:
    respx_mock.get(URL).respond(200, text="<html></html>")

    async with MissingProductScraper() as scraper:
        with pytest.raises(ScraperNotFound):
            await scraper.fetch(URL)


def test_scraper_without_store_cannot_be_created() -> None:
    class NoStore(BaseScraper):
        async def scrape(self, url: str) -> ProductData:
            raise NotImplementedError

    with pytest.raises(TypeError, match="store"):
        NoStore()

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
import respx

from price_tracker.scrapers.exceptions import (
    ScraperError,
    ScraperNotFound,
    ScraperParseError,
)
from price_tracker.scrapers.oliveyoung import API_URL, OliveYoungScraper

URL = "https://global.oliveyoung.com/product/detail?prdtNo=GA251034528"

FIXTURE = Path(__file__).parent.parent / "fixtures" / "oliveyoung_product.json"


def _payload() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return data


async def test_scrape_parses_product(respx_mock: respx.MockRouter) -> None:
    respx_mock.post(API_URL).respond(200, json=_payload())

    async with OliveYoungScraper() as scraper:
        product = await scraper.scrape(URL)

    assert product.name == "Dr. Althea 345 Relief Cream 50ml"
    assert product.brand == "Dr. Althea"
    assert product.price == Decimal("22.8")
    assert product.currency == "USD"
    assert product.in_stock is True
    assert product.url == URL
    assert product.import_fee_due is True
    assert product.price_includes_vat is False


async def test_request_sends_the_product_number(respx_mock: respx.MockRouter) -> None:
    route = respx_mock.post(API_URL).respond(200, json=_payload())

    async with OliveYoungScraper() as scraper:
        await scraper.scrape(URL)

    assert json.loads(route.calls.last.request.content) == {"prdtNo": "GA251034528"}


@pytest.mark.parametrize(
    ("field", "value"),
    [
        pytest.param("tempOutOfStockYn", "Y", id="temporarily-out"),
        pytest.param("sellStatCode", "20", id="not-on-sale"),
    ],
)
async def test_out_of_stock(
    respx_mock: respx.MockRouter, field: str, value: str
) -> None:
    payload = _payload()
    payload["product"][field] = value
    respx_mock.post(API_URL).respond(200, json=payload)

    async with OliveYoungScraper() as scraper:
        product = await scraper.scrape(URL)

    assert product.in_stock is False


async def test_missing_product_raises_not_found(respx_mock: respx.MockRouter) -> None:
    respx_mock.post(API_URL).respond(200, json={"product": None})

    async with OliveYoungScraper() as scraper:
        with pytest.raises(ScraperNotFound):
            await scraper.scrape(URL)


@pytest.mark.parametrize(
    "body",
    [
        pytest.param(b"<html>nothing here</html>", id="not-json"),
        pytest.param(b"[]", id="not-an-object"),
    ],
)
async def test_unusable_response_body_raises(
    respx_mock: respx.MockRouter, body: bytes
) -> None:
    respx_mock.post(API_URL).respond(200, content=body)

    async with OliveYoungScraper() as scraper:
        with pytest.raises(ScraperParseError):
            await scraper.scrape(URL)


async def test_missing_price_raises(respx_mock: respx.MockRouter) -> None:
    payload = _payload()
    del payload["product"]["saleAmt"]
    respx_mock.post(API_URL).respond(200, json=payload)

    async with OliveYoungScraper() as scraper:
        with pytest.raises(ScraperParseError):
            await scraper.scrape(URL)


async def test_url_without_product_number_raises() -> None:
    async with OliveYoungScraper() as scraper:
        with pytest.raises(ScraperError):
            await scraper.scrape("https://global.oliveyoung.com/product/detail")

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
import respx

from price_tracker.scrapers.exceptions import ScraperParseError
from price_tracker.scrapers.skinseoul import SkinSeoulScraper

URL = "https://skin-seoul.com/product/345-relief-cream/"
NAME = "Dr. Althea 345 Relief Cream, 50ml"
BRAND = "Dr. Althea"
PRICE = Decimal("88.98")

FIXTURE = Path(__file__).parent.parent / "fixtures" / "skinseoul_product.html"

PRODUCT = {"@type": "Product", "name": "X", "brand": {"name": "B"}}


def _page(*graph: dict[str, Any]) -> str:
    data = {"@context": "https://schema.org", "@graph": list(graph)}
    return f'<script type="application/ld+json">{json.dumps(data)}</script>'


async def test_scrape_parses_product(respx_mock: respx.MockRouter) -> None:
    respx_mock.get(URL).respond(200, content=FIXTURE.read_bytes())

    async with SkinSeoulScraper() as scraper:
        product = await scraper.scrape(URL)

    assert product.name == NAME
    assert product.brand == BRAND
    assert product.price == PRICE
    assert product.currency == "PLN"
    assert product.in_stock is True
    assert product.url == URL
    assert product.import_fee_due is False
    assert product.price_includes_vat is False


async def test_out_of_stock(respx_mock: respx.MockRouter) -> None:
    html = FIXTURE.read_bytes()
    assert b"schema.org/InStock" in html
    respx_mock.get(URL).respond(
        200, content=html.replace(b"schema.org/InStock", b"schema.org/OutOfStock")
    )

    async with SkinSeoulScraper() as scraper:
        product = await scraper.scrape(URL)

    assert product.in_stock is False


async def test_product_is_found_among_other_graph_entries(
    respx_mock: respx.MockRouter,
) -> None:
    product = {
        **PRODUCT,
        "offers": {
            "price": "88.98",
            "priceCurrency": "PLN",
            "availability": "https://schema.org/InStock",
        },
    }
    page = _page({"@type": "WebSite"}, {"@type": ["Store", "Organization"]}, product)
    respx_mock.get(URL).respond(200, text=page)

    async with SkinSeoulScraper() as scraper:
        result = await scraper.scrape(URL)

    assert result.price == PRICE


async def test_page_without_json_ld_raises(respx_mock: respx.MockRouter) -> None:
    respx_mock.get(URL).respond(200, text="<html><body>nothing here</body></html>")

    async with SkinSeoulScraper() as scraper:
        with pytest.raises(ScraperParseError):
            await scraper.scrape(URL)


@pytest.mark.parametrize(
    "product",
    [
        pytest.param({**PRODUCT, "offers": {}}, id="empty-offers"),
        pytest.param({**PRODUCT, "offers": {"priceCurrency": "PLN"}}, id="no-price"),
    ],
)
async def test_unusable_product_data_raises(
    respx_mock: respx.MockRouter, product: dict[str, Any]
) -> None:
    respx_mock.get(URL).respond(200, text=_page(product))

    async with SkinSeoulScraper() as scraper:
        with pytest.raises(ScraperParseError):
            await scraper.scrape(URL)

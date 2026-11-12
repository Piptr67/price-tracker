import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
import respx

from price_tracker.scrapers.cosibella import CosibellaScraper
from price_tracker.scrapers.exceptions import ScraperNotFound, ScraperParseError

URL = "https://cosibella.pl/pl/products/dr-althea-16911"
NAME_PREFIX = "Dr. Althea - 345 Relief Cream"
BRAND = "Dr. Althea"
PRICE = Decimal("76.50")

FIXTURE = Path(__file__).parent.parent / "fixtures" / "cosibella_product.html"

PRODUCT = {"@type": "Product", "name": "X", "brand": {"name": "B"}}


def _page(product: dict[str, Any]) -> str:
    return f'<script type="application/ld+json">{json.dumps(product)}</script>'


async def test_scrape_parses_product(respx_mock: respx.MockRouter) -> None:
    respx_mock.get(URL).respond(200, content=FIXTURE.read_bytes())

    async with CosibellaScraper() as scraper:
        product = await scraper.scrape(URL)

    assert product.name.startswith(NAME_PREFIX)
    assert product.brand == BRAND
    assert product.price == PRICE
    assert product.currency == "PLN"
    assert product.in_stock is True
    assert product.url == URL
    assert product.ships_from_eu is True
    assert product.price_includes_vat is True


async def test_out_of_stock(respx_mock: respx.MockRouter) -> None:
    html = FIXTURE.read_bytes()
    assert b"schema.org/InStock" in html
    respx_mock.get(URL).respond(
        200, content=html.replace(b"schema.org/InStock", b"schema.org/OutOfStock")
    )

    async with CosibellaScraper() as scraper:
        product = await scraper.scrape(URL)

    assert product.in_stock is False


async def test_page_without_json_ld_raises(respx_mock: respx.MockRouter) -> None:
    respx_mock.get(URL).respond(200, text="<html><body>nothing here</body></html>")

    async with CosibellaScraper() as scraper:
        with pytest.raises(ScraperParseError):
            await scraper.scrape(URL)


@pytest.mark.parametrize(
    "product",
    [
        pytest.param({**PRODUCT, "offers": []}, id="empty-offers"),
        pytest.param({**PRODUCT, "offers": [{"priceCurrency": "PLN"}]}, id="no-price"),
    ],
)
async def test_unusable_product_data_raises(
    respx_mock: respx.MockRouter, product: dict[str, Any]
) -> None:
    respx_mock.get(URL).respond(200, text=_page(product))

    async with CosibellaScraper() as scraper:
        with pytest.raises(ScraperParseError):
            await scraper.scrape(URL)


async def test_redirect_to_home_raises_not_found(respx_mock: respx.MockRouter) -> None:
    respx_mock.get(URL).respond(301, headers={"location": "/"})
    respx_mock.get("https://cosibella.pl/").respond(200, text="<html></html>")

    async with CosibellaScraper() as scraper:
        with pytest.raises(ScraperNotFound):
            await scraper.scrape(URL)

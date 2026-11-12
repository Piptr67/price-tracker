import json
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx
from bs4 import BeautifulSoup
from pydantic import ValidationError

from price_tracker.models.product import ProductData
from price_tracker.scrapers.base import BaseScraper
from price_tracker.scrapers.exceptions import ScraperParseError


class CosibellaScraper(BaseScraper):
    headers = {**BaseScraper.headers, "Accept-Language": "pl-PL,pl;q=0.9"}
    min_delay = 5.0
    jitter = 1.5

    async def scrape(self, url: str) -> ProductData:
        soup = await self.fetch(url)
        product = self._product_json(soup, url)

        try:
            offer = product["offers"][0]
            return ProductData(
                name=product["name"],
                brand=product["brand"]["name"],
                price=Decimal(str(offer["price"])),
                currency=offer["priceCurrency"],
                in_stock=offer["availability"].endswith("/InStock"),
                url=url,
                ships_from_eu=True,
                price_includes_vat=True,
            )
        except (
            KeyError,
            IndexError,
            TypeError,
            InvalidOperation,
            ValidationError,
        ) as e:
            raise ScraperParseError(url, f"Unexpected product data at {url}") from e

    def _is_not_found(self, response: httpx.Response) -> bool:
        return "products" not in response.url.path.split("/")

    @staticmethod
    def _product_json(soup: BeautifulSoup, url: str) -> dict[str, Any]:
        for tag in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(tag.get_text())
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict) and data.get("@type") == "Product":
                return data
        raise ScraperParseError(url, f"No Product JSON-LD found at {url}")

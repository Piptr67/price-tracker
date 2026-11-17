import json
from decimal import Decimal, InvalidOperation
from typing import Any

from bs4 import BeautifulSoup
from pydantic import ValidationError

from price_tracker.models.product import ProductData
from price_tracker.scrapers.base import BaseScraper
from price_tracker.scrapers.exceptions import ScraperParseError


class SkinSeoulScraper(BaseScraper):
    store = "skinseoul"
    import_fee_due = False
    price_includes_vat = False
    min_delay = 5.0
    jitter = 1.5

    async def scrape(self, url: str) -> ProductData:
        soup = await self.fetch(url)
        product = self._product_json(soup, url)

        try:
            offer = product["offers"]
            return ProductData(
                name=product["name"],
                brand=product["brand"]["name"],
                price=Decimal(str(offer["price"])),
                currency=offer["priceCurrency"],
                in_stock=offer["availability"].endswith("/InStock"),
                url=url,
                import_fee_due=self.import_fee_due,
                price_includes_vat=self.price_includes_vat,
            )
        except (
            KeyError,
            IndexError,
            TypeError,
            InvalidOperation,
            ValidationError,
        ) as e:
            raise ScraperParseError(url, f"Unexpected product data at {url}") from e

    @staticmethod
    def _product_json(soup: BeautifulSoup, url: str) -> dict[str, Any]:
        for tag in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(tag.get_text())
            except json.JSONDecodeError:
                continue
            if not isinstance(data, dict):
                continue
            for item in data.get("@graph", []):
                if isinstance(item, dict) and item.get("@type") == "Product":
                    return item
        raise ScraperParseError(url, f"No Product JSON-LD found at {url}")

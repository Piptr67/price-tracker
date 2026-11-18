import json
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import parse_qs, urlparse

from pydantic import ValidationError

from price_tracker.models.product import ProductData
from price_tracker.scrapers.base import BaseScraper
from price_tracker.scrapers.exceptions import (
    ScraperError,
    ScraperNotFound,
    ScraperParseError,
)

API_URL = "https://global.oliveyoung.com/product/detail-data"
API_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://global.oliveyoung.com",
    "X-Requested-With": "XMLHttpRequest",
}


class OliveYoungScraper(BaseScraper):
    store = "oliveyoung"
    import_fee_due = True
    price_includes_vat = False
    min_delay = 3.0
    jitter = 1.0

    async def scrape(self, url: str) -> ProductData:
        product = await self._product_payload(url)

        try:
            return ProductData(
                name=product.get("prdtNameEn") or product["prdtName"],
                brand=product.get("brandNameEn") or product["brandName"],
                price=Decimal(str(product["saleAmt"])),
                currency="USD",
                in_stock=(
                    product["sellStatCode"] == "10"
                    and product.get("tempOutOfStockYn") != "Y"
                ),
                url=url,
                import_fee_due=self.import_fee_due,
                price_includes_vat=self.price_includes_vat,
            )
        except (
            KeyError,
            TypeError,
            InvalidOperation,
            ValidationError,
        ) as e:
            raise ScraperParseError(url, f"Unexpected product data at {url}") from e

    async def _product_payload(self, url: str) -> dict[str, Any]:
        response = await self._request(
            "POST",
            API_URL,
            json={"prdtNo": self._extract_prdt_no(url)},
            headers={**API_HEADERS, "Referer": url},
        )

        try:
            data = response.json()
        except json.JSONDecodeError as e:
            raise ScraperParseError(url, f"Invalid JSON response from {url}") from e

        if not isinstance(data, dict):
            raise ScraperParseError(url, f"Unexpected JSON root at {url}")

        product = data.get("product")
        if product is None:
            raise ScraperNotFound(url)
        if not isinstance(product, dict):
            raise ScraperParseError(url, f"Unexpected product payload at {url}")
        return product

    @staticmethod
    def _extract_prdt_no(url: str) -> str:
        prdt_no = parse_qs(urlparse(url).query).get("prdtNo", [None])[0]
        if not prdt_no:
            raise ScraperError(url, f"Missing prdtNo query parameter in {url}")
        return prdt_no

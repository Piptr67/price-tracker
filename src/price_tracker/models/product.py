from decimal import Decimal

from pydantic import BaseModel


class ProductData(BaseModel):
    name: str
    brand: str
    price: Decimal
    currency: str
    in_stock: bool
    url: str
    import_fee_due: bool | None = None
    price_includes_vat: bool | None = None

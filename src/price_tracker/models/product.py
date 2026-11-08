from pydantic import BaseModel


class ProductData(BaseModel):
    name: str
    brand: str
    price: float
    currency: str
    in_stock: bool
    url: str

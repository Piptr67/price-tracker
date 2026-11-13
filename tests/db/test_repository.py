from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from price_tracker.db import repository
from price_tracker.db.models import Listing, PriceSnapshot
from price_tracker.models.product import ProductData

URL = "https://shop.example/product"


async def make_listing(
    session: AsyncSession, url: str = URL, store: str = "Product"
) -> Listing:
    product = await repository.add_product(session, "Product", "Brand")
    return await repository.add_listing(session, product.id, store, url)


def make_data(**overrides: Any) -> ProductData:
    fields: dict[str, Any] = {
        "name": "Product",
        "brand": "Brand",
        "price": Decimal("10.00"),
        "currency": "PLN",
        "in_stock": True,
        "url": URL,
    }
    return ProductData(**{**fields, **overrides})


def snapshot(listing_id: int, price: str, checked_at: datetime) -> PriceSnapshot:
    return PriceSnapshot(
        listing_id=listing_id,
        price=Decimal(price),
        currency="PLN",
        in_stock=True,
        checked_at=checked_at,
    )


async def test_add_product_and_listing(session: AsyncSession) -> None:
    product = await repository.add_product(session, "Product", "Brand")
    listing = await repository.add_listing(session, product.id, "shop", URL)

    assert listing.product_id == product.id
    assert listing.active is True
    assert listing.created_at is not None


async def test_duplicate_url_is_rejected(session: AsyncSession) -> None:
    product = await repository.add_product(session, "Product", "Brand")
    await repository.add_listing(session, product.id, "shop", URL)

    with pytest.raises(IntegrityError):
        await repository.add_listing(session, product.id, "other", URL)


async def test_list_active_skips_inactive(session: AsyncSession) -> None:
    first = await make_listing(session, "https://a.example/p", "a")
    second = await make_listing(session, "https://b.example/p", "b")
    third = await make_listing(session, "https://c.example/p", "c")
    second.active = False
    await session.flush()

    assert await repository.list_active_listings(session) == [first, third]


async def test_record_snapshot_stores_every_field(session: AsyncSession) -> None:
    listing = await make_listing(session)
    data = make_data(
        price=Decimal("76.50"),
        in_stock=False,
        ships_from_eu=True,
        price_includes_vat=None,
    )

    saved = await repository.record_snapshot(session, listing.id, data)
    await session.refresh(saved)

    assert saved.listing_id == listing.id
    assert saved.price == Decimal("76.50")
    assert saved.currency == "PLN"
    assert saved.in_stock is False
    assert saved.ships_from_eu is True
    assert saved.price_includes_vat is None
    assert saved.checked_at.tzinfo is not None


async def test_price_history_orders_and_filters(session: AsyncSession) -> None:
    one = await make_listing(session, "https://a.example/p", "a")
    two = await make_listing(session, "https://b.example/p", "b")
    base = datetime(2026, 11, 1, tzinfo=UTC)
    newest = snapshot(one.id, "3", base + timedelta(days=2))
    oldest = snapshot(one.id, "1", base)
    middle = snapshot(one.id, "2", base + timedelta(days=1))
    elsewhere = snapshot(two.id, "9", base)
    session.add_all([newest, oldest, middle, elsewhere])
    await session.flush()

    assert await repository.price_history(session, one.id) == [oldest, middle, newest]
    since = base + timedelta(days=1)
    assert await repository.price_history(session, one.id, since) == [middle, newest]

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from price_tracker.db.models import Listing, PriceSnapshot, Product
from price_tracker.models.product import ProductData


async def add_product(session: AsyncSession, name: str, brand: str) -> Product:
    product = Product(name=name, brand=brand)
    session.add(product)
    await session.flush()
    return product


async def add_listing(
    session: AsyncSession, product_id: int, store: str, url: str
) -> Listing:
    listing = Listing(product_id=product_id, store=store, url=url)
    session.add(listing)
    await session.flush()
    return listing


async def list_active_listings(session: AsyncSession) -> list[Listing]:
    stmt = select(Listing).where(Listing.active).order_by(Listing.id)
    return list((await session.scalars(stmt)).all())


async def record_snapshot(
    session: AsyncSession, listing_id: int, data: ProductData
) -> PriceSnapshot:
    snapshot = PriceSnapshot(
        listing_id=listing_id,
        price=data.price,
        currency=data.currency,
        in_stock=data.in_stock,
        ships_from_eu=data.ships_from_eu,
        price_includes_vat=data.price_includes_vat,
    )
    session.add(snapshot)
    await session.flush()
    return snapshot


async def price_history(
    session: AsyncSession, listing_id: int, since: datetime | None = None
) -> list[PriceSnapshot]:
    stmt = select(PriceSnapshot).where(PriceSnapshot.listing_id == listing_id)
    if since is not None:
        stmt = stmt.where(PriceSnapshot.checked_at >= since)
    stmt = stmt.order_by(PriceSnapshot.checked_at, PriceSnapshot.id)
    return list((await session.scalars(stmt)).all())

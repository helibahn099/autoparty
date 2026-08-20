"""Match approved sellers to an order by location and category."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import (
    Order,
    OrderItem,
    OrderLocation,
    SellerCategory,
    SellerCity,
    SellerProfile,
    SellerStatus,
)
from app.services.reputation import seller_accepts_new_orders


def matching_sellers(db: Session, order: Order) -> list[SellerProfile]:
    city_ids = [loc.city_id for loc in db.query(OrderLocation).filter(OrderLocation.order_id == order.id).all()]
    if not city_ids:
        return []

    category_ids = [
        item.category_id
        for item in db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
        if item.category_id
    ]

    q = (
        db.query(SellerProfile)
        .filter(SellerProfile.status == SellerStatus.APPROVED)
        .join(SellerCity, SellerCity.seller_id == SellerProfile.id)
        .filter(SellerCity.city_id.in_(city_ids))
    )

    if category_ids:
        q = q.join(SellerCategory, SellerCategory.seller_id == SellerProfile.id).filter(
            SellerCategory.category_id.in_(category_ids)
        )

    sellers = q.distinct().all()
    now = datetime.now(timezone.utc)
    out = []
    for seller in sellers:
        if seller.user and (seller.user.is_blocked or not seller.user.is_active):
            continue
        if not seller_accepts_new_orders(seller):
            continue
        _ = now
        out.append(seller)
    return out

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.deps import get_optional_user
from app.models import (
    Availability,
    Chat,
    City,
    Order,
    SellerOffer,
    SellerOfferItem,
    SellerProfile,
    SellerStatus,
    User,
    UserRole,
)
from app.serializers import seller_public, vehicle_label

router = APIRouter(prefix="/api/map", tags=["map"])

BISHKEK = [42.8746, 74.5698]


def _partner_points(db: Session, skip_ids: set[int]) -> list[dict]:
    partners = (
        db.query(SellerProfile)
        .filter(
            SellerProfile.is_partner.is_(True),
            SellerProfile.status == SellerStatus.APPROVED,
            SellerProfile.lat.isnot(None),
            SellerProfile.lng.isnot(None),
        )
        .all()
    )
    out = []
    for seller in partners:
        if seller.id in skip_ids:
            continue
        out.append(
            {
                "id": f"partner-{seller.id}",
                "kind": "partner",
                "seller": seller_public(seller),
                "lat": seller.lat,
                "lng": seller.lng,
                "title": seller.display_name,
                "subtitle": seller.address or "",
                "is_partner": True,
            }
        )
    return out


def _offer_point(db: Session, offer: SellerOffer) -> dict | None:
    seller = offer.seller
    if not seller or seller.lat is None or seller.lng is None:
        return None
    yes_items = [it for it in offer.items if it.availability in {Availability.YES, Availability.PARTIAL}]
    if not yes_items:
        return None
    chat = (
        db.query(Chat)
        .filter(Chat.order_id == offer.order_id, Chat.seller_id == seller.id)
        .first()
    )
    return {
        "id": f"offer-{offer.id}",
        "kind": "offer",
        "seller": seller_public(seller),
        "lat": seller.lat,
        "lng": seller.lng,
        "title": seller.display_name,
        "subtitle": seller.address or "Адрес не указан",
        "order_id": offer.order_id,
        "vehicle": vehicle_label(offer.order) if offer.order else None,
        "parts": [it.order_item.description if it.order_item else "" for it in yes_items],
        "price_from": min(float(it.price) for it in yes_items if it.price is not None) if any(it.price for it in yes_items) else None,
        "chat_id": chat.id if chat else None,
        "is_partner": bool(seller.is_partner),
    }


@router.get("/points")
def map_points(
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    cities = db.query(City).filter(City.is_active.is_(True), City.lat.isnot(None)).all()
    city_pins = [
        {"id": c.id, "name": c.name, "lat": c.lat, "lng": c.lng, "search_radius_km": c.search_radius_km or 8}
        for c in cities
    ]
    points = []
    seen_sellers: set[int] = set()

    if user and user.role == UserRole.SELLER and user.seller_profile:
        seller = user.seller_profile
        if seller.lat and seller.lng:
            points.append(
                {
                    "id": f"me-{seller.id}",
                    "kind": "mine",
                    "seller": seller_public(seller),
                    "lat": seller.lat,
                    "lng": seller.lng,
                    "title": seller.display_name,
                    "subtitle": seller.address or "Ваша точка",
                }
            )
            seen_sellers.add(seller.id)
    elif user and user.role in {UserRole.CLIENT, UserRole.ADMIN}:
        since = datetime.now(timezone.utc) - timedelta(days=90)
        q = (
            db.query(SellerOffer)
            .join(Order, Order.id == SellerOffer.order_id)
            .options(
                joinedload(SellerOffer.seller),
                joinedload(SellerOffer.items).joinedload(SellerOfferItem.order_item),
                joinedload(SellerOffer.order),
            )
        )
        if user.role == UserRole.CLIENT:
            q = q.filter(Order.client_id == user.id, Order.created_at >= since)
        else:
            q = q.filter(Order.created_at >= since)
        for offer in q.all():
            row = _offer_point(db, offer)
            if not row:
                continue
            points.append(row)
            if offer.seller_id:
                seen_sellers.add(offer.seller_id)

    partners = _partner_points(db, seen_sellers)
    points.extend(partners)
    offers = [p for p in points if p.get("kind") == "offer"]

    return {
        "center": BISHKEK,
        "zoom": 12,
        "cities": city_pins,
        "points": points,
        "offer_count": len(offers),
        "partner_count": len(partners),
        "has_orders": bool(offers),
    }

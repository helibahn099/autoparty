from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import (
    AssignmentStatus,
    Chat,
    ChatParticipant,
    City,
    Message,
    Order,
    OrderItem,
    OrderSellerAssignment,
    Payment,
    Rating,
    Region,
    SellerOffer,
    SellerProfile,
    User,
    UserRole,
)


def user_out(user: User) -> dict:
    seller_status = None
    if user.seller_profile:
        seller_status = user.seller_profile.status.value
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "phone": user.phone,
        "role": user.role.value,
        "is_active": user.is_active,
        "is_blocked": user.is_blocked,
        "seller_status": seller_status,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


def city_out(city: City, lang: str = "ru") -> dict:
    from app.i18n import localized_name

    return {
        "id": city.id,
        "name": localized_name(city, lang) or city.name,
        "name_ru": city.name,
        "name_en": city.name_en,
        "name_ky": city.name_ky,
        "region_id": city.region_id,
        "region": city.region.name if city.region else None,
        "country": city.region.country.name if city.region and city.region.country else None,
        "lat": city.lat,
        "lng": city.lng,
        "search_radius_km": city.search_radius_km or 8,
    }


def seller_public(seller: SellerProfile, admin: bool = False) -> dict:
    data = {
        "id": seller.id,
        "user_id": seller.user_id,
        "display_name": seller.display_name,
        "status": seller.status.value,
        "user_rating_avg": round(seller.user_rating_avg or 0, 2),
        "user_rating_count": seller.user_rating_count or 0,
        "display_rating": round(seller.display_rating or seller.user_rating_avg or 0, 2),
        "completed_orders_count": seller.completed_orders_count or 0,
        "activity_score": round(seller.activity_score or 0, 1),
        "quality_score": round(seller.quality_score or 0, 1),
        "processed_requests_count": seller.processed_requests_count or 0,
        "cities": [sc.city.name for sc in seller.cities if sc.city],
        "categories": [sc.category.name for sc in seller.categories if sc.category],
        "address": seller.address,
        "lat": seller.lat,
        "lng": seller.lng,
        "whatsapp": seller.whatsapp,
        "telegram": seller.telegram,
        "instagram": seller.instagram,
        "pickup_note": seller.pickup_note,
    }
    if admin:
        until = seller.new_orders_blocked_until
        data.update(
            {
                "is_partner": bool(seller.is_partner),
                "partner_level": seller.partner_level,
                "strike_count": seller.strike_count or 0,
                "confirmed_reports_count": seller.confirmed_reports_count or 0,
                "false_availability_count": seller.false_availability_count or 0,
                "new_orders_blocked_until": until.isoformat() if until else None,
                "new_orders_blocked": bool(until and until > datetime.now(timezone.utc)),
            }
        )
    return data


def garage_out(row) -> dict:
    label_parts = []
    if row.brand:
        label_parts.append(row.brand.name)
    if row.model:
        label_parts.append(row.model.name)
    if row.year:
        label_parts.append(str(row.year))
    label = row.nickname or " ".join(label_parts) or "Авто"
    return {
        "id": row.id,
        "brand_id": row.brand_id,
        "model_id": row.model_id,
        "year": row.year,
        "nickname": row.nickname,
        "is_default": row.is_default,
        "label": label,
        "brand": row.brand.name if row.brand else None,
        "model": row.model.name if row.model else None,
    }


def order_item_out(item: OrderItem) -> dict:
    return {
        "id": item.id,
        "description": item.description,
        "category_id": item.category_id,
        "category": item.category.name if item.category else None,
        "status": item.status.value,
    }


def vehicle_label(order: Order) -> str:
    parts = []
    if order.brand:
        parts.append(order.brand.name)
    if order.model:
        parts.append(order.model.name)
    if order.vehicle_year:
        parts.append(str(order.vehicle_year))
    if not parts and order.vehicle_text:
        return order.vehicle_text
    if order.vehicle_text and order.vehicle_text not in " ".join(parts):
        parts.append(order.vehicle_text)
    return " ".join(parts) if parts else "Автомобиль не указан"


def offer_out(offer: SellerOffer, include_seller: bool = True, include_prices: bool = True) -> dict:
    items = []
    for it in offer.items:
        row = {
            "id": it.id,
            "order_item_id": it.order_item_id,
            "description": it.order_item.description if it.order_item else None,
            "availability": it.availability.value,
            "comment": it.comment,
            "detail": it.detail,
            "condition": it.condition,
            "is_original": it.is_original,
            "photo_path": it.photo_path,
        }
        if include_prices:
            row["price"] = float(it.price) if it.price is not None else None
        items.append(row)
    data = {
        "id": offer.id,
        "order_id": offer.order_id,
        "seller_id": offer.seller_id,
        "created_at": offer.created_at.isoformat() if offer.created_at else None,
        "items": items,
    }
    if include_seller and offer.seller:
        data["seller"] = seller_public(offer.seller)
    avs = [it.availability.value for it in offer.items]
    if avs and all(a == "YES" for a in avs):
        data["tone"] = "yes"
    elif avs and all(a == "NO" for a in avs):
        data["tone"] = "no"
    else:
        data["tone"] = "partial"
    return data


def order_out(
    db: Session,
    order: Order,
    viewer: User | None,
    include_all_offers: bool = False,
) -> dict:
    cities = [city_out(loc.city) for loc in order.locations if loc.city]
    offers_payload = []
    visible_offers: list[SellerOffer] = []
    if viewer and viewer.role == UserRole.ADMIN or include_all_offers:
        visible_offers = list(order.offers)
    elif viewer and viewer.role == UserRole.SELLER and viewer.seller_profile:
        visible_offers = [o for o in order.offers if o.seller_id == viewer.seller_profile.id]
    elif viewer and viewer.role == UserRole.CLIENT and viewer.id == order.client_id:
        visible_offers = list(order.offers)
        include_all_offers = True

    show_prices = True
    if viewer and viewer.role == UserRole.SELLER:
        show_prices = True  # own prices only because we filtered offers

    for offer in visible_offers:
        offers_payload.append(offer_out(offer, include_seller=True, include_prices=show_prices))

    chats_payload = []
    if viewer:
        chats = order.chats
        if viewer.role == UserRole.CLIENT:
            chats = [c for c in chats if c.client_id == viewer.id]
        elif viewer.role == UserRole.SELLER:
            chats = [c for c in chats if c.seller_user_id == viewer.id]
        for chat in chats:
            chats_payload.append(chat_summary(db, chat, viewer))

    assignment_payload = []
    if viewer and viewer.role == UserRole.ADMIN:
        for a in order.assignments:
            assignment_payload.append(
                {
                    "id": a.id,
                    "seller_id": a.seller_id,
                    "quality_score": a.quality_score,
                    "delay_seconds": a.delay_seconds,
                    "status": a.status.value,
                    "delivered_at": a.delivered_at.isoformat() if a.delivered_at else None,
                }
            )
    elif viewer and viewer.role == UserRole.SELLER and viewer.seller_profile:
        mine = [a for a in order.assignments if a.seller_id == viewer.seller_profile.id]
        for a in mine:
            assignment_payload.append(
                {
                    "id": a.id,
                    "status": a.status.value,
                    "delivered_at": a.delivered_at.isoformat() if a.delivered_at else None,
                    "delay_seconds": a.delay_seconds,
                    "quality_score": a.quality_score,
                }
            )

    return {
        "id": order.id,
        "client_id": order.client_id,
        "status": order.status.value,
        "search_mode": order.search_mode.value,
        "vehicle": vehicle_label(order),
        "vehicle_brand_id": order.vehicle_brand_id,
        "vehicle_model_id": order.vehicle_model_id,
        "vehicle_year": order.vehicle_year,
        "vehicle_text": order.vehicle_text,
        "search_price": float(order.search_price),
        "currency": order.currency,
        "batch_id": order.batch_id,
        "selected_offer_id": order.selected_offer_id,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "paid_at": order.paid_at.isoformat() if order.paid_at else None,
        "completed_at": order.completed_at.isoformat() if order.completed_at else None,
        "items": [order_item_out(i) for i in order.items],
        "cities": cities,
        "offers": offers_payload,
        "chats": chats_payload,
        "assignments": assignment_payload,
        "client": {"id": order.client.id, "name": order.client.name} if order.client else None,
    }


def chat_summary(db: Session, chat: Chat, viewer: User) -> dict:
    last = (
        db.query(Message)
        .filter(Message.chat_id == chat.id)
        .order_by(Message.created_at.desc())
        .first()
    )
    participant = (
        db.query(ChatParticipant)
        .filter(ChatParticipant.chat_id == chat.id, ChatParticipant.user_id == viewer.id)
        .first()
    )
    unread = 0
    q = db.query(Message).filter(Message.chat_id == chat.id, Message.sender_id != viewer.id)
    if participant and participant.last_read_at:
        q = q.filter(Message.created_at > participant.last_read_at)
    unread = q.count()
    other_name = None
    if viewer.id == chat.client_id:
        seller_user = db.query(User).filter(User.id == chat.seller_user_id).first()
        other_name = seller_user.name if seller_user else "Продавец"
        if chat.offer_id:
            from app.models import SellerOffer

            offer = db.query(SellerOffer).filter(SellerOffer.id == chat.offer_id).first()
            if offer and offer.seller:
                other_name = offer.seller.display_name
    else:
        client = db.query(User).filter(User.id == chat.client_id).first()
        other_name = client.name if client else "Клиент"
    return {
        "id": chat.id,
        "order_id": chat.order_id,
        "client_id": chat.client_id,
        "seller_id": chat.seller_id,
        "other_name": other_name,
        "last_message": last.text if last else None,
        "last_message_at": (last.created_at if last else chat.created_at).isoformat()
        if (last or chat.created_at)
        else None,
        "unread": unread,
    }


def message_out(msg: Message) -> dict:
    return {
        "id": msg.id,
        "chat_id": msg.chat_id,
        "sender_id": msg.sender_id,
        "text": msg.text,
        "created_at": msg.created_at.isoformat() if msg.created_at else None,
        "attachments": [
            {
                "id": a.id,
                "url": f"/api/media/{a.file_path}",
                "mime_type": a.mime_type,
                "original_name": a.original_name,
            }
            for a in msg.attachments
        ],
    }


def payment_out(p: Payment) -> dict:
    return {
        "id": p.id,
        "order_id": p.order_id,
        "user_id": p.user_id,
        "amount": float(p.amount),
        "currency": p.currency,
        "status": p.status.value,
        "demo_token": p.demo_token,
        "paid_at": p.paid_at.isoformat() if p.paid_at else None,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "qr_url": f"/api/payments/demo/{p.demo_token}/qr.png",
        "scan_url": f"/api/payments/demo/{p.demo_token}/scan",
    }

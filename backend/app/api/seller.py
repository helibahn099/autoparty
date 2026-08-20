from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.deps import get_current_user, require_seller
from app.models import (
    AssignmentStatus,
    Availability,
    Category,
    Chat,
    ChatParticipant,
    City,
    NotificationType,
    Order,
    OrderItem,
    OrderItemStatus,
    OrderSellerAssignment,
    OrderStatus,
    SellerCategory,
    SellerCity,
    SellerOffer,
    SellerOfferItem,
    SellerProfile,
    User,
)
from app.realtime import hub
from app.schemas import OfferCreateIn, SellerProfileUpdateIn
from app.serializers import order_out, seller_public
from app.services.notifications import create_notification
from app.services.ratings import record_response
from app.services.storage import storage

router = APIRouter(prefix="/api/seller", tags=["seller"])


@router.get("/profile")
def seller_profile(ctx: tuple[User, SellerProfile] = Depends(require_seller)):
    _user, profile = ctx
    return seller_public(profile)


@router.patch("/profile")
def update_seller_profile(
    payload: SellerProfileUpdateIn,
    ctx: tuple[User, SellerProfile] = Depends(require_seller),
    db: Session = Depends(get_db),
):
    _user, profile = ctx
    if payload.display_name:
        profile.display_name = payload.display_name.strip()
    if payload.category_ids is not None:
        db.query(SellerCategory).filter(SellerCategory.seller_id == profile.id).delete()
        for cid in set(payload.category_ids):
            if db.query(Category).filter(Category.id == cid).first():
                db.add(SellerCategory(seller_id=profile.id, category_id=cid))
    if payload.city_ids is not None:
        db.query(SellerCity).filter(SellerCity.seller_id == profile.id).delete()
        for city_id in set(payload.city_ids):
            if db.query(City).filter(City.id == city_id).first():
                db.add(SellerCity(seller_id=profile.id, city_id=city_id))
    if payload.address is not None:
        profile.address = payload.address.strip() or None
    if payload.lat is not None:
        profile.lat = payload.lat
    if payload.lng is not None:
        profile.lng = payload.lng
    if payload.whatsapp is not None:
        profile.whatsapp = payload.whatsapp.strip() or None
    if payload.telegram is not None:
        profile.telegram = payload.telegram.strip().lstrip("@") or None
    if payload.instagram is not None:
        profile.instagram = payload.instagram.strip().lstrip("@") or None
    if payload.pickup_note is not None:
        profile.pickup_note = payload.pickup_note.strip() or None
    db.commit()
    db.refresh(profile)
    return seller_public(profile)


@router.get("/requests")
def seller_requests(
    ctx: tuple[User, SellerProfile] = Depends(require_seller),
    db: Session = Depends(get_db),
):
    _user, profile = ctx
    assignments = (
        db.query(OrderSellerAssignment)
        .filter(
            OrderSellerAssignment.seller_id == profile.id,
            OrderSellerAssignment.status == AssignmentStatus.DELIVERED,
        )
        .order_by(OrderSellerAssignment.delivered_at.desc())
        .all()
    )
    result = []
    for a in assignments:
        order = (
            db.query(Order)
            .options(joinedload(Order.items), joinedload(Order.locations), joinedload(Order.brand), joinedload(Order.model))
            .filter(Order.id == a.order_id)
            .first()
        )
        if not order or order.status in {OrderStatus.CANCELLED, OrderStatus.EXPIRED}:
            continue
        offer = (
            db.query(SellerOffer)
            .filter(SellerOffer.order_id == order.id, SellerOffer.seller_id == profile.id)
            .first()
        )
        payload = order_out(db, order, _user)
        payload["assignment"] = {
            "delay_seconds": a.delay_seconds,
            "quality_score": a.quality_score,
            "delivered_at": a.delivered_at.isoformat() if a.delivered_at else None,
        }
        payload["my_offer"] = None
        if offer:
            from app.serializers import offer_out

            payload["my_offer"] = offer_out(offer, include_seller=False)
        result.append(payload)
    return result


@router.get("/requests/{order_id}")
def seller_request_detail(
    order_id: int,
    ctx: tuple[User, SellerProfile] = Depends(require_seller),
    db: Session = Depends(get_db),
):
    _user, profile = ctx
    assignment = (
        db.query(OrderSellerAssignment)
        .filter(
            OrderSellerAssignment.order_id == order_id,
            OrderSellerAssignment.seller_id == profile.id,
            OrderSellerAssignment.status == AssignmentStatus.DELIVERED,
        )
        .first()
    )
    if not assignment:
        raise HTTPException(status_code=404, detail="Запрос не найден")
    order = (
        db.query(Order)
        .options(
            joinedload(Order.items),
            joinedload(Order.locations),
            joinedload(Order.brand),
            joinedload(Order.model),
            joinedload(Order.client),
        )
        .filter(Order.id == order_id)
        .first()
    )
    return order_out(db, order, _user)


def _ensure_chat(db: Session, order: Order, profile: SellerProfile, offer: SellerOffer) -> Chat:
    chat = (
        db.query(Chat)
        .filter(Chat.order_id == order.id, Chat.seller_id == profile.id)
        .first()
    )
    if chat:
        chat.offer_id = offer.id
        return chat
    chat = Chat(
        order_id=order.id,
        client_id=order.client_id,
        seller_user_id=profile.user_id,
        seller_id=profile.id,
        offer_id=offer.id,
    )
    db.add(chat)
    db.flush()
    db.add(ChatParticipant(chat_id=chat.id, user_id=order.client_id))
    db.add(ChatParticipant(chat_id=chat.id, user_id=profile.user_id))
    return chat


@router.post("/offers")
def create_offer(
    payload: OfferCreateIn,
    ctx: tuple[User, SellerProfile] = Depends(require_seller),
    db: Session = Depends(get_db),
):
    user, profile = ctx
    if not payload.items:
        raise HTTPException(status_code=400, detail="Выберите хотя бы одну деталь")
    assignment = (
        db.query(OrderSellerAssignment)
        .filter(
            OrderSellerAssignment.order_id == payload.order_id,
            OrderSellerAssignment.seller_id == profile.id,
            OrderSellerAssignment.status == AssignmentStatus.DELIVERED,
        )
        .first()
    )
    if not assignment:
        raise HTTPException(status_code=403, detail="Этот запрос вам недоступен")
    order = db.query(Order).filter(Order.id == payload.order_id).first()
    if not order or order.status in {OrderStatus.CANCELLED, OrderStatus.EXPIRED, OrderStatus.COMPLETED}:
        raise HTTPException(status_code=400, detail="Заказ недоступен для ответа")

    item_ids = {i.id for i in order.items}
    offer = (
        db.query(SellerOffer)
        .filter(SellerOffer.order_id == order.id, SellerOffer.seller_id == profile.id)
        .first()
    )
    is_first = offer is None
    if not offer:
        offer = SellerOffer(order_id=order.id, seller_id=profile.id)
        db.add(offer)
        db.flush()

    for row in payload.items:
        if row.order_item_id not in item_ids:
            raise HTTPException(status_code=400, detail="Некорректная деталь заказа")
        if row.availability in {Availability.YES, Availability.PARTIAL} and (row.price is None or row.price <= 0):
            raise HTTPException(status_code=400, detail="Укажите цену для имеющейся детали")
        existing = (
            db.query(SellerOfferItem)
            .filter(SellerOfferItem.offer_id == offer.id, SellerOfferItem.order_item_id == row.order_item_id)
            .first()
        )
        in_stock = row.availability in {Availability.YES, Availability.PARTIAL}
        if existing:
            existing.availability = row.availability
            existing.price = row.price if in_stock else None
            existing.comment = row.comment
            existing.detail = row.detail
            existing.condition = row.condition.value if row.condition else None
            existing.is_original = row.is_original
        else:
            db.add(
                SellerOfferItem(
                    offer_id=offer.id,
                    order_item_id=row.order_item_id,
                    availability=row.availability,
                    price=row.price if in_stock else None,
                    comment=row.comment,
                    detail=row.detail,
                    condition=row.condition.value if row.condition else None,
                    is_original=row.is_original,
                )
            )
        order_item = db.query(OrderItem).filter(OrderItem.id == row.order_item_id).first()
        if order_item:
            if row.availability in {Availability.YES, Availability.PARTIAL}:
                order_item.status = OrderItemStatus.FOUND
            elif order_item.status == OrderItemStatus.PENDING:
                # stay pending until someone has it; mark NOT_FOUND only if we want
                pass

    if is_first:
        elapsed = 0.0
        if assignment.delivered_at:
            elapsed = (datetime.now(timezone.utc) - assignment.delivered_at).total_seconds()
        record_response(profile, elapsed)

    _ensure_chat(db, order, profile, offer)
    if order.status == OrderStatus.SEARCHING:
        order.status = OrderStatus.OFFERS_RECEIVED

    create_notification(
        db,
        user_id=order.client_id,
        ntype=NotificationType.NEW_OFFER,
        title="Новый ответ продавца",
        body=f"{profile.display_name} ответил по заказу #{order.id}",
        payload={"order_id": order.id, "offer_id": offer.id},
    )
    db.commit()
    hub.send_to_user(order.client_id, {"event": "offer.new", "data": {"order_id": order.id}})
    return order_out(db, order, user)


@router.post("/offers/{offer_id}/items/{item_id}/photo")
def offer_item_photo(
    offer_id: int,
    item_id: int,
    file: UploadFile = File(...),
    ctx: tuple[User, SellerProfile] = Depends(require_seller),
    db: Session = Depends(get_db),
):
    _user, profile = ctx
    item = (
        db.query(SellerOfferItem)
        .join(SellerOffer)
        .filter(SellerOfferItem.id == item_id, SellerOffer.id == offer_id, SellerOffer.seller_id == profile.id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Позиция не найдена")
    key = storage.save_image(file)
    item.photo_path = key
    db.commit()
    return {"photo_path": key, "url": f"/api/media/{key}"}

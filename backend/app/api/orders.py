from datetime import datetime, timedelta, timezone
import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.models import (
    AssignmentStatus,
    City,
    NotificationType,
    Order,
    OrderItem,
    OrderItemStatus,
    OrderLocation,
    OrderSellerAssignment,
    OrderStatus,
    SearchMode,
    SellerOffer,
    User,
    UserRole,
    UserVehicle,
)
from app.realtime import hub
from app.schemas import BatchCreateIn, OrderCreateIn, SelectSellerIn
from app.serializers import order_out
from app.services.notifications import create_notification

router = APIRouter(prefix="/api/orders", tags=["orders"])


def _validate_items(items) -> None:
    if not items:
        raise HTTPException(status_code=400, detail="Добавьте хотя бы одну деталь")
    for item in items:
        text = item.description.strip()
        if len(text) < 2 or len(text) > 500:
            raise HTTPException(status_code=400, detail="Описание детали должно быть от 2 до 500 символов")


def _validate_cities(db: Session, city_ids: list[int]) -> None:
    if not city_ids:
        raise HTTPException(status_code=400, detail="Выберите хотя бы один населённый пункт")
    cities = db.query(City).filter(City.id.in_(city_ids), City.is_active.is_(True)).all()
    if len(cities) != len(set(city_ids)):
        raise HTTPException(status_code=400, detail="Некорректные населённые пункты")


def _has_vehicle(brand_id, model_id, year, text) -> bool:
    return bool(brand_id or model_id or (text and str(text).strip()))


def _maybe_save_garage(db: Session, user: User, brand_id, model_id, year) -> None:
    if not brand_id:
        return
    exists = (
        db.query(UserVehicle)
        .filter(
            UserVehicle.user_id == user.id,
            UserVehicle.brand_id == brand_id,
            UserVehicle.model_id == model_id,
            UserVehicle.year == year,
        )
        .first()
    )
    if exists:
        return
    count = db.query(UserVehicle).filter(UserVehicle.user_id == user.id).count()
    db.add(
        UserVehicle(
            user_id=user.id,
            brand_id=brand_id,
            model_id=model_id,
            year=year,
            is_default=count == 0,
        )
    )


def _build_order(db, user, items, city_ids, brand_id, model_id, year, vehicle_text, price, batch_id=None, save_garage=True):
    if not _has_vehicle(brand_id, model_id, year, vehicle_text):
        raise HTTPException(status_code=400, detail="Укажите автомобиль: марку/модель или текстовое описание")
    mode = SearchMode.MULTIPLE if len(items) > 1 else SearchMode.SINGLE
    order = Order(
        client_id=user.id,
        status=OrderStatus.WAITING_FOR_PAYMENT,
        search_mode=mode,
        vehicle_brand_id=brand_id,
        vehicle_model_id=model_id,
        vehicle_year=year,
        vehicle_text=(vehicle_text or "").strip() or None,
        search_price=price,
        currency=settings.SEARCH_CURRENCY,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.ORDER_EXPIRE_DAYS),
        batch_id=batch_id,
    )
    db.add(order)
    db.flush()
    for item in items:
        db.add(
            OrderItem(
                order_id=order.id,
                description=item.description.strip(),
                category_id=item.category_id,
                status=OrderItemStatus.PENDING,
            )
        )
    for city_id in set(city_ids):
        db.add(OrderLocation(order_id=order.id, city_id=city_id))
    if save_garage:
        _maybe_save_garage(db, user, brand_id, model_id, year)
    return order


def _reload(db, order_id):
    return (
        db.query(Order)
        .options(
            joinedload(Order.items),
            joinedload(Order.locations),
            joinedload(Order.brand),
            joinedload(Order.model),
        )
        .filter(Order.id == order_id)
        .first()
    )


@router.post("")
def create_order(payload: OrderCreateIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role == UserRole.ADMIN:
        raise HTTPException(status_code=400, detail="Администратор не создаёт клиентские заказы")
    _validate_items(payload.items)
    _validate_cities(db, payload.city_ids)
    order = _build_order(
        db,
        user,
        payload.items,
        payload.city_ids,
        payload.vehicle_brand_id,
        payload.vehicle_model_id,
        payload.vehicle_year,
        payload.vehicle_text,
        settings.SEARCH_PRICE_KGS,
        save_garage=payload.save_to_garage,
    )
    db.commit()
    return order_out(db, _reload(db, order.id), user)


@router.post("/batch")
def create_batch(payload: BatchCreateIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role == UserRole.ADMIN:
        raise HTTPException(status_code=400, detail="Администратор не создаёт клиентские заказы")
    if not payload.vehicles:
        raise HTTPException(status_code=400, detail="Выберите хотя бы один автомобиль")
    _validate_cities(db, payload.city_ids)
    batch_id = secrets.token_urlsafe(12)
    created = []
    for index, vehicle in enumerate(payload.vehicles):
        items = vehicle.items if (not payload.same_parts and vehicle.items) else payload.items
        _validate_items(items)
        brand_id = vehicle.vehicle_brand_id
        model_id = vehicle.vehicle_model_id
        year = vehicle.vehicle_year
        text = vehicle.vehicle_text
        if vehicle.garage_id:
            gv = db.query(UserVehicle).filter(UserVehicle.id == vehicle.garage_id, UserVehicle.user_id == user.id).first()
            if not gv:
                raise HTTPException(status_code=400, detail="Автомобиль из гаража не найден")
            brand_id = gv.brand_id
            model_id = gv.model_id
            year = gv.year
            if not text:
                text = gv.nickname
        price = settings.SEARCH_PRICE_KGS if index == 0 else 0
        order = _build_order(
            db,
            user,
            items,
            payload.city_ids,
            brand_id,
            model_id,
            year,
            text,
            price,
            batch_id=batch_id,
            save_garage=True,
        )
        created.append(order)
    db.commit()
    orders = [order_out(db, _reload(db, o.id), user) for o in created]
    return {
        "batch_id": batch_id,
        "pay_order_id": created[0].id,
        "search_price": settings.SEARCH_PRICE_KGS,
        "currency": settings.SEARCH_CURRENCY,
        "orders": orders,
    }


@router.get("")
def list_orders(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    since = datetime.now(timezone.utc) - timedelta(days=90)
    q = db.query(Order).filter(Order.created_at >= since)
    if user.role != UserRole.ADMIN:
        q = q.filter(Order.client_id == user.id)
    orders = q.order_by(Order.created_at.desc()).all()
    return [order_out(db, o, user) for o in orders]


@router.get("/{order_id}")
def get_order(order_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    order = (
        db.query(Order)
        .options(
            joinedload(Order.items),
            joinedload(Order.locations),
            joinedload(Order.offers),
            joinedload(Order.chats),
            joinedload(Order.assignments),
            joinedload(Order.brand),
            joinedload(Order.model),
            joinedload(Order.client),
        )
        .filter(Order.id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    if user.role == UserRole.CLIENT and order.client_id != user.id:
        raise HTTPException(status_code=403, detail="Нет доступа к этому заказу")
    if user.role == UserRole.SELLER:
        from app.models import OrderSellerAssignment

        if not user.seller_profile:
            raise HTTPException(status_code=403, detail="Нет профиля продавца")
        assigned = (
            db.query(OrderSellerAssignment)
            .filter(
                OrderSellerAssignment.order_id == order.id,
                OrderSellerAssignment.seller_id == user.seller_profile.id,
                OrderSellerAssignment.status == AssignmentStatus.DELIVERED,
            )
            .first()
        )
        if not assigned:
            raise HTTPException(status_code=403, detail="Запрос вам ещё не доступен")
    return order_out(db, order, user)


@router.post("/{order_id}/select-seller")
def select_seller(
    order_id: int,
    payload: SelectSellerIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order or order.client_id != user.id:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    if order.status not in {OrderStatus.OFFERS_RECEIVED, OrderStatus.SEARCHING, OrderStatus.SELLER_SELECTED}:
        raise HTTPException(status_code=400, detail="Нельзя выбрать продавца на этом этапе")
    offer = db.query(SellerOffer).filter(SellerOffer.id == payload.offer_id, SellerOffer.order_id == order.id).first()
    if not offer:
        raise HTTPException(status_code=404, detail="Предложение не найдено")
    has_stock = any(i.availability.value in {"YES", "PARTIAL"} for i in offer.items)
    if not has_stock:
        raise HTTPException(status_code=400, detail="У выбранного продавца нет наличия")
    order.selected_offer_id = offer.id
    order.status = OrderStatus.SELLER_SELECTED
    db.commit()
    from app.services.reputation import refresh_reputation

    refresh_reputation(db, offer.seller)
    create_notification(
        db,
        user_id=offer.seller.user_id,
        ntype=NotificationType.SELLER_SELECTED,
        title="Вас выбрали",
        body=f"Клиент выбрал вас по заказу #{order.id}",
        payload={"order_id": order.id},
    )
    db.commit()
    hub.send_to_user(order.client_id, {"event": "order.status", "data": {"order_id": order.id, "status": order.status.value}})
    return order_out(db, order, user)


@router.post("/{order_id}/complete")
def complete_order(order_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order or order.client_id != user.id:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    if order.status != OrderStatus.SELLER_SELECTED:
        raise HTTPException(status_code=400, detail="Сначала выберите продавца")
    order.status = OrderStatus.COMPLETED
    order.completed_at = datetime.now(timezone.utc)
    db.commit()
    return order_out(db, order, user)


@router.post("/{order_id}/cancel")
def cancel_order(order_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order or (order.client_id != user.id and user.role != UserRole.ADMIN):
        raise HTTPException(status_code=404, detail="Заказ не найден")
    if order.status in {OrderStatus.COMPLETED, OrderStatus.CANCELLED}:
        raise HTTPException(status_code=400, detail="Заказ уже закрыт")
    order.status = OrderStatus.CANCELLED
    db.commit()
    return order_out(db, order, user)

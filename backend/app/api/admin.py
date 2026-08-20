from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.deps import require_admin
from app.models import (
    AuditLog,
    Category,
    Chat,
    City,
    Country,
    Message,
    Order,
    OrderStatus,
    Payment,
    PaymentStatus,
    Region,
    Report,
    ReportReason,
    ReportStatus,
    SellerCategory,
    SellerCity,
    SellerOffer,
    SellerProfile,
    SellerStatus,
    User,
    UserRole,
)
from app.schemas import (
    AdminSellerUpdateIn,
    AdminUserUpdateIn,
    CategoryIn,
    CityIn,
    OrderStatusIn,
    RegionIn,
    RotationSettingsIn,
)
from app.serializers import chat_summary, order_out, payment_out, seller_public, user_out
from app.services.audit import write_audit
from app.services.reputation import get_settings, refresh_reputation
from app.services.scoring import refresh_seller_scores

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/dashboard")
def dashboard(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    users_count = db.query(User).count()
    sellers_count = db.query(SellerProfile).count()
    approved_sellers = db.query(SellerProfile).filter(SellerProfile.status == SellerStatus.APPROVED).count()
    orders_count = db.query(Order).count()
    active_orders = (
        db.query(Order)
        .filter(Order.status.in_([OrderStatus.SEARCHING, OrderStatus.OFFERS_RECEIVED, OrderStatus.WAITING_FOR_PAYMENT, OrderStatus.PAID, OrderStatus.SELLER_SELECTED]))
        .count()
    )
    completed = db.query(Order).filter(Order.status == OrderStatus.COMPLETED).count()
    paid_sum = (
        db.query(func.coalesce(func.sum(Payment.amount), 0))
        .filter(Payment.status == PaymentStatus.PAID)
        .scalar()
    )
    payments_count = db.query(Payment).count()
    chats_count = db.query(Chat).count()
    pending_reports = db.query(Report).filter(Report.status == ReportStatus.PENDING.value).count()
    confirmed_false = (
        db.query(Report)
        .filter(Report.reason == ReportReason.FALSE_AVAILABILITY.value, Report.status == ReportStatus.CONFIRMED.value)
        .count()
    )
    return {
        "users": users_count,
        "sellers": sellers_count,
        "approved_sellers": approved_sellers,
        "orders": orders_count,
        "active_orders": active_orders,
        "completed_orders": completed,
        "payments": payments_count,
        "payments_sum": float(paid_sum or 0),
        "chats": chats_count,
        "messages": db.query(Message).count(),
        "pending_reports": pending_reports,
        "false_answers": confirmed_false,
    }


@router.get("/users")
def list_users(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.id).all()
    return [user_out(u) for u in users]


@router.patch("/users/{user_id}")
def update_user(
    user_id: int,
    payload: AdminUserUpdateIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    old = user_out(user)
    if payload.name is not None:
        user.name = payload.name
    if payload.phone is not None:
        user.phone = payload.phone
    if payload.role is not None:
        user.role = payload.role
        if payload.role == UserRole.SELLER and not user.seller_profile:
            profile = SellerProfile(user_id=user.id, display_name=user.name, status=SellerStatus.PENDING)
            db.add(profile)
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.is_blocked is not None:
        user.is_blocked = payload.is_blocked
        if user.is_blocked:
            user.is_active = False
    write_audit(db, admin, "USER_UPDATED", "user", user.id, old, user_out(user))
    db.commit()
    return user_out(user)


@router.post("/users/{user_id}/block")
def block_user(user_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    user.is_blocked = True
    user.is_active = False
    write_audit(db, admin, "USER_BLOCKED", "user", user.id, None, {"is_blocked": True})
    db.commit()
    return user_out(user)


@router.post("/users/{user_id}/unblock")
def unblock_user(user_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    user.is_blocked = False
    user.is_active = True
    write_audit(db, admin, "USER_UNBLOCKED", "user", user.id, None, {"is_blocked": False})
    db.commit()
    return user_out(user)


@router.delete("/users/{user_id}")
def delete_user(user_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    if user.role == UserRole.ADMIN:
        raise HTTPException(status_code=400, detail="Нельзя удалить администратора")
    user.is_active = False
    user.is_blocked = True
    write_audit(db, admin, "USER_DELETED", "user", user.id, user_out(user), {"is_active": False})
    db.commit()
    return {"ok": True}


@router.get("/sellers")
def list_sellers(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    sellers = db.query(SellerProfile).options(joinedload(SellerProfile.user)).all()
    return [seller_public(s, admin=True) | {"email": s.user.email if s.user else None} for s in sellers]


@router.post("/sellers/{seller_id}/approve")
def approve_seller(seller_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    seller = db.query(SellerProfile).filter(SellerProfile.id == seller_id).first()
    if not seller:
        raise HTTPException(status_code=404, detail="Продавец не найден")
    old = seller.status.value
    seller.status = SellerStatus.APPROVED
    seller.user.role = UserRole.SELLER
    refresh_seller_scores(seller)
    write_audit(
        db,
        admin,
        "SELLER_APPROVED",
        "seller",
        seller.id,
        {"status": old},
        {"status": seller.status.value},
    )
    db.commit()
    return seller_public(seller)


@router.patch("/sellers/{seller_id}")
def update_seller(
    seller_id: int,
    payload: AdminSellerUpdateIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    seller = db.query(SellerProfile).filter(SellerProfile.id == seller_id).first()
    if not seller:
        raise HTTPException(status_code=404, detail="Продавец не найден")
    old = seller_public(seller)
    if payload.display_name:
        seller.display_name = payload.display_name
    if payload.status:
        seller.status = payload.status
        if payload.status == SellerStatus.BLOCKED:
            seller.user.is_blocked = True
    if payload.category_ids is not None:
        db.query(SellerCategory).filter(SellerCategory.seller_id == seller.id).delete()
        for cid in payload.category_ids:
            db.add(SellerCategory(seller_id=seller.id, category_id=cid))
    if payload.city_ids is not None:
        db.query(SellerCity).filter(SellerCity.seller_id == seller.id).delete()
        for city_id in payload.city_ids:
            db.add(SellerCity(seller_id=seller.id, city_id=city_id))
    if payload.is_partner is not None:
        seller.is_partner = payload.is_partner
        if not payload.is_partner:
            seller.partner_level = None
    if payload.partner_level is not None:
        seller.is_partner = True
        seller.partner_level = payload.partner_level
    if payload.strike_count is not None:
        seller.strike_count = payload.strike_count
    if payload.clear_new_orders_block:
        seller.new_orders_blocked_until = None
    refresh_reputation(db, seller)
    write_audit(db, admin, "SELLER_UPDATED", "seller", seller.id, old, seller_public(seller, admin=True))
    db.commit()
    return seller_public(seller, admin=True)


@router.get("/orders")
def admin_orders(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    orders = (
        db.query(Order)
        .options(
            joinedload(Order.items),
            joinedload(Order.locations),
            joinedload(Order.offers),
            joinedload(Order.client),
        )
        .order_by(Order.created_at.desc())
        .all()
    )
    return [order_out(db, o, admin) for o in orders]


@router.get("/orders/{order_id}")
def admin_order(order_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    return order_out(db, order, admin)


@router.patch("/orders/{order_id}")
def admin_update_order(
    order_id: int,
    payload: OrderStatusIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    old = order.status.value
    order.status = payload.status
    write_audit(db, admin, "ORDER_STATUS_CHANGED", "order", order.id, {"status": old}, {"status": payload.status.value})
    db.commit()
    return order_out(db, order, admin)


@router.get("/payments")
def admin_payments(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    rows = db.query(Payment).order_by(Payment.created_at.desc()).all()
    return [payment_out(p) for p in rows]


@router.get("/chats")
def admin_chats(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    chats = db.query(Chat).order_by(Chat.last_message_at.desc().nullslast()).all()
    return [chat_summary(db, c, admin) for c in chats]


@router.get("/offers")
def admin_offers(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    from app.serializers import offer_out

    offers = db.query(SellerOffer).order_by(SellerOffer.created_at.desc()).all()
    return [offer_out(o) for o in offers]


@router.get("/categories")
def admin_categories(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    rows = db.query(Category).order_by(Category.name).all()
    return [{"id": c.id, "slug": c.slug, "name": c.name, "name_en": c.name_en, "name_ky": c.name_ky, "is_active": c.is_active} for c in rows]


@router.post("/categories")
def create_category(payload: CategoryIn, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    slug = payload.slug or payload.name.lower().replace(" ", "-")
    cat = Category(name=payload.name, name_en=payload.name_en, name_ky=payload.name_ky, slug=slug, is_active=payload.is_active)
    db.add(cat)
    db.flush()
    write_audit(db, admin, "CATEGORY_CREATED", "category", cat.id, None, {"name": cat.name})
    db.commit()
    return {"id": cat.id, "slug": cat.slug, "name": cat.name}


@router.patch("/categories/{category_id}")
def update_category(
    category_id: int,
    payload: CategoryIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    cat = db.query(Category).filter(Category.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Категория не найдена")
    old = {"name": cat.name, "is_active": cat.is_active}
    cat.name = payload.name
    cat.is_active = payload.is_active
    if payload.slug:
        cat.slug = payload.slug
    write_audit(db, admin, "CATEGORY_UPDATED", "category", cat.id, old, {"name": cat.name, "is_active": cat.is_active})
    db.commit()
    return {"id": cat.id, "name": cat.name, "slug": cat.slug, "is_active": cat.is_active}


@router.delete("/categories/{category_id}")
def delete_category(category_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    cat = db.query(Category).filter(Category.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Категория не найдена")
    cat.is_active = False
    write_audit(db, admin, "CATEGORY_DELETED", "category", cat.id, {"is_active": True}, {"is_active": False})
    db.commit()
    return {"ok": True}


@router.get("/locations")
def admin_locations(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    countries = db.query(Country).all()
    out = []
    for c in countries:
        regions = []
        for r in c.regions:
            cities = [
                {"id": city.id, "name": city.name, "name_en": city.name_en, "name_ky": city.name_ky, "is_active": city.is_active, "lat": city.lat, "lng": city.lng}
                for city in r.cities
            ]
            regions.append({"id": r.id, "name": r.name, "is_active": r.is_active, "cities": cities})
        out.append({"id": c.id, "code": c.code, "name": c.name, "regions": regions})
    return out


@router.post("/regions")
def create_region(payload: RegionIn, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    region = Region(name=payload.name, country_id=payload.country_id, is_active=payload.is_active)
    db.add(region)
    db.flush()
    write_audit(db, admin, "REGION_CREATED", "region", region.id, None, {"name": region.name})
    db.commit()
    return {"id": region.id, "name": region.name}


@router.post("/cities")
def create_city(payload: CityIn, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    city = City(
        name=payload.name,
        name_en=payload.name_en,
        name_ky=payload.name_ky,
        region_id=payload.region_id,
        is_active=payload.is_active,
        lat=payload.lat,
        lng=payload.lng,
    )
    db.add(city)
    db.flush()
    write_audit(db, admin, "CITY_CREATED", "city", city.id, None, {"name": city.name})
    db.commit()
    return {"id": city.id, "name": city.name}


@router.patch("/cities/{city_id}")
def update_city(city_id: int, payload: CityIn, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    city = db.query(City).filter(City.id == city_id).first()
    if not city:
        raise HTTPException(status_code=404, detail="Город не найден")
    old = {"name": city.name, "is_active": city.is_active}
    city.name = payload.name
    city.region_id = payload.region_id
    city.is_active = payload.is_active
    if payload.name_en is not None:
        city.name_en = payload.name_en
    if payload.name_ky is not None:
        city.name_ky = payload.name_ky
    if payload.lat is not None:
        city.lat = payload.lat
    if payload.lng is not None:
        city.lng = payload.lng
    write_audit(db, admin, "CITY_UPDATED", "city", city.id, old, {"name": city.name, "is_active": city.is_active})
    db.commit()
    return {"id": city.id, "name": city.name, "is_active": city.is_active}


@router.get("/audit-logs")
def audit_logs(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(300).all()
    return [
        {
            "id": log.id,
            "admin_id": log.admin_id,
            "admin_email": log.admin.email if log.admin else None,
            "action": log.action,
            "target_type": log.target_type,
            "target_id": log.target_id,
            "old_value": log.old_value,
            "new_value": log.new_value,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]


@router.get("/rotation")
def get_rotation(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    s = get_settings(db)
    paid_like = (
        db.query(Order)
        .filter(
            Order.status.in_(
                [
                    OrderStatus.PAID,
                    OrderStatus.SEARCHING,
                    OrderStatus.OFFERS_RECEIVED,
                    OrderStatus.SELLER_SELECTED,
                    OrderStatus.COMPLETED,
                ]
            )
        )
        .count()
    )
    return {
        "rotation_after_orders": s.rotation_after_orders,
        "rotation_lookback_hours": s.rotation_lookback_hours,
        "rotation_max_extra_delay": s.rotation_max_extra_delay,
        "strike_limit": s.strike_limit,
        "strike_ban_days": s.strike_ban_days,
        "current_paid_orders": paid_like,
        "rotation_active": paid_like >= (s.rotation_after_orders or 20),
    }


@router.patch("/rotation")
def update_rotation(
    payload: RotationSettingsIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    s = get_settings(db)
    old = {
        "rotation_after_orders": s.rotation_after_orders,
        "rotation_lookback_hours": s.rotation_lookback_hours,
        "rotation_max_extra_delay": s.rotation_max_extra_delay,
        "strike_limit": s.strike_limit,
        "strike_ban_days": s.strike_ban_days,
    }
    if payload.rotation_after_orders is not None:
        s.rotation_after_orders = payload.rotation_after_orders
    if payload.rotation_lookback_hours is not None:
        s.rotation_lookback_hours = payload.rotation_lookback_hours
    if payload.rotation_max_extra_delay is not None:
        s.rotation_max_extra_delay = payload.rotation_max_extra_delay
    if payload.strike_limit is not None:
        s.strike_limit = payload.strike_limit
    if payload.strike_ban_days is not None:
        s.strike_ban_days = payload.strike_ban_days
    write_audit(db, admin, "ROTATION_UPDATED", "settings", 1, old, payload.model_dump(exclude_none=True))
    db.commit()
    return get_rotation(admin, db)

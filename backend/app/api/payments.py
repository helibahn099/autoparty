"""Demo payment flow. Not a real bank integration.

TODO: replace demo payment flow with O!Bank payment API/webhook
"""

import io
import secrets
from datetime import datetime, timezone

import qrcode
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_current_user, get_optional_user
from app.models import NotificationType, Order, OrderStatus, Payment, PaymentStatus, User, UserRole
from app.realtime import hub
from app.serializers import payment_out
from app.services.distribution import start_distribution
from app.services.notifications import create_notification

router = APIRouter(prefix="/api/payments", tags=["payments"])


class DemoCreateIn(BaseModel):
    order_id: int


def _mark_paid(db: Session, payment: Payment) -> None:
    if payment.status == PaymentStatus.PAID:
        return
    order = db.query(Order).filter(Order.id == payment.order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    payment.status = PaymentStatus.PAID
    payment.paid_at = datetime.now(timezone.utc)
    siblings = [order]
    if order.batch_id:
        siblings = db.query(Order).filter(Order.batch_id == order.batch_id).all()
    for sibling in siblings:
        if sibling.status not in {OrderStatus.WAITING_FOR_PAYMENT, OrderStatus.DRAFT, OrderStatus.PAID}:
            continue
        sibling.status = OrderStatus.PAID
        sibling.paid_at = payment.paid_at
        db.flush()
        sibling.status = OrderStatus.SEARCHING
        start_distribution(db, sibling)
        create_notification(
            db,
            user_id=sibling.client_id,
            ntype=NotificationType.ORDER_STATUS,
            title="Оплата получена",
            body=f"Заказ #{sibling.id} оплачен, начинаем поиск продавцов",
            payload={"order_id": sibling.id, "status": sibling.status.value},
        )
        hub.send_to_user(
            sibling.client_id,
            {"event": "order.status", "data": {"order_id": sibling.id, "status": sibling.status.value}},
        )
    db.commit()


@router.post("/demo/create")
def demo_create(payload: DemoCreateIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # TODO: replace demo payment flow with O!Bank payment API/webhook
    order = db.query(Order).filter(Order.id == payload.order_id).first()
    if not order or (order.client_id != user.id and user.role != UserRole.ADMIN):
        raise HTTPException(status_code=404, detail="Заказ не найден")
    if order.status not in {OrderStatus.WAITING_FOR_PAYMENT, OrderStatus.DRAFT}:
        existing = (
            db.query(Payment)
            .filter(Payment.order_id == order.id)
            .order_by(Payment.created_at.desc())
            .first()
        )
        if existing:
            return payment_out(existing)
        raise HTTPException(status_code=400, detail="Заказ не ожидает оплаты")
    existing = (
        db.query(Payment)
        .filter(Payment.order_id == order.id, Payment.status == PaymentStatus.PENDING)
        .first()
    )
    if existing:
        return payment_out(existing)
    payment = Payment(
        order_id=order.id,
        user_id=order.client_id,
        amount=order.search_price or settings.SEARCH_PRICE_KGS,
        currency=order.currency,
        status=PaymentStatus.PENDING,
        demo_token=secrets.token_urlsafe(24),
        batch_id=order.batch_id,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment_out(payment)


@router.get("/demo/{token}/qr.png")
def demo_qr(token: str, db: Session = Depends(get_db)):
    payment = db.query(Payment).filter(Payment.demo_token == token).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Платёж не найден")
    scan_url = f"{settings.PUBLIC_URL.rstrip('/')}/api/payments/demo/{token}/scan"
    img = qrcode.make(scan_url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")


@router.get("/demo/{token}/scan")
def demo_scan(token: str, db: Session = Depends(get_db)):
    """Opened when the QR is scanned. Marks demo payment paid, then rickrolls.

    TODO: replace demo payment flow with O!Bank payment API/webhook
    """
    payment = db.query(Payment).filter(Payment.demo_token == token).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Платёж не найден")
    _mark_paid(db, payment)
    return RedirectResponse(url=settings.DEMO_PAYMENT_REDIRECT_URL, status_code=302)


@router.post("/demo/callback")
def demo_callback(payload: DemoCreateIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Browser-side demo callback (simulate scan from the payment screen).

    TODO: replace demo payment flow with O!Bank payment API/webhook
    """
    order = db.query(Order).filter(Order.id == payload.order_id).first()
    if not order or (order.client_id != user.id and user.role != UserRole.ADMIN):
        raise HTTPException(status_code=404, detail="Заказ не найден")
    payment = (
        db.query(Payment)
        .filter(Payment.order_id == order.id)
        .order_by(Payment.created_at.desc())
        .first()
    )
    if not payment:
        raise HTTPException(status_code=404, detail="Платёж не найден")
    _mark_paid(db, payment)
    return {"ok": True, "status": "PAID", "order_id": order.id}


@router.get("/by-order/{order_id}")
def by_order(order_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    if user.role != UserRole.ADMIN and order.client_id != user.id:
        raise HTTPException(status_code=403, detail="Нет доступа")
    payment = (
        db.query(Payment)
        .filter(Payment.order_id == order_id)
        .order_by(Payment.created_at.desc())
        .first()
    )
    if not payment:
        raise HTTPException(status_code=404, detail="Платёж не найден")
    return payment_out(payment)

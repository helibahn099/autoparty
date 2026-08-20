"""Order distribution with delayed delivery by seller quality + soft rotation.

Partners skip rotation penalties and get shorter delays.
Until the platform has `rotation_after_orders` paid searches, everyone is notified together.
"""

from __future__ import annotations

import asyncio
import threading
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import (
    AssignmentStatus,
    NotificationType,
    Order,
    OrderSellerAssignment,
    OrderStatus,
    SellerProfile,
)
from app.services.matching import matching_sellers
from app.services.notifications import create_notification
from app.services.reputation import get_settings, seller_accepts_new_orders
from app.services.scoring import delay_for_score, refresh_seller_scores


async def _deliver_later(assignment_id: int, delay_seconds: int) -> None:
    if delay_seconds > 0:
        await asyncio.sleep(delay_seconds)
    db = SessionLocal()
    try:
        deliver_assignment(db, assignment_id)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def schedule_delivery(assignment_id: int, delay_seconds: int) -> None:
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_deliver_later(assignment_id, delay_seconds))
        return
    except RuntimeError:
        pass
    threading.Thread(
        target=lambda: asyncio.run(_deliver_later(assignment_id, delay_seconds)),
        daemon=True,
    ).start()


def _rotation_extra(db: Session, seller: SellerProfile) -> int:
    settings = get_settings(db)
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
    if paid_like < (settings.rotation_after_orders or 20):
        return 0
    if seller.is_partner:
        return 0
    since = datetime.now(timezone.utc) - timedelta(hours=settings.rotation_lookback_hours or 24)
    recent = (
        db.query(OrderSellerAssignment)
        .filter(
            OrderSellerAssignment.seller_id == seller.id,
            OrderSellerAssignment.scheduled_at >= since,
        )
        .count()
    )
    return min(recent * 6, settings.rotation_max_extra_delay or 40)


def delay_for_seller(db: Session, seller: SellerProfile) -> int:
    refresh_seller_scores(seller)
    delay = delay_for_score(seller.quality_score or 0)
    delay += _rotation_extra(db, seller)
    if seller.is_partner:
        delay = max(0, delay - (seller.partner_level or 1) * 8)
    return delay


def start_distribution(db: Session, order: Order) -> list[OrderSellerAssignment]:
    if order.status not in {OrderStatus.PAID, OrderStatus.SEARCHING}:
        order.status = OrderStatus.SEARCHING

    sellers = matching_sellers(db, order)
    assignments: list[OrderSellerAssignment] = []
    immediate: list[int] = []
    delayed: list[tuple[int, int]] = []

    for seller in sellers:
        delay = delay_for_seller(db, seller)
        existing = (
            db.query(OrderSellerAssignment)
            .filter(
                OrderSellerAssignment.order_id == order.id,
                OrderSellerAssignment.seller_id == seller.id,
            )
            .first()
        )
        if existing:
            continue
        assignment = OrderSellerAssignment(
            order_id=order.id,
            seller_id=seller.id,
            quality_score=seller.quality_score,
            delay_seconds=delay,
            status=AssignmentStatus.SCHEDULED,
        )
        db.add(assignment)
        db.flush()
        assignments.append(assignment)
        if delay <= 0:
            immediate.append(assignment.id)
        else:
            delayed.append((assignment.id, delay))

    for assignment_id in immediate:
        deliver_assignment(db, assignment_id)
    db.commit()

    for assignment_id, delay in delayed:
        schedule_delivery(assignment_id, delay)

    return assignments


def deliver_assignment(db: Session, assignment_id: int) -> None:
    assignment = db.query(OrderSellerAssignment).filter(OrderSellerAssignment.id == assignment_id).first()
    if not assignment or assignment.status == AssignmentStatus.DELIVERED:
        return
    order = db.query(Order).filter(Order.id == assignment.order_id).first()
    assignment.status = AssignmentStatus.DELIVERED
    assignment.delivered_at = datetime.now(timezone.utc)
    if not order or order.status in {
        OrderStatus.COMPLETED,
        OrderStatus.CANCELLED,
        OrderStatus.EXPIRED,
        OrderStatus.SELLER_SELECTED,
        OrderStatus.WAITING_FOR_PAYMENT,
    }:
        return

    seller = db.query(SellerProfile).filter(SellerProfile.id == assignment.seller_id).first()
    if seller and not seller_accepts_new_orders(seller):
        return
    if seller:
        seller.assigned_requests_count = (seller.assigned_requests_count or 0) + 1
        refresh_seller_scores(seller)
        create_notification(
            db,
            user_id=seller.user_id,
            ntype=NotificationType.NEW_REQUEST,
            title="Новый запрос на поиск",
            body=f"Вам доступен заказ #{assignment.order_id}",
            payload={"order_id": assignment.order_id},
        )

"""Seller display rating, strikes, fulfilled-order recount."""

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models import (
    Order,
    OrderStatus,
    PlatformSettings,
    Report,
    ReportReason,
    ReportStatus,
    SellerOffer,
    SellerProfile,
)
from app.services.scoring import refresh_seller_scores


def get_settings(db: Session) -> PlatformSettings:
    row = db.query(PlatformSettings).filter(PlatformSettings.id == 1).first()
    if row:
        return row
    row = PlatformSettings(id=1)
    db.add(row)
    db.flush()
    return row


def compute_display_rating(seller: SellerProfile) -> float:
    prior_n, prior_avg = 2.0, 4.2
    n = seller.user_rating_count or 0
    avg = float(seller.user_rating_avg or 0)
    stars = prior_avg if n <= 0 else (prior_n * prior_avg + n * avg) / (prior_n + n)
    experience = min((seller.completed_orders_count or 0) * 0.025, 0.35)
    reports = (seller.confirmed_reports_count or 0) * 0.4
    false_yes = (seller.false_availability_count or 0) * 0.25
    return round(max(1.0, min(5.0, stars + experience - reports - false_yes)), 2)


def recount_completed_orders(db: Session, seller: SellerProfile) -> None:
    offer_ids = [row.id for row in db.query(SellerOffer.id).filter(SellerOffer.seller_id == seller.id).all()]
    if not offer_ids:
        seller.completed_orders_count = 0
        return
    seller.completed_orders_count = (
        db.query(Order)
        .filter(
            Order.selected_offer_id.in_(offer_ids),
            Order.status.in_([OrderStatus.SELLER_SELECTED, OrderStatus.COMPLETED]),
        )
        .count()
    )


def refresh_reputation(db: Session, seller: SellerProfile) -> None:
    recount_completed_orders(db, seller)
    confirmed = (
        db.query(Report)
        .filter(Report.seller_id == seller.id, Report.status == ReportStatus.CONFIRMED.value)
        .all()
    )
    seller.confirmed_reports_count = len(confirmed)
    seller.false_availability_count = sum(1 for r in confirmed if r.reason == ReportReason.FALSE_AVAILABILITY.value)
    seller.display_rating = compute_display_rating(seller)
    refresh_seller_scores(seller)


def apply_confirmed_report(db: Session, seller: SellerProfile) -> None:
    settings = get_settings(db)
    seller.strike_count = (seller.strike_count or 0) + 1
    if seller.strike_count >= (settings.strike_limit or 3):
        days = settings.strike_ban_days or 30
        seller.new_orders_blocked_until = datetime.now(timezone.utc) + timedelta(days=days)
    refresh_reputation(db, seller)


def seller_accepts_new_orders(seller: SellerProfile) -> bool:
    until = seller.new_orders_blocked_until
    if until is None:
        return True
    if until.tzinfo is None:
        until = until.replace(tzinfo=timezone.utc)
    return until <= datetime.now(timezone.utc)

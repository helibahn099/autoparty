from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Rating, SellerProfile
from app.services.scoring import refresh_seller_scores


def apply_rating(db: Session, seller: SellerProfile) -> None:
    agg = (
        db.query(func.avg(Rating.score), func.count(Rating.id))
        .filter(Rating.seller_id == seller.id)
        .one()
    )
    avg, count = agg
    seller.user_rating_avg = round(float(avg or 0), 2)
    seller.user_rating_count = int(count or 0)
    from app.services.reputation import refresh_reputation

    refresh_reputation(db, seller)


def record_response(seller: SellerProfile, response_seconds: float) -> None:
    prev_n = seller.responded_requests_count or 0
    prev_avg = float(seller.avg_response_seconds or 0)
    new_n = prev_n + 1
    seller.responded_requests_count = new_n
    seller.processed_requests_count = (seller.processed_requests_count or 0) + 1
    seller.avg_response_seconds = ((prev_avg * prev_n) + max(response_seconds, 0)) / new_n
    refresh_seller_scores(seller)

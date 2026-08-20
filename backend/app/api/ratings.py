from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Order, OrderStatus, Rating, SellerOffer, SellerProfile, User
from app.schemas import RatingIn
from app.services.ratings import apply_rating
from app.services.reputation import refresh_reputation

router = APIRouter(prefix="/api/ratings", tags=["ratings"])


@router.post("")
def create_rating(payload: RatingIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == payload.order_id).first()
    if not order or order.client_id != user.id:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    if order.status not in {OrderStatus.SELLER_SELECTED, OrderStatus.COMPLETED}:
        raise HTTPException(status_code=400, detail="Оценить можно после выбора продавца")
    offer = (
        db.query(SellerOffer)
        .filter(SellerOffer.id == order.selected_offer_id, SellerOffer.seller_id == payload.seller_id)
        .first()
    )
    if not offer:
        raise HTTPException(status_code=400, detail="Можно оценить только выбранного продавца")
    existing = db.query(Rating).filter(Rating.order_id == order.id, Rating.seller_id == payload.seller_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Оценка уже оставлена")
    rating = Rating(
        order_id=order.id,
        client_id=user.id,
        seller_id=payload.seller_id,
        score=payload.score,
        comment=payload.comment,
    )
    db.add(rating)
    seller = db.query(SellerProfile).filter(SellerProfile.id == payload.seller_id).first()
    db.flush()
    apply_rating(db, seller)
    refresh_reputation(db, seller)
    if order.status == OrderStatus.SELLER_SELECTED:
        order.status = OrderStatus.COMPLETED
        order.completed_at = datetime.now(timezone.utc)
    db.commit()
    return {
        "ok": True,
        "seller": {
            "id": seller.id,
            "user_rating_avg": seller.user_rating_avg,
            "user_rating_count": seller.user_rating_count,
            "activity_score": seller.activity_score,
        },
    }

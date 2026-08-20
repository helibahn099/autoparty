from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.models import Chat, Order, User
from app.schemas import ProfileUpdateIn
from app.serializers import chat_summary, order_out, user_out

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("")
def get_profile(user: User = Depends(get_current_user)):
    return user_out(user)


@router.patch("")
def update_profile(payload: ProfileUpdateIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if payload.name is not None:
        user.name = payload.name.strip()
    if payload.phone is not None:
        user.phone = payload.phone.strip()
    db.commit()
    db.refresh(user)
    return user_out(user)


@router.get("/orders")
def my_orders(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    since = datetime.now(timezone.utc) - timedelta(days=90)
    orders = (
        db.query(Order)
        .options(
            joinedload(Order.items),
            joinedload(Order.locations),
            joinedload(Order.brand),
            joinedload(Order.model),
        )
        .filter(Order.client_id == user.id, Order.created_at >= since)
        .order_by(Order.created_at.desc())
        .all()
    )
    return [order_out(db, o, user) for o in orders]


@router.get("/chats")
def my_chats(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    chats = (
        db.query(Chat)
        .filter((Chat.client_id == user.id) | (Chat.seller_user_id == user.id))
        .order_by(Chat.last_message_at.desc().nullslast(), Chat.created_at.desc())
        .all()
    )
    return [chat_summary(db, c, user) for c in chats]

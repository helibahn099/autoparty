from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Notification, User

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("")
def list_notifications(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(Notification)
        .filter(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc())
        .limit(100)
        .all()
    )
    unread = db.query(Notification).filter(Notification.user_id == user.id, Notification.is_read.is_(False)).count()
    return {
        "unread": unread,
        "items": [
            {
                "id": n.id,
                "type": n.type.value,
                "title": n.title,
                "body": n.body,
                "payload": n.payload,
                "is_read": n.is_read,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in rows
        ],
    }


@router.post("/{note_id}/read")
def read_one(note_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    note = db.query(Notification).filter(Notification.id == note_id, Notification.user_id == user.id).first()
    if note:
        note.is_read = True
        db.commit()
    return {"ok": True}


@router.post("/read-all")
def read_all(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(Notification).filter(Notification.user_id == user.id, Notification.is_read.is_(False)).update(
        {"is_read": True}
    )
    db.commit()
    return {"ok": True}

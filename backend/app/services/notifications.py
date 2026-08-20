from sqlalchemy.orm import Session

from app.models import Notification, NotificationType
from app.realtime import hub


def create_notification(
    db: Session,
    user_id: int,
    ntype: NotificationType,
    title: str,
    body: str,
    payload: dict | None = None,
) -> Notification:
    note = Notification(
        user_id=user_id,
        type=ntype,
        title=title,
        body=body,
        payload=payload or {},
    )
    db.add(note)
    db.flush()
    hub.send_to_user(
        user_id,
        {
            "event": "notification",
            "data": {
                "id": note.id,
                "type": note.type.value,
                "title": note.title,
                "body": note.body,
                "payload": note.payload,
            },
        },
    )
    return note

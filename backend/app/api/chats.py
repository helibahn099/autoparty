from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Chat, ChatParticipant, Message, MessageAttachment, Notification, NotificationType, User, UserRole
from app.realtime import hub
from app.serializers import chat_summary, message_out
from app.services.notifications import create_notification
from app.services.storage import storage

router = APIRouter(prefix="/api/chats", tags=["chats"])


def _get_chat_for_user(db: Session, chat_id: int, user: User) -> Chat:
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Чат не найден")
    if user.role == UserRole.ADMIN:
        return chat
    if user.id not in {chat.client_id, chat.seller_user_id}:
        raise HTTPException(status_code=403, detail="Нет доступа к чату")
    return chat


@router.get("")
def list_chats(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role == UserRole.ADMIN:
        chats = db.query(Chat).order_by(Chat.last_message_at.desc().nullslast()).all()
    else:
        chats = (
            db.query(Chat)
            .filter((Chat.client_id == user.id) | (Chat.seller_user_id == user.id))
            .order_by(Chat.last_message_at.desc().nullslast())
            .all()
        )
    return [chat_summary(db, c, user) for c in chats]


@router.get("/unread-count")
def unread_count(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    chats = (
        db.query(Chat)
        .filter((Chat.client_id == user.id) | (Chat.seller_user_id == user.id))
        .all()
    )
    total = 0
    conversations = 0
    for chat in chats:
        summary = chat_summary(db, chat, user)
        if summary["unread"] > 0:
            conversations += 1
            total += summary["unread"]
    return {"unread": total, "chats": conversations}


@router.get("/{chat_id}")
def get_chat(chat_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    chat = _get_chat_for_user(db, chat_id, user)
    messages = (
        db.query(Message)
        .filter(Message.chat_id == chat.id)
        .order_by(Message.created_at.asc())
        .all()
    )
    participant = (
        db.query(ChatParticipant)
        .filter(ChatParticipant.chat_id == chat.id, ChatParticipant.user_id == user.id)
        .first()
    )
    if not participant:
        participant = ChatParticipant(chat_id=chat.id, user_id=user.id)
        db.add(participant)
        db.flush()
    participant.last_read_at = datetime.now(timezone.utc)
    notes = (
        db.query(Notification)
        .filter(
            Notification.user_id == user.id,
            Notification.type == NotificationType.NEW_MESSAGE,
            Notification.is_read.is_(False),
        )
        .all()
    )
    for note in notes:
        if (note.payload or {}).get("chat_id") == chat.id:
            note.is_read = True
    db.commit()
    return {
        **chat_summary(db, chat, user),
        "messages": [message_out(m) for m in messages],
    }


@router.post("/{chat_id}/messages")
async def send_message(
    chat_id: int,
    text: str | None = Form(default=None),
    files: list[UploadFile] | None = File(default=None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    chat = _get_chat_for_user(db, chat_id, user)
    if user.role == UserRole.ADMIN:
        raise HTTPException(status_code=400, detail="Администратор только просматривает чаты")
    files = files or []
    clean_text = (text or "").strip()
    if not clean_text and not files:
        raise HTTPException(status_code=400, detail="Введите текст или прикрепите фото")
    if len(clean_text) > 4000:
        raise HTTPException(status_code=400, detail="Сообщение слишком длинное")
    msg = Message(chat_id=chat.id, sender_id=user.id, text=clean_text or None)
    db.add(msg)
    db.flush()
    for upload in files:
        if not upload.filename:
            continue
        key = storage.save_image(upload)
        db.add(
            MessageAttachment(
                message_id=msg.id,
                file_path=key,
                mime_type=upload.content_type or "image/jpeg",
                original_name=upload.filename,
            )
        )
    now = datetime.now(timezone.utc)
    chat.last_message_at = now
    db.commit()
    db.refresh(msg)

    payload = message_out(msg)
    other_id = chat.seller_user_id if user.id == chat.client_id else chat.client_id
    create_notification(
        db,
        user_id=other_id,
        ntype=NotificationType.NEW_MESSAGE,
        title="Новое сообщение",
        body=clean_text[:120] if clean_text else "Фотография",
        payload={"chat_id": chat.id, "order_id": chat.order_id},
    )
    db.commit()
    hub.send_to_user(other_id, {"event": "chat.message", "data": payload})
    hub.send_to_user(user.id, {"event": "chat.message", "data": payload})
    return payload

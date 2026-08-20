from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import User
from app.realtime import hub
from app.services.auth import decode_token

router = APIRouter()


@router.websocket("/api/ws")
async def websocket_endpoint(ws: WebSocket, token: str = Query(default="")):
    payload = decode_token(token)
    if not payload or "sub" not in payload:
        await ws.close(code=4401)
        return
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.id == int(payload["sub"])).first()
    finally:
        db.close()
    if not user or not user.is_active or user.is_blocked:
        await ws.close(code=4401)
        return
    await hub.connect(user.id, ws)
    try:
        await ws.send_json({"event": "connected", "data": {"user_id": user.id}})
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        hub.disconnect(user.id, ws)
    except Exception:
        hub.disconnect(user.id, ws)

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import SellerProfile, SellerStatus, User, UserRole
from app.services.auth import decode_token

bearer = HTTPBearer(auto_error=False)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if creds is None or not creds.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Требуется авторизация")
    payload = decode_token(creds.credentials)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Недействительный токен")
    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user or not user.is_active or user.is_blocked:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Пользователь недоступен")
    return user


def get_optional_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User | None:
    if creds is None or not creds.credentials:
        return None
    payload = decode_token(creds.credentials)
    if not payload or "sub" not in payload:
        return None
    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user or not user.is_active or user.is_blocked:
        return None
    return user


def require_roles(*roles: UserRole):
    def _inner(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Недостаточно прав")
        return user

    return _inner


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Только администратор")
    return user


def require_seller(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> tuple[User, SellerProfile]:
    if user.role != UserRole.SELLER:
        raise HTTPException(status_code=403, detail="Только продавец")
    profile = db.query(SellerProfile).filter(SellerProfile.user_id == user.id).first()
    if not profile:
        raise HTTPException(status_code=403, detail="Профиль продавца не найден")
    if profile.status != SellerStatus.APPROVED:
        raise HTTPException(status_code=403, detail="Продавец ещё не подтверждён")
    return user, profile

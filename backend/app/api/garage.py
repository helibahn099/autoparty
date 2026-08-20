from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.deps import get_current_user
from app.models import User, UserVehicle, VehicleBrand, VehicleModel
from app.schemas import GarageIn
from app.serializers import garage_out

router = APIRouter(prefix="/api/garage", tags=["garage"])


def _load(db: Session, user_id: int):
    return (
        db.query(UserVehicle)
        .options(joinedload(UserVehicle.brand), joinedload(UserVehicle.model))
        .filter(UserVehicle.user_id == user_id)
        .order_by(UserVehicle.is_default.desc(), UserVehicle.id)
        .all()
    )


@router.get("")
def list_garage(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return [garage_out(v) for v in _load(db, user.id)]


@router.post("")
def add_vehicle(payload: GarageIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not payload.brand_id and not (payload.nickname or "").strip():
        raise HTTPException(status_code=400, detail="Укажите марку или название авто")
    if payload.brand_id and not db.query(VehicleBrand).filter(VehicleBrand.id == payload.brand_id).first():
        raise HTTPException(status_code=400, detail="Марка не найдена")
    if payload.model_id and not db.query(VehicleModel).filter(VehicleModel.id == payload.model_id).first():
        raise HTTPException(status_code=400, detail="Модель не найдена")
    existing = (
        db.query(UserVehicle)
        .filter(
            UserVehicle.user_id == user.id,
            UserVehicle.brand_id == payload.brand_id,
            UserVehicle.model_id == payload.model_id,
            UserVehicle.year == payload.year,
        )
        .first()
    )
    if existing:
        return garage_out(existing)
    count = db.query(UserVehicle).filter(UserVehicle.user_id == user.id).count()
    row = UserVehicle(
        user_id=user.id,
        brand_id=payload.brand_id,
        model_id=payload.model_id,
        year=payload.year,
        nickname=(payload.nickname or "").strip() or None,
        is_default=payload.is_default or count == 0,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    row = db.query(UserVehicle).options(joinedload(UserVehicle.brand), joinedload(UserVehicle.model)).filter(UserVehicle.id == row.id).first()
    return garage_out(row)


@router.delete("/{vehicle_id}")
def delete_vehicle(vehicle_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.query(UserVehicle).filter(UserVehicle.id == vehicle_id, UserVehicle.user_id == user.id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Авто не найдено")
    db.delete(row)
    db.commit()
    return {"ok": True}

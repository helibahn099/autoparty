from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.deps import get_current_user, require_admin
from app.models import Chat, Order, Report, ReportReason, ReportStatus, SellerProfile, User, UserRole
from app.schemas import ReportIn, ReportReviewIn
from app.services.audit import write_audit
from app.services.reputation import apply_confirmed_report, refresh_reputation

router = APIRouter(prefix="/api/reports", tags=["reports"])

ALLOWED_REASONS = {r.value for r in ReportReason}


def _report_out(row: Report) -> dict:
    return {
        "id": row.id,
        "reporter_id": row.reporter_id,
        "reporter_name": row.reporter.name if row.reporter else None,
        "seller_id": row.seller_id,
        "seller_name": row.seller.display_name if row.seller else None,
        "order_id": row.order_id,
        "chat_id": row.chat_id,
        "reason": row.reason,
        "comment": row.comment,
        "status": row.status,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "reviewed_at": row.reviewed_at.isoformat() if row.reviewed_at else None,
        "reviewed_by_id": row.reviewed_by_id,
    }


@router.post("")
def create_report(payload: ReportIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != UserRole.CLIENT:
        raise HTTPException(status_code=403, detail="Жалобу может оставить клиент")
    if payload.reason not in ALLOWED_REASONS:
        raise HTTPException(status_code=400, detail="Некорректная причина жалобы")
    seller = db.query(SellerProfile).filter(SellerProfile.id == payload.seller_id).first()
    if not seller:
        raise HTTPException(status_code=404, detail="Продавец не найден")
    if payload.order_id:
        order = db.query(Order).filter(Order.id == payload.order_id, Order.client_id == user.id).first()
        if not order:
            raise HTTPException(status_code=404, detail="Заказ не найден")
    if payload.chat_id:
        chat = db.query(Chat).filter(Chat.id == payload.chat_id, Chat.client_id == user.id).first()
        if not chat:
            raise HTTPException(status_code=404, detail="Чат не найден")
        if chat.seller_id != seller.id:
            raise HTTPException(status_code=400, detail="Продавец не относится к этому чату")
    pending = (
        db.query(Report)
        .filter(
            Report.reporter_id == user.id,
            Report.seller_id == seller.id,
            Report.status == ReportStatus.PENDING.value,
        )
        .first()
    )
    if pending:
        raise HTTPException(status_code=400, detail="Жалоба уже на рассмотрении")
    row = Report(
        reporter_id=user.id,
        seller_id=seller.id,
        order_id=payload.order_id,
        chat_id=payload.chat_id,
        reason=payload.reason,
        comment=payload.comment,
        status=ReportStatus.PENDING.value,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _report_out(row)


@router.get("/mine")
def my_reports(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(Report).filter(Report.reporter_id == user.id).order_by(Report.created_at.desc()).all()
    return [_report_out(r) for r in rows]


@router.get("")
def admin_reports(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    rows = db.query(Report).options(joinedload(Report.seller), joinedload(Report.reporter)).order_by(Report.created_at.desc()).all()
    return [_report_out(r) for r in rows]


@router.patch("/{report_id}")
def review_report(
    report_id: int,
    payload: ReportReviewIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    row = db.query(Report).filter(Report.id == report_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Жалоба не найдена")
    if payload.status not in {ReportStatus.CONFIRMED.value, ReportStatus.REJECTED.value}:
        raise HTTPException(status_code=400, detail="Статус должен быть CONFIRMED или REJECTED")
    was = row.status
    row.status = payload.status
    row.reviewed_at = datetime.now(timezone.utc)
    row.reviewed_by_id = admin.id
    seller = db.query(SellerProfile).filter(SellerProfile.id == row.seller_id).first()
    if payload.status == ReportStatus.CONFIRMED.value and was != ReportStatus.CONFIRMED.value and seller:
        apply_confirmed_report(db, seller)
    elif seller:
        refresh_reputation(db, seller)
    write_audit(
        db,
        admin,
        "REPORT_REVIEWED",
        "report",
        row.id,
        {"status": was},
        {"status": row.status, "note": payload.note},
    )
    db.commit()
    return _report_out(row)


@router.get("/false-answers")
def false_answers(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    rows = (
        db.query(Report)
        .options(joinedload(Report.seller), joinedload(Report.reporter))
        .filter(
            Report.reason == ReportReason.FALSE_AVAILABILITY.value,
            Report.status == ReportStatus.CONFIRMED.value,
        )
        .order_by(Report.created_at.desc())
        .all()
    )
    by_seller: dict[int, dict] = {}
    for row in rows:
        bucket = by_seller.setdefault(
            row.seller_id,
            {
                "seller_id": row.seller_id,
                "seller_name": row.seller.display_name if row.seller else None,
                "count": 0,
                "display_rating": row.seller.display_rating if row.seller else None,
                "reports": [],
            },
        )
        bucket["count"] += 1
        bucket["reports"].append(_report_out(row))
    listed = sorted(by_seller.values(), key=lambda x: x["count"], reverse=True)
    return {"total": len(rows), "sellers": listed}

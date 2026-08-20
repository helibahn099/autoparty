from sqlalchemy.orm import Session

from app.models import AuditLog, User


def write_audit(
    db: Session,
    admin: User,
    action: str,
    target_type: str,
    target_id,
    old_value: dict | None = None,
    new_value: dict | None = None,
) -> AuditLog:
    log = AuditLog(
        admin_id=admin.id,
        action=action,
        target_type=target_type,
        target_id=str(target_id),
        old_value=old_value,
        new_value=new_value,
    )
    db.add(log)
    db.flush()
    return log

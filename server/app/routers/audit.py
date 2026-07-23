import json

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import get_db, require_admin
from app.models import AuditLog, User
from app.schemas import AuditOut

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("", response_model=list[AuditOut])
def list_audit(
    limit: int = 100,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    limit = max(1, min(limit, 1000))
    rows = db.scalars(
        select(AuditLog).order_by(AuditLog.id.desc()).limit(limit)
    ).all()
    out = []
    for row in rows:
        details = None
        if row.details_json:
            try:
                details = json.loads(row.details_json)
            except (TypeError, ValueError):
                details = row.details_json
        out.append(
            AuditOut(
                id=row.id,
                user_email=row.user.email if row.user is not None else None,
                action=row.action,
                entity=row.entity,
                entity_id=row.entity_id,
                details=details,
                created_at=row.created_at,
            )
        )
    return out

import json
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models import AuditLog


def log_action(
    db: Session,
    user_id: Optional[int],
    action: str,
    entity: str,
    entity_id: Any,
    details: Optional[dict] = None,
) -> AuditLog:
    entry = AuditLog(
        user_id=user_id,
        action=action,
        entity=entity,
        entity_id=str(entity_id) if entity_id is not None else "",
        details_json=(
            json.dumps(details, ensure_ascii=False, default=str)
            if details is not None
            else None
        ),
    )
    db.add(entry)
    db.commit()
    return entry

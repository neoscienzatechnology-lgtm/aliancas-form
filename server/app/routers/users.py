from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import audit
from app.deps import get_db, require_admin
from app.models import User, new_uuid
from app.schemas import UserCreate, UserOut
from app.security import hash_password

router = APIRouter(prefix="/api/users", tags=["users"])


@router.post("", response_model=UserOut)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    if db.scalar(select(User).where(User.email == payload.email)):
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")
    user = User(
        uuid=new_uuid(),
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    audit.log_action(
        db, admin.id, "user_create", "user", user.uuid,
        {"email": user.email, "role": user.role},
    )
    return UserOut.model_validate(user)


@router.get("", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    users = db.scalars(select(User).order_by(User.id)).all()
    return [UserOut.model_validate(u) for u in users]

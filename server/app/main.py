from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from app.config import settings
from app.database import SessionLocal, init_db
from app.models import User, new_uuid
from app.routers import audit as audit_router
from app.routers import auth, captures, exams, patients, reports, sync, users
from app.security import hash_password


def bootstrap_admin() -> None:
    db = SessionLocal()
    try:
        if db.scalar(select(User.id).limit(1)) is None:
            admin = User(
                uuid=new_uuid(),
                name=settings.admin_name,
                email=settings.admin_email,
                password_hash=hash_password(settings.admin_password),
                role="admin",
                is_active=True,
            )
            db.add(admin)
            db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    (Path(settings.data_dir) / "captures").mkdir(parents=True, exist_ok=True)
    bootstrap_admin()
    yield


app = FastAPI(title="FootScan", lifespan=lifespan)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(patients.router)
app.include_router(exams.router)
app.include_router(captures.router)
app.include_router(reports.router)
app.include_router(sync.router)
app.include_router(audit_router.router)

(Path(__file__).resolve().parents[2] / "webpanel").mkdir(parents=True, exist_ok=True)
app.mount(
    "/panel",
    StaticFiles(directory=Path(__file__).resolve().parents[2] / "webpanel", html=True),
)


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/panel/")

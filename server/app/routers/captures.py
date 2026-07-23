import json
import mimetypes
import re
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import audit
from app.config import settings
from app.deps import get_current_user, get_db
from app.models import Capture, User, new_uuid, utcnow
from app.processing.pipeline import (
    ProcessingError,
    process_capture,
    recompute_from_landmarks,
    render_overlay,
)
from app.routers.exams import get_exam_or_404
from app.schemas import LANDMARK_KEYS, CaptureOut, LandmarksIn, capture_to_out, parse_measures

router = APIRouter(prefix="/api", tags=["captures"])

FOOT_SIDES = ("left", "right")
VIEWS = ("plantar", "lateral", "dorsal")
ALLOWED_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
CLIENT_UUID_RE = re.compile(
    r"^(?:[0-9a-fA-F]{32}|[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}"
    r"-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})$"
)


def captures_dir() -> Path:
    directory = Path(settings.data_dir) / "captures"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def remove_file(path_str: Optional[str]) -> None:
    if not path_str:
        return
    try:
        Path(path_str).unlink(missing_ok=True)
    except OSError:
        pass


def get_capture_or_404(db: Session, capture_uuid: str) -> Capture:
    capture = db.scalar(select(Capture).where(Capture.uuid == capture_uuid))
    if capture is None:
        raise HTTPException(status_code=404, detail="Captura não encontrada")
    return capture


@router.post("/exams/{exam_uuid}/captures", response_model=CaptureOut)
async def upload_capture(
    exam_uuid: str,
    foot_side: str = Form(...),
    view: str = Form("plantar"),
    client_uuid: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if foot_side not in FOOT_SIDES:
        raise HTTPException(
            status_code=422, detail="foot_side deve ser 'left' ou 'right'"
        )
    if view not in VIEWS:
        raise HTTPException(
            status_code=422, detail="view deve ser 'plantar', 'lateral' ou 'dorsal'"
        )
    if client_uuid:
        if not CLIENT_UUID_RE.fullmatch(client_uuid):
            raise HTTPException(
                status_code=422, detail="client_uuid deve ser um UUID válido"
            )
        existing = db.scalar(select(Capture).where(Capture.uuid == client_uuid))
        if existing is not None:
            return capture_to_out(existing)

    exam = get_exam_or_404(db, exam_uuid)
    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "invalid_image",
                "message": "Arquivo de imagem vazio ou ilegível",
            },
        )
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "invalid_image",
                "message": "Arquivo de imagem muito grande (limite de 20 MB)",
            },
        )

    measures = None
    error_text = None
    processed = False
    if view == "plantar":
        try:
            measures = process_capture(content, foot_side)
            processed = True
        except ProcessingError as exc:
            code = getattr(exc, "code", "invalid_image")
            message = getattr(exc, "message", str(exc))
            if code == "invalid_image":
                raise HTTPException(
                    status_code=400, detail={"code": code, "message": message}
                )
            error_text = f"{code}: {message}"

    replaced_uuid = None
    old = db.scalar(
        select(Capture).where(
            Capture.exam_id == exam.id,
            Capture.foot_side == foot_side,
            Capture.view == view,
        )
    )
    if old is not None:
        replaced_uuid = old.uuid
        remove_file(old.image_path)
        db.delete(old)
        db.flush()

    cap_uuid = client_uuid or new_uuid()
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTS:
        ext = ".jpg"
    dest = captures_dir() / f"{cap_uuid}{ext}"
    dest.write_bytes(content)

    capture = Capture(
        uuid=cap_uuid,
        exam_id=exam.id,
        foot_side=foot_side,
        view=view,
        image_path=str(dest.resolve()),
        processed=processed,
        measures_json=json.dumps(measures) if measures is not None else None,
        error=error_text,
    )
    db.add(capture)
    if processed:
        exam.status = "processed"
        exam.updated_at = utcnow()
    db.commit()
    db.refresh(capture)

    if replaced_uuid:
        audit.log_action(
            db, current_user.id, "capture_delete", "capture", replaced_uuid,
            {"replaced_by": cap_uuid},
        )
    audit.log_action(
        db, current_user.id, "capture_create", "capture", cap_uuid,
        {
            "exam": exam.uuid,
            "foot_side": foot_side,
            "view": view,
            "processed": processed,
        },
    )
    return capture_to_out(capture)


@router.put("/captures/{capture_uuid}/landmarks", response_model=CaptureOut)
def adjust_landmarks(
    capture_uuid: str,
    payload: LandmarksIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    capture = get_capture_or_404(db, capture_uuid)
    measures = parse_measures(capture)
    if measures is None:
        raise HTTPException(
            status_code=400, detail="Captura sem medidas processadas para ajustar"
        )
    unknown = [key for key in payload.landmarks if key not in LANDMARK_KEYS]
    if unknown:
        raise HTTPException(
            status_code=422, detail=f"Landmark desconhecido: {', '.join(unknown)}"
        )
    landmarks = {
        key: [float(value[0]), float(value[1])]
        for key, value in payload.landmarks.items()
    }
    new_measures = recompute_from_landmarks(measures, landmarks)
    capture.measures_json = json.dumps(new_measures)
    capture.manual_landmarks_json = json.dumps(landmarks)
    capture.updated_at = utcnow()
    exam = capture.exam
    exam.status = "reviewed"
    exam.updated_at = utcnow()
    db.commit()
    db.refresh(capture)
    audit.log_action(
        db, current_user.id, "landmarks_adjust", "capture", capture.uuid,
        {"exam": exam.uuid, "landmarks": list(landmarks.keys())},
    )
    return capture_to_out(capture)


@router.get("/captures/{capture_uuid}/image")
def get_capture_image(
    capture_uuid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    capture = get_capture_or_404(db, capture_uuid)
    path = Path(capture.image_path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Arquivo de imagem não encontrado")
    media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return FileResponse(path, media_type=media_type)


@router.get("/captures/{capture_uuid}/overlay")
def get_capture_overlay(
    capture_uuid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    capture = get_capture_or_404(db, capture_uuid)
    measures = parse_measures(capture)
    if measures is None:
        raise HTTPException(status_code=400, detail="Captura sem medidas processadas")
    path = Path(capture.image_path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Arquivo de imagem não encontrado")
    try:
        png_bytes = render_overlay(path.read_bytes(), measures)
    except ProcessingError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "code": getattr(exc, "code", "invalid_image"),
                "message": getattr(exc, "message", str(exc)),
            },
        )
    return Response(content=png_bytes, media_type="image/png")

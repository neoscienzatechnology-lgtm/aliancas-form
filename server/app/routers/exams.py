from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app import audit
from app.deps import get_current_user, get_db
from app.models import Exam, Patient, User, new_uuid
from app.schemas import (
    ExamCreate,
    ExamDetail,
    ExamOut,
    PreviousExamOut,
    compute_asymmetry,
    exam_to_out,
    measures_by_side,
)

router = APIRouter(prefix="/api/exams", tags=["exams"])


def get_exam_or_404(db: Session, exam_uuid: str) -> Exam:
    exam = db.scalar(select(Exam).where(Exam.uuid == exam_uuid))
    if exam is None:
        raise HTTPException(status_code=404, detail="Exame não encontrado")
    return exam


def find_previous_exam(db: Session, exam: Exam) -> Optional[PreviousExamOut]:
    stmt = (
        select(Exam)
        .where(
            Exam.patient_id == exam.patient_id,
            Exam.id != exam.id,
            or_(
                Exam.created_at < exam.created_at,
                and_(Exam.created_at == exam.created_at, Exam.id < exam.id),
            ),
        )
        .order_by(Exam.created_at.desc(), Exam.id.desc())
    )
    for previous in db.scalars(stmt):
        sides = measures_by_side(previous)
        if sides["left"] or sides["right"]:
            return PreviousExamOut(
                uuid=previous.uuid,
                created_at=previous.created_at,
                measures_by_side=sides,
            )
    return None


@router.post("", response_model=ExamOut)
def create_exam(
    payload: ExamCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    patient = db.scalar(
        select(Patient).where(
            Patient.uuid == payload.patient_uuid, Patient.deleted_at.is_(None)
        )
    )
    if patient is None:
        raise HTTPException(status_code=404, detail="Paciente não encontrado")
    if patient.consent_accepted_at is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "Paciente sem consentimento LGPD registrado. "
                "Registre o consentimento antes de criar o exame."
            ),
        )
    exam = Exam(
        uuid=new_uuid(),
        patient_id=patient.id,
        professional_id=current_user.id,
        status="draft",
        notes=payload.notes,
    )
    db.add(exam)
    db.commit()
    db.refresh(exam)
    audit.log_action(
        db, current_user.id, "exam_create", "exam", exam.uuid,
        {"patient": patient.uuid},
    )
    return exam_to_out(exam)


@router.get("", response_model=list[ExamOut])
def list_exams(
    patient_uuid: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Exam).order_by(Exam.created_at.desc(), Exam.id.desc())
    if patient_uuid:
        stmt = stmt.join(Exam.patient).where(Patient.uuid == patient_uuid)
    return [exam_to_out(exam) for exam in db.scalars(stmt).all()]


@router.get("/{exam_uuid}", response_model=ExamDetail)
def get_exam(
    exam_uuid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    exam = get_exam_or_404(db, exam_uuid)
    base = exam_to_out(exam)
    return ExamDetail(
        **base.model_dump(),
        asymmetry=compute_asymmetry(exam),
        previous_exam=find_previous_exam(db, exam),
    )


@router.delete("/{exam_uuid}")
def delete_exam(
    exam_uuid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    exam = get_exam_or_404(db, exam_uuid)
    exam_id = exam.uuid
    n_captures = len(exam.captures)
    for capture in exam.captures:
        try:
            if capture.image_path:
                Path(capture.image_path).unlink(missing_ok=True)
        except OSError:
            pass
    db.delete(exam)
    db.commit()
    audit.log_action(
        db, current_user.id, "exam_delete", "exam", exam_id,
        {"captures": n_captures},
    )
    return {"ok": True}

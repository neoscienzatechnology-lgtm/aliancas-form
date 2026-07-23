from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app import audit
from app.deps import get_current_user, get_db
from app.models import Exam, Patient, User, new_uuid, utcnow
from app.schemas import (
    ConsentIn,
    HistoryItem,
    PatientIn,
    PatientOut,
    measures_by_side,
)

router = APIRouter(prefix="/api/patients", tags=["patients"])


def get_patient_or_404(db: Session, patient_uuid: str) -> Patient:
    patient = db.scalar(
        select(Patient).where(Patient.uuid == patient_uuid, Patient.deleted_at.is_(None))
    )
    if patient is None:
        raise HTTPException(status_code=404, detail="Paciente não encontrado")
    return patient


@router.get("", response_model=list[PatientOut])
def list_patients(
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Patient).where(Patient.deleted_at.is_(None))
    if search:
        like = f"%{search}%"
        stmt = stmt.where(or_(Patient.name.ilike(like), Patient.document.ilike(like)))
    stmt = stmt.order_by(Patient.name.asc(), Patient.id.asc())
    return [PatientOut.model_validate(p) for p in db.scalars(stmt).all()]


@router.post("", response_model=PatientOut)
def create_patient(
    payload: PatientIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    patient = Patient(
        uuid=new_uuid(), created_by_id=current_user.id, **payload.model_dump()
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)
    audit.log_action(
        db, current_user.id, "patient_create", "patient", patient.uuid,
        {"name": patient.name},
    )
    return PatientOut.model_validate(patient)


@router.get("/{patient_uuid}", response_model=PatientOut)
def get_patient(
    patient_uuid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return PatientOut.model_validate(get_patient_or_404(db, patient_uuid))


@router.put("/{patient_uuid}", response_model=PatientOut)
def update_patient(
    patient_uuid: str,
    payload: PatientIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    patient = get_patient_or_404(db, patient_uuid)
    for field, value in payload.model_dump().items():
        setattr(patient, field, value)
    patient.updated_at = utcnow()
    db.commit()
    db.refresh(patient)
    audit.log_action(
        db, current_user.id, "patient_update", "patient", patient.uuid,
        {"name": patient.name},
    )
    return PatientOut.model_validate(patient)


@router.delete("/{patient_uuid}")
def delete_patient(
    patient_uuid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    patient = get_patient_or_404(db, patient_uuid)
    patient.deleted_at = utcnow()
    db.commit()
    audit.log_action(
        db, current_user.id, "patient_delete", "patient", patient.uuid,
        {"name": patient.name},
    )
    return {"ok": True}


@router.post("/{patient_uuid}/consent", response_model=PatientOut)
def register_consent(
    patient_uuid: str,
    payload: ConsentIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    patient = get_patient_or_404(db, patient_uuid)
    patient.consent_accepted_at = utcnow()
    patient.consent_version = payload.version
    patient.updated_at = utcnow()
    db.commit()
    db.refresh(patient)
    audit.log_action(
        db, current_user.id, "consent", "patient", patient.uuid,
        {"version": payload.version},
    )
    return PatientOut.model_validate(patient)


@router.get("/{patient_uuid}/history", response_model=list[HistoryItem])
def patient_history(
    patient_uuid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    patient = get_patient_or_404(db, patient_uuid)
    exams = db.scalars(
        select(Exam)
        .where(Exam.patient_id == patient.id)
        .order_by(Exam.created_at.asc(), Exam.id.asc())
    ).all()
    return [
        HistoryItem(
            exam_uuid=exam.uuid,
            created_at=exam.created_at,
            status=exam.status,
            measures_by_side=measures_by_side(exam),
        )
        for exam in exams
    ]

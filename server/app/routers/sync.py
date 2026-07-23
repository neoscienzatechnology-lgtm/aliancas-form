from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import audit
from app.deps import get_current_user, get_db
from app.models import Exam, Patient, User, utcnow
from app.schemas import SyncBatchIn, SyncBatchOut, SyncCounts

router = APIRouter(prefix="/api/sync", tags=["sync"])

PATIENT_FIELDS = (
    "name",
    "birth_date",
    "sex",
    "document",
    "phone",
    "email",
    "notes",
    "consent_accepted_at",
    "consent_version",
)


@router.post("/batch", response_model=SyncBatchOut)
def sync_batch(
    payload: SyncBatchIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    patients_created = patients_updated = 0
    exams_created = exams_updated = 0

    for item in payload.patients:
        data = item.model_dump(exclude_unset=True)
        data.pop("uuid", None)
        patient = db.scalar(select(Patient).where(Patient.uuid == item.uuid))
        if patient is None:
            patient = Patient(uuid=item.uuid, created_by_id=current_user.id)
            for field in PATIENT_FIELDS:
                if field in data:
                    setattr(patient, field, data[field])
            db.add(patient)
            patients_created += 1
        else:
            for field in PATIENT_FIELDS:
                if field in data:
                    setattr(patient, field, data[field])
            patient.updated_at = utcnow()
            patients_updated += 1
    db.flush()

    for item in payload.exams:
        patient = db.scalar(select(Patient).where(Patient.uuid == item.patient_uuid))
        if patient is None:
            raise HTTPException(
                status_code=400,
                detail=f"Paciente {item.patient_uuid} não encontrado para sincronizar exame",
            )
        exam = db.scalar(select(Exam).where(Exam.uuid == item.uuid))
        if exam is None:
            exam = Exam(
                uuid=item.uuid,
                patient_id=patient.id,
                professional_id=current_user.id,
                status="draft",
                notes=item.notes,
            )
            if item.created_at is not None:
                exam.created_at = item.created_at
            db.add(exam)
            exams_created += 1
        else:
            exam.patient_id = patient.id
            if item.notes is not None:
                exam.notes = item.notes
            exam.updated_at = utcnow()
            exams_updated += 1

    db.commit()

    result = SyncBatchOut(
        patients=SyncCounts(created=patients_created, updated=patients_updated),
        exams=SyncCounts(created=exams_created, updated=exams_updated),
    )
    audit.log_action(
        db, current_user.id, "sync", "sync", "batch", result.model_dump()
    )
    return result

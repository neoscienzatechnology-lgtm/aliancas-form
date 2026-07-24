import json
from datetime import date, datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: str
    name: str
    email: str
    role: str
    is_active: bool
    created_at: datetime


class LoginIn(BaseModel):
    email: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    role: Literal["admin", "professional"] = "professional"


class PatientIn(BaseModel):
    name: str
    birth_date: Optional[date] = None
    sex: Optional[Literal["F", "M", "outro"]] = None
    document: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    notes: Optional[str] = None


class PatientOut(PatientIn):
    model_config = ConfigDict(from_attributes=True)

    uuid: str
    consent_accepted_at: Optional[datetime] = None
    consent_version: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class ConsentIn(BaseModel):
    version: str = "v1"


class CaptureOut(BaseModel):
    uuid: str
    foot_side: str
    view: str
    processed: bool
    error: Optional[str] = None
    measures: Optional[dict[str, Any]] = None
    manually_adjusted: bool = False
    created_at: datetime


class ExamCreate(BaseModel):
    patient_uuid: str
    notes: Optional[str] = None


class ExamOut(BaseModel):
    uuid: str
    patient_uuid: str
    professional: UserOut
    status: str
    notes: Optional[str] = None
    created_at: datetime
    captures: list[CaptureOut] = []


class AsymmetryOut(BaseModel):
    length_mm: float
    forefoot_width_mm: float
    midfoot_width_mm: float
    heel_width_mm: float
    plantar_area_cm2: float


class PreviousExamOut(BaseModel):
    uuid: str
    created_at: datetime
    measures_by_side: dict[str, Optional[dict[str, Any]]]


class ExamDetail(ExamOut):
    asymmetry: Optional[AsymmetryOut] = None
    previous_exam: Optional[PreviousExamOut] = None


class HistoryItem(BaseModel):
    exam_uuid: str
    created_at: datetime
    status: str
    measures_by_side: dict[str, Optional[dict[str, Any]]]


LANDMARK_KEYS = (
    "toe",
    "heel",
    "forefoot_a",
    "forefoot_b",
    "midfoot_a",
    "midfoot_b",
    "heel_a",
    "heel_b",
)


class LandmarksIn(BaseModel):
    landmarks: dict[str, tuple[float, float]]


class SyncPatientIn(PatientIn):
    uuid: str
    consent_accepted_at: Optional[datetime] = None
    consent_version: Optional[str] = None


class SyncExamIn(BaseModel):
    uuid: str
    patient_uuid: str
    notes: Optional[str] = None
    created_at: Optional[datetime] = None


class SyncBatchIn(BaseModel):
    patients: list[SyncPatientIn] = []
    exams: list[SyncExamIn] = []


class SyncCounts(BaseModel):
    created: int = 0
    updated: int = 0


class SyncBatchOut(BaseModel):
    patients: SyncCounts
    exams: SyncCounts


class AuditOut(BaseModel):
    id: int
    user_email: Optional[str] = None
    action: str
    entity: str
    entity_id: str
    details: Optional[Any] = None
    created_at: datetime


MEASURE_KEYS = (
    "length_mm",
    "forefoot_width_mm",
    "midfoot_width_mm",
    "heel_width_mm",
    "plantar_area_cm2",
)


def parse_measures(capture) -> Optional[dict]:
    if not capture.measures_json:
        return None
    try:
        return json.loads(capture.measures_json)
    except (TypeError, ValueError):
        return None


def capture_to_out(capture) -> CaptureOut:
    measures = parse_measures(capture)
    return CaptureOut(
        uuid=capture.uuid,
        foot_side=capture.foot_side,
        view=capture.view,
        processed=capture.processed,
        error=capture.error,
        measures=measures,
        manually_adjusted=bool(measures.get("manually_adjusted")) if measures else False,
        created_at=capture.created_at,
    )


def exam_to_out(exam) -> ExamOut:
    return ExamOut(
        uuid=exam.uuid,
        patient_uuid=exam.patient.uuid,
        professional=UserOut.model_validate(exam.professional),
        status=exam.status,
        notes=exam.notes,
        created_at=exam.created_at,
        captures=[capture_to_out(c) for c in exam.captures],
    )


def measures_by_side(exam) -> dict[str, Optional[dict]]:
    result: dict[str, Optional[dict]] = {"left": None, "right": None}
    for capture in exam.captures:
        if capture.view != "plantar" or not capture.processed:
            continue
        measures = parse_measures(capture)
        if measures and capture.foot_side in result:
            result[capture.foot_side] = measures
    return result


def compute_asymmetry(exam) -> Optional[AsymmetryOut]:
    sides = measures_by_side(exam)
    left, right = sides["left"], sides["right"]
    if not left or not right:
        return None
    try:
        values = {
            key: round(float(left[key]) - float(right[key]), 2) for key in MEASURE_KEYS
        }
    except (KeyError, TypeError, ValueError):
        return None
    return AsymmetryOut(**values)

import re
import unicodedata
from pathlib import Path

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app import audit
from app.deps import get_current_user, get_db
from app.models import User
from app.processing.pipeline import render_overlay
from app.reportgen.pdf import build_exam_pdf
from app.routers.exams import find_previous_exam, get_exam_or_404
from app.schemas import compute_asymmetry, parse_measures

router = APIRouter(prefix="/api", tags=["reports"])


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()
    return value or "paciente"


@router.get("/exams/{exam_uuid}/report.pdf")
def exam_report_pdf(
    exam_uuid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    exam = get_exam_or_404(db, exam_uuid)
    patient = exam.patient
    professional = exam.professional

    captures_with_measures = []
    overlay_pngs: dict[str, bytes] = {}
    for capture in exam.captures:
        measures = parse_measures(capture)
        if capture.view != "plantar" or measures is None:
            continue
        captures_with_measures.append((capture, measures))
        path = Path(capture.image_path)
        if path.is_file():
            try:
                overlay_pngs[capture.foot_side] = render_overlay(
                    path.read_bytes(), measures
                )
            except Exception:
                pass

    asymmetry = compute_asymmetry(exam)
    previous = find_previous_exam(db, exam)
    pdf_bytes = build_exam_pdf(
        exam,
        patient,
        professional,
        captures_with_measures,
        asymmetry.model_dump() if asymmetry is not None else None,
        previous.model_dump(mode="json") if previous is not None else None,
        overlay_pngs,
    )

    filename = "relatorio_{}_{}.pdf".format(
        slugify(patient.name), exam.created_at.strftime("%Y-%m-%d")
    )
    audit.log_action(
        db, current_user.id, "report_download", "exam", exam.uuid,
        {"filename": filename},
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

"""Geração do relatório PDF do exame (A4 retrato, pt-BR, reportlab)."""

import io
from datetime import date, datetime
from xml.sax.saxutils import escape as _xml_escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    Image,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

REPORT_TITLE = "Relatório de Avaliação do Pé — FootScan"
FOOTER_DISCLAIMER = (
    "Documento de apoio à avaliação profissional; não constitui diagnóstico."
)
FOOTER_LGPD = (
    "Dados pessoais tratados conforme a LGPD (Lei nº 13.709/2018), com consentimento "
    "do titular, exclusivamente para avaliação e documentação clínica."
)

MEASURE_ROWS = [
    ("length_mm", "Comprimento", "mm", 1),
    ("forefoot_width_mm", "Largura do antepé", "mm", 1),
    ("midfoot_width_mm", "Largura do mediopé", "mm", 1),
    ("heel_width_mm", "Largura do calcanhar", "mm", 1),
    ("plantar_area_cm2", "Área plantar", "cm²", 1),
    ("axis_angle_deg", "Ângulo do eixo", "°", 1),
]
ASYMMETRY_ROWS = MEASURE_ROWS[:5]

FOOT_SIDE_LABELS = {"left": "Pé esquerdo", "right": "Pé direito"}
FOOT_SIDE_SHORT = {"left": "Esquerdo", "right": "Direito"}
SEX_LABELS = {"F": "Feminino", "M": "Masculino", "outro": "Outro"}

_HEADER_BG = colors.HexColor("#e3f2fd")
_GRID_COLOR = colors.HexColor("#b0bec5")
_HEADING_COLOR = colors.HexColor("#1d4e89")

_CONTENT_WIDTH = A4[0] - 30 * mm


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _fmt_number(value, decimals=1, signed=False):
    number = _to_float(value)
    if number is None:
        return "—"
    pattern = "{:+.%df}" % decimals if signed else "{:.%df}" % decimals
    return pattern.format(number).replace(".", ",")


def _fmt_measure(value, unit, decimals=1, signed=False):
    text = _fmt_number(value, decimals=decimals, signed=signed)
    if text == "—":
        return text
    return f"{text} {unit}"


def _fmt_date(value, with_time=False):
    if value is None:
        return "—"
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return _xml_escape(value)
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y %H:%M" if with_time else "%d/%m/%Y")
    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")
    return _xml_escape(str(value))


def _text(value):
    """Texto livre (vindo do usuário) seguro para Paragraph: escapa marcação."""
    if value is None:
        return "—"
    text = str(value).strip()
    return _xml_escape(text) if text else "—"


def _styles():
    return {
        "title": ParagraphStyle(
            "FSTitle",
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=19,
            alignment=TA_CENTER,
            textColor=_HEADING_COLOR,
        ),
        "heading": ParagraphStyle(
            "FSHeading",
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            spaceBefore=6 * mm,
            spaceAfter=2 * mm,
            textColor=_HEADING_COLOR,
        ),
        "body": ParagraphStyle(
            "FSBody",
            fontName="Helvetica",
            fontSize=9,
            leading=12,
        ),
        "note": ParagraphStyle(
            "FSNote",
            fontName="Helvetica-Oblique",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#546e7a"),
            spaceBefore=1 * mm,
        ),
    }


def _table_style(with_header=True, numeric_from_col=None):
    commands = [
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.4, _GRID_COLOR),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]
    if with_header:
        commands += [
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("BACKGROUND", (0, 0), (-1, 0), _HEADER_BG),
        ]
    if numeric_from_col is not None:
        commands.append(
            ("ALIGN", (numeric_from_col, 1 if with_header else 0), (-1, -1), "RIGHT")
        )
    return TableStyle(commands)


def _info_block(exam, patient, professional, styles):
    prof_name = _text(getattr(professional, "name", None))
    prof_email = getattr(professional, "email", None)
    if prof_email and prof_name != "—":
        prof_text = f"{prof_name} ({_xml_escape(str(prof_email))})"
    elif prof_email:
        prof_text = _xml_escape(str(prof_email))
    else:
        prof_text = prof_name

    sex_raw = getattr(patient, "sex", None)
    rows = [
        ("Paciente", _text(getattr(patient, "name", None))),
        ("Data de nascimento", _fmt_date(getattr(patient, "birth_date", None))),
        ("Sexo", SEX_LABELS.get(sex_raw, _text(sex_raw))),
        ("Documento", _text(getattr(patient, "document", None))),
        ("Profissional", prof_text),
        ("Data do exame", _fmt_date(getattr(exam, "created_at", None), with_time=True)),
    ]
    notes = getattr(exam, "notes", None)
    if notes:
        rows.append(("Observações", _text(notes)))

    data = [
        [Paragraph(f"<b>{label}</b>", styles["body"]), Paragraph(value, styles["body"])]
        for label, value in rows
    ]
    table = Table(data, colWidths=[42 * mm, _CONTENT_WIDTH - 42 * mm])
    table.setStyle(_table_style(with_header=False))
    return table


def _overlay_image(png_bytes, max_width=95 * mm, max_height=110 * mm):
    if not png_bytes:
        return None
    try:
        reader = ImageReader(io.BytesIO(png_bytes))
        img_w, img_h = reader.getSize()
        if not img_w or not img_h:
            return None
        scale = min(max_width / float(img_w), max_height / float(img_h))
        return Image(
            io.BytesIO(png_bytes), width=img_w * scale, height=img_h * scale
        )
    except Exception:
        return None


def _measures_table(measures):
    data = [["Medida", "Valor"]]
    for key, label, unit, decimals in MEASURE_ROWS:
        data.append([label, _fmt_measure(measures.get(key), unit, decimals)])
    table = Table(data, colWidths=[80 * mm, 45 * mm], hAlign="LEFT")
    table.setStyle(_table_style(numeric_from_col=1))
    return table


def _foot_section(label, measures, overlay_png, styles):
    elements = [Paragraph(label, styles["heading"])]
    image = _overlay_image(overlay_png)
    if image is not None:
        image.hAlign = "LEFT"
        elements.append(image)
        elements.append(Spacer(1, 2 * mm))
    else:
        elements.append(
            Paragraph("Imagem do overlay indisponível.", styles["note"])
        )
    elements.append(_measures_table(measures))
    if measures.get("manually_adjusted"):
        elements.append(
            Paragraph(
                "Medidas ajustadas manualmente pelo profissional.", styles["note"]
            )
        )
    quality = measures.get("quality")
    warnings = quality.get("warnings") if isinstance(quality, dict) else None
    if warnings:
        elements.append(
            Paragraph(
                "Avisos: " + "; ".join(_xml_escape(str(w)) for w in warnings),
                styles["note"],
            )
        )
    return elements


def _collect_feet(captures_with_measures):
    """Normaliza a lista de (capture, measures) em seções ordenadas e coleta falhas."""
    sections = []
    failures = []
    for item in captures_with_measures or []:
        try:
            capture, measures = item
        except (TypeError, ValueError):
            continue
        side = getattr(capture, "foot_side", None)
        view = getattr(capture, "view", "plantar") or "plantar"
        label = FOOT_SIDE_LABELS.get(side, f"Pé ({_text(side)})")
        if view != "plantar":
            label = f"{label} — vista {view}"
        if isinstance(measures, dict) and measures:
            sections.append({"side": side, "view": view, "label": label, "measures": measures})
        else:
            error = getattr(capture, "error", None)
            if error:
                failures.append(f"{label}: processamento falhou ({_text(error)}).")
            else:
                failures.append(f"{label}: sem medidas processadas.")
    order = {"left": 0, "right": 1}
    sections.sort(key=lambda s: (order.get(s["side"], 2), 0 if s["view"] == "plantar" else 1))
    return sections, failures


def _asymmetry_section(asymmetry, styles):
    if not isinstance(asymmetry, dict):
        return []
    rows = []
    for key, label, unit, decimals in ASYMMETRY_ROWS:
        value = asymmetry.get(key)
        if _to_float(value) is None:
            continue
        rows.append([label, _fmt_measure(value, unit, decimals, signed=True)])
    if not rows:
        return []
    table = Table(
        [["Medida", "Diferença (E - D)"]] + rows,
        colWidths=[80 * mm, 45 * mm],
        hAlign="LEFT",
    )
    table.setStyle(_table_style(numeric_from_col=1))
    return [
        Paragraph("Assimetria (esquerdo - direito)", styles["heading"]),
        table,
        Paragraph(
            "Valores positivos indicam medida maior no pé esquerdo.", styles["note"]
        ),
    ]


def _previous_section(previous, current_by_side, styles):
    if not isinstance(previous, dict):
        return []
    prev_by_side = previous.get("measures_by_side")
    if not isinstance(prev_by_side, dict):
        prev_by_side = {}
    rows = []
    for key, label, unit, decimals in MEASURE_ROWS:
        for side in ("left", "right"):
            current = current_by_side.get(side)
            prev = prev_by_side.get(side)
            if not isinstance(current, dict) or not isinstance(prev, dict):
                continue
            current_value = _to_float(current.get(key))
            prev_value = _to_float(prev.get(key))
            if current_value is None or prev_value is None:
                continue
            rows.append(
                [
                    label,
                    FOOT_SIDE_SHORT.get(side, _text(side)),
                    _fmt_measure(prev_value, unit, decimals),
                    _fmt_measure(current_value, unit, decimals),
                    _fmt_measure(current_value - prev_value, unit, decimals, signed=True),
                ]
            )
    prev_date = _fmt_date(previous.get("created_at"))
    title = "Comparação com exame anterior"
    if prev_date != "—":
        title = f"{title} ({prev_date})"
    elements = [Paragraph(title, styles["heading"])]
    if not rows:
        elements.append(
            Paragraph(
                "Sem medidas comparáveis com o exame anterior.", styles["note"]
            )
        )
        return elements
    table = Table(
        [["Medida", "Pé", "Anterior", "Atual", "Diferença"]] + rows,
        colWidths=[52 * mm, 24 * mm, 32 * mm, 32 * mm, 32 * mm],
        hAlign="LEFT",
    )
    table.setStyle(_table_style(numeric_from_col=2))
    elements.append(table)
    return elements


def _draw_footer(canvas, doc):
    canvas.saveState()
    width = A4[0]
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#607d8b"))
    canvas.drawCentredString(width / 2.0, 16.5 * mm, FOOTER_DISCLAIMER)
    canvas.drawCentredString(width / 2.0, 13 * mm, FOOTER_LGPD)
    canvas.drawCentredString(width / 2.0, 9.5 * mm, f"Página {canvas.getPageNumber()}")
    canvas.restoreState()


def build_exam_pdf(
    exam,
    patient,
    professional,
    captures_with_measures,
    asymmetry,
    previous,
    overlay_pngs: "dict[str, bytes]",
) -> bytes:
    """Monta o PDF do relatório do exame e retorna os bytes."""
    overlay_pngs = overlay_pngs or {}
    styles = _styles()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=26 * mm,
        title=REPORT_TITLE,
        author="FootScan",
    )

    story = [
        Paragraph(REPORT_TITLE, styles["title"]),
        Spacer(1, 4 * mm),
        _info_block(exam, patient, professional, styles),
    ]

    sections, failures = _collect_feet(captures_with_measures)

    if not sections:
        story.append(Spacer(1, 4 * mm))
        story.append(
            Paragraph(
                "Nenhuma medida processada disponível para este exame.",
                styles["body"],
            )
        )
    for section in sections:
        overlay_png = overlay_pngs.get(section["side"]) if section["view"] == "plantar" else None
        story.append(
            KeepTogether(
                _foot_section(section["label"], section["measures"], overlay_png, styles)
            )
        )
    for failure in failures:
        story.append(Paragraph(failure, styles["note"]))

    asym_elements = _asymmetry_section(asymmetry, styles)
    if asym_elements:
        story.append(KeepTogether(asym_elements))

    current_by_side = {
        s["side"]: s["measures"]
        for s in sections
        if s["view"] == "plantar" and s["side"] in ("left", "right")
    }
    prev_elements = _previous_section(previous, current_by_side, styles)
    if prev_elements:
        story.append(KeepTogether(prev_elements))

    doc.build(story, onFirstPage=_draw_footer, onLaterPages=_draw_footer)
    return buffer.getvalue()

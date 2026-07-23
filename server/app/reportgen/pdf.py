"""Geração do relatório PDF do exame (A4 retrato, pt-BR, reportlab).

Identidade visual conforme o Manual de Marca Palmilha Inteligente:
Azul Petróleo #0A5B7E, Turquesa #1EC7E6/#49D7EE, Vermelho Destaque #D73045,
Cinza Institucional #7E8494; tipografia Montserrat (títulos) + Inter (texto).
"""

import io
from datetime import date, datetime
from pathlib import Path
from xml.sax.saxutils import escape as _xml_escape

from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

_FONT_DIR = Path(__file__).with_name("fonts")
try:
    pdfmetrics.registerFont(TTFont("Montserrat-Bold", str(_FONT_DIR / "Montserrat-700.ttf")))
    pdfmetrics.registerFont(TTFont("Montserrat-SemiBold", str(_FONT_DIR / "Montserrat-600.ttf")))
    pdfmetrics.registerFont(TTFont("Inter", str(_FONT_DIR / "Inter-400.ttf")))
    pdfmetrics.registerFont(TTFont("Inter-SemiBold", str(_FONT_DIR / "Inter-600.ttf")))
    registerFontFamily(
        "Inter", normal="Inter", bold="Inter-SemiBold",
        italic="Inter", boldItalic="Inter-SemiBold",
    )
    _F_TITLE = "Montserrat-Bold"
    _F_HEAD = "Montserrat-SemiBold"
    _F_BODY = "Inter"
    _F_BOLD = "Inter-SemiBold"
    _F_NOTE = "Inter"
except Exception:  # fontes ausentes: mantém o relatório funcional
    _F_TITLE = _F_HEAD = _F_BOLD = "Helvetica-Bold"
    _F_BODY = "Helvetica"
    _F_NOTE = "Helvetica-Oblique"

BRAND_NAME = "Palmilha Inteligente"
BRAND_SLOGAN = "Você, livre das dores!"
REPORT_TITLE = f"Relatório de Avaliação do Pé — {BRAND_NAME}"
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

_PETROL = colors.HexColor("#0a5b7e")       # Azul Petróleo
_TURQUOISE = colors.HexColor("#1ec7e6")    # Turquesa Principal
_TURQUOISE_2 = colors.HexColor("#49d7ee")  # Turquesa Secundário
_RED = colors.HexColor("#d73045")          # Vermelho Destaque
_GRAY = colors.HexColor("#7e8494")         # Cinza Institucional

_HEADER_BG = colors.HexColor("#e6f6fb")
_GRID_COLOR = colors.HexColor("#b9d9e6")
_HEADING_COLOR = _PETROL

_CONTENT_WIDTH = A4[0] - 30 * mm

_LOGO_PATH = Path(__file__).with_name("assets") / "logo.png"


def _brand_header():
    """Cabeçalho da marca: logotipo oficial (assinatura completa do manual)."""
    if _LOGO_PATH.exists():
        try:
            reader = ImageReader(str(_LOGO_PATH))
            img_w, img_h = reader.getSize()
            width = 58 * mm
            height = width * img_h / float(img_w)
            image = Image(str(_LOGO_PATH), width=width, height=height)
            image.hAlign = "CENTER"
            return image
        except Exception:
            pass
    # fallback textual caso o asset não esteja disponível
    d = Drawing(_CONTENT_WIDTH, 14 * mm)
    d.add(String(_CONTENT_WIDTH / 2.0, 7 * mm, "PALMILHA",
                 fontName=_F_TITLE, fontSize=17, fillColor=_PETROL, textAnchor="middle"))
    d.add(String(_CONTENT_WIDTH / 2.0, 2.5 * mm, " ".join("INTELIGENTE"),
                 fontName=_F_HEAD, fontSize=9, fillColor=_TURQUOISE, textAnchor="middle"))
    return d


def _tricolor_rule():
    """Régua divisória tricolor do manual de marca (petróleo / vermelho / turquesa)."""
    d = Drawing(_CONTENT_WIDTH, 1.4 * mm)
    w = _CONTENT_WIDTH
    d.add(Rect(0, 0, w * 0.62, 1.1 * mm, fillColor=_PETROL, strokeColor=None))
    d.add(Rect(w * 0.62, 0, w * 0.12, 1.1 * mm, fillColor=_RED, strokeColor=None))
    d.add(Rect(w * 0.74, 0, w * 0.26, 1.1 * mm, fillColor=_TURQUOISE, strokeColor=None))
    return d


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
            fontName=_F_TITLE,
            fontSize=14,
            leading=18,
            alignment=TA_CENTER,
            textColor=_HEADING_COLOR,
        ),
        "heading": ParagraphStyle(
            "FSHeading",
            fontName=_F_HEAD,
            fontSize=12,
            leading=15,
            spaceBefore=6 * mm,
            spaceAfter=2 * mm,
            textColor=_HEADING_COLOR,
        ),
        "body": ParagraphStyle(
            "FSBody",
            fontName=_F_BODY,
            fontSize=9,
            leading=12,
        ),
        "note": ParagraphStyle(
            "FSNote",
            fontName=_F_NOTE,
            fontSize=8,
            leading=10,
            textColor=_GRAY,
            spaceBefore=1 * mm,
        ),
    }


def _table_style(with_header=True, numeric_from_col=None):
    commands = [
        ("FONTNAME", (0, 0), (-1, -1), _F_BODY),
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
            ("FONTNAME", (0, 0), (-1, 0), _F_BOLD),
            ("TEXTCOLOR", (0, 0), (-1, 0), _PETROL),
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
    canvas.setFillColor(_PETROL)
    canvas.rect(0, 0, width, 4.5 * mm, stroke=0, fill=1)
    canvas.setFillColor(_TURQUOISE)
    canvas.rect(0, 4.5 * mm, width, 0.8 * mm, stroke=0, fill=1)
    canvas.setFont(_F_NOTE, 7)
    canvas.setFillColor(_GRAY)
    canvas.drawCentredString(width / 2.0, 16.5 * mm, FOOTER_DISCLAIMER)
    canvas.drawCentredString(width / 2.0, 13 * mm, FOOTER_LGPD)
    canvas.drawCentredString(width / 2.0, 9.5 * mm, f"{BRAND_NAME} — Página {canvas.getPageNumber()}")
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
        author=BRAND_NAME,
    )

    story = [
        _brand_header(),
        Spacer(1, 2 * mm),
        _tricolor_rule(),
        Spacer(1, 4 * mm),
        Paragraph("Relatório de Avaliação do Pé", styles["title"]),
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

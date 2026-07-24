#!/usr/bin/env python3
"""Gera o PDF imprimível (A3, escala 100%) da placa de captura Palmilha Inteligente.

Uso: python3 tools/generate_markers.py [--out placa_palmilha_inteligente.pdf]

Os 4 marcadores ArUco DICT_4X4_50 (ids 0..3 = TL, TR, BR, BL) são desenhados
em tamanho real (40 mm), com centros formando o retângulo de 250 x 380 mm.
Identidade visual conforme o Manual de Marca (logotipo oficial, Azul Petróleo,
Turquesa e tipografia Montserrat/Inter); os marcadores permanecem preto puro.
"""

import argparse
import os
import sys

import cv2
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as pdfcanvas

_SERVER_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _SERVER_DIR)

from app.processing import calibration  # noqa: E402

PAGE_WIDTH_MM = 297.0
PAGE_HEIGHT_MM = 420.0

OFFSET_X_MM = (PAGE_WIDTH_MM - calibration.PLATE_WIDTH_MM) / 2.0
OFFSET_Y_MM = (PAGE_HEIGHT_MM - calibration.PLATE_HEIGHT_MM) / 2.0

_FONT_DIR = os.path.join(_SERVER_DIR, "app", "reportgen", "fonts")
_LOGO_PATH = os.path.join(_SERVER_DIR, "app", "reportgen", "assets", "logo.png")
try:
    pdfmetrics.registerFont(TTFont("Montserrat-Bold", os.path.join(_FONT_DIR, "Montserrat-700.ttf")))
    pdfmetrics.registerFont(TTFont("Inter", os.path.join(_FONT_DIR, "Inter-400.ttf")))
    FONT_TITLE, FONT_TEXT = "Montserrat-Bold", "Inter"
except Exception:
    FONT_TITLE, FONT_TEXT = "Helvetica-Bold", "Helvetica"

# Paleta do Manual de Marca
PETROL = (0.039, 0.357, 0.494)     # #0A5B7E
TURQUOISE = (0.118, 0.780, 0.902)  # #1EC7E6
GRAY = (0.494, 0.518, 0.580)       # #7E8494


def _to_pdf_y(y_top_mm: float) -> float:
    """Converte y medido a partir do topo da página para o y do reportlab."""
    return (PAGE_HEIGHT_MM - y_top_mm) * mm


def _draw_marker(c: pdfcanvas.Canvas, dictionary, marker_id: int, cx_mm: float, cy_top_mm: float) -> None:
    bitmap = cv2.aruco.generateImageMarker(dictionary, marker_id, 6)
    modules = bitmap.shape[0]
    module_mm = calibration.MARKER_SIZE_MM / modules
    x0 = cx_mm - calibration.MARKER_SIZE_MM / 2.0
    y0_top = cy_top_mm - calibration.MARKER_SIZE_MM / 2.0
    c.setFillColorRGB(0, 0, 0)
    epsilon = 0.02
    for row in range(modules):
        for col in range(modules):
            if bitmap[row, col] == 0:
                x = x0 + col * module_mm
                y_top = y0_top + row * module_mm
                c.rect(
                    x * mm,
                    _to_pdf_y(y_top + module_mm) - epsilon * mm,
                    (module_mm + epsilon) * mm,
                    (module_mm + epsilon) * mm,
                    stroke=0,
                    fill=1,
                )


def _draw_cross(c: pdfcanvas.Canvas, x_mm: float, y_top_mm: float, size_mm: float = 5.0) -> None:
    half = size_mm / 2.0
    c.line((x_mm - half) * mm, _to_pdf_y(y_top_mm), (x_mm + half) * mm, _to_pdf_y(y_top_mm))
    c.line(x_mm * mm, _to_pdf_y(y_top_mm - half), x_mm * mm, _to_pdf_y(y_top_mm + half))


def build_pdf(out_path: str) -> None:
    c = pdfcanvas.Canvas(out_path, pagesize=(PAGE_WIDTH_MM * mm, PAGE_HEIGHT_MM * mm))
    c.setTitle("Palmilha Inteligente — Placa de captura (A3, escala 100%)")

    dictionary = cv2.aruco.getPredefinedDictionary(calibration.ARUCO_DICT_ID)
    centers_page = {}
    for marker_id, (mx, my) in calibration.MARKER_CENTERS_MM.items():
        cx = OFFSET_X_MM + mx
        cy_top = OFFSET_Y_MM + my
        centers_page[marker_id] = (cx, cy_top)
        _draw_marker(c, dictionary, marker_id, cx, cy_top)

    # Rótulos dos ids (fora da zona de silêncio dos marcadores)
    c.setFont(FONT_TEXT, 7)
    c.setFillColorRGB(*GRAY)
    for marker_id, (cx, cy_top) in centers_page.items():
        label_y = cy_top + 30.0 if cy_top < PAGE_HEIGHT_MM / 2.0 else cy_top - 29.0
        c.drawCentredString(cx * mm, _to_pdf_y(label_y), f"ID {marker_id}")

    center_x = PAGE_WIDTH_MM / 2.0
    center_y_top = PAGE_HEIGHT_MM / 2.0

    # Cruzes de referência (centro da placa e pontos médios das bordas)
    c.setStrokeColorRGB(0.55, 0.65, 0.72)
    c.setLineWidth(0.4)
    _draw_cross(c, center_x, center_y_top, 8.0)
    _draw_cross(c, center_x, OFFSET_Y_MM)
    _draw_cross(c, center_x, OFFSET_Y_MM + calibration.PLATE_HEIGHT_MM)
    _draw_cross(c, OFFSET_X_MM, center_y_top)
    _draw_cross(c, OFFSET_X_MM + calibration.PLATE_WIDTH_MM, center_y_top)

    # Área do pé
    foot_w, foot_h = 160.0, 290.0
    fx0 = center_x - foot_w / 2.0
    fy0_top = center_y_top - foot_h / 2.0
    c.setStrokeColorRGB(*TURQUOISE)
    c.setLineWidth(0.6)
    c.setDash(4, 3)
    c.roundRect(fx0 * mm, _to_pdf_y(fy0_top + foot_h), foot_w * mm, foot_h * mm, 8 * mm)
    c.line(center_x * mm, _to_pdf_y(fy0_top + 12), center_x * mm, _to_pdf_y(fy0_top + foot_h - 12))
    c.setDash()

    # Silhueta-guia do pé (antepé em cima, calcanhar embaixo)
    c.setStrokeColorRGB(0.78, 0.91, 0.96)
    c.setLineWidth(0.8)
    fore_cy = fy0_top + 90.0
    heel_cy = fy0_top + 225.0
    c.ellipse(
        (center_x - 48.0) * mm, _to_pdf_y(fore_cy + 62.0),
        (center_x + 48.0) * mm, _to_pdf_y(fore_cy - 62.0),
    )
    c.ellipse(
        (center_x - 35.0) * mm, _to_pdf_y(heel_cy + 48.0),
        (center_x + 35.0) * mm, _to_pdf_y(heel_cy - 48.0),
    )
    c.setFillColorRGB(*PETROL)
    c.setFont(FONT_TITLE, 10)
    c.drawCentredString(center_x * mm, _to_pdf_y(fy0_top + 22.0), "Posicione o pé aqui")
    c.setFont(FONT_TEXT, 8)
    c.drawCentredString(center_x * mm, _to_pdf_y(fy0_top + 30.0), "dedos para cima, calcanhar para baixo")

    # Cabeçalho com o logotipo oficial (entre os marcadores superiores)
    header_bottom = 20.0
    if os.path.exists(_LOGO_PATH):
        try:
            reader = ImageReader(_LOGO_PATH)
            img_w, img_h = reader.getSize()
            logo_h = 15.0
            logo_w = logo_h * img_w / float(img_h)
            c.drawImage(
                reader,
                (center_x - logo_w / 2.0) * mm,
                _to_pdf_y(2.5 + logo_h),
                logo_w * mm,
                logo_h * mm,
            )
            header_bottom = 2.5 + logo_h
        except Exception:
            pass
    c.setFillColorRGB(*PETROL)
    c.setFont(FONT_TITLE, 10)
    c.drawCentredString(center_x * mm, _to_pdf_y(header_bottom + 5.5), "Placa de captura")
    c.setFillColorRGB(*GRAY)
    c.setFont(FONT_TEXT, 8)
    c.drawCentredString(center_x * mm, _to_pdf_y(header_bottom + 10.5), "Imprimir em A3, escala 100% (tamanho real)")

    # Instruções
    c.setFillColorRGB(0.2, 0.2, 0.2)
    c.setFont(FONT_TEXT, 7)
    instructions = [
        "1. Imprima este arquivo em papel A3, escala 100% (tamanho real), sem \"ajustar à página\".",
        "2. Confira com uma régua: a barra de escala abaixo deve medir exatamente 100 mm.",
        "3. Fixe a folha, bem plana, sobre placa rígida (acrílico ≥ 6 mm). Centros dos marcadores: retângulo de 250 × 380 mm.",
    ]
    for i, text in enumerate(instructions):
        c.drawCentredString(center_x * mm, _to_pdf_y(385.0 + i * 5.0), text)

    # Barra de escala de 100 mm
    bar_y_top = 404.0
    c.setStrokeColorRGB(0.1, 0.1, 0.1)
    c.setLineWidth(1.0)
    c.line((center_x - 50.0) * mm, _to_pdf_y(bar_y_top), (center_x + 50.0) * mm, _to_pdf_y(bar_y_top))
    for tick_x in (center_x - 50.0, center_x + 50.0):
        c.line(tick_x * mm, _to_pdf_y(bar_y_top - 2.0), tick_x * mm, _to_pdf_y(bar_y_top + 2.0))
    c.setFont(FONT_TEXT, 7)
    c.drawCentredString(center_x * mm, _to_pdf_y(bar_y_top + 5.5), "100 mm — confira com régua")
    c.setFillColorRGB(*PETROL)
    c.setFont(FONT_TITLE, 6.5)
    c.drawCentredString(center_x * mm, _to_pdf_y(bar_y_top + 10.5), "PALMILHA INTELIGENTE — VOCÊ, LIVRE DAS DORES!")

    c.showPage()
    c.save()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Gera o PDF A3 imprimível da placa de captura Palmilha Inteligente."
    )
    parser.add_argument("--out", default="placa_palmilha_inteligente.pdf", help="arquivo PDF de saída")
    args = parser.parse_args()
    build_pdf(args.out)
    print(f"PDF gerado em {args.out}")
    print("Imprima em A3, escala 100%, e confira a barra de 100 mm com uma régua.")


if __name__ == "__main__":
    main()

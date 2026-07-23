"""Pipeline principal: process_capture, recompute_from_landmarks, render_overlay."""

import copy
import math

import cv2
import numpy as np

from . import calibration, segmentation
from . import measures as measures_mod


class ProcessingError(Exception):
    """Erro de processamento com código estável para a API.

    codes: "markers_not_found", "foot_not_found", "invalid_image".
    """

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


MAX_IMAGE_PIXELS = 40_000_000


def _decode_image(image_bytes: bytes) -> np.ndarray:
    if not image_bytes:
        raise ProcessingError("invalid_image", "Arquivo de imagem vazio ou ilegível.")
    buffer = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
    if image is None:
        raise ProcessingError(
            "invalid_image", "Não foi possível decodificar a imagem enviada."
        )
    if image.shape[0] * image.shape[1] > MAX_IMAGE_PIXELS:
        raise ProcessingError(
            "invalid_image",
            "Imagem grande demais para processar (limite de 40 megapixels).",
        )
    return image


def _rectify_or_raise(image: np.ndarray):
    markers = calibration.detect_markers(image)
    if len(markers) < len(calibration.MARKER_IDS):
        raise ProcessingError(
            "markers_not_found",
            f"Apenas {len(markers)} de 4 marcadores ArUco foram encontrados. "
            "Enquadre a placa inteira, com boa iluminação e sem reflexos.",
        )
    return calibration.rectify(image, markers), len(markers)


def process_capture(image_bytes: bytes, foot_side: str) -> dict:
    """Foto (bytes) -> dict de medidas no formato do SPEC."""
    image = _decode_image(image_bytes)
    rectified, markers_found = _rectify_or_raise(image)
    contour = segmentation.segment_foot(rectified)
    if contour is None:
        raise ProcessingError(
            "foot_not_found",
            "Não foi possível localizar o pé na placa. "
            "Verifique o contraste entre o pé e o fundo e o posicionamento.",
        )
    return measures_mod.compute_measures(contour, foot_side, markers_found)


def _distance(a, b) -> float:
    return math.hypot(float(a[0]) - float(b[0]), float(a[1]) - float(b[1]))


def recompute_from_landmarks(measures: dict, landmarks: dict) -> dict:
    """Substitui landmarks (subconjunto das 8 chaves) e recalcula medidas lineares."""
    result = copy.deepcopy(measures)
    merged = dict(result.get("landmarks") or {})
    for key, value in (landmarks or {}).items():
        if key not in measures_mod.LANDMARK_KEYS:
            continue
        merged[key] = [round(float(value[0]), 1), round(float(value[1]), 1)]
    result["landmarks"] = merged

    pairs = {
        "length_mm": ("toe", "heel"),
        "forefoot_width_mm": ("forefoot_a", "forefoot_b"),
        "midfoot_width_mm": ("midfoot_a", "midfoot_b"),
        "heel_width_mm": ("heel_a", "heel_b"),
    }
    for measure_key, (a, b) in pairs.items():
        if a in merged and b in merged:
            result[measure_key] = round(_distance(merged[a], merged[b]), 1)

    result["manually_adjusted"] = True
    return result


_CONTOUR_COLOR = (80, 175, 76)
_LINE_COLOR = (200, 120, 0)
_POINT_FILL = (255, 255, 255)
_POINT_EDGE = (40, 40, 210)
_TEXT_COLOR = (90, 50, 10)


def _landmark_px(landmarks: dict, name: str):
    if name not in landmarks:
        return None
    x, y = calibration.mm_to_px(landmarks[name])
    return int(round(x)), int(round(y))


def render_overlay(image_bytes: bytes, measures: dict) -> bytes:
    """PNG da imagem retificada com contorno, landmarks e medidas desenhados."""
    image = _decode_image(image_bytes)
    rectified, _markers_found = _rectify_or_raise(image)
    canvas = rectified.copy()

    contour_mm = measures.get("contour_mm") or []
    if len(contour_mm) >= 3:
        contour_px = (
            calibration.mm_to_px(np.asarray(contour_mm, dtype=np.float64))
            .round()
            .astype(np.int32)
            .reshape(-1, 1, 2)
        )
        cv2.polylines(canvas, [contour_px], True, _CONTOUR_COLOR, 2, cv2.LINE_AA)

    landmarks = measures.get("landmarks") or {}
    for a, b in (
        ("toe", "heel"),
        ("forefoot_a", "forefoot_b"),
        ("midfoot_a", "midfoot_b"),
        ("heel_a", "heel_b"),
    ):
        pa = _landmark_px(landmarks, a)
        pb = _landmark_px(landmarks, b)
        if pa is not None and pb is not None:
            cv2.line(canvas, pa, pb, _LINE_COLOR, 2, cv2.LINE_AA)

    for name in measures_mod.LANDMARK_KEYS:
        point = _landmark_px(landmarks, name)
        if point is not None:
            cv2.circle(canvas, point, 6, _POINT_FILL, -1, cv2.LINE_AA)
            cv2.circle(canvas, point, 6, _POINT_EDGE, 2, cv2.LINE_AA)

    # Fontes Hershey não suportam acentos: rótulos em pt-BR sem acentuação.
    lines = [
        f"Comprimento: {measures.get('length_mm', '-')} mm",
        f"Largura antepe: {measures.get('forefoot_width_mm', '-')} mm",
        f"Largura mediope: {measures.get('midfoot_width_mm', '-')} mm",
        f"Largura calcanhar: {measures.get('heel_width_mm', '-')} mm",
        f"Area plantar: {measures.get('plantar_area_cm2', '-')} cm2",
        f"Eixo: {measures.get('axis_angle_deg', '-')} graus",
    ]
    if measures.get("manually_adjusted"):
        lines.append("Ajustado manualmente")

    x0, y0 = 118, 8
    line_h = 20
    box_w = 292
    box_h = len(lines) * line_h + 12
    roi = canvas[y0 : y0 + box_h, x0 : x0 + box_w]
    white = np.full_like(roi, 255)
    canvas[y0 : y0 + box_h, x0 : x0 + box_w] = cv2.addWeighted(roi, 0.25, white, 0.75, 0)
    for i, text in enumerate(lines):
        cv2.putText(
            canvas,
            text,
            (x0 + 8, y0 + 20 + i * line_h),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.52,
            _TEXT_COLOR,
            1,
            cv2.LINE_AA,
        )

    ok, encoded = cv2.imencode(".png", canvas)
    if not ok:
        raise ProcessingError("invalid_image", "Falha ao gerar o PNG do overlay.")
    return encoded.tobytes()

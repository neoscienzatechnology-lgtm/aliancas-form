"""Segmentação do pé na imagem retificada (Otsu + morfologia)."""

import cv2
import numpy as np

from . import calibration

MIN_FOOT_AREA_CM2 = 40.0
MAX_FOOT_AREA_CM2 = 450.0
MIN_CONTRAST_GRAY = 20.0
MAX_FOREGROUND_RATIO = 0.5
USEFUL_EXPAND_MM = 5.0


def _useful_area_mask() -> np.ndarray:
    """Máscara da área útil: retângulo dos centros expandido, sem marcadores."""
    mask = np.zeros(
        (calibration.RECTIFIED_HEIGHT_PX, calibration.RECTIFIED_WIDTH_PX),
        dtype=np.uint8,
    )
    x0, y0 = calibration.mm_to_px((-USEFUL_EXPAND_MM, -USEFUL_EXPAND_MM))
    x1, y1 = calibration.mm_to_px(
        (
            calibration.PLATE_WIDTH_MM + USEFUL_EXPAND_MM,
            calibration.PLATE_HEIGHT_MM + USEFUL_EXPAND_MM,
        )
    )
    mask[int(y0) : int(y1), int(x0) : int(x1)] = 255
    for rx0, ry0, rx1, ry1 in calibration.marker_regions_px():
        mask[ry0:ry1, rx0:rx1] = 0
    return mask


def segment_foot(rectified_bgr: np.ndarray):
    """Encontra o contorno do pé na imagem retificada.

    Retorna o maior contorno plausível (np.ndarray (N, 1, 2) int32, em pixels
    da imagem retificada) ou None quando nenhum contorno com área mínima é
    encontrado dentro da área útil.
    """
    gray = cv2.cvtColor(rectified_bgr, cv2.COLOR_BGR2GRAY)
    background = int(np.median(gray))

    work = gray.copy()
    for x0, y0, x1, y1 in calibration.marker_regions_px():
        work[y0:y1, x0:x1] = background

    blurred = cv2.GaussianBlur(work, (7, 7), 0)
    _thr, binary = cv2.threshold(
        blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
    )

    useful_mask = _useful_area_mask()
    binary = cv2.bitwise_and(binary, useful_mask)

    # Sem pé na placa, Otsu divide o fundo quase uniforme em duas classes de
    # contraste ínfimo: exige separação real entre "pé" e fundo.
    useful = useful_mask > 0
    foreground = binary > 0
    if not foreground.any():
        return None
    if foreground.sum() / useful.sum() > MAX_FOREGROUND_RATIO:
        return None
    contrast = float(blurred[useful & ~foreground].mean()) - float(
        blurred[foreground].mean()
    )
    if contrast < MIN_CONTRAST_GRAY:
        return None

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=2)

    contours, _hier = cv2.findContours(
        binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE
    )
    area_px_per_cm2 = 100.0 * calibration.SCALE_PX_PER_MM**2
    min_area_px = MIN_FOOT_AREA_CM2 * area_px_per_cm2
    max_area_px = MAX_FOOT_AREA_CM2 * area_px_per_cm2

    best = None
    best_area = 0.0
    for contour in contours:
        area = cv2.contourArea(contour)
        if min_area_px <= area <= max_area_px and area > best_area:
            best = contour
            best_area = area
    return best

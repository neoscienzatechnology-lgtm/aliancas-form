"""Medidas do pé a partir do contorno segmentado.

Sistema de coordenadas: mm, origem no canto superior-esquerdo do retângulo
dos centros dos marcadores, eixo y para baixo. Eixo longitudinal por PCA;
posição relativa 0.0 = ponta do dedo (toe), 1.0 = calcanhar (heel).
"""

import math

import cv2
import numpy as np

from . import calibration

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

FOREFOOT_BAND = (0.10, 0.40)
MIDFOOT_BAND = (0.40, 0.70)
HEEL_BAND = (0.75, 0.95)

BIN_MM = 1.0
MAX_CONTOUR_POINTS = 400
SIMPLIFY_EPSILON_MM = 1.0


def _band_max_width(rel: np.ndarray, s: np.ndarray, lo: float, hi: float) -> float:
    selected = (rel >= lo) & (rel <= hi)
    if selected.sum() < 2:
        return 0.0
    values = s[selected]
    return float(values.max() - values.min())


def _bin_widths(rel: np.ndarray, s: np.ndarray, length: float):
    nbins = max(int(math.ceil(length / BIN_MM)), 1)
    bin_idx = np.minimum((rel * length / BIN_MM).astype(int), nbins - 1)
    widths = np.full(nbins, np.nan)
    idx_lo = np.zeros(nbins, dtype=int)
    idx_hi = np.zeros(nbins, dtype=int)
    for b in np.unique(bin_idx):
        sel = np.flatnonzero(bin_idx == b)
        if len(sel) < 2:
            continue
        sb = s[sel]
        i_lo = sel[int(np.argmin(sb))]
        i_hi = sel[int(np.argmax(sb))]
        widths[b] = s[i_hi] - s[i_lo]
        idx_lo[b] = i_lo
        idx_hi[b] = i_hi
    bin_rel = (np.arange(nbins) + 0.5) * BIN_MM / length
    return widths, idx_lo, idx_hi, bin_rel


def _pick_band(widths, idx_lo, idx_hi, bin_rel, band, mode):
    valid = ~np.isnan(widths)
    in_band = valid & (bin_rel >= band[0]) & (bin_rel <= band[1])
    candidates = np.flatnonzero(in_band if in_band.any() else valid)
    if mode == "max":
        b = candidates[int(np.argmax(widths[candidates]))]
    else:
        b = candidates[int(np.argmin(widths[candidates]))]
    return float(widths[b]), int(idx_lo[b]), int(idx_hi[b])


def _rounded_point(point) -> list:
    return [round(float(point[0]), 1), round(float(point[1]), 1)]


def _ordered_pair(pts_mm, i, j):
    p, q = pts_mm[i], pts_mm[j]
    if p[0] > q[0]:
        p, q = q, p
    return _rounded_point(p), _rounded_point(q)


def simplify_contour_mm(contour_px: np.ndarray) -> np.ndarray:
    """Simplifica o contorno (approxPolyDP, epsilon ~1 mm, máx. 400 pontos)."""
    epsilon = SIMPLIFY_EPSILON_MM * calibration.SCALE_PX_PER_MM
    approx = cv2.approxPolyDP(contour_px, epsilon, True)
    while len(approx) > MAX_CONTOUR_POINTS:
        epsilon *= 1.5
        approx = cv2.approxPolyDP(contour_px, epsilon, True)
    return calibration.px_to_mm(approx.reshape(-1, 2))


def compute_measures(contour_px: np.ndarray, foot_side: str, markers_found: int) -> dict:
    """Calcula o dict de medidas (formato do SPEC) a partir do contorno em px."""
    pts_mm = calibration.px_to_mm(contour_px.reshape(-1, 2))
    area_cm2 = float(cv2.contourArea(pts_mm.astype(np.float32))) / 100.0

    centroid = pts_mm.mean(axis=0)
    centered = pts_mm - centroid
    cov = centered.T @ centered / len(centered)
    eigenvalues, eigenvectors = np.linalg.eigh(cov)
    axis = eigenvectors[:, int(np.argmax(eigenvalues))]
    if axis[1] < 0:
        axis = -axis
    perp = np.array([-axis[1], axis[0]])

    t = centered @ axis
    s = centered @ perp
    length = float(t.max() - t.min())
    rel = (t - t.min()) / length

    # Orientação toe->heel: o antepé (lado do toe) é o mais largo.
    front_width = _band_max_width(rel, s, 0.05, 0.45)
    back_width = _band_max_width(rel, s, 0.55, 0.95)
    if back_width > front_width:
        axis = -axis
        perp = -perp
        t = -t
        s = -s
        rel = 1.0 - rel

    toe = pts_mm[int(np.argmin(t))]
    heel = pts_mm[int(np.argmax(t))]

    widths, idx_lo, idx_hi, bin_rel = _bin_widths(rel, s, length)
    forefoot_w, fa, fb = _pick_band(widths, idx_lo, idx_hi, bin_rel, FOREFOOT_BAND, "max")
    midfoot_w, ma, mb = _pick_band(widths, idx_lo, idx_hi, bin_rel, MIDFOOT_BAND, "min")
    heel_w, ha, hb = _pick_band(widths, idx_lo, idx_hi, bin_rel, HEEL_BAND, "max")

    angle = math.degrees(math.atan2(axis[0], axis[1]))
    if angle > 90.0:
        angle -= 180.0
    elif angle <= -90.0:
        angle += 180.0

    forefoot_a, forefoot_b = _ordered_pair(pts_mm, fa, fb)
    midfoot_a, midfoot_b = _ordered_pair(pts_mm, ma, mb)
    heel_a, heel_b = _ordered_pair(pts_mm, ha, hb)

    warnings = []
    if abs(angle) > 25.0:
        warnings.append("Pé muito inclinado em relação ao eixo da placa.")
    if area_cm2 < 60.0:
        warnings.append("Área plantar pequena — confira a segmentação.")

    contour_simplified = simplify_contour_mm(contour_px)

    return {
        "version": 1,
        "foot_side": foot_side,
        "scale_px_per_mm": calibration.SCALE_PX_PER_MM,
        "length_mm": round(length, 1),
        "forefoot_width_mm": round(forefoot_w, 1),
        "midfoot_width_mm": round(midfoot_w, 1),
        "heel_width_mm": round(heel_w, 1),
        "plantar_area_cm2": round(area_cm2, 1),
        "axis_angle_deg": round(angle, 1),
        "landmarks": {
            "toe": _rounded_point(toe),
            "heel": _rounded_point(heel),
            "forefoot_a": forefoot_a,
            "forefoot_b": forefoot_b,
            "midfoot_a": midfoot_a,
            "midfoot_b": midfoot_b,
            "heel_a": heel_a,
            "heel_b": heel_b,
        },
        "contour_mm": [_rounded_point(p) for p in contour_simplified],
        "quality": {"markers_found": int(markers_found), "warnings": warnings},
    }

#!/usr/bin/env python3
"""Gera foto sintética da placa FootScan para testes e demonstração.

Uso: python3 tools/make_demo_image.py [--out demo_foot.jpg] [--length-mm 245] [--warp]
"""

import argparse
import math
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.processing import calibration  # noqa: E402

DEMO_SCALE_PX_PER_MM = 4.0
DEMO_MARGIN_MM = 35.0
DEMO_WIDTH_PX = int((calibration.PLATE_WIDTH_MM + 2 * DEMO_MARGIN_MM) * DEMO_SCALE_PX_PER_MM)
DEMO_HEIGHT_PX = int((calibration.PLATE_HEIGHT_MM + 2 * DEMO_MARGIN_MM) * DEMO_SCALE_PX_PER_MM)

FOOT_FILL_BGR = (120, 150, 190)
FOOT_EDGE_BGR = (95, 122, 158)


def _mm_to_demo_px(points_mm):
    pts = np.asarray(points_mm, dtype=np.float64)
    return (pts + DEMO_MARGIN_MM) * DEMO_SCALE_PX_PER_MM


def _smoothstep(x: float) -> float:
    return x * x * (3.0 - 2.0 * x)


def _width_profile(rel: float, forefoot: float, mid: float, heel: float) -> float:
    """Largura do pé (mm) na posição relativa rel (0=toe, 1=heel).

    Máximo forefoot em rel=0.25, mínimo mid em rel=0.55, máximo heel em
    rel=0.85 — dentro das faixas de medida do SPEC.
    """
    if rel <= 0.25:
        u = (0.25 - rel) / 0.25
        return forefoot * math.sqrt(max(0.0, 1.0 - u * u))
    if rel <= 0.55:
        return forefoot - (forefoot - mid) * _smoothstep((rel - 0.25) / 0.30)
    if rel <= 0.85:
        return mid + (heel - mid) * _smoothstep((rel - 0.55) / 0.30)
    u = (rel - 0.85) / 0.15
    return heel * math.sqrt(max(0.0, 1.0 - u * u))


def _foot_polygon_mm(length, forefoot, mid, heel, center_x, toe_y, angle_deg, samples=240):
    rels = np.linspace(0.0, 1.0, samples)
    left = []
    right = []
    for rel in rels:
        half = _width_profile(float(rel), forefoot, mid, heel) / 2.0
        y = toe_y + float(rel) * length
        left.append((center_x - half, y))
        right.append((center_x + half, y))
    polygon = np.array(left + right[::-1], dtype=np.float64)
    pivot = np.array([center_x, toe_y + length / 2.0])
    a = math.radians(angle_deg)
    rotation = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
    return (polygon - pivot) @ rotation.T + pivot


def _polygon_area_mm2(polygon: np.ndarray) -> float:
    x = polygon[:, 0]
    y = polygon[:, 1]
    return 0.5 * abs(float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))))


def _draw_plate() -> np.ndarray:
    base = np.full((DEMO_HEIGHT_PX, DEMO_WIDTH_PX), 231.0)
    base += np.linspace(-6.0, 7.0, DEMO_WIDTH_PX)[None, :]
    base += np.linspace(4.0, -5.0, DEMO_HEIGHT_PX)[:, None]
    image = np.dstack([base * 0.98, base, base * 1.01])
    image = np.clip(image, 0, 255).astype(np.uint8)

    dictionary = cv2.aruco.getPredefinedDictionary(calibration.ARUCO_DICT_ID)
    marker_px = int(calibration.MARKER_SIZE_MM * DEMO_SCALE_PX_PER_MM)
    quiet_px = int((calibration.MARKER_SIZE_MM / 2.0 + 6.0) * DEMO_SCALE_PX_PER_MM)
    for marker_id, center_mm in calibration.MARKER_CENTERS_MM.items():
        cx, cy = _mm_to_demo_px(center_mm).round().astype(int)
        image[cy - quiet_px : cy + quiet_px, cx - quiet_px : cx + quiet_px] = (250, 250, 250)
        bitmap = cv2.aruco.generateImageMarker(dictionary, marker_id, 6)
        marker = cv2.resize(bitmap, (marker_px, marker_px), interpolation=cv2.INTER_NEAREST)
        marker_bgr = np.where(marker[:, :, None] < 128, 15, 250).astype(np.uint8)
        half = marker_px // 2
        image[cy - half : cy + half, cx - half : cx + half] = marker_bgr
    return image


def _apply_warp(image: np.ndarray) -> np.ndarray:
    h, w = image.shape[:2]
    src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    dst = np.float32([[38, 22], [w - 30, 9], [w - 13, h - 31], [19, h - 14]])
    homography = cv2.getPerspectiveTransform(src, dst)
    return cv2.warpPerspective(
        image,
        homography,
        (w, h),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(226, 229, 231),
    )


def make_demo(
    length_mm: float = 245.0,
    forefoot_mm: float = 98.0,
    heel_mm: float = 70.0,
    warp: bool = True,
    draw_foot: bool = True,
    angle_deg: float = 2.0,
    seed: int = 7,
):
    """Gera (jpg_bytes, ground_truth) de uma foto sintética da placa."""
    rng = np.random.default_rng(seed)
    midfoot_mm = round(min(forefoot_mm * 0.63, heel_mm * 0.92), 1)

    image = _draw_plate()
    area_cm2 = 0.0
    if draw_foot:
        toe_y = (calibration.PLATE_HEIGHT_MM - length_mm) / 2.0
        center_x = calibration.PLATE_WIDTH_MM / 2.0
        polygon_mm = _foot_polygon_mm(
            length_mm, forefoot_mm, midfoot_mm, heel_mm, center_x, toe_y, angle_deg
        )
        area_cm2 = _polygon_area_mm2(polygon_mm) / 100.0
        polygon_px = _mm_to_demo_px(polygon_mm).round().astype(np.int32).reshape(-1, 1, 2)
        cv2.fillPoly(image, [polygon_px], FOOT_FILL_BGR, cv2.LINE_AA)
        cv2.polylines(image, [polygon_px], True, FOOT_EDGE_BGR, 3, cv2.LINE_AA)

    if warp:
        image = _apply_warp(image)

    image = cv2.GaussianBlur(image, (3, 3), 0.8)
    noise = rng.normal(0.0, 2.5, image.shape)
    image = np.clip(image.astype(np.float64) + noise, 0, 255).astype(np.uint8)

    ok, encoded = cv2.imencode(".jpg", image, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
    if not ok:
        raise RuntimeError("Falha ao codificar a imagem de demonstração.")

    ground_truth = {
        "length_mm": float(length_mm),
        "forefoot_width_mm": float(forefoot_mm),
        "midfoot_width_mm": float(midfoot_mm),
        "heel_width_mm": float(heel_mm),
        "plantar_area_cm2": round(area_cm2, 1),
        # Convenção do pipeline (eixo y para baixo): rotação horária positiva
        # do desenho aparece como ângulo negativo do eixo toe->heel.
        "axis_angle_deg": float(-angle_deg),
    }
    return encoded.tobytes(), ground_truth


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Gera imagem sintética de demonstração da placa FootScan."
    )
    parser.add_argument("--out", default="demo_foot.jpg", help="arquivo JPG de saída")
    parser.add_argument("--length-mm", type=float, default=245.0, help="comprimento do pé (mm)")
    parser.add_argument("--forefoot-mm", type=float, default=98.0, help="largura do antepé (mm)")
    parser.add_argument("--heel-mm", type=float, default=70.0, help="largura do calcanhar (mm)")
    parser.add_argument("--warp", action="store_true", help="aplica perspectiva leve")
    args = parser.parse_args()

    jpg_bytes, ground_truth = make_demo(
        length_mm=args.length_mm,
        forefoot_mm=args.forefoot_mm,
        heel_mm=args.heel_mm,
        warp=args.warp,
    )
    with open(args.out, "wb") as fh:
        fh.write(jpg_bytes)
    print(f"Imagem gerada em {args.out} ({len(jpg_bytes)} bytes)")
    print("Valores reais (ground truth):")
    for key, value in ground_truth.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()

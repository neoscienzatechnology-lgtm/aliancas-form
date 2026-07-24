"""Testes de acurácia e robustez do pipeline de processamento."""

import math
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

SERVER_DIR = Path(__file__).resolve().parents[1]
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

from app.processing import calibration  # noqa: E402
from app.processing.pipeline import (  # noqa: E402
    ProcessingError,
    process_capture,
    recompute_from_landmarks,
    render_overlay,
)
from tools.make_demo_image import make_demo  # noqa: E402

TOLERANCE_MM = 3.0
LANDMARK_KEYS = {
    "toe",
    "heel",
    "forefoot_a",
    "forefoot_b",
    "midfoot_a",
    "midfoot_b",
    "heel_a",
    "heel_b",
}


def test_accuracy_with_warp():
    jpg_bytes, gt = make_demo(warp=True)
    measures = process_capture(jpg_bytes, "left")

    assert measures["quality"]["markers_found"] == 4
    assert abs(measures["length_mm"] - gt["length_mm"]) <= TOLERANCE_MM
    assert abs(measures["forefoot_width_mm"] - gt["forefoot_width_mm"]) <= TOLERANCE_MM
    assert abs(measures["heel_width_mm"] - gt["heel_width_mm"]) <= TOLERANCE_MM

    assert measures["version"] == 1
    assert measures["foot_side"] == "left"
    assert measures["scale_px_per_mm"] == 2.0
    assert measures["midfoot_width_mm"] < measures["forefoot_width_mm"]
    assert measures["plantar_area_cm2"] > 0
    assert set(measures["landmarks"]) == LANDMARK_KEYS
    assert 3 <= len(measures["contour_mm"]) <= 400
    assert measures["quality"]["warnings"] == []


def test_accuracy_without_warp():
    jpg_bytes, gt = make_demo(warp=False)
    measures = process_capture(jpg_bytes, "right")
    assert measures["foot_side"] == "right"
    assert abs(measures["length_mm"] - gt["length_mm"]) <= TOLERANCE_MM
    assert abs(measures["forefoot_width_mm"] - gt["forefoot_width_mm"]) <= TOLERANCE_MM
    assert abs(measures["heel_width_mm"] - gt["heel_width_mm"]) <= TOLERANCE_MM


def test_accuracy_other_foot_size():
    jpg_bytes, gt = make_demo(length_mm=228.0, forefoot_mm=90.0, heel_mm=62.0, warp=True)
    measures = process_capture(jpg_bytes, "left")
    assert abs(measures["length_mm"] - gt["length_mm"]) <= TOLERANCE_MM
    assert abs(measures["forefoot_width_mm"] - gt["forefoot_width_mm"]) <= TOLERANCE_MM
    assert abs(measures["heel_width_mm"] - gt["heel_width_mm"]) <= TOLERANCE_MM


def test_landmarks_are_consistent_with_measures():
    jpg_bytes, _gt = make_demo(warp=True)
    measures = process_capture(jpg_bytes, "left")
    lm = measures["landmarks"]

    forefoot_dist = math.dist(lm["forefoot_a"], lm["forefoot_b"])
    heel_dist = math.dist(lm["heel_a"], lm["heel_b"])
    assert abs(forefoot_dist - measures["forefoot_width_mm"]) <= 2.0
    assert abs(heel_dist - measures["heel_width_mm"]) <= 2.0
    # toe acima do heel (origem no canto sup-esq, y para baixo)
    assert lm["toe"][1] < lm["heel"][1]


def test_recompute_from_landmarks():
    jpg_bytes, _gt = make_demo(warp=True)
    measures = process_capture(jpg_bytes, "left")

    new_toe = [125.0, 10.0]
    adjusted = recompute_from_landmarks(measures, {"toe": new_toe})

    assert adjusted["manually_adjusted"] is True
    assert adjusted["landmarks"]["toe"] == new_toe
    expected_length = round(math.dist(new_toe, adjusted["landmarks"]["heel"]), 1)
    assert adjusted["length_mm"] == expected_length
    assert adjusted["plantar_area_cm2"] == measures["plantar_area_cm2"]
    assert adjusted["contour_mm"] == measures["contour_mm"]
    # o dict original não é mutado
    assert "manually_adjusted" not in measures
    assert measures["landmarks"]["toe"] != new_toe


def test_invalid_image():
    with pytest.raises(ProcessingError) as excinfo:
        process_capture(b"isto-nao-e-uma-imagem", "left")
    assert excinfo.value.code == "invalid_image"


def test_markers_not_found():
    blank = np.full((600, 450, 3), 235, dtype=np.uint8)
    ok, encoded = cv2.imencode(".jpg", blank)
    assert ok
    with pytest.raises(ProcessingError) as excinfo:
        process_capture(encoded.tobytes(), "left")
    assert excinfo.value.code == "markers_not_found"


def test_foot_not_found():
    jpg_bytes, _gt = make_demo(warp=True, draw_foot=False)
    with pytest.raises(ProcessingError) as excinfo:
        process_capture(jpg_bytes, "left")
    assert excinfo.value.code == "foot_not_found"


def test_rectified_geometry():
    """O painel web depende de pixel = (mm + 30) * 2 na imagem retificada."""
    jpg_bytes, _gt = make_demo(warp=True)
    image = cv2.imdecode(np.frombuffer(jpg_bytes, np.uint8), cv2.IMREAD_COLOR)
    markers = calibration.detect_markers(image)
    assert len(markers) == 4

    rectified = calibration.rectify(image, markers)
    assert rectified.shape[:2] == (880, 620)

    redetected = calibration.detect_markers(rectified)
    assert len(redetected) == 4
    expected_centers_px = {
        0: (60.0, 60.0),
        1: (560.0, 60.0),
        2: (560.0, 820.0),
        3: (60.0, 820.0),
    }
    for marker_id, expected in expected_centers_px.items():
        center = redetected[marker_id].mean(axis=0)
        assert abs(center[0] - expected[0]) <= 4.0
        assert abs(center[1] - expected[1]) <= 4.0


def test_render_overlay():
    jpg_bytes, _gt = make_demo(warp=True)
    measures = process_capture(jpg_bytes, "left")
    png_bytes = render_overlay(jpg_bytes, measures)

    assert png_bytes[:8] == b"\x89PNG\r\n\x1a\n"
    overlay = cv2.imdecode(np.frombuffer(png_bytes, np.uint8), cv2.IMREAD_COLOR)
    assert overlay.shape[:2] == (880, 620)

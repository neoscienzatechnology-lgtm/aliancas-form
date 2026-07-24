"""Fluxo e2e do exame: upload dos dois pés, medidas, assimetria, ajuste de
landmarks, overlay, PDF, histórico e exame anterior."""

import pytest

from tools.make_demo_image import make_demo

MM_TOLERANCE = 3.0
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"

LEFT_PARAMS = {"length_mm": 252.0, "forefoot_mm": 99.0, "heel_mm": 71.0}
RIGHT_PARAMS = {"length_mm": 246.0, "forefoot_mm": 96.0, "heel_mm": 69.0}


def create_patient_with_consent(client, headers, name="Paciente Exame"):
    response = client.post("/api/patients", json={"name": name}, headers=headers)
    assert response.status_code in (200, 201), response.text
    patient_uuid = response.json()["uuid"]
    response = client.post(
        f"/api/patients/{patient_uuid}/consent",
        json={"version": "v1"},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return patient_uuid


def create_exam(client, headers, patient_uuid, notes=None):
    response = client.post(
        "/api/exams",
        json={"patient_uuid": patient_uuid, "notes": notes},
        headers=headers,
    )
    assert response.status_code in (200, 201), response.text
    return response.json()


def upload_capture(client, headers, exam_uuid, foot_side, jpg_bytes):
    response = client.post(
        f"/api/exams/{exam_uuid}/captures",
        data={"foot_side": foot_side, "view": "plantar"},
        files={"file": (f"{foot_side}.jpg", jpg_bytes, "image/jpeg")},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()


def assert_processed_capture(capture, foot_side, ground_truth):
    assert capture["foot_side"] == foot_side
    assert capture["view"] == "plantar"
    assert capture["processed"] is True
    assert capture["error"] is None
    assert capture["manually_adjusted"] is False
    measures = capture["measures"]
    assert measures is not None
    assert measures["foot_side"] == foot_side
    assert measures["quality"]["markers_found"] == 4
    for key in ("length_mm", "forefoot_width_mm", "heel_width_mm"):
        assert measures[key] == pytest.approx(ground_truth[key], abs=MM_TOLERANCE), key


def test_exam_full_flow(client, auth_headers):
    patient_uuid = create_patient_with_consent(client, auth_headers)
    exam = create_exam(client, auth_headers, patient_uuid, notes="avaliação inicial")
    exam_uuid = exam["uuid"]
    assert exam["status"] == "draft"

    left_jpg, left_gt = make_demo(warp=True, **LEFT_PARAMS)
    right_jpg, right_gt = make_demo(warp=True, **RIGHT_PARAMS)

    left_capture = upload_capture(client, auth_headers, exam_uuid, "left", left_jpg)
    assert_processed_capture(left_capture, "left", left_gt)

    detail = client.get(f"/api/exams/{exam_uuid}", headers=auth_headers).json()
    assert detail["status"] == "processed"
    assert detail["asymmetry"] is None

    right_capture = upload_capture(client, auth_headers, exam_uuid, "right", right_jpg)
    assert_processed_capture(right_capture, "right", right_gt)

    detail = client.get(f"/api/exams/{exam_uuid}", headers=auth_headers).json()
    assert len(detail["captures"]) == 2
    asymmetry = detail["asymmetry"]
    assert asymmetry is not None
    for key in (
        "length_mm",
        "forefoot_width_mm",
        "midfoot_width_mm",
        "heel_width_mm",
        "plantar_area_cm2",
    ):
        assert key in asymmetry
    for key in ("length_mm", "forefoot_width_mm", "heel_width_mm"):
        expected = left_gt[key] - right_gt[key]
        assert asymmetry[key] == pytest.approx(expected, abs=2 * MM_TOLERANCE), key

    original_length = left_capture["measures"]["length_mm"]
    response = client.put(
        f"/api/captures/{left_capture['uuid']}/landmarks",
        json={"landmarks": {"toe": [120.0, 30.0], "heel": [120.0, 230.0]}},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    adjusted = response.json()
    assert adjusted["manually_adjusted"] is True
    assert adjusted["measures"]["manually_adjusted"] is True
    assert adjusted["measures"]["length_mm"] == pytest.approx(200.0, abs=0.1)
    assert adjusted["measures"]["length_mm"] != original_length

    detail = client.get(f"/api/exams/{exam_uuid}", headers=auth_headers).json()
    assert detail["status"] == "reviewed"

    response = client.get(
        f"/api/captures/{left_capture['uuid']}/overlay", headers=auth_headers
    )
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("image/png")
    assert response.content.startswith(PNG_MAGIC)

    response = client.get(f"/api/exams/{exam_uuid}/report.pdf", headers=auth_headers)
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("application/pdf")
    assert "attachment" in response.headers.get("content-disposition", "")
    assert response.content.startswith(b"%PDF")

    response = client.get(f"/api/patients/{patient_uuid}/history", headers=auth_headers)
    assert response.status_code == 200, response.text
    history = response.json()
    assert len(history) == 1
    item = history[0]
    assert item["exam_uuid"] == exam_uuid
    assert item["measures_by_side"]["left"] is not None
    assert item["measures_by_side"]["right"] is not None


def test_second_exam_has_previous_exam(client, auth_headers):
    patient_uuid = create_patient_with_consent(
        client, auth_headers, name="Paciente Retorno"
    )
    first_exam = create_exam(client, auth_headers, patient_uuid, notes="primeiro exame")
    jpg_bytes, ground_truth = make_demo(
        length_mm=248.0, forefoot_mm=97.0, heel_mm=70.0, warp=True
    )
    capture = upload_capture(client, auth_headers, first_exam["uuid"], "left", jpg_bytes)
    assert_processed_capture(capture, "left", ground_truth)

    first_detail = client.get(
        f"/api/exams/{first_exam['uuid']}", headers=auth_headers
    ).json()
    assert first_detail["previous_exam"] is None

    second_exam = create_exam(client, auth_headers, patient_uuid, notes="retorno")
    second_detail = client.get(
        f"/api/exams/{second_exam['uuid']}", headers=auth_headers
    ).json()
    previous = second_detail["previous_exam"]
    assert previous is not None
    assert previous["uuid"] == first_exam["uuid"]
    assert previous["measures_by_side"]["left"] is not None
    assert previous["measures_by_side"]["right"] is None

    response = client.get(f"/api/patients/{patient_uuid}/history", headers=auth_headers)
    assert [item["exam_uuid"] for item in response.json()] == [
        first_exam["uuid"],
        second_exam["uuid"],
    ]

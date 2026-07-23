"""Sincronização offline: upsert por uuid e idempotência de capture por client_uuid."""

import uuid

import cv2
import numpy as np


def make_blank_jpg() -> bytes:
    image = np.full((240, 320, 3), 210, dtype=np.uint8)
    ok, encoded = cv2.imencode(".jpg", image)
    assert ok
    return encoded.tobytes()


def test_sync_batch_upsert_by_uuid(client, auth_headers):
    patient_uuid = uuid.uuid4().hex
    exam_uuid = uuid.uuid4().hex

    payload = {
        "patients": [
            {
                "uuid": patient_uuid,
                "name": "Paciente Sync",
                "phone": "11 97777-0000",
                "consent_accepted_at": "2026-07-20T12:00:00Z",
                "consent_version": "v1",
            }
        ],
        "exams": [
            {
                "uuid": exam_uuid,
                "patient_uuid": patient_uuid,
                "notes": "primeira sync",
                "created_at": "2026-07-20T12:05:00Z",
            }
        ],
    }
    response = client.post("/api/sync/batch", json=payload, headers=auth_headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["patients"]["created"] == 1
    assert body["patients"]["updated"] == 0
    assert body["exams"]["created"] == 1
    assert body["exams"]["updated"] == 0

    patient = client.get(f"/api/patients/{patient_uuid}", headers=auth_headers).json()
    assert patient["name"] == "Paciente Sync"
    assert patient["consent_version"] == "v1"
    assert patient["consent_accepted_at"] is not None

    exam = client.get(f"/api/exams/{exam_uuid}", headers=auth_headers).json()
    assert exam["patient_uuid"] == patient_uuid
    assert exam["notes"] == "primeira sync"

    payload["patients"][0]["name"] = "Paciente Sync Atualizado"
    payload["exams"][0]["notes"] = "sync atualizada"
    response = client.post("/api/sync/batch", json=payload, headers=auth_headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["patients"]["created"] == 0
    assert body["patients"]["updated"] == 1
    assert body["exams"]["created"] == 0
    assert body["exams"]["updated"] == 1

    patient = client.get(f"/api/patients/{patient_uuid}", headers=auth_headers).json()
    assert patient["name"] == "Paciente Sync Atualizado"

    exam = client.get(f"/api/exams/{exam_uuid}", headers=auth_headers).json()
    assert exam["notes"] == "sync atualizada"

    listing = client.get("/api/patients", headers=auth_headers).json()
    assert [p["uuid"] for p in listing].count(patient_uuid) == 1


def test_capture_client_uuid_is_idempotent(client, auth_headers):
    patient_uuid = uuid.uuid4().hex
    exam_uuid = uuid.uuid4().hex
    payload = {
        "patients": [
            {
                "uuid": patient_uuid,
                "name": "Paciente Offline",
                "consent_accepted_at": "2026-07-20T12:00:00Z",
                "consent_version": "v1",
            }
        ],
        "exams": [{"uuid": exam_uuid, "patient_uuid": patient_uuid}],
    }
    response = client.post("/api/sync/batch", json=payload, headers=auth_headers)
    assert response.status_code == 200, response.text

    client_uuid = uuid.uuid4().hex
    jpg_bytes = make_blank_jpg()

    def upload():
        return client.post(
            f"/api/exams/{exam_uuid}/captures",
            data={"foot_side": "left", "view": "plantar", "client_uuid": client_uuid},
            files={"file": ("offline.jpg", jpg_bytes, "image/jpeg")},
            headers=auth_headers,
        )

    first = upload()
    assert first.status_code == 200, first.text
    assert first.json()["uuid"] == client_uuid

    second = upload()
    assert second.status_code == 200, second.text
    assert second.json()["uuid"] == client_uuid

    exam = client.get(f"/api/exams/{exam_uuid}", headers=auth_headers).json()
    captures = exam["captures"]
    assert len(captures) == 1
    assert captures[0]["uuid"] == client_uuid
    assert captures[0]["foot_side"] == "left"

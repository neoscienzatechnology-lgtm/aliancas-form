"""Pacientes: CRUD, busca, soft delete, consentimento e regra LGPD do exame."""


def create_patient(client, headers, **overrides):
    payload = {"name": "Paciente Teste"}
    payload.update(overrides)
    response = client.post("/api/patients", json=payload, headers=headers)
    assert response.status_code in (200, 201), response.text
    return response.json()


def test_create_and_get_patient(client, auth_headers):
    created = create_patient(
        client,
        auth_headers,
        name="Maria da Silva",
        birth_date="1980-05-10",
        sex="F",
        document="123.456.789-00",
        phone="11 99999-0000",
        email="maria@exemplo.com",
        notes="Observação inicial",
    )
    assert created["uuid"]
    assert created["name"] == "Maria da Silva"
    assert created["birth_date"] == "1980-05-10"
    assert created["sex"] == "F"
    assert created["document"] == "123.456.789-00"
    assert created["consent_accepted_at"] is None
    assert created["consent_version"] is None
    assert created["created_at"]

    response = client.get(f"/api/patients/{created['uuid']}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["uuid"] == created["uuid"]

    listing = client.get("/api/patients", headers=auth_headers)
    assert listing.status_code == 200
    assert created["uuid"] in [patient["uuid"] for patient in listing.json()]


def test_update_patient(client, auth_headers):
    created = create_patient(client, auth_headers, name="Paciente Original")
    response = client.put(
        f"/api/patients/{created['uuid']}",
        json={"name": "Paciente Atualizado", "phone": "21 98888-7777"},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["uuid"] == created["uuid"]
    assert body["name"] == "Paciente Atualizado"
    assert body["phone"] == "21 98888-7777"


def test_get_unknown_patient_returns_404(client, auth_headers):
    response = client.get("/api/patients/nao-existe", headers=auth_headers)
    assert response.status_code == 404


def test_search_patients(client, auth_headers):
    maria = create_patient(
        client, auth_headers, name="Maria Aparecida", document="111.222.333-44"
    )
    joao = create_patient(
        client, auth_headers, name="João Pereira", document="555.666.777-88"
    )

    response = client.get("/api/patients", params={"search": "maria"}, headers=auth_headers)
    uuids = [patient["uuid"] for patient in response.json()]
    assert maria["uuid"] in uuids
    assert joao["uuid"] not in uuids

    response = client.get("/api/patients", params={"search": "MARIA"}, headers=auth_headers)
    assert maria["uuid"] in [patient["uuid"] for patient in response.json()]

    response = client.get(
        "/api/patients", params={"search": "555.666"}, headers=auth_headers
    )
    uuids = [patient["uuid"] for patient in response.json()]
    assert joao["uuid"] in uuids
    assert maria["uuid"] not in uuids


def test_soft_delete_patient(client, auth_headers):
    created = create_patient(client, auth_headers, name="Paciente Removido")
    response = client.delete(f"/api/patients/{created['uuid']}", headers=auth_headers)
    assert response.status_code == 200, response.text

    listing = client.get("/api/patients", headers=auth_headers)
    assert created["uuid"] not in [patient["uuid"] for patient in listing.json()]

    response = client.get(f"/api/patients/{created['uuid']}", headers=auth_headers)
    assert response.status_code == 404


def test_consent(client, auth_headers):
    created = create_patient(client, auth_headers, name="Paciente Consentimento")
    response = client.post(
        f"/api/patients/{created['uuid']}/consent",
        json={"version": "v1"},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["consent_accepted_at"] is not None
    assert body["consent_version"] == "v1"


def test_exam_requires_consent(client, auth_headers):
    created = create_patient(client, auth_headers, name="Paciente Sem Consentimento")

    response = client.post(
        "/api/exams", json={"patient_uuid": created["uuid"]}, headers=auth_headers
    )
    assert response.status_code == 400

    consent = client.post(
        f"/api/patients/{created['uuid']}/consent",
        json={"version": "v1"},
        headers=auth_headers,
    )
    assert consent.status_code == 200

    response = client.post(
        "/api/exams", json={"patient_uuid": created["uuid"]}, headers=auth_headers
    )
    assert response.status_code in (200, 201), response.text
    body = response.json()
    assert body["patient_uuid"] == created["uuid"]
    assert body["status"] == "draft"
    assert body["captures"] == []

"""Autenticação: login, /me, rotas protegidas e permissões de admin."""


def test_login_ok(client, admin_credentials):
    response = client.post("/api/auth/login", json=admin_credentials)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"
    assert body["user"]["email"] == admin_credentials["email"]
    assert body["user"]["role"] == "admin"
    assert body["user"]["is_active"] is True


def test_login_wrong_password(client, admin_credentials):
    response = client.post(
        "/api/auth/login",
        json={"email": admin_credentials["email"], "password": "senha-errada"},
    )
    assert response.status_code == 401


def test_login_unknown_email(client):
    response = client.post(
        "/api/auth/login",
        json={"email": "ninguem@teste.local", "password": "qualquer"},
    )
    assert response.status_code == 401


def test_me_returns_current_user(client, admin_headers, admin_credentials):
    response = client.get("/api/auth/me", headers=admin_headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["email"] == admin_credentials["email"]
    assert body["role"] == "admin"
    assert body["uuid"]


def test_protected_route_without_token(client):
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/patients").status_code == 401


def test_protected_route_invalid_token(client):
    headers = {"Authorization": "Bearer token-invalido"}
    assert client.get("/api/auth/me", headers=headers).status_code == 401


def test_admin_creates_professional(client, admin_headers):
    payload = {
        "name": "Nova Profissional",
        "email": "nova.pro@teste.local",
        "password": "senha-segura",
        "role": "professional",
    }
    response = client.post("/api/users", json=payload, headers=admin_headers)
    assert response.status_code in (200, 201), response.text
    body = response.json()
    assert body["email"] == payload["email"]
    assert body["role"] == "professional"
    assert body["is_active"] is True
    assert "password" not in body and "password_hash" not in body

    login = client.post(
        "/api/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    assert login.status_code == 200, login.text

    listing = client.get("/api/users", headers=admin_headers)
    assert listing.status_code == 200
    assert payload["email"] in [user["email"] for user in listing.json()]


def test_professional_cannot_access_users(client, professional_headers):
    assert client.get("/api/users", headers=professional_headers).status_code == 403
    response = client.post(
        "/api/users",
        json={
            "name": "Intruso",
            "email": "intruso@teste.local",
            "password": "senha-intruso",
            "role": "admin",
        },
        headers=professional_headers,
    )
    assert response.status_code == 403

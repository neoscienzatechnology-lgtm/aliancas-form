"""Fixtures dos testes de API: app com settings isolados por teste (tmp_path)."""

import importlib
import sys
from pathlib import Path

import pytest

SERVER_DIR = Path(__file__).resolve().parents[1]
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

ADMIN_EMAIL = "admin@teste.local"
ADMIN_PASSWORD = "admin-senha-teste"
PROFESSIONAL_EMAIL = "profissional@teste.local"
PROFESSIONAL_PASSWORD = "pro-senha-teste"


def _purge_app_modules() -> None:
    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            del sys.modules[name]


@pytest.fixture()
def app(tmp_path, monkeypatch):
    """App FastAPI com banco SQLite e data_dir exclusivos do teste.

    As env vars FOOTSCAN_* são definidas ANTES de importar o pacote `app`
    (config/database leem as settings no import), e os módulos `app.*` são
    reimportados a cada teste para garantir isolamento total de engine e dados.
    """
    monkeypatch.setenv("FOOTSCAN_DB_URL", f"sqlite:///{tmp_path / 'footscan_test.db'}")
    monkeypatch.setenv("FOOTSCAN_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv(
        "FOOTSCAN_SECRET_KEY", "segredo-de-teste-suficientemente-longo-para-hs256"
    )
    monkeypatch.setenv("FOOTSCAN_TOKEN_EXPIRE_MINUTES", "60")
    monkeypatch.setenv("FOOTSCAN_ADMIN_EMAIL", ADMIN_EMAIL)
    monkeypatch.setenv("FOOTSCAN_ADMIN_PASSWORD", ADMIN_PASSWORD)
    monkeypatch.setenv("FOOTSCAN_ADMIN_NAME", "Admin Teste")

    _purge_app_modules()
    main = importlib.import_module("app.main")
    try:
        yield main.app
    finally:
        database = sys.modules.get("app.database")
        if database is not None:
            database.engine.dispose()
        _purge_app_modules()


@pytest.fixture()
def client(app):
    from fastapi.testclient import TestClient

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def admin_credentials():
    return {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}


def login_headers(client, email: str, password: str) -> dict:
    response = client.post(
        "/api/auth/login", json={"email": email, "password": password}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture()
def admin_headers(client):
    return login_headers(client, ADMIN_EMAIL, ADMIN_PASSWORD)


@pytest.fixture()
def professional_headers(client, admin_headers):
    response = client.post(
        "/api/users",
        json={
            "name": "Profissional Teste",
            "email": PROFESSIONAL_EMAIL,
            "password": PROFESSIONAL_PASSWORD,
            "role": "professional",
        },
        headers=admin_headers,
    )
    assert response.status_code in (200, 201), response.text
    assert response.json()["role"] == "professional"
    return login_headers(client, PROFESSIONAL_EMAIL, PROFESSIONAL_PASSWORD)


@pytest.fixture()
def auth_headers(professional_headers):
    return professional_headers

import dataclasses
import hashlib

import pytest
from fastapi.testclient import TestClient

from hotline import config, main

SECRET = "admin-secret-value"
HEADER = "X-Hotline-Admin-Secret"

STUB_ROUTES = [
    ("POST", "/api/tools/get_weather_forecast"),
    ("POST", "/api/jobs/process-pending"),
    ("POST", "/api/calls/conv_123/process"),
]


@pytest.fixture
def client():
    return TestClient(main.app)


def _patch_settings(monkeypatch, **overrides):
    monkeypatch.setattr(config, "settings", dataclasses.replace(config.settings, **overrides))


def test_health_ok(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_deep_health_requires_admin_secret(client, monkeypatch):
    _patch_settings(monkeypatch, hotline_admin_secret=SECRET)
    assert client.get("/api/health?deep=1").status_code == 401
    assert client.get("/api/health?deep=1", headers={HEADER: "wrong"}).status_code == 401


def test_deep_health_wrong_secret_same_length(client, monkeypatch):
    _patch_settings(monkeypatch, hotline_admin_secret=SECRET)
    wrong = "x" * len(SECRET)
    assert client.get("/api/health?deep=1", headers={HEADER: wrong}).status_code == 401


def test_deep_health_unset_admin_secret_is_closed(client, monkeypatch):
    _patch_settings(monkeypatch, hotline_admin_secret=None)
    assert client.get("/api/health?deep=1", headers={HEADER: ""}).status_code == 401


def test_deep_health_salt_fp_matches_sha256_prefix(client, monkeypatch):
    salt = "pepper"
    _patch_settings(monkeypatch, hotline_admin_secret=SECRET, ledger_pin_salt=salt)
    monkeypatch.setattr(main, "_db_status", lambda: "ok")
    body = client.get("/api/health?deep=1", headers={HEADER: SECRET}).json()
    assert body == {
        "status": "ok",
        "db": "ok",
        "salt_fp": hashlib.sha256(salt.encode()).hexdigest()[:8],
    }
    assert salt not in str(body)


def test_deep_health_salt_unset_returns_null_fp(client, monkeypatch):
    _patch_settings(monkeypatch, hotline_admin_secret=SECRET, ledger_pin_salt=None)
    monkeypatch.setattr(main, "_db_status", lambda: "ok")
    response = client.get("/api/health?deep=1", headers={HEADER: SECRET})
    assert response.status_code == 200
    assert response.json()["salt_fp"] is None


@pytest.mark.parametrize(("method", "path"), STUB_ROUTES)
def test_all_stub_routes_return_501(client, method, path):
    response = client.request(method, path)
    assert response.status_code == 501
    assert response.json() == {"status": "not_implemented"}


def test_config_import_does_not_require_secrets(monkeypatch):
    for name in config.Settings.__dataclass_fields__:
        monkeypatch.delenv(name.upper(), raising=False)
    settings = config.load_settings()
    assert settings.database_url is None
    assert settings.ledger_pin_salt is None
    assert settings.price_include_synthetic is True


def test_deep_health_db_failure_reports_error_without_leaking(client, monkeypatch):
    """Exercise the real _db_status: a failing connect must yield db=error, not a 500,
    and neither the database URL nor the exception text may reach the response."""
    url = "postgresql://user:hunter2@pooler.example:6543/postgres"
    _patch_settings(monkeypatch, hotline_admin_secret=SECRET, ledger_pin_salt=None, database_url=url)

    def failing_connect():
        raise RuntimeError(f"could not connect to {url}")

    monkeypatch.setattr(main.db, "connect", failing_connect)
    response = client.get("/api/health?deep=1", headers={HEADER: SECRET})
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "db": "error", "salt_fp": None}
    assert "hunter2" not in response.text
    assert "pooler.example" not in response.text


def test_deep_health_non_ascii_secret_is_401_not_500(client, monkeypatch):
    """hmac.compare_digest raises TypeError on non-ASCII str; the check must compare bytes."""
    _patch_settings(monkeypatch, hotline_admin_secret=SECRET)
    wrong = ("\xe9" * len(SECRET)).encode("latin-1")
    response = client.get("/api/health?deep=1", headers={HEADER: wrong})
    assert response.status_code == 401


def test_plain_health_ignores_admin_header(client, monkeypatch):
    """Plain health must never return deep fields, even with a valid admin secret."""
    _patch_settings(monkeypatch, hotline_admin_secret=SECRET, ledger_pin_salt="pepper")
    response = client.get("/api/health", headers={HEADER: SECRET})
    assert response.json() == {"status": "ok"}

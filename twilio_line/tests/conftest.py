import pytest
from fastapi.testclient import TestClient

from twilio_line import app as line
from twilio_line.tests.signing import AUTH_TOKEN, PUBLIC_BASE_URL


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", AUTH_TOKEN)
    monkeypatch.setenv("PUBLIC_BASE_URL", PUBLIC_BASE_URL)
    return TestClient(line.app)

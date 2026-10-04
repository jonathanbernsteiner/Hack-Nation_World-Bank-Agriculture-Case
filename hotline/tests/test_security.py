import base64
import dataclasses
import hashlib
import hmac
import logging
import time

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from hotline import config, security

TOOL = "tool-secret-value"
ADMIN = "admin-secret-value"
WEBHOOK = "whsec_test"
NOW = 1_700_000_000
BODY = b'{"type":"post_call_transcription"}'
KNOWN_HEX = "02c2877dc2f785ce97475b66c6b9a512019eaab5809f9021e6221d8571ebcfaa"


def _patch(monkeypatch, **overrides):
    monkeypatch.setattr(config, "settings", dataclasses.replace(config.settings, **overrides))


@pytest.fixture
def client():
    app = FastAPI()

    @app.get("/tool", dependencies=[Depends(security.require_tool_secret)])
    def tool():
        return {"ok": True}

    @app.get("/admin", dependencies=[Depends(security.require_admin_secret)])
    def admin():
        return {"ok": True}

    @app.get("/demo", dependencies=[Depends(security.require_demo_basic_auth)])
    def demo():
        return {"ok": True}

    return TestClient(app)


def _sign(body: bytes, ts: int, secret: str = WEBHOOK) -> str:
    digest = hmac.new(secret.encode(), f"{ts}.".encode() + body, hashlib.sha256).hexdigest()
    return f"t={ts},v0={digest}"


# tool secret


def test_tool_secret_missing_401(client, monkeypatch):
    _patch(monkeypatch, hotline_tool_secret=TOOL)
    assert client.get("/tool").status_code == 401


def test_tool_secret_wrong_401(client, monkeypatch):
    _patch(monkeypatch, hotline_tool_secret=TOOL)
    assert client.get("/tool", headers={"X-Hotline-Tool-Secret": "nope"}).status_code == 401
    same_len = "x" * len(TOOL)
    assert client.get("/tool", headers={"X-Hotline-Tool-Secret": same_len}).status_code == 401


def test_tool_secret_ok(client, monkeypatch):
    _patch(monkeypatch, hotline_tool_secret=TOOL)
    assert client.get("/tool", headers={"X-Hotline-Tool-Secret": TOOL}).status_code == 200


def test_tool_secret_server_unset_fails_closed(client, monkeypatch):
    _patch(monkeypatch, hotline_tool_secret=None)
    assert client.get("/tool").status_code == 401
    assert client.get("/tool", headers={"X-Hotline-Tool-Secret": ""}).status_code == 401
    assert client.get("/tool", headers={"X-Hotline-Tool-Secret": "anything"}).status_code == 401


def test_tool_secret_non_ascii_is_401_not_500(client, monkeypatch):
    _patch(monkeypatch, hotline_tool_secret=TOOL)
    response = client.get("/tool", headers={"X-Hotline-Tool-Secret": "\xe9\xe9".encode("latin-1")})
    assert response.status_code == 401


# admin secret


def test_admin_secret_missing_401(client, monkeypatch):
    _patch(monkeypatch, hotline_admin_secret=ADMIN)
    assert client.get("/admin").status_code == 401


def test_admin_secret_wrong_401(client, monkeypatch):
    _patch(monkeypatch, hotline_admin_secret=ADMIN)
    assert client.get("/admin", headers={"X-Hotline-Admin-Secret": "nope"}).status_code == 401


def test_admin_secret_ok(client, monkeypatch):
    _patch(monkeypatch, hotline_admin_secret=ADMIN)
    assert client.get("/admin", headers={"X-Hotline-Admin-Secret": ADMIN}).status_code == 200


def test_admin_secret_server_unset_fails_closed(client, monkeypatch):
    _patch(monkeypatch, hotline_admin_secret=None)
    assert client.get("/admin", headers={"X-Hotline-Admin-Secret": ""}).status_code == 401


def test_tool_secret_does_not_open_admin(client, monkeypatch):
    _patch(monkeypatch, hotline_tool_secret=TOOL, hotline_admin_secret=ADMIN)
    assert client.get("/admin", headers={"X-Hotline-Admin-Secret": TOOL}).status_code == 401


# ElevenLabs signature


def test_signature_valid():
    assert security.verify_elevenlabs_signature(BODY, _sign(BODY, NOW), WEBHOOK, now=NOW)


def test_signature_known_answer():
    header = f"t={NOW},v0={KNOWN_HEX}"
    assert security.verify_elevenlabs_signature(BODY, header, WEBHOOK, now=NOW)


def test_signature_tampered_body():
    header = _sign(BODY, NOW)
    assert not security.verify_elevenlabs_signature(BODY + b" ", header, WEBHOOK, now=NOW)


def test_signature_wrong_secret():
    assert not security.verify_elevenlabs_signature(BODY, _sign(BODY, NOW, "other"), WEBHOOK, now=NOW)


def test_signature_expired_timestamp():
    header = _sign(BODY, NOW)
    assert security.verify_elevenlabs_signature(BODY, header, WEBHOOK, now=NOW + 1800)
    assert not security.verify_elevenlabs_signature(BODY, header, WEBHOOK, now=NOW + 1801)


def test_signature_future_timestamp_beyond_tolerance():
    header = _sign(BODY, NOW)
    assert security.verify_elevenlabs_signature(BODY, header, WEBHOOK, now=NOW - 1800)
    assert not security.verify_elevenlabs_signature(BODY, header, WEBHOOK, now=NOW - 1801)


@pytest.mark.parametrize(
    "header",
    ["", "garbage", "t=abc,v0=ff", f"t={NOW}", "v0=ff", f"t={NOW},v0", f"t={NOW},v0=zz", None],
)
def test_signature_malformed_header(header):
    assert security.verify_elevenlabs_signature(BODY, header, WEBHOOK, now=NOW) is False


def test_signature_secret_unset():
    header = _sign(BODY, NOW, "")
    assert not security.verify_elevenlabs_signature(BODY, header, None, now=NOW)
    assert not security.verify_elevenlabs_signature(BODY, header, "", now=NOW)


def test_signature_invalid_utf8_body_does_not_raise():
    body = b"\xff\xfe"
    assert security.verify_elevenlabs_signature(body, _sign(body, NOW), WEBHOOK, now=NOW)


# demo basic auth


def _basic(user: str, password: str) -> dict[str, str]:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def test_basic_auth_ok_and_wrong(client, monkeypatch):
    _patch(monkeypatch, demo_user="judge", demo_password="pw-1234")
    assert client.get("/demo", headers=_basic("judge", "pw-1234")).status_code == 200
    for headers in (_basic("judge", "bad"), _basic("bad", "pw-1234"), _basic("bad", "bad")):
        response = client.get("/demo", headers=headers)
        assert response.status_code == 401
        assert response.headers["WWW-Authenticate"] == "Basic"


def test_basic_auth_missing_header_401_with_challenge(client, monkeypatch):
    _patch(monkeypatch, demo_user="judge", demo_password="pw-1234")
    response = client.get("/demo")
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Basic"


def test_basic_auth_server_unset_fails_closed(client, monkeypatch):
    _patch(monkeypatch, demo_user=None, demo_password=None)
    assert client.get("/demo", headers=_basic("", "")).status_code == 401
    assert client.get("/demo", headers=_basic("judge", "pw")).status_code == 401


# review regressions


def test_admin_secret_does_not_open_tool(client, monkeypatch):
    _patch(monkeypatch, hotline_tool_secret=TOOL, hotline_admin_secret=ADMIN)
    assert client.get("/tool", headers={"X-Hotline-Tool-Secret": ADMIN}).status_code == 401


def test_signature_matches_spec_string_formula_for_utf8_body():
    # Spec §7 signs f"{t}.{raw_body}" as text; the bytes form must agree for UTF-8 bodies.
    text = '{"type":"post_call_transcription","data":{"transcript":"Habari, bei ya kahawa ☕"}}'
    digest = hmac.new(WEBHOOK.encode("utf-8"), f"{NOW}.{text}".encode("utf-8"), hashlib.sha256).hexdigest()
    header = f"t={NOW},v0={digest}"
    assert security.verify_elevenlabs_signature(text.encode("utf-8"), header, WEBHOOK, now=NOW)


def test_signature_timestamp_is_covered_by_mac():
    # Replaying an old signature with a fresh timestamp must fail.
    old = _sign(BODY, NOW - 3600)
    digest = old.split("v0=", 1)[1]
    assert not security.verify_elevenlabs_signature(BODY, f"t={NOW},v0={digest}", WEBHOOK, now=NOW)


def test_signature_uses_real_clock_by_default():
    fresh = int(time.time())
    assert security.verify_elevenlabs_signature(BODY, _sign(BODY, fresh), WEBHOOK)
    stale = fresh - security.SIGNATURE_TOLERANCE_S - 60
    assert not security.verify_elevenlabs_signature(BODY, _sign(BODY, stale), WEBHOOK)


@pytest.mark.parametrize("ts", ["9" * 400, "-" + "9" * 400], ids=["huge", "huge-negative"])
def test_signature_huge_timestamp_returns_false_with_real_clock(ts):
    assert security.verify_elevenlabs_signature(BODY, f"t={ts},v0=ff", WEBHOOK) is False


@pytest.mark.parametrize(
    "authorization",
    ["Basic !!!not-base64", "Basic " + base64.b64encode(b"no-colon").decode(), "Bearer judge:pw-1234", "Basic"],
)
def test_basic_auth_malformed_header_401_with_challenge(client, monkeypatch, authorization):
    _patch(monkeypatch, demo_user="judge", demo_password="pw-1234")
    response = client.get("/demo", headers={"Authorization": authorization})
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Basic"


def test_basic_auth_password_unset_fails_closed(client, monkeypatch):
    _patch(monkeypatch, demo_user="judge", demo_password=None)
    assert client.get("/demo", headers=_basic("judge", "")).status_code == 401


# review cycle 2 regressions


@pytest.mark.parametrize(
    ("path", "value"),
    [("/tool", TOOL), ("/admin", ADMIN)],
)
@pytest.mark.parametrize("name", ["x_hotline_tool_secret", "x_hotline_admin_secret", "X-Hotline-Tool-Secret"])
def test_secret_in_query_string_never_authenticates(client, monkeypatch, path, value, name):
    # Secrets come only from headers; a query parameter (which lands in access logs) must not open a route.
    _patch(monkeypatch, hotline_tool_secret=TOOL, hotline_admin_secret=ADMIN)
    assert client.get(path, params={name: value}).status_code == 401


def test_401_is_generic_and_never_echoes_secrets(client, monkeypatch):
    _patch(monkeypatch, hotline_tool_secret=TOOL, hotline_admin_secret=ADMIN, demo_user="judge", demo_password="pw-1234")
    responses = [
        client.get("/tool", headers={"X-Hotline-Tool-Secret": "guess-1"}),
        client.get("/admin", headers={"X-Hotline-Admin-Secret": "guess-2"}),
        client.get("/demo", headers=_basic("judge", "guess-3")),
    ]
    for response in responses:
        assert response.status_code == 401
        assert response.json() == {"detail": "unauthorized"}
        dump = response.text + repr(sorted(response.headers.items()))
        for value in (TOOL, ADMIN, "pw-1234", "judge", "guess-1", "guess-2", "guess-3"):
            assert value not in dump


def test_auth_paths_log_no_secret(client, monkeypatch, caplog):
    caplog.set_level(logging.DEBUG)
    _patch(monkeypatch, hotline_tool_secret=TOOL, hotline_admin_secret=ADMIN, demo_user="judge", demo_password="pw-1234")
    client.get("/tool", headers={"X-Hotline-Tool-Secret": TOOL})
    client.get("/tool", headers={"X-Hotline-Tool-Secret": "guess-1"})
    client.get("/admin", headers={"X-Hotline-Admin-Secret": ADMIN})
    client.get("/demo", headers=_basic("judge", "pw-1234"))
    client.get("/demo", headers=_basic("judge", "guess-3"))
    security.verify_elevenlabs_signature(BODY, _sign(BODY, NOW), WEBHOOK, now=NOW)
    security.verify_elevenlabs_signature(BODY, "t=x,v0=y", WEBHOOK, now=NOW)
    for value in (TOOL, ADMIN, WEBHOOK, "pw-1234", "guess-1", "guess-3"):
        assert value not in caplog.text


@pytest.mark.parametrize(
    "header",
    [
        f"t={'9' * 5000},v0=ff",  # beyond int()'s digit limit: ValueError path
        f"t={NOW},v0=\xe9\xe9",  # non-ASCII digest (headers arrive latin-1 decoded)
        f"t={NOW},v0={KNOWN_HEX},",  # trailing empty field
        f"t={NOW},v0={KNOWN_HEX[:-1]}",  # truncated digest
        f"t={NOW},v1={KNOWN_HEX}",  # unknown scheme only
        f"t={NOW + 1},v0={KNOWN_HEX}",  # digest bound to a different timestamp
    ],
    ids=["t-5000-digits", "non-ascii-v0", "trailing-comma", "truncated-v0", "v1-only", "t-off-by-one"],
)
def test_signature_hostile_header_returns_false(header):
    assert security.verify_elevenlabs_signature(BODY, header, WEBHOOK, now=NOW) is False


def test_signature_empty_body_is_still_signed():
    # An empty body signs "t." only; a digest for the real body must not verify an empty one and vice versa.
    assert security.verify_elevenlabs_signature(b"", _sign(b"", NOW), WEBHOOK, now=NOW)
    assert not security.verify_elevenlabs_signature(b"", _sign(BODY, NOW), WEBHOOK, now=NOW)
    assert not security.verify_elevenlabs_signature(BODY, _sign(b"", NOW), WEBHOOK, now=NOW)

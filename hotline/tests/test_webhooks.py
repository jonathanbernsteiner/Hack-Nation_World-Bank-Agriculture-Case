"""POST /api/calls: signature checks, idempotent storage and response time (issue #11)."""

import copy
import dataclasses
import hashlib
import hmac
import json
import logging
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from hotline import config
from hotline.main import app
from hotline.routes import webhooks

SECRET = "whsec_test_secret"
FIXTURE = Path(__file__).parent / "fixtures" / "post_call_transcription.json"
RESPONSE_BUDGET_S = 1.0


def _payload() -> dict:
    return json.loads(FIXTURE.read_text())


def _sign(body: bytes, timestamp: int | None = None, secret: str = SECRET) -> str:
    ts = int(time.time()) if timestamp is None else timestamp
    digest = hmac.new(secret.encode(), f"{ts}.".encode() + body, hashlib.sha256).hexdigest()
    return f"t={ts},v0={digest}"


def _post(client, payload: dict | bytes, header: str | None = "auto"):
    body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
    headers = {"content-type": "application/json"}
    if header == "auto":
        header = _sign(body)
    if header is not None:
        headers["ElevenLabs-Signature"] = header
    return client.post("/api/calls", content=body, headers=headers)


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(
        config, "settings", dataclasses.replace(config.settings, elevenlabs_webhook_secret=SECRET)
    )
    return TestClient(app)


@pytest.fixture
def stub_store(monkeypatch):
    """Replace the DB write and the process hook; record how often each ran."""
    calls = {"store": [], "process": []}

    def fake_store(conversation_id, data):
        calls["store"].append(conversation_id)
        return "stored"

    monkeypatch.setattr(webhooks, "_store_in_transaction", fake_store)
    monkeypatch.setattr(webhooks, "process_call", lambda cid: calls["process"].append(cid))
    return calls


@pytest.fixture
def rollback_store(monkeypatch, db):
    """Run the real SQL on the explicit rolled-back connection (never commits)."""
    monkeypatch.setattr(
        webhooks, "_store_in_transaction", lambda cid, data: webhooks.store_call(db, cid, data)
    )
    monkeypatch.setattr(webhooks, "process_call", lambda cid: None)
    return db


def test_valid_signature_stores_and_schedules_process(client, stub_store):
    response = _post(client, _payload())
    assert response.status_code == 200
    assert response.json() == {"status": "stored"}
    assert stub_store["store"] == [_payload()["data"]["conversation_id"]]
    assert stub_store["process"] == stub_store["store"]


def test_tampered_body_is_401_and_writes_nothing(client, stub_store):
    body = json.dumps(_payload()).encode()
    header = _sign(body)
    response = client.post("/api/calls", content=body.replace(b"kahawa", b"kahawA"),
                           headers={"ElevenLabs-Signature": header})
    assert response.status_code == 401
    assert stub_store["store"] == [] and stub_store["process"] == []


def test_stale_timestamp_is_401(client, stub_store):
    body = json.dumps(_payload()).encode()
    stale = _sign(body, timestamp=int(time.time()) - 31 * 60)
    assert _post(client, body, header=stale).status_code == 401
    assert stub_store["store"] == []


def test_missing_header_is_401(client, stub_store):
    assert _post(client, _payload(), header=None).status_code == 401
    assert stub_store["store"] == []


def test_unset_secret_rejects_everything(monkeypatch, stub_store):
    monkeypatch.setattr(
        config, "settings", dataclasses.replace(config.settings, elevenlabs_webhook_secret=None)
    )
    assert _post(TestClient(app), _payload()).status_code == 401


def test_non_transcription_event_is_ignored(client, stub_store):
    event = _payload() | {"type": "post_call_audio"}
    response = _post(client, event)
    assert response.status_code == 200
    assert response.json() == {"status": "ignored"}
    assert stub_store["store"] == []


def test_unknown_fields_and_null_tool_calls_are_accepted(client, stub_store):
    event = _payload()
    event["surprise"] = {"x": 1}
    event["data"]["transcript"][0]["tool_calls"] = None
    assert _post(client, event).json() == {"status": "stored"}


def test_signed_but_missing_conversation_id_is_400(client, stub_store):
    event = _payload()
    del event["data"]["conversation_id"]
    assert _post(client, event).status_code == 400
    assert stub_store["store"] == []


def test_signed_invalid_json_is_400(client, stub_store):
    assert _post(client, b"not json").status_code == 400


def test_response_is_fast_with_db_stubbed(client, stub_store):
    body = json.dumps(_payload()).encode()
    started = time.perf_counter()
    response = _post(client, body)
    assert response.status_code == 200
    assert time.perf_counter() - started < RESPONSE_BUDGET_S


def test_store_failure_is_503_and_logs_no_payload(client, monkeypatch, caplog):
    def boom(conversation_id, data):
        raise RuntimeError("DETAIL: Key contains Nimeuza kilo hamsini")

    monkeypatch.setattr(webhooks, "_store_in_transaction", boom)
    with caplog.at_level(logging.DEBUG):
        response = _post(client, _payload())
    assert response.status_code == 503
    assert "Nimeuza" not in caplog.text
    assert _payload()["data"]["conversation_id"] in caplog.text


def test_process_hook_not_scheduled_for_duplicates(client, monkeypatch):
    ran = []
    monkeypatch.setattr(webhooks, "_store_in_transaction", lambda cid, data: "duplicate")
    monkeypatch.setattr(webhooks, "process_call", lambda cid: ran.append(cid))
    assert _post(client, _payload()).json() == {"status": "duplicate"}
    assert ran == []


def test_transcript_lines_and_tool_results_are_minimal():
    data = _payload()["data"]
    data["transcript"][1]["tool_results"] = [
        {"tool_name": "identify", "request_id": "r1", "is_error": False,
         "result_value": '{"status":"ok"}', "params_as_json": '{"pin":"1234"}'}
    ]
    params = webhooks._row_params("conv_x", data)
    lines = json.loads(params["lines"])
    assert [line["role"] for line in lines][:2] == ["agent", "farmer"]
    assert [line["i"] for line in lines] == list(range(len(lines)))
    scrubbed = json.loads(params["tool_results"])
    assert scrubbed == [{"tool_name": "identify", "request_id": "r1", "t": 0,
                         "is_error": False, "result": '{"status":"ok"}'}]
    assert "1234" not in params["tool_results"]
    assert params["audio_path"] == "elevenlabs:conv_x"


# ---- real database, rolled back, connection passed explicitly (RUN_SUPABASE=1) ----

CONV = "conv_test_issue11"


def _count(conn, conversation_id=CONV) -> int:
    return conn.execute(
        "select count(*) from calls where conversation_id = %s", (conversation_id,)
    ).fetchone()[0]


def _data(conversation_id=CONV) -> dict:
    data = copy.deepcopy(_payload()["data"])
    data["conversation_id"] = conversation_id
    return data


@pytest.mark.supabase
def test_db_first_delivery_stores_row(rollback_store):
    assert webhooks.store_call(rollback_store, CONV, _data()) == "stored"
    row = rollback_store.execute(
        "select source, status, audio_path, language, duration_secs, farmer_id,"
        " jsonb_array_length(transcript_lines), is_synthetic from calls where conversation_id = %s",
        (CONV,),
    ).fetchone()
    assert row == ("elevenlabs", "received", f"elevenlabs:{CONV}", "sw", 14, None, 9, False)


@pytest.mark.supabase
def test_db_duplicate_delivery_is_one_row(rollback_store):
    assert webhooks.store_call(rollback_store, CONV, _data()) == "stored"
    assert webhooks.store_call(rollback_store, CONV, _data()) == "duplicate"
    assert _count(rollback_store) == 1


@pytest.mark.supabase
def test_db_duplicate_does_not_overwrite_a_processed_row(rollback_store):
    webhooks.store_call(rollback_store, CONV, _data())
    rollback_store.execute(
        "update calls set status = 'processed', transcript_en = 'done' where conversation_id = %s",
        (CONV,),
    )
    assert webhooks.store_call(rollback_store, CONV, _data()) == "duplicate"
    assert rollback_store.execute(
        "select status, transcript_en from calls where conversation_id = %s", (CONV,)
    ).fetchone() == ("processed", "done")


@pytest.mark.supabase
def test_db_in_call_row_keeps_farmer_and_identified_by(rollback_store):
    farmer_id = rollback_store.execute(
        "insert into farmers (name, pin_hash) values ('Test Farmer', 'hash-issue11') returning id"
    ).fetchone()[0]
    rollback_store.execute(
        "insert into calls (conversation_id, farmer_id, identified_by, status, source, is_synthetic)"
        " values (%s, %s, 'pin', 'in_call', 'elevenlabs', true)",
        (CONV, farmer_id),
    )
    assert webhooks.store_call(rollback_store, CONV, _data()) == "stored"
    row = rollback_store.execute(
        "select farmer_id, identified_by, status, is_synthetic, transcript_sw is not null"
        " from calls where conversation_id = %s",
        (CONV,),
    ).fetchone()
    assert row == (farmer_id, "pin", "received", True, True)
    assert _count(rollback_store) == 1

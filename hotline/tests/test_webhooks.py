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
    monkeypatch.setattr(webhooks.process, "process_call", lambda cid: calls["process"].append(cid))
    return calls


@pytest.fixture
def rollback_store(monkeypatch, db):
    """Run the real SQL on the explicit rolled-back connection (never commits)."""
    monkeypatch.setattr(
        webhooks, "_store_in_transaction", lambda cid, data: webhooks.store_call(db, cid, data)
    )
    monkeypatch.setattr(webhooks.process, "process_call", lambda cid: None)
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
    monkeypatch.setattr(webhooks.process, "process_call", lambda cid: ran.append(cid))
    assert _post(client, _payload()).json() == {"status": "duplicate"}
    assert ran == []


def test_transcript_lines_and_tool_results_are_minimal():
    data = _payload()["data"]
    data["transcript"][1]["tool_calls"] = [
        {"tool_name": "identify", "request_id": "r1", "params_as_json": '{"pin":"1234"}'}
    ]
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
                         "is_error": False, "result": {"status": "ok"}}]
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


# ---- review regression tests (PR #84, cycle 1) ----

PIN = "4831"
PIN_WORDS_SW = "nne, nane, tatu, moja"
FARMER_PHRASE = "Nimeuza kilo hamsini"


def _with_new_pin(data: dict) -> dict:
    """A registration call: the tool answers with a new PIN, the agent reads it back in
    Kiswahili words and digits, and the farmer types it."""
    data = copy.deepcopy(data)
    turns = data["transcript"]
    turns[2]["tool_calls"] = [
        {"request_id": "r1", "tool_name": "register_farmer", "type": "webhook",
         "tool_has_been_called": True,
         "params_as_json": json.dumps({"first_name": "Mukasa", "district": "Masaka"})}
    ]
    turns[2]["tool_results"] = [
        {"request_id": "r1", "tool_name": "register_farmer", "is_error": False,
         "tool_has_been_called": True,
         "result_value": json.dumps({"status": "registered", "pin": PIN, "pin_digits_sw": PIN_WORDS_SW})}
    ]
    turns[4]["message"] = f"Namba yako mpya ya siri ni {PIN_WORDS_SW}. Narudia: {PIN}."
    turns[5]["message"] = PIN
    return data


def test_tool_results_never_store_a_new_pin():
    params = webhooks._row_params("conv_x", _with_new_pin(_payload()["data"]))
    assert PIN not in params["tool_results"]
    assert PIN_WORDS_SW not in params["tool_results"]


@pytest.mark.parametrize("field", ["lines", "transcript_sw"])
def test_stored_transcript_never_holds_a_pin(field):
    params = webhooks._row_params("conv_x", _with_new_pin(_payload()["data"]))
    assert PIN not in params[field]
    assert PIN_WORDS_SW not in params[field]


def test_signature_covers_the_raw_bytes_as_sent(client, stub_store):
    """Pretty-printed non-ASCII bytes verify as sent; a re-serialising receiver would 401."""
    event = _payload()
    event["data"]["transcript"][1]["message"] = "Habari — nataka kuuza kahawa yangu."
    body = json.dumps(event, indent=2, ensure_ascii=False).encode()
    assert _post(client, body).json() == {"status": "stored"}


def test_signature_of_equivalent_json_is_401(client, stub_store):
    compact = json.dumps(_payload(), separators=(",", ":")).encode()
    pretty = json.dumps(_payload(), indent=2).encode()
    assert _post(client, pretty, header=_sign(compact)).status_code == 401
    assert stub_store == {"store": [], "process": []}


def test_signature_with_another_secret_is_401(client, stub_store):
    body = json.dumps(_payload()).encode()
    assert _post(client, body, header=_sign(body, secret="whsec_other")).status_code == 401
    assert stub_store == {"store": [], "process": []}


def test_timestamp_inside_the_30_minute_tolerance_is_accepted(client, stub_store):
    body = json.dumps(_payload()).encode()
    recent = _sign(body, timestamp=int(time.time()) - 29 * 60)
    assert _post(client, body, header=recent).json() == {"status": "stored"}


@pytest.mark.parametrize(
    "body", [b"not json", json.dumps({"type": "post_call_audio"}).encode(), b"[]"]
)
def test_unsigned_requests_are_401_before_any_parsing(client, stub_store, body):
    response = _post(client, body, header=None)
    assert response.status_code == 401
    assert stub_store == {"store": [], "process": []}


def test_unset_secret_writes_nothing(monkeypatch, stub_store):
    monkeypatch.setattr(
        config, "settings", dataclasses.replace(config.settings, elevenlabs_webhook_secret=None)
    )
    assert _post(TestClient(app), _payload()).status_code == 401
    assert stub_store == {"store": [], "process": []}


def test_ignored_event_schedules_nothing(client, stub_store):
    assert _post(client, _payload() | {"type": "post_call_audio"}).json() == {"status": "ignored"}
    assert stub_store["process"] == []


@pytest.mark.parametrize("header", ["auto", None])
def test_request_path_never_logs_farmer_speech(client, stub_store, caplog, header):
    with caplog.at_level(logging.DEBUG):
        _post(client, _payload(), header=header)
    assert FARMER_PHRASE in json.dumps(_payload(), ensure_ascii=False)
    assert FARMER_PHRASE not in caplog.text


def _insert_in_call_row(conn, pin_hash: str) -> int:
    farmer_id = conn.execute(
        "insert into farmers (name, pin_hash) values ('Test Farmer', %s) returning id", (pin_hash,)
    ).fetchone()[0]
    conn.execute(
        "insert into calls (conversation_id, farmer_id, identified_by, status, source)"
        " values (%s, %s, 'pin', 'in_call', 'elevenlabs')",
        (CONV, farmer_id),
    )
    return farmer_id


@pytest.mark.supabase
def test_db_route_duplicate_delivery_end_to_end(client, rollback_store):
    """Required test 5 through the HTTP route and the real SQL: stored, duplicate, one row."""
    event = _payload()
    event["data"]["conversation_id"] = CONV
    assert _post(client, event).json() == {"status": "stored"}
    assert _post(client, event).json() == {"status": "duplicate"}
    assert _count(rollback_store) == 1


@pytest.mark.supabase
def test_db_retry_after_in_call_takeover_is_duplicate_and_keeps_farmer(rollback_store):
    farmer_id = _insert_in_call_row(rollback_store, "hash-issue11-retry")
    assert webhooks.store_call(rollback_store, CONV, _data()) == "stored"
    assert webhooks.store_call(rollback_store, CONV, _data()) == "duplicate"
    assert rollback_store.execute(
        "select farmer_id, identified_by, status from calls where conversation_id = %s", (CONV,)
    ).fetchone() == (farmer_id, "pin", "received")


@pytest.mark.supabase
def test_db_received_at_is_the_call_start(rollback_store):
    data = _data()
    started = data["metadata"]["start_time_unix_secs"]
    webhooks.store_call(rollback_store, CONV, data)
    assert rollback_store.execute(
        "select received_at = to_timestamp(%s) from calls where conversation_id = %s", (started, CONV)
    ).fetchone() == (True,)


@pytest.mark.supabase
def test_db_missing_start_time_falls_back_to_now(rollback_store):
    data = _data()
    del data["metadata"]["start_time_unix_secs"]
    assert webhooks.store_call(rollback_store, CONV, data) == "stored"
    assert rollback_store.execute(
        "select received_at = now() from calls where conversation_id = %s", (CONV,)
    ).fetchone() == (True,)


# ---- review regression tests (PR #84, cycle 2) ----

PHONE = "+256772123456"
AGENT_NUMBER = "+15555550100"
CALL_SID = "CA0123456789abcdef0123456789abcdef"
ID_PIN = "9001"
MEDIAN = 5300


def _phone_call(data: dict) -> dict:
    """A real phone call: caller id in metadata and dynamic variables, call_sid in the tool
    params, and an identify_farmer result that echoes the caller id."""
    data = copy.deepcopy(data)
    data["metadata"]["phone_call"] = {
        "direction": "inbound", "type": "twilio", "external_number": PHONE,
        "agent_number": AGENT_NUMBER, "call_sid": CALL_SID,
    }
    data["conversation_initiation_client_data"]["dynamic_variables"].update(
        {"system__caller_id": PHONE, "system__called_number": AGENT_NUMBER, "system__call_sid": CALL_SID}
    )
    turn = data["transcript"][2]
    turn["tool_calls"] = [
        {"request_id": "r9", "tool_name": "identify_farmer",
         "params_as_json": json.dumps({"pin": ID_PIN, "conversation_id": "c", "call_sid": CALL_SID})}
    ]
    turn["tool_results"] = [
        {"request_id": "r9", "tool_name": "identify_farmer", "is_error": False,
         "result_value": json.dumps({
             "status": "found", "identified_by": "pin", "caller_id": PHONE,
             "farmer": {"first_name": "Nakato", "district": "Masaka"},
             "village_price": {"form": "kiboko", "median_ugx_per_kg": MEDIAN, "n_sales": 7},
         })}
    ]
    return data


def test_phone_number_and_call_sid_are_never_stored():
    params = webhooks._row_params("conv_x", _phone_call(_payload()["data"]))
    stored = json.dumps(params, ensure_ascii=False)
    for secret in (PHONE, PHONE.lstrip("+"), AGENT_NUMBER, CALL_SID, ID_PIN):
        assert secret not in stored


def test_tool_results_keep_price_medians_as_numbers():
    """verify (#59) walks tool_results for numeric median_ugx_per_kg: `result` must stay parsed JSON."""
    scrubbed = json.loads(webhooks._row_params("conv_x", _phone_call(_payload()["data"]))["tool_results"])
    assert [item["tool_name"] for item in scrubbed] == ["identify_farmer"]
    assert scrubbed[0]["result"]["village_price"]["median_ugx_per_kg"] == MEDIAN


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d.update(transcript=None),
        lambda d: d.update(metadata=None),
        lambda d: d.update(transcript=[None, "text", 3]),
        lambda d: d["transcript"][0].update(role=None, message=None),
        lambda d: d["transcript"][0].update(
            tool_calls=None, tool_results=[{"request_id": "orphan", "result_value": "not json"}]
        ),
    ],
    ids=["null_transcript", "null_metadata", "non_dict_turns", "null_role_message", "orphan_result"],
)
def test_odd_signed_shapes_build_a_row_instead_of_a_503_loop(mutate):
    """Any exception here becomes a 503 and ElevenLabs retries until it disables the webhook."""
    data = copy.deepcopy(_payload()["data"])
    mutate(data)
    params = webhooks._row_params("conv_x", data)
    assert isinstance(json.loads(params["lines"]), list)
    assert isinstance(json.loads(params["tool_results"]), list)


def test_store_failure_schedules_no_processing(client, monkeypatch):
    ran = []

    def boom(conversation_id, data):
        raise RuntimeError("pooler down")

    monkeypatch.setattr(webhooks, "_store_in_transaction", boom)
    monkeypatch.setattr(webhooks.process, "process_call", lambda cid: ran.append(cid))
    assert _post(client, _payload()).status_code == 503
    assert ran == []


@pytest.mark.supabase
@pytest.mark.parametrize("status", ["received", "processing", "failed", "needs_review"])
def test_db_retry_never_rewrites_a_row_past_in_call(rollback_store, status):
    """A retry during or after processing must not reset the row or its transcript."""
    rollback_store.execute(
        "insert into calls (conversation_id, status, source, transcript_sw) values (%s, %s, 'elevenlabs', 'kept')",
        (CONV, status),
    )
    assert webhooks.store_call(rollback_store, CONV, _data()) == "duplicate"
    assert rollback_store.execute(
        "select status, transcript_sw, transcript_lines from calls where conversation_id = %s", (CONV,)
    ).fetchone() == (status, "kept", None)


@pytest.mark.supabase
def test_db_in_call_row_from_failed_pins_keeps_attempts(rollback_store):
    """#51 creates an in_call row with no farmer when a PIN fails; the takeover keeps the count."""
    rollback_store.execute(
        "insert into calls (conversation_id, status, source, pin_attempts) values (%s, 'in_call', 'elevenlabs', 2)",
        (CONV,),
    )
    data = _data()
    assert webhooks.store_call(rollback_store, CONV, data) == "stored"
    assert rollback_store.execute(
        "select status, farmer_id, pin_attempts, received_at = to_timestamp(%s),"
        " jsonb_array_length(transcript_lines) from calls where conversation_id = %s",
        (data["metadata"]["start_time_unix_secs"], CONV),
    ).fetchone() == ("received", None, 2, True, 9)
    assert _count(rollback_store) == 1


@pytest.mark.supabase
def test_db_route_takeover_schedules_processing_once(client, rollback_store, monkeypatch):
    ran = []
    monkeypatch.setattr(webhooks.process, "process_call", lambda cid: ran.append(cid))
    farmer_id = _insert_in_call_row(rollback_store, "hash-issue11-route")
    event = _payload()
    event["data"]["conversation_id"] = CONV
    assert _post(client, event).json() == {"status": "stored"}
    assert _post(client, event).json() == {"status": "duplicate"}
    assert ran == [CONV]
    assert rollback_store.execute(
        "select farmer_id, status from calls where conversation_id = %s", (CONV,)
    ).fetchone() == (farmer_id, "received")


@pytest.mark.supabase
def test_db_route_stores_no_pin_in_any_column(client, rollback_store):
    """Checklist item 'stored lines are redacted', end to end: route, real SQL, jsonb columns."""
    event = _payload()
    event["data"] = _with_new_pin(_data())
    assert _post(client, event).json() == {"status": "stored"}
    lines, rendered, tools = rollback_store.execute(
        "select transcript_lines::text, transcript_sw, tool_results::text from calls"
        " where conversation_id = %s",
        (CONV,),
    ).fetchone()
    for column in (lines, rendered, tools):
        assert PIN not in column
        assert PIN_WORDS_SW not in column
    assert "[PIN]" in rendered and "[PIN]" in tools

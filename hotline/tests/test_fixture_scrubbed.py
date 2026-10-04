"""Regression checks for the #39 post-call webhook fixture: shape and scrubbing."""

import json
import os
import re
from pathlib import Path

FIXTURE = Path(__file__).parent / "fixtures" / "post_call_transcription.json"
TIMESTAMP_KEY = "event_timestamp"
TIMESTAMP_SUFFIX = "_unix_secs"
MIN_TURNS = 4
PHONE_PLUS = re.compile(r"\+\d{6,}")
LONG_DIGITS = re.compile(r"\d{9,}")
PIN_LIKE = re.compile(r"(?<!\d)\d{4,8}(?!\d)")
REAL_AGENT_ID = re.compile(r"\bagent_[0-9a-z]{28}\b")
CALLER_VARS = (
    "system__caller_id",
    "system__called_number",
    "system__call_sid",
    "system__user_id",
    "system__call_id",
    "system__initiator_id",
)
MESSAGE_FIELDS = ("message", "original_message")
SECRET_ENV_NAMES = (
    "ELEVENLABS_API_KEY",
    "ELEVENLABS_AGENT_ID",
    "ELEVENLABS_WEBHOOK_SECRET",
    "HOTLINE_TOOL_SECRET",
    "HOTLINE_ADMIN_SECRET",
    "LEDGER_PIN_SALT",
    "DEMO_PASSWORD",
    "DATABASE_URL",
    "ANTHROPIC_API_KEY",
    "TWILIO_ACCOUNT_SID",
    "TWILIO_AUTH_TOKEN",
    "TWILIO_PHONE_NUMBER",
)


def _load() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _leaves(node, key=""):
    if isinstance(node, dict):
        for child_key, value in node.items():
            yield from _leaves(value, child_key)
    elif isinstance(node, list):
        for item in node:
            yield from _leaves(item, key)
    else:
        yield key, node


def test_fixture_is_webhook_shape():
    body = _load()
    assert body["type"] == "post_call_transcription"
    assert isinstance(body["event_timestamp"], int)
    data = body["data"]
    assert data["conversation_id"]
    assert isinstance(data["metadata"]["start_time_unix_secs"], int)
    turns = data["transcript"]
    assert len(turns) >= MIN_TURNS
    for turn in turns:
        assert turn["role"] in {"agent", "user"}
        assert isinstance(turn["message"], str)
        assert isinstance(turn["time_in_call_secs"], int)
        assert turn["tool_calls"] is None or isinstance(turn["tool_calls"], list)
        assert turn["tool_results"] is None or isinstance(turn["tool_results"], list)


def test_fixture_has_no_phone_numbers():
    for key, value in _leaves(_load()):
        if key == TIMESTAMP_KEY or key.endswith(TIMESTAMP_SUFFIX):
            continue
        text = str(value)
        assert not PHONE_PLUS.search(text), key
        assert not LONG_DIGITS.search(text), key


def test_fixture_caller_fields_are_scrubbed():
    data = _load()["data"]
    assert data["user_id"] is None
    assert data["metadata"]["phone_call"] is None
    dynamic = data["conversation_initiation_client_data"]["dynamic_variables"]
    for name in CALLER_VARS:
        assert dynamic.get(name) is None, name


def test_fixture_has_no_real_agent_id():
    raw = FIXTURE.read_text(encoding="utf-8")
    has_real_format_id = REAL_AGENT_ID.search(raw) is not None
    assert not has_real_format_id, "use a placeholder agent id (spec §3)"
    real_id = os.environ.get("ELEVENLABS_AGENT_ID")
    leaks_env_id = bool(real_id) and real_id in raw
    assert not leaks_env_id, "fixture contains ELEVENLABS_AGENT_ID"


def test_no_turn_carries_pin():
    """Spec §7: agent read-outs count too, not only farmer turns."""
    for turn in _load()["data"]["transcript"]:
        for field in MESSAGE_FIELDS:
            text = turn.get(field) or ""
            assert not PIN_LIKE.search(text), (turn["role"], field, text)


def test_fixture_has_no_secret_env_values():
    """Spec §3: no .env value is ever committed (runs when the env is loaded)."""
    raw = FIXTURE.read_text(encoding="utf-8")
    leaked = [
        name
        for name in SECRET_ENV_NAMES
        if os.environ.get(name) and os.environ[name] in raw
    ]
    assert not leaked, f"fixture contains values of {leaked}"

"""POST /api/calls: the ElevenLabs post-call webhook receiver (docs/hotline-spec.md section 7).

Store first, return fast, process later. The request path does only the HMAC check and one
short database write. Retries are on at ElevenLabs, so a delivery is idempotent by
conversation_id. The payload holds farmer speech: it is never logged, only the id."""

import json
import logging
from typing import Any

import psycopg
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from starlette.concurrency import run_in_threadpool

from hotline import config, db, security

logger = logging.getLogger(__name__)
router = APIRouter()

TRANSCRIPTION_EVENT = "post_call_transcription"
ROLE_MAP = {"agent": "agent", "user": "farmer"}

# New row, or an existing row with no data yet (an `in_call` stub from the identifying tools).
# The in_call update leaves farmer_id, identified_by, is_synthetic and pin_attempts alone.
_INSERT_SQL = """
insert into calls (conversation_id, source, status, language, audio_path, received_at,
                   duration_secs, transcript_lines, transcript_sw, tool_results)
values (%(conversation_id)s, 'elevenlabs', 'received', 'sw', %(audio_path)s,
        coalesce(to_timestamp(%(started)s), now()), %(duration)s,
        %(lines)s, %(transcript_sw)s, %(tool_results)s)
on conflict (conversation_id) do nothing
returning id
"""
_TAKE_OVER_SQL = """
update calls set source = 'elevenlabs', status = 'received', language = 'sw',
       audio_path = %(audio_path)s, received_at = coalesce(to_timestamp(%(started)s), received_at),
       duration_secs = %(duration)s, transcript_lines = %(lines)s,
       transcript_sw = %(transcript_sw)s, tool_results = %(tool_results)s
where conversation_id = %(conversation_id)s and status = 'in_call'
returning id
"""


def process_call(conversation_id: str) -> None:
    """Placeholder for #66, which replaces this call site with the real pipeline
    (translate, extract, verify, save). Until then the pg_cron safety net finds the row."""


def _build_lines(transcript: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # TODO(#57): switch to hotline.pipeline.transcript.to_lines, which also redacts PINs.
    lines: list[dict[str, Any]] = []
    for turn in transcript:
        role = ROLE_MAP.get(turn.get("role"))
        text = (turn.get("message") or "").strip()
        if role and text:
            lines.append({"i": len(lines), "role": role, "sw": text, "t": turn.get("time_in_call_secs")})
    return lines


def _scrub_tool_results(transcript: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep what a tool answered, never what it was asked (parameters carry PINs)."""
    results: list[dict[str, Any]] = []
    for turn in transcript:
        for item in turn.get("tool_results") or []:
            results.append(
                {
                    "tool_name": item.get("tool_name"),
                    "request_id": item.get("request_id"),
                    "t": turn.get("time_in_call_secs"),
                    "is_error": bool(item.get("is_error")),
                    "result": item.get("result_value"),
                }
            )
    return results


def _render_sw(lines: list[dict[str, Any]]) -> str:
    return "\n".join(f"{'Agent' if line['role'] == 'agent' else 'Farmer'}: {line['sw']}" for line in lines)


def _row_params(conversation_id: str, data: dict[str, Any]) -> dict[str, Any]:
    transcript = [t for t in (data.get("transcript") or []) if isinstance(t, dict)]
    metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
    lines = _build_lines(transcript)
    return {
        "conversation_id": conversation_id,
        "audio_path": f"elevenlabs:{conversation_id}",
        "started": metadata.get("start_time_unix_secs"),
        "duration": metadata.get("call_duration_secs"),
        "lines": json.dumps(lines),
        "transcript_sw": _render_sw(lines),
        "tool_results": json.dumps(_scrub_tool_results(transcript)),
    }


def store_call(conn: psycopg.Connection, conversation_id: str, data: dict[str, Any]) -> str:
    """Write the call on `conn` (caller commits). Returns "stored" or "duplicate"."""
    params = _row_params(conversation_id, data)
    for sql in (_INSERT_SQL, _TAKE_OVER_SQL):
        if conn.execute(sql, params).fetchone() is not None:
            return "stored"
    return "duplicate"


def _store_in_transaction(conversation_id: str, data: dict[str, Any]) -> str:
    with db.transaction() as conn:
        return store_call(conn, conversation_id, data)


def _parse_event(raw: bytes) -> dict[str, Any]:
    try:
        event = json.loads(raw)
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid_json") from None
    if not isinstance(event, dict):
        raise HTTPException(status_code=400, detail="invalid_event")
    return event


@router.post("/api/calls")
async def receive_call(request: Request, background_tasks: BackgroundTasks) -> dict[str, str]:
    raw = await request.body()  # raw bytes: re-serialising would break the signature
    header = request.headers.get("elevenlabs-signature")
    if not security.verify_elevenlabs_signature(raw, header, config.settings.elevenlabs_webhook_secret):
        raise HTTPException(status_code=401, detail="unauthorized")

    event = _parse_event(raw)
    if event.get("type") != TRANSCRIPTION_EVENT:
        return {"status": "ignored"}
    data = event.get("data")
    conversation_id = data.get("conversation_id") if isinstance(data, dict) else None
    if not isinstance(conversation_id, str) or not conversation_id:
        raise HTTPException(status_code=400, detail="missing_conversation_id")

    try:
        status = await run_in_threadpool(_store_in_transaction, conversation_id, data)
    except Exception as exc:  # noqa: BLE001 - any failure must become a retryable 503
        # A 5xx makes ElevenLabs retry. Log the error class only: driver messages can echo row data.
        logger.error("storing call %s failed: %s", conversation_id, type(exc).__name__)
        raise HTTPException(status_code=503, detail="store_failed") from None

    if status == "stored":
        background_tasks.add_task(process_call, conversation_id)
    return {"status": status}

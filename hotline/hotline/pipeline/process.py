"""Claim, run and save one call (spec section 7, Process).

Three short steps so no database connection or transaction is open during the model calls
(20-90 s): claim in one transaction, run the pipeline with no connection, then save in a
second transaction. The save only succeeds while this run still owns the claim.
Claims use FOR UPDATE SKIP LOCKED, so BackgroundTasks, the cron sweeper and the CLI can run
at the same time. Re-processing a call deletes its entries first, so it is idempotent.
Transaction pooler safe: no session state, no prepared statements.
"""

from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from typing import Any

import psycopg

from hotline import db
from hotline.pipeline.run import RunResult, run_call

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3
STALE_CLAIM_MINUTES = 5
MAX_LAST_ERROR_CHARS = 500
DEFAULT_PENDING_LIMIT = 5
KAMPALA_TZ = timezone(timedelta(hours=3), "Africa/Kampala")  # no DST in Uganda
# Typed refusal / max_tokens errors from translate.py and extract.py; never retried.
REVIEW_ERRORS = frozenset(
    {"TranslationRefused", "TranslationTruncated", "ExtractionRefused", "ExtractionTruncated"}
)
# entries columns the pipeline may write (everything except id, call_id, farmer_id).
ENTRY_COLUMNS = (
    "kind plot crop amount unit price_total currency date_sold buyer_type buyer_name paid_how "
    "activity input quantity yield_amount disease_detected symptom evidence_quote description "
    "quote_verified likely_disease disease_confidence confidence coffee_form coffee_type amount_kg"
).split()

_CLAIM_SQL = """
with picked as (
    select c.id from calls c
    where (%(conversation_id)s::text is null or c.conversation_id = %(conversation_id)s)
      and c.attempts < %(max_attempts)s
      and (c.status in ('received', 'failed')
           or (c.status = 'processing'
               and c.processing_started_at < now() - make_interval(mins => %(stale)s)))
    order by c.received_at
    limit 1
    for update skip locked
)
update calls c
   set status = 'processing', processing_started_at = now(), last_error = null
  from picked
 where c.id = picked.id
returning c.id, c.conversation_id, c.farmer_id, c.identified_by, c.received_at,
          c.transcript_lines, c.tool_results, c.processing_started_at,
          coalesce((select f.is_synthetic from farmers f where f.id = c.farmer_id), c.is_synthetic)
              as is_synthetic
"""
_SAVE_CALL_SQL = """
update calls set status = %(status)s, transcript_en = %(transcript_en)s,
       transcript_lines = %(lines)s::jsonb, extraction = %(extraction)s::jsonb,
       consent = %(consent)s, is_synthetic = %(is_synthetic)s, last_error = null,
       processed_at = now()
 where id = %(id)s and status = 'processing' and processing_started_at = %(claimed_at)s
returning id
"""
_FINISH_SQL = """
update calls set status = %(status)s, last_error = %(error)s, attempts = attempts + %(bump)s
 where id = %(id)s and status = 'processing' and processing_started_at = %(claimed_at)s
"""


def _claim(conn: psycopg.Connection, conversation_id: str | None = None) -> dict | None:
    cursor = conn.execute(
        _CLAIM_SQL,
        {"conversation_id": conversation_id, "max_attempts": MAX_ATTEMPTS, "stale": STALE_CLAIM_MINUTES},
    )
    row = cursor.fetchone()
    if row is None:
        return None
    return dict(zip([column.name for column in cursor.description], row))


def _call_date(received_at: datetime) -> date:
    return received_at.astimezone(KAMPALA_TZ).date()


def _entry_params(call: dict, entry: dict) -> dict:
    return {
        **{column: entry.get(column) for column in ENTRY_COLUMNS},
        "call_id": call["id"],
        "farmer_id": call["farmer_id"],
    }


def _save(conn: psycopg.Connection, call: dict, result: RunResult) -> bool:
    """Delete, insert and update in the caller's transaction. False if the claim was lost."""
    saved = conn.execute(
        _SAVE_CALL_SQL,
        {
            "status": result.status,
            "transcript_en": result.transcript_en,
            "lines": json.dumps(result.lines_en),
            "extraction": json.dumps(result.extraction),
            "consent": result.consent,
            "is_synthetic": bool(call["is_synthetic"]),
            "id": call["id"],
            "claimed_at": call["processing_started_at"],
        },
    ).fetchone()
    if saved is None:
        return False
    conn.execute("delete from entries where call_id = %s", (call["id"],))
    rows = [_entry_params(call, entry) for entry in result.entries] if result.consent != "no" else []
    columns = [*ENTRY_COLUMNS, "call_id", "farmer_id"]
    sql = f"insert into entries ({', '.join(columns)}) values ({', '.join(f'%({c})s' for c in columns)})"
    for row in rows:
        conn.execute(sql, row)
    return True


def _finish(conn: psycopg.Connection, call: dict, status: str, error: str, bump: int) -> None:
    conn.execute(
        _FINISH_SQL,
        {
            "status": status,
            "error": error[:MAX_LAST_ERROR_CHARS],
            "bump": bump,
            "id": call["id"],
            "claimed_at": call["processing_started_at"],
        },
    )


def _error_status(exc: BaseException) -> tuple[str, str, int]:
    """(status, last_error, attempts increment). Class names only: messages can echo payloads."""
    names = {cls.__name__ for cls in type(exc).__mro__}
    category = getattr(exc, "category", None)
    label = type(exc).__name__ + (f" ({category})" if category else "")
    if names & REVIEW_ERRORS:
        return "needs_review", label, 0
    return "failed", label, 1


def _run_claimed(call: dict) -> str:
    """Run the pipeline for a claimed call with no connection open, then save."""
    try:
        result = run_call(
            call["transcript_lines"] or [],
            _call_date(call["received_at"]),
            tool_results=call["tool_results"] or [],
            identified_by=call["identified_by"],
        )
    except Exception as exc:  # noqa: BLE001 - every failure must land in the row
        status, error, bump = _error_status(exc)
        logger.error("processing %s failed: %s", call["conversation_id"], error)
        with db.transaction() as conn:
            _finish(conn, call, status, error, bump)
        return status
    with db.transaction() as conn:
        saved = _save(conn, call, result)
    if not saved:
        logger.warning("claim on %s was lost before save; result dropped", call["conversation_id"])
        return "lost_claim"
    return result.status


def _current_status(conversation_id: str) -> str:
    with db.transaction() as conn:
        row = conn.execute("select status from calls where conversation_id = %s", (conversation_id,)).fetchone()
    return row[0] if row else "not_found"


def process_call(conversation_id: str) -> str:
    """Claim and process one call. Returns the final status, or the current status if it
    cannot be claimed (already processed, claimed elsewhere, out of attempts) or "not_found"."""
    with db.transaction() as conn:
        call = _claim(conn, conversation_id)
    if call is None:
        return _current_status(conversation_id)
    return _run_claimed(call)


def process_pending(limit: int = DEFAULT_PENDING_LIMIT) -> list[str]:
    """Claim up to `limit` pending calls, run them in parallel, return their final statuses."""
    claimed: list[dict] = []
    for _ in range(limit):
        with db.transaction() as conn:
            call = _claim(conn)
        if call is None:
            break
        claimed.append(call)
    if not claimed:
        return []
    with ThreadPoolExecutor(max_workers=len(claimed)) as pool:
        return list(pool.map(_run_claimed, claimed))

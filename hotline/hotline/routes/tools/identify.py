"""identify_farmer: PIN login (spec section 6). Always HTTP 200 with a status."""

import logging
import re

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from hotline import calls_repo, db, pins, profile, security
from hotline.routes.tools.register import DIGIT_WORDS_SW

log = logging.getLogger(__name__)

MAX_PIN_ATTEMPTS = 3
IDENTIFIED_BY_PIN = "pin"
_DIGIT_BY_WORD_SW = {word: str(digit) for digit, word in enumerate(DIGIT_WORDS_SW)}
_PIN_TOKEN_SEPARATORS = re.compile(r"[\s,.\-]+")

router = APIRouter(dependencies=[Depends(security.require_tool_secret)])


class IdentifyRequest(BaseModel):
    pin: str | None = None
    conversation_id: str | None = None
    call_sid: str | None = None


def pin_from_speech(raw: str) -> str | None:
    """Digits or Kiswahili digit words ("tisa sifuri sifuri moja") -> "9001", else None."""
    tokens = _PIN_TOKEN_SEPARATORS.split(raw.strip().lower())
    return pins.normalize_pin("".join(_DIGIT_BY_WORD_SW.get(t, t) for t in tokens))


def _find_farmer(conn, pin: str) -> int | None:
    row = conn.execute("select id from farmers where pin_hash = %s", (pins.hash_pin(pin),)).fetchone()
    return int(row[0]) if row else None


def _failed_attempt(conn, conversation_id: str) -> dict:
    used = calls_repo.bump_pin_attempts(conn, conversation_id)
    return {"status": "not_found", "attempts_left": max(MAX_PIN_ATTEMPTS - used, 0)}


def identify(conn, conversation_id: str, raw_pin: str) -> dict:
    if calls_repo.pin_attempts(conn, conversation_id) >= MAX_PIN_ATTEMPTS:
        return {"status": "locked"}
    pin = pin_from_speech(raw_pin)
    farmer_id = _find_farmer(conn, pin) if pin else None
    if farmer_id is None:
        return _failed_attempt(conn, conversation_id)
    calls_repo.upsert_call_identity(
        conn,
        conversation_id,
        farmer_id=farmer_id,
        identified_by=IDENTIFIED_BY_PIN,
        is_synthetic=profile.is_synthetic_farmer(conn, farmer_id),
    )
    found = profile.build_profile(
        conn, farmer_id, as_of=profile.kampala_today(), identified_by=IDENTIFIED_BY_PIN
    )
    return {"status": "found", **found}


@router.post("/api/tools/identify_farmer")
def identify_farmer(body: IdentifyRequest) -> dict:
    conversation_id = (body.conversation_id or "").strip()
    if not conversation_id:
        return {"status": "error", "reason": "missing_conversation_id"}
    try:
        pins.hash_pin("0000")  # fail closed before any lookup when the salt is unset
    except pins.PinSaltMissing:
        return {"status": "error", "reason": "pin_salt_missing"}
    try:
        with db.transaction() as conn:
            return identify(conn, conversation_id, body.pin or "")
    except Exception:
        log.exception("identify_farmer failed")
        return {"status": "error"}

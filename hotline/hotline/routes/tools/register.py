"""register_farmer: the only tool that returns a PIN, and only the caller's new one
(spec section 6). The farmer insert and the call upsert share one transaction."""

import logging

import psycopg
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from hotline import calls_repo, db, places, pins, profile, security
from hotline.routes.tools import find

log = logging.getLogger(__name__)

IDENTIFIED_BY_REGISTRATION = "registration"
MAX_PIN_INSERT_TRIES = 20
DIGIT_WORDS_SW = ("sifuri", "moja", "mbili", "tatu", "nne", "tano", "sita", "saba", "nane", "tisa")

router = APIRouter(dependencies=[Depends(security.require_tool_secret)])


class RegisterRequest(BaseModel):
    first_name: str | None = None
    district: str | None = None
    sub_county: str | None = None
    parish: str | None = None
    village: str | None = None
    coffee_type: str | None = None
    conversation_id: str | None = None
    call_sid: str | None = None


def pin_digits_sw(pin: str) -> str:
    return ", ".join(DIGIT_WORDS_SW[int(d)] for d in pin)


def _has_duplicate(conn, village_id: int, first_name: str) -> bool:
    rows = conn.execute("select name from farmers where village_id = %s", (village_id,)).fetchall()
    return any(places.score(first_name, profile.first_name_of(r[0])) >= places.MATCH_THRESHOLD for r in rows)


def _insert_farmer(conn, first_name: str, district: places.DistrictMatch, village_id: int) -> tuple[int, str]:
    """Insert with a fresh PIN; retry when a race makes the unique pin_hash collide."""
    for _ in range(MAX_PIN_INSERT_TRIES):
        pin = pins.allocate_pin(conn)
        try:
            with conn.transaction():  # savepoint: a collision must not abort the outer transaction
                row = conn.execute(
                    "insert into farmers (name, pin_hash, region, lat, lon, is_synthetic, village_id)"
                    " values (%s, %s, %s, %s, %s, false, %s) returning id",
                    (first_name, pins.hash_pin(pin), district.region, district.lat, district.lon, village_id),
                ).fetchone()
            return int(row[0]), pin
        except psycopg.errors.UniqueViolation:
            continue
    raise pins.PinAllocationError("PIN insert kept colliding")


def register(conn, req: RegisterRequest, conversation_id: str) -> dict:
    first_name = " ".join((req.first_name or "").split()[:1])
    district = places.match_district(req.district or "")
    if district is None:
        return {"status": "need_district"}
    if not first_name or not (req.village or "").strip():
        return {"status": "need_village"}
    match = places.match_village(conn, district.district, req.village, req.parish, req.sub_county)
    if match.status == "ambiguous":  # never guess between same-name villages: ask, villages only
        candidates = [find.village_option(c) for c in match.candidates]
        return {"status": "ambiguous", "ask": "parish", "candidates": candidates}
    known = match.status == "unique"
    if known and _has_duplicate(conn, match.best.village_id, first_name):
        return {"status": "possible_duplicate"}
    if known:
        village_id = match.best.village_id
    else:  # unknown villages are created unverified so real callers can register anywhere
        village_id = places.create_unverified_village(conn, district, req.village, req.parish, req.sub_county)
    farmer_id, pin = _insert_farmer(conn, first_name.title(), district, village_id)
    calls_repo.upsert_call_identity(
        conn, conversation_id, farmer_id=farmer_id, identified_by=IDENTIFIED_BY_REGISTRATION, is_synthetic=False
    )
    found = profile.build_profile(
        conn, farmer_id, as_of=profile.kampala_today(), identified_by=IDENTIFIED_BY_REGISTRATION
    )
    return {
        "status": "registered",
        "pin": pin,
        "pin_digits_sw": pin_digits_sw(pin),
        "village_known": known,
        "farmer": found["farmer"],
        "village_price": found["village_price"],
        "other_prices": found["other_prices"],
    }


@router.post("/api/tools/register_farmer")
def register_farmer(body: RegisterRequest) -> dict:
    conversation_id = (body.conversation_id or "").strip()
    if not conversation_id:
        return {"status": "error", "reason": "missing_conversation_id"}
    try:
        pins.hash_pin("0000")
    except pins.PinSaltMissing:
        return {"status": "error", "reason": "pin_salt_missing"}
    try:
        with db.transaction() as conn:
            return register(conn, body, conversation_id)
    except Exception:
        log.exception("register_farmer failed")
        return {"status": "error"}

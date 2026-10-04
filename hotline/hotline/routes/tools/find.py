"""find_farmer_by_location: login without a PIN (spec section 6). Weaker than a PIN, so a
unique match returns the price and the farmer's own coffee-year totals only. Candidates are
villages, never people."""

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from hotline import calls_repo, db, places, profile, security

log = logging.getLogger(__name__)

IDENTIFIED_BY_LOCATION = "location"

router = APIRouter(dependencies=[Depends(security.require_tool_secret)])


class FindRequest(BaseModel):
    first_name: str | None = None
    district: str | None = None
    village: str | None = None
    parish: str | None = None
    sub_county: str | None = None
    conversation_id: str | None = None
    call_sid: str | None = None


def village_option(village: places.VillageCandidate) -> dict:
    return {"village": village.village, "parish": village.parish, "sub_county": village.sub_county}


def _ask_for(candidates: tuple, parish: str | None) -> str:
    parishes = {c.parish for c in candidates}
    return "parish" if len(parishes) > 1 and not parish else "village"


def _farmers_in_village(conn, village_id: int) -> list[tuple[int, str, bool]]:
    rows = conn.execute("select id, name, is_synthetic from farmers where village_id = %s", (village_id,))
    return [(int(r[0]), r[1], bool(r[2])) for r in rows.fetchall()]


def _same_first_name(spoken: str, stored_name: str) -> bool:
    return places.score(spoken, profile.first_name_of(stored_name)) >= places.MATCH_THRESHOLD


def locate(conn, req: FindRequest, conversation_id: str) -> dict:
    spoken_name = (req.first_name or "").strip()
    district = places.match_district(req.district or "")
    if not spoken_name or not (req.village or "").strip() or district is None:
        return {"status": "not_found"}
    match = places.match_village(conn, district.district, req.village, req.parish, req.sub_county)
    if match.status == "none":
        return {"status": "not_found"}
    if match.status == "ambiguous":
        ask = _ask_for(match.candidates, req.parish)
        return {"status": "ambiguous", "ask": ask, "candidates": [village_option(c) for c in match.candidates]}
    hits = [f for f in _farmers_in_village(conn, match.best.village_id) if _same_first_name(spoken_name, f[1])]
    if not hits:
        return {"status": "not_found"}
    if len(hits) > 1:  # same villages-only shape: never reveal that two people share the name
        return {"status": "ambiguous", "ask": "village", "candidates": [village_option(match.best)]}
    farmer_id, _, is_synthetic = hits[0]
    calls_repo.upsert_call_identity(
        conn, conversation_id, farmer_id=farmer_id, identified_by=IDENTIFIED_BY_LOCATION, is_synthetic=is_synthetic
    )
    found = profile.build_profile(
        conn, farmer_id, as_of=profile.kampala_today(), identified_by=IDENTIFIED_BY_LOCATION
    )
    return {"status": "found", **found}


@router.post("/api/tools/find_farmer_by_location")
def find_farmer_by_location(body: FindRequest) -> dict:
    conversation_id = (body.conversation_id or "").strip()
    if not conversation_id:
        return {"status": "error", "reason": "missing_conversation_id"}
    try:
        with db.transaction() as conn:
            return locate(conn, body, conversation_id)
    except Exception:
        log.exception("find_farmer_by_location failed")
        return {"status": "error"}

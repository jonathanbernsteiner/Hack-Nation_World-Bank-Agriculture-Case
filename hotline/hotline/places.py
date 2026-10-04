"""Fuzzy matching of Ugandan district and village names spoken by callers.

Swahili speech recognition spells Luganda/Lugisu names inconsistently ("Kyanamukaka",
"Kyanamukaaka", "Chanamukaka"), so every comparison takes the better of a text score and
a hand-written phonetic-key score.

Districts come from data/uganda_districts.csv (UBOS / OCHA COD-AB admin level 2 centroids,
CC BY-IGO, https://data.humdata.org/dataset/cod-ab-uga). Villages come from the `villages`
table and are always searched inside one matched district only. Candidates returned to the
agent are villages, never farmers. The caller owns the connection and its transaction.
"""

import csv
import re
import time
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from rapidfuzz import fuzz

DISTRICTS_CSV = Path(__file__).parent / "data" / "uganda_districts.csv"
MATCH_THRESHOLD = 85
MARGIN_POINTS = 5
CANDIDATE_FLOOR = 60
MAX_CANDIDATES = 3
UNKNOWN_PLACE = "unknown"
VILLAGE_CACHE_TTL_SECS = 60
MIN_VILLAGE_LETTERS = 4

# Filler words callers put around place names ("kijiji cha X" = "village of X").
FILLER_WORDS = frozenset(
    {"kijiji", "muluka", "gombolola", "kata", "wilaya", "village", "parish", "sub", "county", "district"}
)
# Swahili connectors, only dropped when a real name remains.
CONNECTOR_WORDS = frozenset({"cha", "ya"})

# Applied in order. ky before ch so both end up as "c".
_PHONETIC_SUBSTITUTIONS = (("ph", "f"), ("ky", "c"), ("ch", "c"), ("r", "l"), ("z", "s"))
_REPEATED_LETTER = re.compile(r"([a-z])\1+")
_NON_LETTER = re.compile(r"[^a-z]+")


@dataclass(frozen=True)
class DistrictMatch:
    district: str
    region: str
    lat: float
    lon: float
    score: float


@dataclass(frozen=True)
class VillageCandidate:
    village_id: int
    village: str
    parish: str
    sub_county: str
    district: str
    score: float


@dataclass(frozen=True)
class VillageMatch:
    status: Literal["unique", "ambiguous", "none"]
    best: VillageCandidate | None
    candidates: tuple[VillageCandidate, ...]


def normalize(name: str) -> str:
    """Lowercase, drop accents, punctuation and filler words, collapse spaces."""
    ascii_text = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    words = _NON_LETTER.sub(" ", ascii_text.lower()).split()
    kept = [w for w in words if w not in FILLER_WORDS]
    named = [w for w in kept if w not in CONNECTOR_WORDS]
    return " ".join(named or kept)


def phonetic_key(name: str) -> str:
    """Spelling-insensitive key: r->l, aa->a, ky/ch->c, ph->f, z->s, doubled letters
    collapsed, ny kept."""
    key = normalize(name)
    for old, new in _PHONETIC_SUBSTITUTIONS:
        key = key.replace(old, new)
    return _REPEATED_LETTER.sub(r"\1", key)


def score(spoken: str, known: str) -> float:
    return max(
        fuzz.WRatio(normalize(spoken), normalize(known)),
        fuzz.WRatio(phonetic_key(spoken), phonetic_key(known)),
    )


@lru_cache(maxsize=1)
def _districts() -> tuple[tuple[str, str, float, float], ...]:
    with DISTRICTS_CSV.open(encoding="utf-8", newline="") as handle:
        lines = (line for line in handle if not line.startswith("#"))
        return tuple(
            (row["district"], row["region"], float(row["lat"]), float(row["lon"]))
            for row in csv.DictReader(lines)
        )


def district_candidates(spoken: str, limit: int = MAX_CANDIDATES) -> list[DistrictMatch]:
    """Best-scoring districts first; entries below CANDIDATE_FLOOR are dropped."""
    if not normalize(spoken):
        return []
    scored = [
        DistrictMatch(name, region, lat, lon, score(spoken, name))
        for name, region, lat, lon in _districts()
    ]
    ranked = sorted(scored, key=lambda m: (-m.score, m.district))
    return [m for m in ranked[:limit] if m.score >= CANDIDATE_FLOOR]


def match_district(spoken: str) -> DistrictMatch | None:
    """A confident match, or None when below threshold or the top two are within 5 points."""
    top = district_candidates(spoken, limit=2)
    if not top or top[0].score < MATCH_THRESHOLD:
        return None
    if len(top) > 1 and top[0].score - top[1].score < MARGIN_POINTS:
        return None
    return top[0]


# Per-process cache of villages by lower-cased district: (fetched_at, rows). Entries expire
# after VILLAGE_CACHE_TTL_SECS so villages created by another instance become visible.
_village_cache: dict[str, tuple[float, tuple[tuple[Any, ...], ...]]] = {}


def clear_village_cache() -> None:
    _village_cache.clear()


def _district_villages(conn: Any, district: str) -> tuple[tuple[Any, ...], ...]:
    key = district.lower()
    cached = _village_cache.get(key)
    if cached and time.monotonic() - cached[0] < VILLAGE_CACHE_TTL_SECS:
        return cached[1]
    rows = conn.execute(
        "select id, village, parish, sub_county, district from villages where lower(district) = %s",
        (key,),
    ).fetchall()
    fresh = tuple(tuple(row) for row in rows)
    _village_cache[key] = (time.monotonic(), fresh)
    return fresh


def _narrow(rows: list[VillageCandidate], parish: str | None, sub_county: str | None):
    scored = []
    for candidate in rows:
        if parish and candidate.parish != UNKNOWN_PLACE and score(parish, candidate.parish) < MATCH_THRESHOLD:
            continue
        if sub_county and candidate.sub_county != UNKNOWN_PLACE and score(sub_county, candidate.sub_county) < MATCH_THRESHOLD:
            continue
        scored.append(candidate)
    return scored


def match_village(
    conn: Any,
    district: str,
    village: str,
    parish: str | None = None,
    sub_county: str | None = None,
) -> VillageMatch:
    """Match a spoken village inside one district. A parish or sub-county that is given
    but matches nothing yields `none` (it may be a different village of the same name)."""
    if len(normalize(village).replace(" ", "")) < MIN_VILLAGE_LETTERS:
        return VillageMatch("none", None, ())
    candidates = [
        VillageCandidate(row[0], row[1], row[2], row[3], row[4], score(village, row[1]))
        for row in _district_villages(conn, district)
    ]
    hits = [c for c in candidates if c.score >= MATCH_THRESHOLD]
    hits = _narrow(hits, parish, sub_county)
    if not hits:
        return VillageMatch("none", None, ())
    hits.sort(key=lambda c: (-c.score, c.parish, c.village_id))
    leaders = tuple(c for c in hits if hits[0].score - c.score < MARGIN_POINTS)[:MAX_CANDIDATES]
    if len(leaders) == 1:
        return VillageMatch("unique", leaders[0], leaders)
    return VillageMatch("ambiguous", None, leaders)


def _clean_place(name: str | None) -> str:
    cleaned = normalize(name or "")
    if not cleaned or cleaned == UNKNOWN_PLACE:
        return UNKNOWN_PLACE
    return cleaned.title()


def create_unverified_village(
    conn: Any,
    district: DistrictMatch,
    village: str,
    parish: str | None,
    sub_county: str | None,
) -> int:
    """Insert (or find) a village named by a caller: is_verified=false, is_synthetic=false,
    at the district centroid. Idempotent on (district, sub_county, parish, village)."""
    village_name = _clean_place(village)
    if village_name == UNKNOWN_PLACE:
        raise ValueError("village name is empty")
    row = conn.execute(
        "insert into villages (region, district, sub_county, parish, village, lat, lon,"
        " is_verified, is_synthetic) values (%s, %s, %s, %s, %s, %s, %s, false, false)"
        " on conflict (district, sub_county, parish, village)"
        " do update set village = excluded.village returning id",
        (
            district.region,
            district.district,
            _clean_place(sub_county),
            _clean_place(parish),
            village_name,
            district.lat,
            district.lon,
        ),
    ).fetchone()
    _village_cache.pop(district.district.lower(), None)
    return int(row[0])

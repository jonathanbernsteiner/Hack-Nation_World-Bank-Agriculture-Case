"""Load the SYNTHETIC Uganda season into Supabase (#44). Nothing here prints a secret.

The connection is a psycopg 3 connection passed in by the caller (psycopg is not a server
dependency, so this module never imports it). Reset and load share one transaction, so a
failure leaves the old data in place. Writes only happen after the salt gate has passed.
"""

import hashlib
import json
import urllib.error
import urllib.request
from collections import Counter
from collections.abc import Callable
from typing import Any
from urllib.parse import urlparse

from .generate import ENTRY_COLUMNS, Season, generate_season

HEALTH_URL = "https://hack-nation-world-bank-agriculture.vercel.app/api/health?deep=1"
ADMIN_HEADER = "X-Hotline-Admin-Secret"
SALT_FP_LENGTH = 8
HEALTH_TIMEOUT_SECS = 10
PRODUCTION_DB_SUFFIXES = (".supabase.com", ".supabase.co")


class LoadError(RuntimeError):
    """The load was refused. The message never contains a secret."""


class SaltGateError(LoadError):
    pass


class ResetRefused(LoadError):
    pass


def salt_fingerprint(salt: str) -> str:
    return hashlib.sha256(salt.encode()).hexdigest()[:SALT_FP_LENGTH]


def hash_pin(salt: str, pin: str) -> str:
    """Same formula as hotline.pins.hash_pin and farm_ledger.db._hash_pin."""
    return hashlib.sha256(f"{salt}:{pin}".encode()).hexdigest()


def fetch_production_fingerprint(admin_secret: str) -> str:
    request = urllib.request.Request(HEALTH_URL, headers={ADMIN_HEADER: admin_secret})
    try:
        with urllib.request.urlopen(request, timeout=HEALTH_TIMEOUT_SECS) as response:
            body = json.load(response)
    except (OSError, ValueError, urllib.error.URLError) as error:
        raise SaltGateError(f"production health check unreachable ({type(error).__name__})") from None
    fingerprint = body.get("salt_fp") if isinstance(body, dict) else None
    if not isinstance(fingerprint, str) or not fingerprint:
        raise SaltGateError("production health check returned no salt_fp")
    return fingerprint


def check_salt_gate(
    salt: str | None,
    admin_secret: str | None,
    fetch: Callable[[str], str] = fetch_production_fingerprint,
) -> str:
    """Fail closed. Returns the matching fingerprint (safe to print: 8 hex chars)."""
    if not salt:
        raise SaltGateError("LEDGER_PIN_SALT is not set")
    if not admin_secret:
        raise SaltGateError("HOTLINE_ADMIN_SECRET is not set")
    local = salt_fingerprint(salt)
    if fetch(admin_secret) != local:
        raise SaltGateError("LEDGER_PIN_SALT does not match production (salt_fp mismatch)")
    return local


def is_production_database(database_url: str | None) -> bool:
    """Fail closed: a URL whose host cannot be read (libpq key=value conninfo, or the host in a
    query parameter) counts as production, and so does any mention of a Supabase host."""
    url = (database_url or "").lower()
    host = urlparse(url).hostname or ""
    if not host:
        return True
    return host.endswith(PRODUCTION_DB_SUFFIXES) or any(s[1:] in url for s in PRODUCTION_DB_SUFFIXES)


def refuse_skip_for_production(database_url: str | None) -> None:
    if is_production_database(database_url):
        raise SaltGateError("--skip-salt-check is not allowed against the production database")


# Rows that reference a synthetic row but are not synthetic themselves. Any hit refuses the reset.
REFUSAL_CHECKS = (
    ("entries in a real call about a synthetic farmer",
     "select count(*) from entries e join calls c on c.id = e.call_id"
     " where not c.is_synthetic and e.farmer_id in (select id from farmers where is_synthetic)"),
    ("real calls from a synthetic farmer",
     "select count(*) from calls where not is_synthetic"
     " and farmer_id in (select id from farmers where is_synthetic)"),
    ("real farmers in a synthetic village",
     "select count(*) from farmers where not is_synthetic"
     " and village_id in (select id from villages where is_synthetic)"),
)
# Order matters: children before parents. An entry counts as synthetic when its call is.
RESET_STATEMENTS = (
    ("entries", "delete from entries where call_id in (select id from calls where is_synthetic)"),
    ("calls", "delete from calls where is_synthetic"),
    ("farmers", "delete from farmers where is_synthetic"),
    ("villages", "delete from villages where is_synthetic"),
)


def reset_synthetic(conn: Any) -> dict[str, int]:
    """Delete only is_synthetic rows. Raises ResetRefused, before any delete, if a real row
    references a synthetic one. Call inside the caller's transaction."""
    blockers = []
    for label, sql in REFUSAL_CHECKS:
        count = conn.execute(sql).fetchone()[0]
        if count:
            blockers.append(f"{count} {label}")
    if blockers:
        raise ResetRefused("refusing to reset: " + "; ".join(blockers))
    return {table: conn.execute(sql).rowcount for table, sql in RESET_STATEMENTS}


INSERT_VILLAGE = (
    "insert into villages (region, district, sub_county, parish, village, lat, lon, coffee_type,"
    " is_verified, is_synthetic) values (%s, %s, %s, %s, %s, %s, %s, %s, true, true) returning id"
)
INSERT_FARMER = (
    "insert into farmers (name, pin_hash, region, lat, lon, village_id, is_synthetic)"
    " values (%s, %s, %s, %s, %s, %s, true) returning id"
)
INSERT_CALL = (
    "insert into calls (farmer_id, received_at, language, transcript_sw, transcript_en, is_synthetic,"
    " source, status, identified_by, consent, duration_secs, transcript_lines, processed_at)"
    " values (%s, %s, %s, %s, %s, true, %s, %s, %s, %s, %s, %s::jsonb, %s) returning id"
)
INSERT_ENTRY = (
    f"insert into entries (call_id, farmer_id, {', '.join(ENTRY_COLUMNS)})"
    f" values (%s, %s, {', '.join(['%s'] * len(ENTRY_COLUMNS))})"
)
MEDIAN_SQL = (
    "select percentile_cont(0.5) within group (order by ugx_per_kg), count(*), count(distinct farmer_id)"
    " from coffee_sale_prices where village = 'Kyabakuza' and coffee_form = 'kiboko'"
    " and sale_date > date '2026-10-03' - 365"
)


def _plain(value: Any) -> Any:
    return value.value if hasattr(value, "value") else value


def season_counts(season: Season) -> dict[str, int]:
    return {
        "villages": len(season.villages),
        "farmers": len(season.farmers),
        "calls": len(season.calls),
        "entries": sum(len(call.entries) for call in season.calls),
    }


def load_season(conn: Any, season: Season, salt: str) -> dict[str, int]:
    """Insert villages, then farmers, then calls and entries. Call inside a transaction."""
    village_ids = []
    for v in season.villages:
        row = conn.execute(INSERT_VILLAGE, (
            v.region, v.district, v.sub_county, v.parish, v.village, v.lat, v.lon, _plain(v.coffee_type),
        )).fetchone()
        village_ids.append(row[0])
    farmer_ids = []
    for f in season.farmers:
        row = conn.execute(INSERT_FARMER, (
            f.name, hash_pin(salt, f.pin), season.villages[f.village].region, f.lat, f.lon,
            village_ids[f.village],
        )).fetchone()
        farmer_ids.append(row[0])
    for call in season.calls:
        farmer_id = farmer_ids[call.farmer]
        call_id = conn.execute(INSERT_CALL, (
            farmer_id, call.received_at, call.language, call.transcript_sw, call.transcript_en,
            call.source, call.status, call.identified_by, call.consent, call.duration_secs,
            json.dumps(list(call.transcript_lines)), call.received_at,
        )).fetchone()[0]
        for entry in call.entries:
            values = [_plain(entry.get(column)) for column in ENTRY_COLUMNS]
            conn.execute(INSERT_ENTRY, (call_id, farmer_id, *values))
    return season_counts(season)


def kyabakuza_median(conn: Any) -> tuple[float | None, int, int]:
    median, sales, farmers = conn.execute(MEDIAN_SQL).fetchone()
    return (None if median is None else float(median), sales, farmers)


def run_load(conn: Any, salt: str, reset: bool, season: Season | None = None) -> dict[str, Any]:
    """Reset (optional) and load in ONE transaction. The salt gate must already have passed."""
    season = season or generate_season()
    with conn.transaction():
        deleted = reset_synthetic(conn) if reset else {}
        inserted = load_season(conn, season, salt)
        median = kyabakuza_median(conn)
    return {"deleted": deleted, "inserted": inserted, "median": median}


def format_counts(label: str, counts: dict[str, int] | Counter) -> str:
    return f"{label}: " + ", ".join(f"{k}={v}" for k, v in counts.items())


def entry_currencies(season: Season) -> Counter:
    return Counter(_plain(e.get("currency")) for call in season.calls for e in call.entries)



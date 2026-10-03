"""SQLite ledger: schema, farmers, calls with their entries, and reads.

Config (env vars):
  LEDGER_DB_PATH  database file; default is data/ledger.db inside server/
  LEDGER_PIN_SALT app-level salt for PIN hashes; default is a dev value

PIN note: a 4-digit PIN has only 10,000 values, so the hash is trivially
guessable if the database leaks. It keeps PINs out of plain text; it is not
strong protection. PINs are unique per farmer because the PIN identifies her.
"""

import hashlib
import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from .enums import Activity, BuyerType, Currency, Kind, PaidHow, Symptom, Unit

DEFAULT_DB = Path(__file__).resolve().parents[1] / "data" / "ledger.db"
DEV_SALT = "dev-salt-change-me"


def _in(column: str, enum) -> str:
    values = ", ".join(f"'{m.value}'" for m in enum)
    return f"CHECK ({column} IN ({values}))"


_BOOL = "INTEGER CHECK ({} IN (0, 1))"
_UNIT_01 = "REAL CHECK ({} BETWEEN 0 AND 1)"

SCHEMA = f"""
CREATE TABLE IF NOT EXISTS farmers (
    id           INTEGER PRIMARY KEY,
    name         TEXT NOT NULL,
    pin_hash     TEXT NOT NULL UNIQUE,
    region       TEXT,
    lat          REAL,
    lon          REAL,
    is_synthetic INTEGER NOT NULL DEFAULT 0 CHECK (is_synthetic IN (0, 1))
);

CREATE TABLE IF NOT EXISTS calls (
    id            INTEGER PRIMARY KEY,
    farmer_id     INTEGER NOT NULL REFERENCES farmers(id),
    received_at   TEXT NOT NULL,
    language      TEXT,
    audio_path    TEXT,
    transcript_sw TEXT,
    transcript_en TEXT,
    is_synthetic  INTEGER NOT NULL DEFAULT 0 CHECK (is_synthetic IN (0, 1))
);

CREATE TABLE IF NOT EXISTS entries (
    id                 INTEGER PRIMARY KEY,
    call_id            INTEGER NOT NULL REFERENCES calls(id),
    farmer_id          INTEGER NOT NULL REFERENCES farmers(id),
    kind               TEXT {_in("kind", Kind)},
    plot               TEXT,
    crop               TEXT,
    amount             REAL,
    unit               TEXT {_in("unit", Unit)},
    price_total        REAL,
    currency           TEXT {_in("currency", Currency)},
    date_sold          TEXT,
    buyer_type         TEXT {_in("buyer_type", BuyerType)},
    buyer_name         TEXT,
    paid_how           TEXT {_in("paid_how", PaidHow)},
    activity           TEXT {_in("activity", Activity)},
    input              TEXT,
    quantity           REAL,
    yield_amount       REAL,
    disease_detected   {_BOOL.format("disease_detected")},
    symptom            TEXT {_in("symptom", Symptom)},
    evidence_quote     TEXT,
    description        TEXT,
    quote_verified     {_BOOL.format("quote_verified")},
    likely_disease     TEXT,
    disease_confidence {_UNIT_01.format("disease_confidence")},
    confidence         {_UNIT_01.format("confidence")}
);

CREATE INDEX IF NOT EXISTS idx_entries_farmer ON entries(farmer_id);
CREATE INDEX IF NOT EXISTS idx_entries_call ON entries(call_id);
CREATE INDEX IF NOT EXISTS idx_calls_received ON calls(received_at);
"""

ENTRY_FIELDS = (
    "kind", "plot", "crop", "amount", "unit", "price_total", "currency",
    "date_sold", "buyer_type", "buyer_name", "paid_how", "activity", "input",
    "quantity", "yield_amount", "disease_detected", "symptom", "evidence_quote",
    "description", "quote_verified", "likely_disease", "disease_confidence",
    "confidence",
)


def db_path() -> Path:
    return Path(os.environ.get("LEDGER_DB_PATH") or DEFAULT_DB)


def connect(path: str | Path | None = None) -> sqlite3.Connection:
    """Open the ledger (creating file and tables if missing). Safe to call repeatedly."""
    path = Path(path) if path else db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    init_db(conn)
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """Create tables and indexes if they do not exist (idempotent)."""
    conn.executescript(SCHEMA)


def clean_crop(name: str) -> str:
    """Lowercase, trim, collapse spaces, and singularise the last word.

    "Bananas" -> "banana", "coffee cherries" -> "coffee cherry",
    "Tomatoes" -> "tomato". Deliberately simple: only -ies, -oes and a plain
    trailing -s (not -ss or -us) are handled; irregular plurals are left alone.
    """
    words = " ".join(name.lower().split()).split(" ")
    w = words[-1]
    if w.endswith("ies") and len(w) > 3:
        w = w[:-3] + "y"
    elif w.endswith("oes") and len(w) > 3:
        w = w[:-2]
    elif w.endswith("s") and not w.endswith(("ss", "us")) and len(w) > 1:
        w = w[:-1]
    words[-1] = w
    return " ".join(words)


def _hash_pin(pin: str) -> str:
    salt = os.environ.get("LEDGER_PIN_SALT", DEV_SALT)
    return hashlib.sha256(f"{salt}:{pin}".encode()).hexdigest()


def add_farmer(conn, name, pin, region=None, lat=None, lon=None, is_synthetic=False) -> int:
    with conn:
        cur = conn.execute(
            "INSERT INTO farmers (name, pin_hash, region, lat, lon, is_synthetic)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (name, _hash_pin(pin), region, lat, lon, int(is_synthetic)),
        )
    return cur.lastrowid


def find_farmer_by_pin(conn, pin) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM farmers WHERE pin_hash = ?", (_hash_pin(pin),)
    ).fetchone()


def insert_call(
    conn, farmer_id, entries, *, received_at=None, language=None, audio_path=None,
    transcript_sw=None, transcript_en=None, is_synthetic=False,
) -> int:
    """Save a call and all its entries in one transaction; return the call id.

    `entries` is a list of dicts keyed by ENTRY_FIELDS (all optional). Any
    invalid entry raises (sqlite3.IntegrityError or ValueError) and nothing
    from the call is saved. `received_at` is ISO text, default now (UTC).
    """
    received_at = received_at or datetime.now(UTC).isoformat(timespec="seconds")
    with conn:  # commit on success, roll back everything on error
        cur = conn.execute(
            "INSERT INTO calls (farmer_id, received_at, language, audio_path,"
            " transcript_sw, transcript_en, is_synthetic) VALUES (?,?,?,?,?,?,?)",
            (farmer_id, received_at, language, audio_path, transcript_sw,
             transcript_en, int(is_synthetic)),
        )
        call_id = cur.lastrowid
        for entry in entries:
            unknown = set(entry) - set(ENTRY_FIELDS)
            if unknown:
                raise ValueError(f"unknown entry fields: {sorted(unknown)}")
            row = {k: (v.value if hasattr(v, "value") else v) for k, v in entry.items()}
            if row.get("crop") is not None:
                row["crop"] = clean_crop(row["crop"])
            cols = ["call_id", "farmer_id", *row]
            conn.execute(
                f"INSERT INTO entries ({', '.join(cols)})"
                f" VALUES ({', '.join('?' * len(cols))})",
                [call_id, farmer_id, *row.values()],
            )
    return call_id


def list_ledger(conn, farmer_id) -> list[dict]:
    """A farmer's entries in time order (call received_at, then entry id),
    each with its call's received_at, language and transcripts."""
    rows = conn.execute(
        "SELECT e.*, c.received_at, c.language, c.transcript_sw, c.transcript_en"
        " FROM entries e JOIN calls c ON c.id = e.call_id"
        " WHERE e.farmer_id = ? ORDER BY c.received_at, e.id",
        (farmer_id,),
    ).fetchall()
    return [dict(r) for r in rows]

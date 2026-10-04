"""The Supabase migration (#19) must keep #7's columns and fixed lists, so the two ledgers can't drift apart."""

import hashlib
import re
from pathlib import Path

import pytest

from farm_ledger import Activity, BuyerType, Currency, Kind, PaidHow, Symptom, Unit
from farm_ledger.db import ENTRY_FIELDS

MIGRATIONS = Path(__file__).resolve().parents[2] / "supabase" / "migrations"
FIXED_LISTS = {"kind": Kind, "unit": Unit, "currency": Currency, "buyer_type": BuyerType,
               "paid_how": PaidHow, "activity": Activity, "symptom": Symptom}
# sha256 of the normalised SQL (see `normalised`); checked against the live
# supabase_migrations.schema_migrations statements for 20261003234752 on 2026-10-03.
APPLIED_LEDGER_SQL_SHA256 = "a3dc06635dd1e25244cfd993b96b74838698c3b4e761f8a89585bb1290f76b45"


@pytest.fixture(scope="module")
def sql():
    (path,) = MIGRATIONS.glob("*_ledger_tables.sql")
    return path.read_text()


def columns(sql, table):
    body = re.search(rf"create table public\.{table} \((.*?)\n\);", sql, re.S).group(1)
    return {m.group(1) for m in re.finditer(r"^ {4}(\w+) ", body, re.M)}


def normalised(sql):
    """The SQL without comments, whitespace collapsed: only a real DDL change alters it."""
    return " ".join(re.sub(r"--[^\n]*", "", sql).split())


def all_migrations():
    return normalised("\n".join(p.read_text() for p in sorted(MIGRATIONS.glob("*.sql")))).lower()


def test_check_lists_match_the_python_enums(sql):
    for column, enum in FIXED_LISTS.items():
        listed = re.search(rf"check \({column} in \((.*?)\)\)", sql, re.S).group(1)
        assert re.findall(r"'([^']*)'", listed) == [m.value for m in enum], column


def test_tables_have_the_ledger_columns(sql):
    assert columns(sql, "farmers") == {"id", "name", "pin_hash", "region", "lat", "lon", "is_synthetic"}
    assert columns(sql, "calls") == {"id", "farmer_id", "received_at", "language", "audio_path",
                                     "transcript_sw", "transcript_en", "is_synthetic"}
    assert columns(sql, "entries") == {"id", "call_id", "farmer_id", *ENTRY_FIELDS}


def test_row_level_security_is_on_for_every_table(sql):
    for table in ("farmers", "calls", "entries"):
        assert f"alter table public.{table} enable row level security;" in sql
    assert "create policy" not in sql


def test_migration_version_matches_remote_name():
    """The version is already applied live; renaming the file would break `supabase db push`."""
    (path,) = MIGRATIONS.glob("*_ledger_tables.sql")
    assert path.name == "20261003234752_ledger_tables.sql"


def test_applied_migration_is_unchanged(sql):
    """`supabase db push` never re-runs an applied version, so editing this file would silently
    split the repo from the live database. Schema changes go into a new, additive migration."""
    digest = hashlib.sha256(normalised(sql).encode()).hexdigest()
    assert digest == APPLIED_LEDGER_SQL_SHA256, "20261003234752 is live: add a new migration instead"


def test_every_migrated_table_keeps_row_level_security_without_policies():
    """Only the server may read or write; the anon and publishable keys must see nothing."""
    text = all_migrations()
    created = set(re.findall(r"create table (?:if not exists )?(?:public\.)?(\w+)", text))
    secured = set(re.findall(r"alter table (?:public\.)?(\w+) enable row level security", text))
    assert {"farmers", "calls", "entries"} <= created
    assert created - secured == set(), "every new table needs `enable row level security`"
    assert "create policy" not in text
    assert "disable row level security" not in text


def test_deleting_a_farmer_or_call_never_cascades():
    """The synthetic reset (#20) relies on this: deleting a farmer or call that real rows
    point at must fail, not take those rows with it (or orphan them)."""
    assert re.findall(r"on delete (cascade|set null|set default)", all_migrations()) == []

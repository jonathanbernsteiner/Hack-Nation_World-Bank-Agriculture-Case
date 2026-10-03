"""The Supabase migration (#19) must keep #7's columns and fixed lists, so the two ledgers can't drift apart."""

import re
from pathlib import Path

import pytest

from farm_ledger import Activity, BuyerType, Currency, Kind, PaidHow, Symptom, Unit
from farm_ledger.db import ENTRY_FIELDS

MIGRATIONS = Path(__file__).resolve().parents[2] / "supabase" / "migrations"
FIXED_LISTS = {"kind": Kind, "unit": Unit, "currency": Currency, "buyer_type": BuyerType,
               "paid_how": PaidHow, "activity": Activity, "symptom": Symptom}


@pytest.fixture(scope="module")
def sql():
    (path,) = MIGRATIONS.glob("*_ledger_tables.sql")
    return path.read_text()


def columns(sql, table):
    body = re.search(rf"create table public\.{table} \((.*?)\n\);", sql, re.S).group(1)
    return {m.group(1) for m in re.finditer(r"^ {4}(\w+) ", body, re.M)}


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

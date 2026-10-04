"""The Python enums must equal the CHECK lists in the migrations, and the district CSV must be usable."""

import csv
import re
from pathlib import Path

import psycopg
import pytest

from hotline.enums import (CallSource, CallStatus, CoffeeForm, CoffeeType, Consent, Currency,
                           IdentifiedBy, Region)

ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = ROOT / "supabase" / "migrations"
DISTRICTS = Path(__file__).resolve().parents[1] / "hotline" / "data" / "uganda_districts.csv"
FIXED_LISTS = {"currency": Currency, "coffee_form": CoffeeForm, "coffee_type": CoffeeType,
               "status": CallStatus, "source": CallSource, "identified_by": IdentifiedBy,
               "consent": Consent, "region": Region}
UGANDA_BBOX = {"lat": (-1.5, 4.3), "lon": (29.5, 35.1)}
DEMO_DISTRICTS = {"Masaka", "Mubende", "Bushenyi", "Bududa", "Zombo"}


def migrations_sql():
    """Every migration in filename order, comments removed."""
    text = "\n".join(p.read_text() for p in sorted(MIGRATIONS.glob("*.sql")))
    return re.sub(r"--[^\n]*", "", text)


def check_lists():
    """column -> allowed values; the last `check (col in (...))` for a column wins."""
    found = re.finditer(r"check\s*\(\s*(\w+)\s+in\s*\(([^)]*)\)\)", migrations_sql())
    return {m.group(1): re.findall(r"'([^']*)'", m.group(2)) for m in found}


def test_hotline_enums_match_sql():
    lists = check_lists()
    for column, enum in FIXED_LISTS.items():
        assert lists[column] == [m.value for m in enum], column


def test_call_status_list_matches_sql():
    assert check_lists()["status"] == [m.value for m in CallStatus]
    assert re.search(r"add column status text not null default 'processed'", migrations_sql())


def test_currency_includes_ugx():
    assert Currency.UGX.value in check_lists()["currency"]


def read_districts():
    lines = [ln for ln in DISTRICTS.read_text().splitlines() if not ln.startswith("#")]
    return list(csv.DictReader(lines))


def test_districts_csv_parses_and_in_uganda_bbox():
    rows = read_districts()
    assert len(rows) >= 100
    assert {r["region"] for r in rows} == {m.value for m in Region}
    assert len({r["district"] for r in rows}) == len(rows)
    for row in rows:
        assert UGANDA_BBOX["lat"][0] <= float(row["lat"]) <= UGANDA_BBOX["lat"][1], row
        assert UGANDA_BBOX["lon"][0] <= float(row["lon"]) <= UGANDA_BBOX["lon"][1], row
    assert DISTRICTS.read_text().startswith("# source: ")


def test_districts_csv_has_demo_districts():
    assert DEMO_DISTRICTS <= {r["district"] for r in read_districts()}


# --- Against the real database; only after `supabase db push`. Everything rolls back. ---

def insert_sale(db, village_id, farmer_id, call_id, form="kiboko"):
    db.execute(
        """insert into public.entries (call_id, farmer_id, kind, crop, currency, price_total,
               coffee_form, coffee_type, amount_kg, date_sold)
           values (%s, %s, 'sale', 'coffee', 'UGX', 5900, %s, 'robusta', 1, '2026-09-01')
           returning id""",
        (call_id, farmer_id, form),
    )


@pytest.fixture
def ids(db):
    village = db.execute(
        """insert into public.villages (region, district, sub_county, parish, village, is_synthetic)
           values ('Central', 'Masaka', 'T', 'T', 'Tdrift', true) returning id""").fetchone()[0]
    farmer = db.execute(
        """insert into public.farmers (name, pin_hash, village_id, is_synthetic)
           values ('T', 'drift-test-hash', %s, true) returning id""", (village,)).fetchone()[0]
    call = db.execute(
        "insert into public.calls (farmer_id, source, is_synthetic) values (%s, 'eval', true) returning id",
        (farmer,)).fetchone()[0]
    return village, farmer, call


@pytest.mark.supabase
def test_sale_round_trip_through_coffee_sale_prices(db, ids):
    village, farmer, call = ids
    insert_sale(db, village, farmer, call)
    row = db.execute(
        "select coffee_form, ugx_per_kg, village, region from public.coffee_sale_prices where farmer_id = %s",
        (farmer,)).fetchone()
    assert row == ("kiboko", 5900, "Tdrift", "Central")


@pytest.mark.supabase
def test_unknown_coffee_form_is_rejected(db, ids):
    village, farmer, call = ids
    with pytest.raises(psycopg.errors.CheckViolation):
        insert_sale(db, village, farmer, call, form="beans")


@pytest.mark.supabase
def test_conversation_id_unique_in_database(db, ids):
    _, farmer, _ = ids
    db.execute("insert into public.calls (farmer_id, conversation_id) values (%s, 'dup')", (farmer,))
    with pytest.raises(psycopg.errors.UniqueViolation):
        db.execute("insert into public.calls (farmer_id, conversation_id) values (%s, 'dup')", (farmer,))

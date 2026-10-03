import sqlite3

import pytest

from farm_ledger import (
    Kind, Unit, add_farmer, clean_crop, connect, find_farmer_by_pin,
    insert_call, list_ledger,
)


@pytest.fixture
def conn(tmp_path):
    c = connect(tmp_path / "ledger.db")
    yield c
    c.close()


@pytest.fixture
def farmer(conn):
    return add_farmer(conn, "Amina", "1234", region="Upper Valley")


def test_fresh_db_has_tables_and_is_idempotent(tmp_path):
    path = tmp_path / "new.db"
    connect(path).close()
    conn = connect(path)  # second open must not fail
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"farmers", "calls", "entries"} <= tables
    cols = {r[1] for r in conn.execute("PRAGMA table_info(entries)")}
    assert {"plot", "price_total", "date_sold", "quote_verified", "likely_disease",
            "disease_confidence", "confidence"} <= cols


def test_call_with_sale_and_disease_reads_back_as_ledger(conn, farmer):
    insert_call(conn, farmer, [
        {"kind": Kind.SALE, "crop": "Coffee Cherries", "amount": 50, "unit": Unit.KG,
         "price_total": 4000, "currency": "KES", "buyer_type": "middleman", "paid_how": "cash"},
        {"kind": "sale", "crop": "Bananas", "amount": 2, "unit": "bunch", "price_total": 600},
        {"kind": "observation", "crop": "coffee", "plot": "upper slope", "disease_detected": True,
         "symptom": "yellowing_leaves", "evidence_quote": "leaves are yellow",
         "quote_verified": True, "confidence": 0.9},
    ], received_at="2026-03-01T08:00:00", language="sw")
    ledger = list_ledger(conn, farmer)
    assert [e["kind"] for e in ledger] == ["sale", "sale", "observation"]
    assert ledger[0]["crop"] == "coffee cherry"
    assert ledger[2]["plot"] == "upper slope" and ledger[2]["disease_detected"] == 1
    assert ledger[0]["received_at"] == "2026-03-01T08:00:00" and ledger[0]["language"] == "sw"


def test_ledger_is_in_time_order_for_backdated_calls(conn, farmer):
    insert_call(conn, farmer, [{"kind": "harvest", "crop": "maize"}], received_at="2026-05-01")
    insert_call(conn, farmer, [{"kind": "harvest", "crop": "beans"}], received_at="2026-02-01")
    assert [e["crop"] for e in list_ledger(conn, farmer)] == ["bean", "maize"]


def test_value_outside_fixed_list_rejects_whole_call(conn, farmer):
    with pytest.raises(sqlite3.IntegrityError):
        insert_call(conn, farmer, [
            {"kind": "sale", "crop": "maize", "unit": "kg"},
            {"kind": "sale", "crop": "maize", "unit": "basket"},
        ])
    assert conn.execute("SELECT COUNT(*) FROM calls").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM entries").fetchone()[0] == 0


@pytest.mark.parametrize("field,value", [("confidence", 1.5), ("disease_confidence", -0.1),
                                         ("kind", "rumour"), ("symptom", "sneezing")])
def test_other_invalid_values_rejected(conn, farmer, field, value):
    with pytest.raises(sqlite3.IntegrityError):
        insert_call(conn, farmer, [{field: value}])


def test_unknown_entry_field_rejected_and_rolled_back(conn, farmer):
    with pytest.raises(ValueError):
        insert_call(conn, farmer, [{"kind": "sale"}, {"colour": "red"}])
    assert conn.execute("SELECT COUNT(*) FROM calls").fetchone()[0] == 0


def test_foreign_keys_enforced(conn):
    with pytest.raises(sqlite3.IntegrityError):
        insert_call(conn, 999, [])


@pytest.mark.parametrize("raw,clean", [
    ("Bananas", "banana"), ("coffee cherries", "coffee cherry"), ("  Maize ", "maize"),
    ("Tomatoes", "tomato"), ("grass", "grass"), ("Rice", "rice"),
])
def test_clean_crop(raw, clean):
    assert clean_crop(raw) == clean


def test_unknown_pin_finds_nobody_and_known_pin_finds_farmer(conn, farmer):
    assert find_farmer_by_pin(conn, "0000") is None
    assert find_farmer_by_pin(conn, "1234")["id"] == farmer
    assert "1234" not in find_farmer_by_pin(conn, "1234")["pin_hash"]

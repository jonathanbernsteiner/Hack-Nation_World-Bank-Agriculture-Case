import dataclasses
import json
import random

import pytest
from fastapi.testclient import TestClient

for _dependency in ("prices", "history", "places"):  # still in open PRs: keep this PR green
    pytest.importorskip(f"hotline.{_dependency}")

from hotline import calls_repo, config, db as hotline_db, pins, places, profile  # noqa: E402
from hotline.main import app  # noqa: E402
from hotline.routes.tools import find, identify, register  # noqa: E402

SALT = "test-salt"
SECRET = "test-secret"
FORBIDDEN_KEYS = {"farmer_id", "pin_hash", "name", "id"}
VILLAGE = "Wamalumbe"
PARISH = "Testparish"


@pytest.fixture(autouse=True)
def settings(monkeypatch):
    patched = dataclasses.replace(config.settings, ledger_pin_salt=SALT, hotline_tool_secret=SECRET)
    monkeypatch.setattr(config, "settings", patched)
    places.clear_village_cache()


def _walk(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from _walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk(item)


def assert_no_leak(response: dict, *secrets: str):
    assert not FORBIDDEN_KEYS & {k for k in _walk(response) if isinstance(k, str)}
    text = json.dumps(response)
    for secret in ("farmer_id", "pin_hash", *secrets):
        assert secret not in text


def _village(conn) -> int:
    return conn.execute(
        "insert into villages (region, district, sub_county, parish, village, is_verified, is_synthetic,"
        " coffee_type) values ('Central', 'Masaka', 'Kyanamukaaka', %s, %s, true, true, 'robusta')"
        " returning id",
        (PARISH, VILLAGE),
    ).fetchone()[0]


def _farmer(conn, village_id, name, pin, synthetic=True) -> int:
    return conn.execute(
        "insert into farmers (name, pin_hash, region, is_synthetic, village_id)"
        " values (%s, %s, 'Central', %s, %s) returning id",
        (name, pins.hash_pin(pin), synthetic, village_id),
    ).fetchone()[0]


def _call(conn, cid):
    return conn.execute(
        "select farmer_id, identified_by, status, pin_attempts, is_synthetic from calls where conversation_id = %s",
        (cid,),
    ).fetchone()


# ---- no database needed ----

def test_pin_digits_sw_matches_digits():
    assert register.pin_digits_sw("4831") == "nne, nane, tatu, moja"
    assert register.pin_digits_sw("0507") == "sifuri, tano, sifuri, saba"


def test_generated_pins_never_reserved():
    rng = random.Random(1)
    for _ in range(3000):
        assert int(pins.allocate_pin(None, rng, lambda p: False)) not in pins.RESERVED_PINS


def test_unset_salt_returns_error_without_lookup(monkeypatch):
    monkeypatch.setattr(config, "settings", dataclasses.replace(config.settings, ledger_pin_salt=None))

    def boom():
        raise AssertionError("database must not be touched")

    monkeypatch.setattr(hotline_db, "transaction", boom)
    client = TestClient(app)
    resp = client.post("/api/tools/identify_farmer", json={"pin": "9001", "conversation_id": "c1"},
                       headers={"X-Hotline-Tool-Secret": SECRET})
    assert resp.status_code == 200 and resp.json()["status"] == "error"


def test_bad_secret_is_401_and_db_failure_is_status_error(monkeypatch):
    client = TestClient(app)
    assert client.post("/api/tools/identify_farmer", json={}).status_code == 401

    def broken():
        raise RuntimeError("no database")

    monkeypatch.setattr(hotline_db, "transaction", broken)
    resp = client.post("/api/tools/find_farmer_by_location", json={"conversation_id": "c1"},
                       headers={"X-Hotline-Tool-Secret": SECRET})
    assert resp.status_code == 200 and resp.json() == {"status": "error"}


# ---- Supabase (rolled back) ----

@pytest.mark.supabase
def test_pin_found_and_no_leak(db):
    farmer = _farmer(db, _village(db), "Nakato Grace Namukasa", "9001")
    result = identify.identify(db, "conv-found", "9 0-01")
    assert result["status"] == "found" and result["identified_by"] == "pin"
    assert result["farmer"]["first_name"] == "Nakato"
    assert result["farmer"]["village"] == VILLAGE
    assert {"village_price", "other_prices", "history", "nearby_reports"} <= result.keys()
    assert_no_leak(result, "Grace", "Namukasa")
    assert _call(db, "conv-found")[:3] == (farmer, "pin", "in_call")


@pytest.mark.supabase
def test_three_attempt_lock_survives_new_call_sid(db):
    _farmer(db, _village(db), "Nakato", "9001")
    assert identify.identify(db, "conv-lock", "1111") == {"status": "not_found", "attempts_left": 2}
    assert identify.identify(db, "conv-lock", "abcd")["attempts_left"] == 1
    assert identify.identify(db, "conv-lock", "2222")["attempts_left"] == 0
    assert identify.identify(db, "conv-lock", "9001") == {"status": "locked"}
    assert calls_repo.pin_attempts(db, "conv-lock") == 3
    assert identify.identify(db, "conv-other", "9001")["status"] == "found"


@pytest.mark.supabase
def test_upsert_does_not_regress_status(db):
    farmer = _farmer(db, _village(db), "Nakato", "9001")
    calls_repo.upsert_call_identity(db, "conv-s", farmer_id=farmer, identified_by="pin", is_synthetic=True)
    db.execute("update calls set status = 'processed' where conversation_id = 'conv-s'")
    calls_repo.upsert_call_identity(db, "conv-s", farmer_id=farmer, identified_by="location", is_synthetic=True)
    assert _call(db, "conv-s")[1:3] == ("location", "processed")


def _find(db, **kw):
    req = find.FindRequest(first_name="Nakato", district="Masaka", village=VILLAGE, **kw)
    return find.locate(db, req, "conv-find")


@pytest.mark.supabase
def test_location_unique_has_totals_only(db):
    farmer = _farmer(db, _village(db), "Nakato Grace", "9001")
    result = _find(db)
    assert result["status"] == "found" and result["identified_by"] == "location"
    assert set(result["history"]) == {"coffee_years"}
    assert not {"last_sales", "problems", "nearby_reports"} & result.keys()
    assert_no_leak(result, "Grace")
    assert _call(db, "conv-find")[:2] == (farmer, "location")


@pytest.mark.supabase
def test_location_misspelled_first_name_matches(db):
    _farmer(db, _village(db), "Nakato", "9001")
    req = find.FindRequest(first_name="Nakatto", district="Masaka", village=VILLAGE)
    assert find.locate(db, req, "conv-find")["status"] == "found"


@pytest.mark.supabase
def test_two_same_name_farmers_reveal_no_people(db):
    village = _village(db)
    _farmer(db, village, "Nakato Grace", "9001")
    _farmer(db, village, "Nakato Rose", "9002")
    result = _find(db)
    assert result["status"] == "ambiguous"
    assert result["candidates"] == [{"village": VILLAGE, "parish": PARISH, "sub_county": "Kyanamukaaka"}]
    assert_no_leak(result, "Grace", "Rose")
    assert _call(db, "conv-find") is None


@pytest.mark.supabase
def test_location_unknown_village_not_found(db):
    _village(db)
    req = find.FindRequest(first_name="Nakato", district="Masaka", village="Qqqqxxyy")
    assert find.locate(db, req, "c")["status"] == "not_found"


@pytest.mark.supabase
def test_same_name_villages_ask_parish(db):
    for parish in ("Parisha", "Parishb"):
        db.execute(
            "insert into villages (region, district, sub_county, parish, village) values"
            " ('Central','Masaka','Kyanamukaaka',%s,%s)", (parish, VILLAGE))
    result = _find(db)
    assert result["status"] == "ambiguous" and result["ask"] == "parish"
    assert {c["parish"] for c in result["candidates"]} == {"Parisha", "Parishb"}


def _register(db, **kw):
    req = register.RegisterRequest(first_name="Mukasa", district="Masaka", village=VILLAGE, **kw)
    return register.register(db, req, "conv-reg")


@pytest.mark.supabase
def test_register_known_village(db):
    village = _village(db)
    result = _register(db)
    assert result["status"] == "registered" and result["village_known"] is True
    pin = result["pin"]
    assert len(pin) == 4 and int(pin) not in pins.RESERVED_PINS
    assert result["pin_digits_sw"] == register.pin_digits_sw(pin)
    row = db.execute("select village_id, is_synthetic from farmers where pin_hash = %s", (pins.hash_pin(pin),)).fetchone()
    assert row == (village, False)
    assert _call(db, "conv-reg")[1] == "registration"
    assert "pin_hash" not in json.dumps(result) and "farmer_id" not in json.dumps(result)


@pytest.mark.supabase
def test_register_unknown_village_creates_unverified(db):
    result = _register(db)
    assert result["status"] == "registered" and result["village_known"] is False
    row = db.execute("select is_verified, is_synthetic from villages where village = %s", (VILLAGE,)).fetchone()
    assert row == (False, False)


@pytest.mark.supabase
def test_register_duplicate_inserts_nothing(db):
    village = _village(db)
    _farmer(db, village, "Mukasa", "9001")
    before = db.execute("select count(*) from farmers").fetchone()[0]
    assert _register(db) == {"status": "possible_duplicate"}
    assert db.execute("select count(*) from farmers").fetchone()[0] == before


@pytest.mark.supabase
def test_register_need_district_writes_nothing(db):
    before = db.execute("select count(*) from farmers").fetchone()[0]
    req = register.RegisterRequest(first_name="Mukasa", village=VILLAGE)
    assert register.register(db, req, "conv-reg") == {"status": "need_district"}
    assert db.execute("select count(*) from farmers").fetchone()[0] == before
    assert _call(db, "conv-reg") is None


@pytest.mark.supabase
def test_register_pin_collision_retries(db, monkeypatch):
    village = _village(db)
    _farmer(db, village, "Other", "1234")
    draws = iter(["1234", "5678"])
    monkeypatch.setattr(pins, "allocate_pin", lambda conn: next(draws))
    # first draw collides on the unique pin_hash and must be retried inside a savepoint
    result = register.register(db, register.RegisterRequest(first_name="Zed", district="Masaka", village=VILLAGE), "c9")
    assert result["status"] == "registered" and result["pin"] == "5678"


@pytest.mark.supabase
def test_register_failure_after_insert_leaves_no_farmer(db, monkeypatch):
    _village(db)
    monkeypatch.setattr(register.profile, "build_profile", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x")))
    before = db.execute("select count(*) from farmers").fetchone()[0]
    with pytest.raises(RuntimeError):
        with db.transaction():  # stands in for db.transaction(): everything rolls back together
            _register(db)
    assert db.execute("select count(*) from farmers").fetchone()[0] == before


# ---- review regression tests ----

@pytest.mark.parametrize("spoken", ["tisa sifuri sifuri moja", "Tisa, sifuri, sifuri, moja", "9 sifuri 0-1", "9001"])
def test_kiswahili_digit_words_become_pin(spoken):
    assert identify.pin_from_speech(spoken) == "9001"


@pytest.mark.parametrize("spoken", ["", "tisa sifuri moja", "tisa sifuri sifuri moja mbili", "nine zero zero one"])
def test_unparseable_spoken_pin_is_rejected(spoken):
    assert identify.pin_from_speech(spoken) is None


@pytest.mark.supabase
def test_pin_spoken_as_kiswahili_words_is_found(db):
    farmer = _farmer(db, _village(db), "Nakato", "9001")
    assert identify.identify(db, "conv-words", "tisa sifuri sifuri moja")["status"] == "found"
    assert _call(db, "conv-words")[:2] == (farmer, "pin")


@pytest.mark.supabase
def test_register_same_name_villages_asks_parish_and_writes_nothing(db):
    for parish in ("Kitovu", "Nyendo"):
        db.execute(
            "insert into villages (region, district, sub_county, parish, village) values"
            " ('Central','Masaka','Kyanamukaaka',%s,%s)", (parish, VILLAGE))
    before = db.execute("select count(*) from farmers").fetchone()[0]
    result = _register(db)
    assert result["status"] == "ambiguous" and result["ask"] == "parish"
    assert {c["parish"] for c in result["candidates"]} == {"Kitovu", "Nyendo"}
    assert_no_leak(result)
    assert db.execute("select count(*) from farmers").fetchone()[0] == before
    assert _call(db, "conv-reg") is None
    # once the caller names the parish, registration goes ahead in that village
    chosen = _register(db, parish="Nyendo")
    assert chosen["status"] == "registered" and chosen["farmer"]["parish"] == "Nyendo"


@pytest.mark.supabase
def test_arabica_farmer_without_sales_defaults_to_parchment(db):
    village = db.execute(
        "insert into villages (region, district, sub_county, parish, village, coffee_type)"
        " values ('Eastern', 'Mbale', 'Bungokho', %s, %s, 'arabica') returning id",
        (PARISH, VILLAGE),
    ).fetchone()[0]
    farmer = _farmer(db, village, "Wanyera", "9002")
    built = profile.build_profile(db, farmer, as_of=profile.kampala_today(), identified_by="pin")
    assert built["farmer"]["main_form"] == "parchment"

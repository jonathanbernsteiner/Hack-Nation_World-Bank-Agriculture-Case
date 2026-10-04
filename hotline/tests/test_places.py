import sqlite3

import pytest

from hotline import places
from hotline.places import (
    DistrictMatch,
    create_unverified_village,
    district_candidates,
    match_district,
    match_village,
    normalize,
    phonetic_key,
)

SCHEMA = """create table villages (
  id integer primary key autoincrement, region text not null, district text not null,
  sub_county text not null, parish text not null, village text not null,
  lat real, lon real, coffee_type text,
  is_verified integer not null default 1, is_synthetic integer not null default 0,
  unique (district, sub_county, parish, village))"""


class SqliteConn:
    """Test double: psycopg-style %s placeholders on top of sqlite."""

    def __init__(self):
        self.raw = sqlite3.connect(":memory:")
        self.raw.execute(SCHEMA)

    def execute(self, sql, params=()):
        return self.raw.execute(sql.replace("%s", "?"), params)


def add(conn, district, sub_county, parish, village):
    conn.execute(
        "insert into villages (region, district, sub_county, parish, village) values (%s, %s, %s, %s, %s)",
        ("Central", district, sub_county, parish, village),
    )


@pytest.fixture(autouse=True)
def fresh_cache():
    places.clear_village_cache()
    yield
    places.clear_village_cache()


@pytest.fixture
def conn():
    c = SqliteConn()
    add(c, "Masaka", "Kyanamukaaka", "Kyabakuza A", "Kyabakuza")
    add(c, "Masaka", "Kyanamukaaka", "Kitovu", "Kisenyi")
    add(c, "Masaka", "Kyanamukaaka", "Nyendo", "Kisenyi")
    add(c, "Mbale", "Namanyonyi", "Bumasikye", "Bumasikye")
    return c


MASAKA = DistrictMatch("Masaka", "Central", -0.48617, 31.83251, 100)


def test_normalize_strips_fillers_and_punctuation():
    assert normalize("Kijiji cha  Kyabakuza!") == "kyabakuza"
    assert normalize("Sub-County Kyanamukaaka") == "kyanamukaaka"
    assert normalize("Wilaya ya Masaka") == "masaka"
    assert normalize("Cha") == "cha"  # a lone connector is kept: it is all we heard


@pytest.mark.parametrize("spoken", ["Kyanamukaka", "Kyanamukaaka", "Chanamukaka", "kyanamukaka"])
def test_phonetic_key_collapses_asr_spellings(spoken):
    assert phonetic_key(spoken) == "canamukaka"


def test_phonetic_key_rules():
    assert phonetic_key("Mbarara") == "mbalala"
    assert phonetic_key("Phone") == "fone"
    assert phonetic_key("Nyendo") == "nyendo"
    assert phonetic_key("Kasse") == "kase"


@pytest.mark.parametrize("spoken", ["Mazaka", "Masaka", "wilaya ya Masaka"])
def test_masaka_spellings_match_district(spoken):
    assert match_district(spoken).district == "Masaka"


def test_masindi_is_not_masaka():
    assert match_district("Masindi").district == "Masindi"
    assert [c.district for c in district_candidates("Masindi")][0] == "Masindi"


def test_mbale_and_mbarara_stay_apart():
    assert match_district("Mbale").district == "Mbale"
    assert match_district("Mbarara").district == "Mbarara"


def test_every_csv_district_matches_itself():
    names = [row[0] for row in places._districts()]
    assert len(names) > 100
    assert all(match_district(n) is not None and match_district(n).district == n for n in names)


def test_district_margin_rule_returns_none_and_lists_both(monkeypatch):
    close = (("Bukomansimbe", "Central", 0.0, 30.0), ("Bukomansimbi", "Central", 0.1, 30.1), ("Arua", "Northern", 3.0, 30.9))
    monkeypatch.setattr(places, "_districts", lambda: close)
    assert match_district("Bukomansimba") is None
    assert [c.district for c in district_candidates("Bukomansimba")][:2] == ["Bukomansimbe", "Bukomansimbi"]


def test_district_garbage_and_empty():
    assert match_district("") is None
    assert match_district("zzzzqq") is None
    assert district_candidates("   ") == []


@pytest.mark.parametrize("spoken", ["Kyabakuza", "Chabakuza", "kijiji cha Kyabakuza", "Kyabakusa"])
def test_kyabakuza_spellings_are_unique_in_masaka(conn, spoken):
    result = match_village(conn, "Masaka", spoken)
    assert result.status == "unique"
    assert result.best.village == "Kyabakuza"
    assert result.best.district == "Masaka"


def test_same_name_in_another_district_is_none(conn):
    assert match_village(conn, "Mbale", "Kyabakuza").status == "none"


def test_unknown_district_or_empty_village_is_none(conn):
    assert match_village(conn, "Gulu", "Kyabakuza").status == "none"
    assert match_village(conn, "Masaka", "kijiji").status == "none"


def test_same_village_name_in_two_parishes_is_ambiguous_then_resolved(conn):
    ambiguous = match_village(conn, "Masaka", "Kisenyi")
    assert ambiguous.status == "ambiguous"
    assert ambiguous.best is None
    assert {c.parish for c in ambiguous.candidates} == {"Kitovu", "Nyendo"}
    resolved = match_village(conn, "Masaka", "Kisenyi", parish="Nyendo")
    assert resolved.status == "unique"
    assert resolved.best.parish == "Nyendo"
    assert match_village(conn, "Masaka", "Kisenyi", sub_county="Kyanamukaka", parish="kitovu").best.parish == "Kitovu"


def test_unmatched_parish_hides_village(conn):
    assert match_village(conn, "Masaka", "Kisenyi", parish="Elsewhere").status == "none"


def test_ambiguous_candidates_capped_at_three(conn):
    for parish in ("P1", "P2", "P3"):
        add(conn, "Masaka", "Kyanamukaaka", parish, "Kisenyi")
    result = match_village(conn, "Masaka", "Kisenyi")
    assert result.status == "ambiguous"
    assert len(result.candidates) == 3


def test_candidates_carry_only_village_fields(conn):
    fields = set(match_village(conn, "Masaka", "Kisenyi").candidates[0].__dataclass_fields__)
    assert fields == {"village_id", "village", "parish", "sub_county", "district", "score"}


def test_match_village_query_is_scoped_to_the_district():
    seen = []

    class Spy:
        def execute(self, sql, params=()):
            seen.append((sql, params))
            return type("R", (), {"fetchall": lambda self: []})()

    match_village(Spy(), "Masaka", "Kyabakuza")
    assert "where lower(district) = %s" in seen[0][0]
    assert seen[0][1] == ("masaka",)


def test_create_unverified_village_is_idempotent_and_flagged(conn):
    first = create_unverified_village(conn, MASAKA, "kijiji cha Lwanda", None, None)
    second = create_unverified_village(conn, MASAKA, "Lwanda", "unknown", "")
    assert first == second
    row = conn.execute(
        "select village, parish, sub_county, lat, lon, is_verified, is_synthetic from villages where id = %s",
        (first,),
    ).fetchone()
    assert row == ("Lwanda", "unknown", "unknown", MASAKA.lat, MASAKA.lon, 0, 0)
    assert conn.execute("select count(*) from villages where village = 'Lwanda'").fetchone()[0] == 1


def test_create_refreshes_cache_so_new_village_matches(conn):
    assert match_village(conn, "Masaka", "Lwanda").status == "none"
    new_id = create_unverified_village(conn, MASAKA, "Lwanda", "Nyendo", "Kyanamukaaka")
    assert match_village(conn, "Masaka", "Lwanda").best.village_id == new_id


def test_create_does_not_unverify_an_existing_village(conn):
    existing = match_village(conn, "Masaka", "Kyabakuza").best
    again = create_unverified_village(conn, MASAKA, "Kyabakuza", "Kyabakuza A", "Kyanamukaaka")
    assert again == existing.village_id
    assert conn.execute("select is_verified from villages where id = %s", (again,)).fetchone()[0] == 1


def test_create_rejects_empty_village(conn):
    with pytest.raises(ValueError):
        create_unverified_village(conn, MASAKA, "kijiji", None, None)


@pytest.mark.supabase
def test_supabase_create_and_match_in_rolled_back_transaction(db):
    district = match_district("Mazaka")
    first = create_unverified_village(db, district, "Zzplaces Test", "Ptest", "Stest")
    assert create_unverified_village(db, district, "zzplaces test", "Ptest", "Stest") == first
    row = db.execute(
        "select is_verified, is_synthetic, lat from villages where id = %s", (first,)
    ).fetchone()
    assert row == (False, False, district.lat)
    assert match_village(db, "Masaka", "Zzplaces Test").best.village_id == first


# --- Review regressions (#48) ---


@pytest.mark.parametrize(
    "spoken, tied",
    [("Kaungu", {"Kalungu", "Kanungu"}), ("Tooro", {"Tororo", "Ntoroko"})],
)
def test_real_districts_within_margin_return_none_and_list_both(spoken, tied):
    top_two = district_candidates(spoken, limit=2)
    assert {c.district for c in top_two} == tied
    assert all(c.score >= places.MATCH_THRESHOLD for c in top_two)
    assert match_district(spoken) is None


@pytest.mark.parametrize(
    "spoken, expected",
    [("Masaka", "Masaka"), ("Mazaka", "Masaka"), ("Massaka", "Masaka"), ("Masaaka", "Masaka"),
     ("Masindi", "Masindi"), ("Mazindi", "Masindi"), ("Masiindi", "Masindi")],
)
def test_masaka_and_masindi_never_collapse(spoken, expected):
    assert match_district(spoken).district == expected
    assert places.score("Masaka", "Masindi") < places.MATCH_THRESHOLD


def test_below_threshold_district_returns_none_but_offers_candidates():
    # Swahili ASR hears "Mbale" as the word "mbali" (far): no confident match, Mbale offered first.
    assert match_district("Mbali") is None
    assert district_candidates("Mbali")[0].district == "Mbale"


def test_village_candidates_stay_inside_the_requested_district(conn):
    add(conn, "Mbale", "Namanyonyi", "Bumasikye", "Kisenyi")
    add(conn, "Mbale", "Namanyonyi", "Bumasikye", "Kyabakuza")
    for spoken in ("Kisenyi", "Kyabakuza", "Chabakuza"):
        result = match_village(conn, "Masaka", spoken)
        assert result.candidates
        assert all(c.district == "Masaka" for c in result.candidates)


def test_village_query_never_touches_farmers():
    seen = []

    class Spy:
        def execute(self, sql, params=()):
            seen.append(sql.lower())
            return type("R", (), {"fetchall": lambda self: []})()

    match_village(Spy(), "Masaka", "Kyabakuza", parish="Kitovu", sub_county="Kyanamukaaka")
    assert seen and all("from villages" in sql and "farmer" not in sql for sql in seen)


def test_district_case_does_not_split_the_cache(conn):
    assert match_village(conn, "MASAKA", "Lwanda").status == "none"
    new_id = create_unverified_village(conn, MASAKA, "Lwanda", None, None)
    assert match_village(conn, "masaka", "Lwanda").best.village_id == new_id


@pytest.mark.xfail(
    strict=True,
    reason="review #48 finding 1: a stored 'unknown' parish/sub-county must not hide a registered village",
)
@pytest.mark.parametrize("narrow", [{"parish": "Nyendo"}, {"sub_county": "Kyanamukaaka"}])
def test_unknown_parish_does_not_hide_a_registered_village(conn, narrow):
    new_id = create_unverified_village(conn, MASAKA, "Lwanda", None, None)
    result = match_village(conn, "Masaka", "Lwanda", **narrow)
    assert result.status == "unique"
    assert result.best.village_id == new_id

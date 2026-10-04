import re
from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest

from hotline import bands, prices
from hotline.numbers_sw import to_words

AS_OF = date(2026, 10, 3)
HOME = {"village_id": 1, "village": "Kyabakuza", "parish": "Kyabakuza P", "sub_county": "Kyanamukaaka", "district": "Masaka"}


def sale(farmer, per_kg=5000, *, village_id=1, village="Kyabakuza", parish="Kyabakuza P", sub_county="Kyanamukaaka",
         district="Masaka", form="kiboko", days_ago=10, kg=100, synthetic=False):
    return {
        "farmer_id": farmer, "is_synthetic": synthetic, "coffee_form": form,
        "sale_date": AS_OF - timedelta(days=days_ago), "amount_kg": kg, "price_total": per_kg * kg,
        "village_id": village_id, "region": "Central", "district": district,
        "sub_county": sub_county, "parish": parish, "village": village,
    }


def three_farmers(**kw):
    return [sale(f, **kw) for f in (1, 2, 3)]


def test_village_level_when_threshold_met():
    out = prices.village_price(three_farmers(per_kg=5900), HOME, "kiboko", AS_OF)
    assert (out["level"], out["area"], out["median_ugx_per_kg"]) == ("village", "Kyabakuza", 5900)
    assert out["n_sales"] == 3 and out["n_farmers"] == 3
    assert out["median_words_sw"] == "elfu tano na mia tisa"
    assert out["window"] == {"from": "2025-10-03", "to": "2026-10-03"}


def test_falls_back_to_parish_when_two_farmers_only():
    rows = [sale(1), sale(2), sale(3, village_id=2, village="Other"), sale(4, village_id=3, village="Third")]
    out = prices.village_price(rows[:2] + rows[2:], HOME, "kiboko", AS_OF)
    assert out["level"] == "parish" and out["n_farmers"] == 4


def test_falls_back_through_all_levels_to_national():
    out = prices.village_price([sale(1), sale(2)], HOME, "kiboko", AS_OF)
    assert out["level"] == "national" and out["is_reference"] is True
    assert out["median_ugx_per_kg"] == prices.NATIONAL_REFERENCE["kiboko"]["median_ugx_per_kg"]
    assert out["n_sales"] == 0


def test_district_level_and_subcounty_level():
    sub = [sale(1), sale(2), sale(3, village_id=9, village="V9", parish="P9")]
    assert prices.village_price(sub, HOME, "kiboko", AS_OF)["level"] == "sub_county"
    dist = [sale(i, village_id=i + 10, village=f"V{i}", parish=f"P{i}", sub_county=f"S{i}") for i in (1, 2, 3)]
    out = prices.village_price(dist, HOME, "kiboko", AS_OF)
    assert (out["level"], out["area"]) == ("district", "Masaka")


def test_other_district_rows_ignored():
    rows = three_farmers(district="Mbarara")
    assert prices.village_price(rows, HOME, "kiboko", AS_OF)["level"] == "national"


def test_single_farmer_many_sales_does_not_qualify():
    rows = [sale(1, days_ago=d) for d in range(1, 8)]
    assert prices.village_price(rows, HOME, "kiboko", AS_OF)["level"] == "national"


def test_other_form_rows_ignored():
    rows = three_farmers(form="faq", per_kg=12000)
    assert prices.village_price(rows, HOME, "kiboko", AS_OF)["level"] == "national"


def test_band_filters_x10_slip():
    rows = three_farmers(per_kg=5000) + [sale(4, per_kg=50000)]
    out = prices.village_price(rows, HOME, "kiboko", AS_OF)
    assert out["n_sales"] == 3 and out["median_ugx_per_kg"] == 5000
    only_slips = three_farmers(per_kg=50000)
    assert prices.village_price(only_slips, HOME, "kiboko", AS_OF)["level"] == "national"


def test_window_edges_365_in_366_out():
    inside = [sale(f, days_ago=365) for f in (1, 2, 3)]
    outside = [sale(f, days_ago=366) for f in (1, 2, 3)]
    assert prices.village_price(inside, HOME, "kiboko", AS_OF)["level"] == "village"
    assert prices.village_price(outside, HOME, "kiboko", AS_OF)["level"] == "national"
    future = [sale(f, days_ago=-1) for f in (1, 2, 3)]
    assert prices.village_price(future, HOME, "kiboko", AS_OF)["level"] == "national"


@pytest.mark.parametrize(("raw", "rounded"), [(5024, 5000), (5025, 5050), (5074, 5050), (5075, 5100), (12250, 12250)])
def test_rounding_to_50(raw, rounded):
    assert prices.round_ugx(raw) == rounded


def test_p25_p75():
    rows = [sale(f, per_kg=p) for f, p in zip(range(1, 6), (4000, 5000, 6000, 7000, 8000), strict=True)]
    out = prices.village_price(rows, HOME, "kiboko", AS_OF)
    assert (out["p25"], out["median_ugx_per_kg"], out["p75"]) == (5000, 6000, 7000)


def test_includes_synthetic_flag():
    rows = [sale(1, synthetic=True), sale(2), sale(3)]
    assert prices.village_price(rows, HOME, "kiboko", AS_OF, include_synthetic=True)["includes_synthetic"] is True
    real = prices.village_price(rows, HOME, "kiboko", AS_OF, include_synthetic=False)
    assert real["level"] == "national" and real["includes_synthetic"] is False
    assert prices.village_price(three_farmers(), HOME, "kiboko", AS_OF, include_synthetic=True)["includes_synthetic"] is False


def test_median_words_present_and_correct():
    rows = three_farmers(per_kg=12300, form="faq")
    out = prices.village_price(rows, HOME, "faq", AS_OF)
    assert out["median_words_sw"] == "elfu kumi na mbili na mia tatu"
    assert not any(ch.isdigit() for ch in out["median_words_sw"])


def test_response_never_leaks_farmers_or_individual_prices():
    out = prices.village_price(three_farmers(), HOME, "kiboko", AS_OF)
    assert "farmer_id" not in str(out) and "rows" not in out
    assert set(out) == {"form", "median_ugx_per_kg", "p25", "p75", "n_sales", "n_farmers", "level", "area",
                        "window", "includes_synthetic", "median_words_sw"}


def test_national_reference_has_source_and_month():
    for ref in prices.NATIONAL_REFERENCE.values():
        assert ref["month"] and ref["source_url"].startswith("https://") and ref["median_ugx_per_kg"] > 0


def test_unknown_form_gets_no_reference():
    out = prices.village_price([], HOME, "red_cherry", AS_OF)
    assert out["level"] == "national" and out["median_ugx_per_kg"] is None and out["median_words_sw"] is None


def test_prices_for_returns_main_and_other_forms():
    rows = three_farmers(per_kg=5900) + three_farmers(per_kg=12300, form="faq") + [sale(1, form="parchment", per_kg=15000)]
    out = prices.prices_for(rows, HOME, "kiboko", AS_OF)
    assert out["village_price"]["form"] == "kiboko" and out["village_price"]["level"] == "village"
    assert [o["form"] for o in out["other_prices"]] == ["faq"]
    assert set(out["other_prices"][0]) == {"form", "median_ugx_per_kg", "n_sales", "level", "median_words_sw"}


@pytest.mark.supabase
def test_load_sale_rows_round_trip(db):
    with db.cursor() as cur:
        cur.execute("insert into villages (region, district, sub_county, parish, village, is_synthetic) "
                    "values ('Central','ZzTestDistrict','S','P','V',true) returning id")
        vid = cur.fetchone()[0]
        cur.execute("insert into farmers (name, pin_hash, village_id, is_synthetic) values ('T','zz-test-hash-43',%s,true) returning id", (vid,))
        fid = cur.fetchone()[0]
        cur.execute("insert into calls (farmer_id, received_at, is_synthetic) values (%s, %s, true) returning id",
                    (fid, "2026-09-20T10:00:00+03:00"))
        cid = cur.fetchone()[0]
        cur.execute("insert into entries (call_id, farmer_id, kind, crop, currency, price_total, amount_kg, coffee_form, date_sold) "
                    "values (%s,%s,'sale','coffee','UGX',590000,100,'kiboko','2026-09-18')", (cid, fid))
    rows = prices.load_sale_rows(db, "ZzTestDistrict", date(2026, 10, 3), include_synthetic=True)
    assert len(rows) == 1 and rows[0]["village_id"] == vid and float(rows[0]["price_total"]) == 590000
    assert prices.load_sale_rows(db, "ZzTestDistrict", date(2026, 10, 3), include_synthetic=False) == []
    assert prices.load_sale_rows(db, "ZzTestDistrict", date(2026, 9, 1), include_synthetic=True) == []


# --- Review regression tests (#43) ---


def test_three_sales_from_two_farmers_falls_back_to_parish():
    """Acceptance: 3 sales from 2 farmers does not qualify, even though the sale count does."""
    village = [sale(1, days_ago=5), sale(1, days_ago=40), sale(2)]
    assert prices.village_price(village, HOME, "kiboko", AS_OF)["level"] == "national"
    neighbour = [sale(3, village_id=2, village="Other")]
    out = prices.village_price(village + neighbour, HOME, "kiboko", AS_OF)
    assert (out["level"], out["n_sales"], out["n_farmers"]) == ("parish", 4, 3)


def test_out_of_band_sale_never_counts_towards_the_threshold():
    """The band runs before the threshold: a x10 slip cannot be the third farmer of a level."""
    rows = [sale(1), sale(2), sale(3, per_kg=50_000), sale(4, village_id=2, village="Other")]
    out = prices.village_price(rows, HOME, "kiboko", AS_OF)
    assert (out["level"], out["n_sales"], out["n_farmers"]) == ("parish", 3, 3)


def test_median_uses_the_bands_defined_in_bands_py(monkeypatch):
    """bands.py is the only definition; prices.py must read it, not a copy."""
    assert prices.BANDS is bands.BANDS
    assert prices.village_price(three_farmers(), HOME, "kiboko", AS_OF)["level"] == "village"
    monkeypatch.setattr(bands, "BANDS", {**bands.BANDS, "kiboko": (1, 2)})
    assert prices.village_price(three_farmers(), HOME, "kiboko", AS_OF)["level"] == "national"


def test_prices_for_never_carries_farmer_ids():
    ids = [f"farmer-secret-{i}" for i in range(6)]
    rows = [sale(f) for f in ids[:3]] + [sale(f, form="faq", per_kg=12_000) for f in ids[3:]]
    out = prices.prices_for(rows, HOME, "kiboko", AS_OF)
    assert "farmer-secret" not in repr(out) and "farmer_id" not in repr(out)
    assert out["village_price"]["level"] == "village" and [o["form"] for o in out["other_prices"]] == ["faq"]


class _FakeCursor:
    def __init__(self, log):
        self.log = log
        self.description = [SimpleNamespace(name=n) for n in ("farmer_id", "sale_date", "price_total")]

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return None

    def execute(self, query, params):
        self.log.append((query, params))

    def fetchall(self):
        return [(7, AS_OF, 590_000)]


class _FakeConn:
    def __init__(self):
        self.log = []

    def cursor(self):
        return _FakeCursor(self.log)


def test_load_sale_rows_is_parameterised_with_an_inclusive_365_day_window(monkeypatch):
    conn = _FakeConn()
    district = "Masaka'; drop table entries; --"
    rows = prices.load_sale_rows(conn, district, AS_OF, include_synthetic=False)
    (query, params), = conn.log
    assert query.count("%s") == 4 and "Masaka" not in query and "drop" not in query
    assert "sale_date > %s and sale_date <= %s" in query and "coffee_sale_prices" in query
    # exclusive lower bound 366 days back == a sale 365 days back is still in
    assert params == (district, AS_OF - timedelta(days=366), AS_OF, False)
    assert rows == [{"farmer_id": 7, "sale_date": AS_OF, "price_total": 590_000}]
    monkeypatch.setattr(prices.config, "settings", replace(prices.config.settings, price_include_synthetic=False))
    prices.load_sale_rows(conn, "Masaka", AS_OF)
    assert conn.log[-1][1][-1] is False


def test_parish_level_is_scoped_to_the_home_sub_county():
    """villages is unique on (district, sub_county, parish, village): parish names repeat across sub-counties."""
    rows = [sale(f, village_id=10 + f, village=f"V{f}", sub_county="Kyesiiga") for f in (1, 2, 3)]
    out = prices.village_price(rows, HOME, "kiboko", AS_OF)
    assert (out["level"], out["area"]) == ("district", "Masaka")


def test_home_type_from_the_interface_contract():
    assert prices.SaleRow is not None
    home = prices.Home(**HOME)
    assert prices.village_price(three_farmers(), home, "kiboko", AS_OF)["level"] == "village"


@pytest.mark.supabase
def test_round_trip_three_farmers_give_a_village_median(db):
    """Acceptance: 3 farmers x 1 sale in one village -> village-level median via load_sale_rows + village_price.

    A 4th farmer sold 366 days back: the SQL window must drop that sale, or the median moves."""
    as_of = date(2026, 10, 3)
    home = {"village_id": None, "village": "V43", "parish": "P43", "sub_county": "S43", "district": "ZzReview43"}
    with db.cursor() as cur:
        cur.execute("insert into villages (region, district, sub_county, parish, village, is_synthetic) "
                    "values ('Central', %s, %s, %s, %s, true) returning id",
                    (home["district"], home["sub_county"], home["parish"], home["village"]))
        home["village_id"] = cur.fetchone()[0]
        for i, (per_kg, days_ago) in enumerate([(5_800, 10), (5_900, 365), (6_000, 30), (9_000, 366)]):
            cur.execute("insert into farmers (name, pin_hash, village_id, is_synthetic) "
                        "values (%s, %s, %s, true) returning id", (f"R{i}", f"zz-review-43-{i}", home["village_id"]))
            fid = cur.fetchone()[0]
            cur.execute("insert into calls (farmer_id, received_at, is_synthetic) values (%s, %s, true) returning id",
                        (fid, "2026-10-02T10:00:00+03:00"))
            cid = cur.fetchone()[0]
            cur.execute("insert into entries (call_id, farmer_id, kind, crop, currency, price_total, amount_kg, "
                        "coffee_form, date_sold) values (%s, %s, 'sale', 'coffee', 'UGX', %s, 100, 'kiboko', %s)",
                        (cid, fid, per_kg * 100, as_of - timedelta(days=days_ago)))
    rows = prices.load_sale_rows(db, home["district"], as_of, include_synthetic=True)
    assert sorted(r["sale_date"] for r in rows) == [as_of - timedelta(days=d) for d in (365, 30, 10)]
    out = prices.village_price(rows, home, "kiboko", as_of, include_synthetic=True)
    assert (out["level"], out["area"], out["n_sales"], out["n_farmers"]) == ("village", "V43", 3, 3)
    assert out["median_ugx_per_kg"] == 5_900 and out["median_words_sw"] == "elfu tano na mia tisa"
    assert out["includes_synthetic"] is True


def test_three_sales_do_not_reveal_individual_prices_through_quartiles():
    rows = [sale(f, per_kg) for f, per_kg in ((1, 4_000), (2, 5_000), (3, 6_500))]
    out = prices.village_price(rows, HOME, "kiboko", AS_OF)
    assert out["n_sales"] == 3 and out["p25"] is None and out["p75"] is None


def test_drugar_has_a_national_reference():
    out = prices.village_price([], HOME, "drugar", AS_OF)
    assert (out["level"], out["median_ugx_per_kg"]) == ("national", 14_500)


# --- Review cycle 2 regression tests (#43) ---


@pytest.mark.xfail(strict=True, reason="review cycle 2 finding 1: level is 'national', the #43 contract says 'national_reference'")
def test_national_fallback_level_is_national_reference():
    """Issue #43 scope: the fallback is {"level": "national_reference", ...}, and the agent prompt (#46) branches on
    that value. Zombo (one farmer in the #20 season) takes this path in the demo."""
    zombo = {"village_id": 6, "village": "Ora", "parish": "Ora P", "sub_county": "Ora S", "district": "Zombo"}
    rows = [sale(1, village_id=6, village="Ora", parish="Ora P", sub_county="Ora S", district="Zombo",
                 form="parchment", per_kg=16_000, days_ago=d) for d in (5, 40, 90)]
    out = prices.prices_for(rows, zombo, "parchment", AS_OF)
    assert out["village_price"]["median_ugx_per_kg"] == 15_500
    assert out["village_price"]["level"] == "national_reference"


@pytest.mark.parametrize("form", sorted(prices.NATIONAL_REFERENCE))
def test_national_reference_is_spoken_from_its_own_figure(form):
    """The fallback the agent reads for Zombo-like callers: words match the figure, the figure is plausible."""
    ref = prices.NATIONAL_REFERENCE[form]
    out = prices.village_price([], HOME, form, AS_OF)
    assert out["median_ugx_per_kg"] == ref["median_ugx_per_kg"] and ref["median_ugx_per_kg"] % 50 == 0
    assert bands.in_band(form, ref["median_ugx_per_kg"]), "a reference outside its band is a typo"
    assert out["median_words_sw"] == to_words(ref["median_ugx_per_kg"])
    assert re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", ref["month"])
    assert (out["reference_month"], out["reference_source_url"]) == (ref["month"], ref["source_url"])
    assert (out["n_sales"], out["n_farmers"], out["p25"], out["p75"], out["includes_synthetic"]) == (0, 0, None, None, False)


def test_quartiles_appear_only_from_five_sales():
    """Guardrail 7: p25/p75 stay None below 5 sales; at 5 they are the 2nd and 4th sale."""
    four = [sale(f, p) for f, p in zip(range(1, 5), (4_000, 5_000, 6_000, 7_000), strict=True)]
    out = prices.village_price(four, HOME, "kiboko", AS_OF)
    assert (out["level"], out["n_sales"], out["p25"], out["p75"]) == ("village", 4, None, None)
    out = prices.village_price([*four, sale(5, 8_000)], HOME, "kiboko", AS_OF)
    assert (out["p25"], out["median_ugx_per_kg"], out["p75"]) == (5_000, 6_000, 7_000)


def test_excluded_synthetic_rows_do_not_move_the_median():
    rows = three_farmers(per_kg=5_000) + [sale(f, per_kg=9_000, synthetic=True) for f in (4, 5, 6)]
    real = prices.village_price(rows, HOME, "kiboko", AS_OF, include_synthetic=False)
    assert (real["n_sales"], real["n_farmers"], real["median_ugx_per_kg"], real["includes_synthetic"]) == (3, 3, 5_000, False)
    mixed = prices.village_price(rows, HOME, "kiboko", AS_OF, include_synthetic=True)
    assert (mixed["n_sales"], mixed["median_ugx_per_kg"], mixed["includes_synthetic"]) == (6, 7_000, True)


def test_numeric_price_total_from_postgres_gives_the_same_median():
    """entries.price_total is numeric(14, 2), so psycopg returns Decimal; amount_kg is double precision."""
    rows = [{**sale(f), "price_total": Decimal("590000.00"), "amount_kg": 100.0} for f in (1, 2, 3)]
    out = prices.village_price(rows, HOME, "kiboko", AS_OF)
    assert (out["level"], out["median_ugx_per_kg"], out["median_words_sw"]) == ("village", 5_900, "elfu tano na mia tisa")

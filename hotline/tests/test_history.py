import json
from datetime import date

import pytest

from hotline import history
from hotline.history import coffee_years, last_sales, nearby_reports, problems, summarize

AS_OF = date(2026, 9, 30)
HOME = {"village_id": 1, "village": "Kyabakuza", "parish": "Kitovu", "sub_county": "Kyanamukaaka",
        "district": "Masaka", "region": "Central"}
BORER = "black_coffee_twig_borer"


def sale(day, kg, total, form="kiboko", buyer="middleman", **extra):
    return {"id": 1, "entry_date": day, "kind": "sale", "crop": "coffee", "amount_kg": kg,
            "price_total": total, "currency": "UGX", "coffee_form": form, "buyer_type": buyer, **extra}


def harvest(day, kg):
    return {"entry_date": day, "kind": "harvest", "crop": "coffee", "yield_amount": kg, "unit": "kg"}


def obs(farmer, day=date(2026, 9, 20), likely=BORER, symptom="wilting", parish="Kitovu",
        sub_county="Kyanamukaaka", district="Masaka"):
    return {"farmer_id": farmer, "entry_date": day, "kind": "observation", "symptom": symptom,
            "likely_disease": likely, "parish": parish, "sub_county": sub_county,
            "district": district}


def keys_and_values(value):
    """Every dict key and string value in a nested structure."""
    if isinstance(value, dict):
        for k, v in value.items():
            yield k
            yield from keys_and_values(v)
    elif isinstance(value, list):
        for v in value:
            yield from keys_and_values(v)
    elif isinstance(value, str):
        yield value


# --- coffee_years ---

def test_coffee_year_boundary_sep_30_vs_oct_1():
    rows = [sale(date(2025, 9, 30), 100, 500_000), sale(date(2025, 10, 1), 200, 1_200_000)]
    years = {y["year"]: y for y in coffee_years(rows, AS_OF)}
    assert years["2024/25"]["sold_kg"] == 100
    assert years["2025/26"]["sold_kg"] == 200


def test_years_newest_first_max_two():
    rows = [sale(date(2023, 11, 1), 50, 1), sale(date(2024, 11, 1), 60, 1), sale(date(2025, 11, 1), 70, 1)]
    assert [y["year"] for y in coffee_years(rows, AS_OF)] == ["2025/26", "2024/25"]


def test_harvest_and_weighted_average_rounded_to_50():
    rows = [harvest(date(2025, 11, 5), 1180), sale(date(2025, 12, 1), 100, 500_000),
            sale(date(2026, 1, 1), 300, 1_800_000)]
    (year,) = coffee_years(rows, AS_OF)
    assert year == {"year": "2025/26", "harvest_kg": 1180, "sold_kg": 400, "avg_ugx_per_kg": 5750}


def test_weighted_average_is_not_mean_of_unit_prices():
    rows = [sale(date(2025, 12, 1), 100, 500_000), sale(date(2025, 12, 2), 900, 7_200_000)]
    (year,) = coffee_years(rows, AS_OF)
    assert year["avg_ugx_per_kg"] == 7700  # 7.7M / 1000 kg; mean of 5000 and 8000 would be 6500


def test_bag_sale_without_kg_counts_in_neither_total_nor_average():
    rows = [sale(date(2025, 12, 1), 100, 500_000), sale(date(2025, 12, 5), None, 900_000, form="faq")]
    (year,) = coffee_years(rows, AS_OF)
    assert year["sold_kg"] == 100
    assert year["avg_ugx_per_kg"] == 5000


def test_only_unweighable_sales_means_null_average():
    (year,) = coffee_years([sale(date(2025, 12, 5), None, 900_000)], AS_OF)
    assert year["sold_kg"] == 0 and year["avg_ugx_per_kg"] is None


def test_empty_history():
    assert coffee_years([], AS_OF) == []
    assert last_sales([]) == [] and problems([]) == []
    assert nearby_reports([], HOME, AS_OF) == []


def test_non_coffee_rows_ignored():
    banana = {**sale(date(2025, 12, 1), 100, 1), "crop": "banana"}
    assert coffee_years([banana], AS_OF) == []


# --- last_sales / problems ---

def test_last_sales_newest_first_n_and_no_buyer_name():
    rows = [sale(date(2026, d, 1), 100, 500_000, buyer_name="Secret Trader") for d in (1, 2, 3, 4)]
    out = last_sales(rows)
    assert [s["date"] for s in out] == ["2026-04-01", "2026-03-01", "2026-02-01"]
    assert out[0] == {"date": "2026-04-01", "form": "kiboko", "kg": 100, "ugx_per_kg": 5000,
                      "buyer": "middleman"}
    assert "Secret Trader" not in json.dumps(out) and "buyer_name" not in json.dumps(out)


def test_last_sales_without_kg_has_null_price_per_kg():
    (s,) = last_sales([sale(date(2026, 7, 1), None, 900_000, form="faq")])
    assert s["kg"] is None and s["ugx_per_kg"] is None


def test_problems_newest_first():
    rows = [obs(1, date(2026, 8, 30)), obs(1, date(2026, 9, 10), likely=None, symptom="rot"),
            sale(date(2026, 9, 11), 1, 1)]
    out = problems(rows, n=3)
    assert out == [{"date": "2026-09-10", "symptom": "rot", "likely": None},
                   {"date": "2026-08-30", "symptom": "wilting", "likely": BORER}]


# --- nearby_reports ---

def test_three_farms_in_parish_give_one_parish_row():
    rows = [obs(10), obs(11), obs(12), obs(10, date(2026, 9, 25))]
    assert nearby_reports(rows, HOME, AS_OF) == [
        {"likely": BORER, "farms": 3, "level": "parish", "last_days": 30}]


def test_single_farm_hidden_two_farms_shown():
    assert nearby_reports([obs(10), obs(10, date(2026, 9, 21))], HOME, AS_OF) == []
    assert len(nearby_reports([obs(10), obs(11)], HOME, AS_OF)) == 1


def test_caller_excluded():
    rows = [obs(1), obs(10)]
    assert nearby_reports(rows, HOME, AS_OF, exclude_farmer_id=1) == []
    assert nearby_reports([obs(1), obs(10), obs(11)], HOME, AS_OF, exclude_farmer_id=1)[0]["farms"] == 2


def test_falls_back_to_sub_county():
    rows = [obs(10, parish="Kitovu"), obs(11, parish="Other Parish")]
    (report,) = nearby_reports(rows, HOME, AS_OF)
    assert report["level"] == "sub_county" and report["farms"] == 2


def test_parish_level_wins_over_sub_county_for_same_label():
    rows = [obs(10), obs(11), obs(12, parish="Other Parish")]
    (report,) = nearby_reports(rows, HOME, AS_OF)
    assert report["level"] == "parish" and report["farms"] == 2


def test_thirty_day_window():
    rows = [obs(10, date(2026, 8, 31)), obs(11, date(2026, 8, 30))]  # 30 days in, 31 days out
    assert nearby_reports(rows, HOME, AS_OF) == []
    assert len(nearby_reports([obs(10, date(2026, 8, 31)), obs(11, date(2026, 9, 1))], HOME, AS_OF)) == 1


def test_sub_county_level_also_respects_window():
    rows = [obs(10, parish="A", day=date(2026, 8, 1)), obs(11, parish="B", day=date(2026, 8, 2))]
    assert nearby_reports(rows, HOME, AS_OF) == []


def test_not_sure_and_missing_likely_group_by_symptom():
    rows = [obs(10, likely="not_sure", symptom="rot"), obs(11, likely=None, symptom="rot")]
    (report,) = nearby_reports(rows, HOME, AS_OF)
    assert report["likely"] == "rot"


def test_other_district_ignored():
    rows = [obs(10, district="Mbarara"), obs(11, district="Mbarara")]
    assert nearby_reports(rows, HOME, AS_OF) == []


def test_nearby_output_has_no_names_or_ids():
    rows = [{**obs(10), "name": "Nakato", "farmer_name": "Nakato"}, obs(11), obs(12)]
    out = nearby_reports(rows, HOME, AS_OF)
    assert set(out[0]) == {"likely", "farms", "level", "last_days"}
    assert not any("farmer" in str(s).lower() or "nakato" in str(s).lower()
                   for s in keys_and_values(out))


# --- summarize with a fake connection ---

class FakeCursor:
    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params):
        self.conn.queries.append((sql, params))
        self.rows = self.conn.results[len(self.conn.queries) - 1]

    def fetchall(self):
        return self.rows


class FakeConn:
    def __init__(self, *results):
        self.results, self.queries = list(results), []

    def cursor(self, row_factory=None):
        return FakeCursor(self)


def test_summarize_full_shape():
    hist = [sale(date(2026, 7, 18), 400, 2_120_000, form="kiboko"), harvest(date(2025, 11, 1), 1180),
            obs(1, date(2026, 8, 30))]
    conn = FakeConn(hist, [obs(10), obs(11), obs(1)])
    out = summarize(conn, 1, HOME, AS_OF)
    assert set(out) == {"coffee_years", "last_sales", "problems", "nearby_reports"}
    assert out["coffee_years"][0]["year"] == "2025/26"
    assert out["last_sales"][0]["ugx_per_kg"] == 5300
    assert out["problems"][0]["likely"] == BORER
    assert out["nearby_reports"] == [{"likely": BORER, "farms": 2, "level": "parish", "last_days": 30}]


def test_totals_only_keys_and_no_nearby_query():
    conn = FakeConn([sale(date(2026, 7, 18), 400, 2_120_000)])
    out = summarize(conn, 1, HOME, AS_OF, totals_only=True)
    assert set(out) == {"coffee_years"}
    assert len(conn.queries) == 1


def test_summarize_no_entries():
    out = summarize(FakeConn([], []), 1, HOME, AS_OF)
    assert out == {"coffee_years": [], "last_sales": [], "problems": [], "nearby_reports": []}


def test_history_sql_selects_only_callers_entries_and_reviewed_rows():
    conn = FakeConn([])
    history.load_history(conn, 42, AS_OF)
    sql, params = conn.queries[0]
    assert "e.farmer_id = %(farmer_id)s" in sql and params["farmer_id"] == 42
    assert "quote_verified is not false" in sql and ">= 0.6" in sql
    assert "buyer_name" not in sql and "pin_hash" not in sql
    assert params["since"] == date(2024, 9, 1)


def test_nearby_sql_excludes_caller_and_limits_to_30_days():
    conn = FakeConn([])
    history.load_nearby(conn, 42, HOME, AS_OF)
    sql, params = conn.queries[0]
    assert "e.farmer_id <> %(farmer_id)s" in sql and params["farmer_id"] == 42
    assert "e.kind = 'observation'" in sql
    assert "f.name" not in sql and "buyer_name" not in sql and "pin_hash" not in sql
    assert params["since"] == date(2026, 8, 31)
    assert params["district"] == "Masaka" and params["sub_county"] == "Kyanamukaaka"


# --- real database, rolled back by the fixture ---

@pytest.mark.supabase
def test_summarize_against_supabase(db):
    def one(sql, params=()):
        return db.execute(sql, params).fetchone()[0]

    village = one("insert into villages (region, district, sub_county, parish, village, is_synthetic) "
                  "values ('Central','TestDistrict','TestSC','TestParish','TestVillage', true) returning id")
    farmers = [one("insert into farmers (name, pin_hash, village_id, is_synthetic) "
                   "values (%s, %s, %s, true) returning id", (f"T{i}", f"test-hash-49-{i}", village))
               for i in range(3)]
    for i, farmer in enumerate(farmers):
        call = one("insert into calls (farmer_id, is_synthetic, received_at) "
                   "values (%s, true, '2026-09-20 08:00+03') returning id", (farmer,))
        db.execute("insert into entries (call_id, farmer_id, kind, symptom, likely_disease, confidence) "
                   "values (%s, %s, 'observation', 'wilting', %s, 0.9)", (call, farmer, BORER))
        if i == 0:
            db.execute("insert into entries (call_id, farmer_id, kind, crop, amount_kg, price_total, "
                       "currency, coffee_form, buyer_type, date_sold, confidence) values "
                       "(%s, %s, 'sale', 'coffee', 100, 530000, 'UGX', 'kiboko', 'middleman', "
                       "'2025-09-30', 0.9)", (call, farmer))
    home = {"district": "TestDistrict", "sub_county": "TestSC", "parish": "TestParish"}

    out = summarize(db, farmers[0], home, AS_OF)

    assert out["coffee_years"] == [
        {"year": "2024/25", "harvest_kg": 0, "sold_kg": 100, "avg_ugx_per_kg": 5300}]
    assert out["nearby_reports"] == [{"likely": BORER, "farms": 2, "level": "parish", "last_days": 30}]
    assert "buyer_name" not in json.dumps(out)


# --- review cycle 1 regressions ---

CALLER_ID = 987_001
OTHER_IDS = (987_011, 987_012, 987_013)


def leaves(value):
    """Every dict key and every scalar value in a nested structure."""
    if isinstance(value, dict):
        for k, v in value.items():
            yield k
            yield from leaves(v)
    elif isinstance(value, (list, tuple)):
        for v in value:
            yield from leaves(v)
    else:
        yield value


def test_summarize_output_never_carries_ids_names_or_buyer_names():
    hist = [sale(date(2026, 7, 18), 400, 2_120_000, buyer_name="Ssali Traders", farmer_id=CALLER_ID,
                 name="Nakato"),
            {**obs(CALLER_ID, date(2026, 8, 30)), "name": "Nakato"}]
    near = [{**obs(farmer), "name": f"Neighbour {farmer}", "pin_hash": "deadbeef"} for farmer in OTHER_IDS]
    out = summarize(FakeConn(hist, near), CALLER_ID, HOME, AS_OF)
    found = list(leaves(out))
    assert out["nearby_reports"][0]["farms"] == 3
    assert not set(found) & {CALLER_ID, *OTHER_IDS}
    for leaf in found:
        text = str(leaf).lower()
        assert not any(bad in text for bad in ("farmer", "name", "pin", "nakato", "ssali", "neighbour",
                                                 "deadbeef"))


def test_caller_never_tips_sub_county_fallback_over_threshold():
    rows = [obs(CALLER_ID, parish="Kitovu"), obs(OTHER_IDS[0], parish="Other Parish")]
    assert nearby_reports(rows, HOME, AS_OF, exclude_farmer_id=CALLER_ID) == []


def test_new_coffee_year_with_data_shows_new_and_previous_year():
    rows = [sale(date(2025, 11, 5), 400, 2_400_000), sale(date(2026, 10, 2), 100, 600_000)]
    assert [y["year"] for y in coffee_years(rows, date(2026, 10, 3))] == ["2026/27", "2025/26"]


def test_history_sql_resolves_dates_in_kampala_time():
    conn = FakeConn([])
    history.load_history(conn, 42, AS_OF)
    sql, _ = conn.queries[0]
    assert "coalesce(e.date_sold, (c.received_at at time zone 'Africa/Kampala')::date)" in sql


def test_early_october_still_shows_two_coffee_years():
    # Demo day is 2026-10-04; the synthetic history covers 2024/25 and 2025/26 and nothing yet in 2026/27.
    rows = [sale(date(2024, 11, 5), 300, 1_500_000), sale(date(2025, 11, 5), 400, 2_400_000)]
    assert [y["year"] for y in coffee_years(rows, date(2026, 10, 3))] == ["2025/26", "2024/25"]


def test_harvest_in_bags_is_not_counted_as_kg():
    rows = [harvest(date(2025, 11, 5), 1180) | {"unit": "kg"},
            harvest(date(2026, 5, 5), 12) | {"unit": "bag"}]
    (year,) = coffee_years(rows, AS_OF)
    assert year["harvest_kg"] == 1180
    conn = FakeConn([])
    history.load_history(conn, 42, AS_OF)
    assert "e.unit" in conn.queries[0][0]


def test_location_login_entries_excluded_from_history_and_nearby():
    conn = FakeConn([], [])
    history.load_history(conn, 42, AS_OF)
    history.load_nearby(conn, 42, HOME, AS_OF)
    assert all("identified_by" in sql for sql, _ in conn.queries)


def test_non_ugx_sale_does_not_feed_ugx_prices():
    usd = sale(date(2025, 12, 1), 100, 500, currency="USD")
    (year,) = coffee_years([usd], AS_OF)
    assert year["avg_ugx_per_kg"] is None
    assert last_sales([usd])[0]["ugx_per_kg"] is None


@pytest.mark.supabase
def test_supabase_kampala_date_rule_own_rows_and_review_filter(db):
    def one(sql, params=()):
        return db.execute(sql, params).fetchone()[0]

    village = one("insert into villages (region, district, sub_county, parish, village, is_synthetic) "
                  "values ('Central','RevDistrict','RevSC','RevParish','RevVillage', true) returning id")
    caller, other = (one("insert into farmers (name, pin_hash, village_id, is_synthetic) "
                         "values (%s, %s, %s, true) returning id", (f"R{i}", f"review-hash-49-{i}", village))
                     for i in range(2))

    def sale_on(farmer, received_at, kg, total, **extra):
        call = one("insert into calls (farmer_id, is_synthetic, received_at) values (%s, true, %s) "
                   "returning id", (farmer, received_at))
        cols = {"call_id": call, "farmer_id": farmer, "kind": "sale", "crop": "coffee", "amount_kg": kg,
                "price_total": total, "currency": "UGX", "coffee_form": "kiboko",
                "buyer_type": "middleman", "confidence": 0.9, **extra}
        db.execute(f"insert into entries ({', '.join(cols)}) values ({', '.join(['%s'] * len(cols))})",
                   tuple(cols.values()))

    sale_on(caller, "2025-09-30 22:30+00", 100, 600_000)   # 01:30 on Oct 1 in Kampala -> 2025/26
    sale_on(caller, "2025-09-30 20:30+00", 50, 250_000)    # 23:30 on Sep 30 in Kampala -> 2024/25
    sale_on(caller, "2026-01-10 08:00+03", 999, 999_000, quote_verified=False)
    sale_on(caller, "2026-01-11 08:00+03", 999, 999_000, confidence=0.5)
    sale_on(other, "2026-01-12 08:00+03", 777, 777_000)
    home = {"district": "RevDistrict", "sub_county": "RevSC", "parish": "RevParish"}

    out = summarize(db, caller, home, AS_OF)

    assert out["coffee_years"] == [
        {"year": "2025/26", "harvest_kg": 0, "sold_kg": 100, "avg_ugx_per_kg": 6000},
        {"year": "2024/25", "harvest_kg": 0, "sold_kg": 50, "avg_ugx_per_kg": 5000}]
    assert [s["kg"] for s in out["last_sales"]] == [100, 50]

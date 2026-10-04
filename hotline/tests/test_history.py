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
            "price_total": total, "coffee_form": form, "buyer_type": buyer, **extra}


def harvest(day, kg):
    return {"entry_date": day, "kind": "harvest", "crop": "coffee", "yield_amount": kg}


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

from datetime import date, timedelta

import pytest

from hotline import prices

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

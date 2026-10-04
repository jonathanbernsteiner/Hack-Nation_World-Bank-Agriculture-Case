"""The SYNTHETIC Uganda season (#20): sizes, labels, value lists, price anchors and planted cases."""

import re
import statistics
from collections import defaultdict
from datetime import timedelta

import pytest
from test_supabase_schema import check_lists

from farm_ledger import BuyerType, Currency, Kind, PaidHow, Symptom, Unit
from farm_ledger.db import ENTRY_FIELDS
from farm_ledger.enums import CoffeeForm, CoffeeType
from synthetic import AS_OF, anchor_price, generate_season, price_anchors

# Spec section 5: plausible UGX per kg per form.
BANDS = {"kiboko": (2000, 15000), "faq": (5000, 25000), "parchment": (6000, 30000),
         "drugar": (6000, 30000), "red_cherry": (800, 8000)}
MEDIAN_STEP = 50
CLUSTER_FARMS, CLUSTER_DAYS = 3, 30
ENTRY_COLUMNS = (*ENTRY_FIELDS, "coffee_form", "coffee_type", "amount_kg")
ENUMS = {"kind": Kind, "unit": Unit, "currency": Currency, "buyer_type": BuyerType, "paid_how": PaidHow,
         "symptom": Symptom, "coffee_form": CoffeeForm, "coffee_type": CoffeeType}


@pytest.fixture(scope="module")
def season():
    return generate_season()


def sales(season):
    """(call, farmer, village, entry) for every sale entry."""
    for call in season.calls:
        farmer = season.farmers[call.farmer]
        for entry in call.entries:
            if entry["kind"] == "sale":
                yield call, farmer, season.villages[farmer.village], entry


def per_kg(entry):
    return entry["price_total"] / entry["amount_kg"]


def test_counts_and_villages(season):
    assert len(season.farmers) == 21
    assert [len(v.farmers) for v in season.villages] == [5, 3, 4, 4, 4, 1]
    assert [v.village for v in season.villages][:2] == ["Kyabakuza", "Bukeeri"]
    kyabakuza, bukeeri = season.villages[:2]
    assert (kyabakuza.region, kyabakuza.district, kyabakuza.sub_county) == ("Central", "Masaka", "Kyanamukaaka")
    assert kyabakuza.parish == bukeeri.parish  # V2 shares the demo parish
    assert {v.district for v in season.villages} == {"Masaka", "Mubende", "Bushenyi", "Bududa", "Zombo"}
    assert all(v.region in check_lists()["region"] for v in season.villages)
    assert len(season.calls) > 200


def test_all_synthetic_and_reserved_pins(season):
    assert all(v.is_synthetic for v in season.villages)
    assert all(f.is_synthetic for f in season.farmers)
    assert all(c.is_synthetic and c.source == "synthetic" for c in season.calls)
    pins = [f.pin for f in season.farmers]
    assert len(set(pins)) == len(pins) and all(9000 <= int(p) <= 9099 for p in pins)
    nakato = season.farmers[0]
    assert (nakato.name, nakato.pin, season.villages[nakato.village].village) == ("Nakato", "9001", "Kyabakuza")
    names = [f.name for f in season.farmers]
    assert len(set(names)) == len(names)


def test_values_in_fixed_lists(season):
    lists = check_lists()
    for call in season.calls:
        assert set(call.entries[0]) == set(ENTRY_COLUMNS)
        assert call.status in lists["status"] and call.source in lists["source"]
        assert call.identified_by in lists["identified_by"] and call.consent in lists["consent"]
        assert call.received_at.tzinfo is not None
        for entry in call.entries:
            for column, enum in ENUMS.items():
                assert entry[column] is None or entry[column] in {m.value for m in enum}, column
            assert entry["currency"] in (None, Currency.UGX.value)
            assert entry["paid_how"] != "M-Pesa" and "M-Pesa" not in call.transcript_en + call.transcript_sw
    assert {v.coffee_type.value for v in season.villages} == {"robusta", "arabica"}
    assert all(v.form in CoffeeForm for v in season.villages)
    assert Currency.UGX in Currency
    assert not any("KES" in str(c.entries) or "Kenya" in c.transcript_en for c in season.calls)


def test_price_anchor_rows_have_source_or_interpolated():
    anchors = price_anchors()
    months = sorted(anchors)
    assert months[0] == "2024-10" and months[-1] == "2026-09" and len(months) == 24
    for month, row in anchors.items():
        assert re.fullmatch(r"https://ugandacoffee\.go\.ug/sites/default/files/\S+\.pdf", row.source) \
            or row.source == "interpolated", month
        for form, price in row.ugx_per_kg.items():
            assert BANDS[form][0] <= price <= BANDS[form][1], (month, form)
    assert [m for m in months if anchors[m].source == "interpolated"] == ["2026-09"]  # report not out yet
    assert anchor_price(AS_OF - timedelta(days=3), CoffeeForm.KIBOKO) == anchors["2026-09"].ugx_per_kg["kiboko"]


def kyabakuza_kiboko_prices(season):
    """Prices the village median would use: verified, confident, with a weight, in the 12-month window."""
    window = AS_OF - timedelta(days=365)
    return [
        (farmer.name, per_kg(entry)) for _, farmer, village, entry in sales(season)
        if village.village == "Kyabakuza" and entry["coffee_form"] == "kiboko" and entry["amount_kg"]
        and entry["quote_verified"] is not False and entry["confidence"] >= 0.6
        and window <= entry["date_sold"] <= AS_OF
    ]


def test_demo_village_kiboko_median_near_5900(season):
    rows = kyabakuza_kiboko_prices(season)
    assert len(rows) >= 10 and len({name for name, _ in rows}) >= 3
    median = round(statistics.median(p for _, p in rows) / MEDIAN_STEP) * MEDIAN_STEP
    assert 5800 <= median <= 6000, median


def test_demo_farmer_nakato_9001_last_sale(season):
    hers = [(entry["date_sold"], entry) for _, farmer, _, entry in sales(season) if farmer.pin == "9001"]
    day, last = max(hers, key=lambda pair: pair[0])
    assert last["amount_kg"] == 400 and per_kg(last) == 5300 and last["coffee_form"] == "kiboko"
    assert last["buyer_type"] == "middleman" and day < AS_OF


def planted(season, tag):
    return [c for c in season.calls if c.planted == tag]


def test_planted_cases_present(season):
    # twig borer cluster: 3 farms, the demo parish, the last 30 days, and no other cluster anywhere
    cluster = planted(season, "twig_borer_cluster")
    parishes = {season.villages[season.farmers[c.farmer].village].parish for c in cluster}
    assert len({c.farmer for c in cluster}) == 3 and parishes == {"Kasaali"}
    assert all(AS_OF - timedelta(days=30) <= c.received_at.date() <= AS_OF for c in cluster)
    assert all(c.entries[0]["likely_disease"] == "black_coffee_twig_borer" for c in cluster)
    reports = defaultdict(set)
    for c in season.calls:
        entry = c.entries[0]
        if entry["kind"] == "observation":
            parish = season.villages[season.farmers[c.farmer].village].parish
            reports[(parish, entry["likely_disease"])].add(c.farmer)
    clusters = [key for key, farms in reports.items() if len(farms) >= CLUSTER_FARMS]
    assert clusters == [("Kasaali", "black_coffee_twig_borer")]
    # distress sale at -35% of the month's anchor, and no other sale far below its anchor
    (distress,) = planted(season, "distress_sale")
    entry = distress.entries[0]
    anchor = anchor_price(entry["date_sold"], CoffeeForm.KIBOKO)
    assert per_kg(entry) <= 0.7 * anchor
    low = [e for _, _, v, e in sales(season)
           if e["amount_kg"] and per_kg(e) < 0.75 * anchor_price(e["date_sold"], v.form)]
    assert low == [entry]
    # one low-confidence entry, with "[unclear]" in the transcript
    weak = [c for c in season.calls for e in c.entries if e["confidence"] < 0.6]
    assert weak == planted(season, "low_confidence") and len(weak) == 1 and "[unclear]" in weak[0].transcript_en
    # x10 slip: the price in the entry is ten times what the farmer said in the call
    (slip,) = planted(season, "price_slip")
    said = int(re.search(r"([\d,]+) shillings a kilo", slip.transcript_en).group(1).replace(",", ""))
    assert per_kg(slip.entries[0]) == 10 * said
    # a bag with no weight: no amount_kg, so it stays out of the price view
    (bag,) = planted(season, "bag_without_kg")
    assert bag.entries[0]["unit"] == "bag" and bag.entries[0]["amount_kg"] is None
    assert bag.entries[0]["price_total"] > 0
    # yield drop: this farmer's 2026 fly-crop harvest is about half of 2025's
    (drop,) = planted(season, "yield_drop")
    same = {c.season: c.entries[0]["yield_amount"] for c in season.calls
            if c.farmer == drop.farmer and c.season and c.season.startswith("fly")}
    assert same["fly-2026"] <= 0.6 * same["fly-2025"]
    assert all(planted(season, tag) for tag in ("wilt", "leaf_rust", "berry_disease"))


def test_deterministic_with_seed(season):
    assert generate_season() == season
    assert generate_season(seed=1) != season


def test_sale_prices_mostly_within_bands(season):
    outside = []
    for call, _, village, entry in sales(season):
        if entry["amount_kg"] is None:
            continue
        low, high = BANDS[village.form.value]
        if not low <= per_kg(entry) <= high:
            outside.append(call.planted)
    assert outside == ["price_slip"]  # everything except the planted x10 slip is inside the bands


def test_no_future_dates(season):
    for call in season.calls:
        assert call.received_at.date() <= AS_OF
        for entry in call.entries:
            assert entry["date_sold"] is None or entry["date_sold"] <= AS_OF
    assert min(c.received_at.date() for c in season.calls) >= AS_OF.replace(year=2024, month=10, day=1)


def test_each_village_has_coffee_type_matching_entries(season):
    for call in season.calls:
        village = season.villages[season.farmers[call.farmer].village]
        for entry in call.entries:
            assert entry["coffee_type"] == village.coffee_type.value
            if entry["kind"] in ("sale", "harvest"):
                assert entry["coffee_form"] == village.form.value


def test_harvest_one_per_season_per_farmer(season):
    seen = defaultdict(list)
    for call in season.calls:
        if any(e["kind"] == "harvest" for e in call.entries):
            seen[call.farmer].append(call.season)
    assert set(seen) == set(range(len(season.farmers)))
    for farmer, seasons in seen.items():
        assert len(seasons) == len(set(seasons)) == 4, farmer


def test_evidence_quotes_are_substrings_of_a_farmer_line(season):
    for call in season.calls:
        farmer_lines = [ln["en"] for ln in call.transcript_lines if ln["role"] == "farmer"]
        for entry in call.entries:
            quote = entry["evidence_quote"]
            assert any(quote in line and quote != line for line in farmer_lines), quote
            assert 1 <= len(quote.split()) <= 12

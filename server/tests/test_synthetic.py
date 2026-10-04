"""The SYNTHETIC Uganda season (#20): sizes, labels, value lists, price anchors and planted cases."""

import csv
import hashlib
import json
import os
import re
import statistics
import subprocess
import sys
from collections import defaultdict
from datetime import date, timedelta, timezone
from pathlib import Path

import pytest
from test_supabase_schema import check_lists

from farm_ledger import BuyerType, Currency, Kind, PaidHow, Symptom, Unit
from farm_ledger.db import ENTRY_FIELDS
from farm_ledger.enums import CoffeeForm, CoffeeType
from synthetic import AS_OF, anchor_price, generate_season, price_anchors
from synthetic.anchors import CSV_PATH

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
    drops = planted(season, "yield_drop")
    assert len(drops) == 2
    for drop in drops:
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


# --- Review regression tests (PR #36, cycle 1) ---

REPO = Path(__file__).resolve().parents[2]
SERVER = REPO / "server"
KAMPALA = timezone(timedelta(hours=3))  # Uganda has no DST
AREA_LEVELS = ("district", "sub_county", "parish", "village")  # spec section 5, outermost first
MIN_SALES = MIN_FARMERS = 3
VIEW_MIN_CONFIDENCE = 0.6
DIAGNOSIS_MIN_CONFIDENCE = 0.6  # spec section 7, verify step 7
SALE_KG = {"kiboko": (150, 600), "faq": (80, 300), "parchment": (60, 250)}  # issue #20 scope, per sale
YIELD_DROP = 0.7  # a 30% drop or more
TWIG_BORER = "black_coffee_twig_borer"  # the disease row lands with #45


def coffee_sale_prices(season):
    """(farmer, village, form, sale_date, ugx_per_kg) as the coffee_sale_prices view (spec section 4) yields them."""
    for call, farmer, village, entry in sales(season):
        confidence = 1 if entry["confidence"] is None else entry["confidence"]
        if (entry["crop"] == "coffee" and entry["currency"] == "UGX" and (entry["amount_kg"] or 0) > 0
                and (entry["price_total"] or 0) > 0 and entry["coffee_form"] != "other"
                and entry["quote_verified"] is not False and confidence >= VIEW_MIN_CONFIDENCE):
            day = entry["date_sold"] or call.received_at.astimezone(KAMPALA).date()
            yield farmer, village, entry["coffee_form"], day, per_kg(entry)


def area_median(season, home, form):
    """Spec section 5: (level, prices) at the first level from village outwards with >=3 sales by >=3 farmers.

    Rows are restricted to the home district, the band and the 365 days ending at AS_OF (the same
    `sale_date > as_of - 365` window as #44's spot-check SQL). (None, []) means the national fallback.
    """
    low, high = BANDS[form]
    rows = [(f, v, price) for f, v, fm, day, price in coffee_sale_prices(season)
            if fm == form and v.district == home.district and low <= price <= high
            and AS_OF - timedelta(days=365) < day <= AS_OF]
    for depth in range(len(AREA_LEVELS), 0, -1):
        area = AREA_LEVELS[:depth]
        hits = [(f, price) for f, v, price in rows
                if all(getattr(v, a) == getattr(home, a) for a in area)]
        if len(hits) >= MIN_SALES and len({f.pin for f, _ in hits}) >= MIN_FARMERS:
            return area[-1], [price for _, price in hits], {f.pin for f, _ in hits}
    return None, [], set()


def village_named(season, name):
    (village,) = [v for v in season.villages if v.village == name]
    return village


def test_kyabakuza_kiboko_median_through_the_view_and_level_rules(season):
    level, prices, farmers = area_median(season, village_named(season, "Kyabakuza"), "kiboko")
    assert level == "village"
    assert len(prices) >= 10 and len(farmers) >= 3
    assert 5700 <= statistics.median(prices) <= 6100  # unrounded, like percentile_cont in #44


def test_v2_kiboko_median_falls_back_to_parish(season):
    level, _, farmers = area_median(season, season.villages[1], "kiboko")
    assert level == "parish"
    assert not any(f.village == 1 for f in season.farmers if f.pin in farmers)  # V2 sells FAQ, not kiboko


def test_zombo_falls_back_to_the_national_reference(season):
    zombo = village_named(season, "Ora")
    assert zombo.district == "Zombo"
    assert area_median(season, zombo, zombo.form.value)[0] is None


def test_price_anchor_csv_has_one_row_per_consecutive_month():
    # price_anchors() builds a dict, so a duplicated month row would silently replace the other one
    with CSV_PATH.open(newline="") as f:
        months = [row["month"] for row in csv.DictReader(f)]
    expected, day = [], date(2024, 10, 1)
    while day <= date(2026, 9, 1):
        expected.append(f"{day.year}-{day.month:02d}")
        day = date(day.year + day.month // 12, day.month % 12 + 1, 1)
    assert months == expected


def test_likely_disease_ids_exist_and_survive_verify(season):
    rows = json.loads((REPO / "data" / "coffee-diseases.json").read_text())
    known = {row["id"] for row in rows} | {TWIG_BORER}
    for call in season.calls:
        for entry in call.entries:
            if entry["likely_disease"] is None:
                continue
            assert entry["likely_disease"] in known, entry["likely_disease"]
            # below 0.6, verify rewrites the diagnosis to not_sure and the planted cluster disappears
            assert entry["disease_confidence"] >= DIAGNOSIS_MIN_CONFIDENCE, entry["likely_disease"]


def test_no_pin_in_any_transcript(season):
    for call in season.calls:
        pin = season.farmers[call.farmer].pin
        texts = [call.transcript_sw, call.transcript_en, *(ln[k] for ln in call.transcript_lines for k in ("sw", "en"))]
        assert not any(pin in text for text in texts), pin
        assert any(ln["role"] == "farmer" and ln["en"] == "[PIN]" for ln in call.transcript_lines)


def season_digest(hash_seed: str) -> str:
    code = ("import hashlib; from synthetic import generate_season; "
            "print(hashlib.sha256(repr(generate_season()).encode()).hexdigest())")
    env = {**os.environ, "PYTHONHASHSEED": hash_seed}
    done = subprocess.run([sys.executable, "-c", code], cwd=SERVER, env=env, capture_output=True,
                          text=True, timeout=120, check=True)
    return done.stdout.strip()


def test_generation_is_identical_across_processes(season):
    here = hashlib.sha256(repr(season).encode()).hexdigest()
    assert season_digest("0") == season_digest("4242") == here


def season_start(village, label):
    name, year = label.split("-")
    (definition,) = [s for s in village.seasons if s.label == name]
    return date(int(year), definition.start_month, 1)


def test_two_farmers_with_yield_drop_and_problem_reports(season):
    harvests = defaultdict(dict)
    for call in season.calls:
        if call.season:
            harvests[call.farmer][call.season] = call.entries[0]["yield_amount"]
    reporters = {c.farmer for c in season.calls if c.entries[0]["kind"] == "observation"}
    dropped = set()
    for farmer, by_season in harvests.items():
        for label, kg in by_season.items():
            name, year = label.split("-")
            before = by_season.get(f"{name}-{int(year) - 1}")
            if before and kg <= YIELD_DROP * before:
                dropped.add(farmer)
    assert len(dropped & reporters) >= 2


def test_season_sales_never_exceed_the_harvest(season):
    harvest, sold = {}, defaultdict(int)
    for call in season.calls:
        farmer = season.farmers[call.farmer]
        if call.season:
            harvest[(call.farmer, season_start(season.villages[farmer.village], call.season))] = \
                call.entries[0]["yield_amount"]
    for call, farmer, village, entry in sales(season):
        if entry["amount_kg"] is None:
            continue
        starts = [start for (f, start) in harvest if f == call.farmer and start <= entry["date_sold"]]
        sold[(call.farmer, max(starts))] += entry["amount_kg"]
    over = {key: (harvest[key], kg) for key, kg in sold.items() if kg > harvest[key]}
    assert not over


def test_sale_sizes_within_issue_ranges(season):
    outside = [(village.form.value, entry["amount_kg"]) for _, _, village, entry in sales(season)
               if entry["amount_kg"] is not None
               and not SALE_KG[village.form.value][0] <= entry["amount_kg"] <= SALE_KG[village.form.value][1]]
    assert not outside

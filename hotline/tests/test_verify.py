from datetime import date

import pytest

pytest.importorskip("hotline.bands")  # bands.py arrives with #43 (PR #80)

from hotline.pipeline.extract import ExtractionRefused  # noqa: E402
from hotline.pipeline.verify import ENTRY_COLUMNS, verify  # noqa: E402
from hotline.schema import CallExtraction, Entry  # noqa: E402

TODAY = date(2026, 10, 3)
LINES = [
    {"i": 0, "role": "agent", "en": "The median in your village is 5900 shillings per kilo, sold at the market."},
    {"i": 1, "role": "farmer", "en": "I sold 300 kilos of kiboko for 1,800,000 shillings yesterday."},
    {"i": 2, "role": "farmer", "en": "Yes."},
    {"i": 3, "role": "farmer", "en": "The leaves have orange powder under them."},
]
BASE = {k: None for k in Entry.model_fields} | {"kind": "sale", "confidence": 0.9}
SALE = BASE | {"crop": "coffee", "coffee_form": "kiboko", "amount": 300, "unit": "kg", "price_total": 1_800_000,
               "currency": "UGX", "evidence_quote": "300 kilos of kiboko"}


def run(entries, consent="yes", lines=LINES, **kwargs):
    extraction = CallExtraction(consent=consent, entries=[Entry(**(BASE | e)) for e in entries])
    return verify(extraction, lines, TODAY, **kwargs)


def one(entry, **kwargs):
    return run([entry], **kwargs).entries[0]


def test_clean_sale_columns_and_values():
    result = run([SALE])
    row = result.entries[0]
    assert set(row) == set(ENTRY_COLUMNS) and "kg_per_unit" not in row
    assert row["amount_kg"] == 300 and row["price_total"] == 1_800_000
    assert row["quote_verified"] is True and row["confidence"] == 0.9
    assert not result.needs_review and result.consent == "yes"


def test_rule1_nulls_fields_not_used_by_kind():
    result = run([BASE | {"kind": "observation", "symptom": "rot", "price_total": 5, "amount": 3, "yield_amount": 2}])
    row = result.entries[0]
    assert row["price_total"] is None and row["amount"] is None and row["yield_amount"] is None
    assert row["symptom"] == "rot" and any("nulled" in f for f in result.flags)


def test_rule2_bag_with_kg_per_unit_and_without():
    bag = SALE | {"unit": "bag", "amount": 5, "kg_per_unit": 60, "price_total": 1_800_000}
    assert one(bag)["amount_kg"] == 300
    assert one(bag | {"kg_per_unit": None})["amount_kg"] is None


def test_rule2_per_unit_computes_total():
    row = one(SALE | {"price_total": None, "price_per_unit": 6000})
    assert row["price_total"] == 1_800_000 and row["confidence"] == 0.9


def test_rule2_total_and_per_unit_disagree_keeps_total_caps_confidence():
    row = one(SALE | {"price_per_unit": 6200})  # 1.86M vs 1.8M = 3.3%
    assert row["price_total"] == 1_800_000 and row["confidence"] == 0.5


def test_rule3_x10_slip_outside_band():
    row = one(SALE | {"price_total": 18_000_000})
    assert row["confidence"] == 0.5


def test_rule4_echoed_median_without_farmer_saying_it():
    medians = {"village_price": {"median_ugx_per_kg": 5900}, "other_prices": []}
    echoed = SALE | {"price_total": 1_770_000}  # 5900/kg
    assert one(echoed, tool_results=medians)["confidence"] == 0.5
    said = [*LINES[:1], {"i": 1, "role": "farmer", "en": "I got 5,900 per kilo for 300 kilos of kiboko."}]
    assert one(echoed, tool_results=medians, lines=said)["confidence"] == 0.9
    other = {"other_prices": [{"median_ugx_per_kg": 5900.0}]}
    assert one(echoed, tool_results=other)["confidence"] == 0.5


def test_rule5_date_range():
    assert one(SALE | {"date_sold": date(2026, 10, 2)})["date_sold"] == date(2026, 10, 2)
    assert one(SALE | {"date_sold": date(2026, 10, 4)})["date_sold"] is None
    assert one(SALE | {"date_sold": date(2025, 8, 1)})["date_sold"] is None


def test_rule6_quote_in_agent_line_fails():
    row = one(SALE | {"evidence_quote": "median in your village"})
    assert row["quote_verified"] is False and row["confidence"] == 0.5


def test_rule6_whole_line_and_too_long_fail():
    whole = one(SALE | {"evidence_quote": "The leaves have orange powder under them"})
    assert whole["quote_verified"] is False
    long = one(SALE | {"evidence_quote": "I sold 300 kilos of kiboko for 1,800,000 shillings yesterday and more words"})
    assert long["quote_verified"] is False


def test_rule6_normalisation_separators_case_punctuation():
    assert one(SALE | {"evidence_quote": "FOR 1800000 shillings"})["quote_verified"] is True


def test_rule6_short_farmer_line_is_unchecked_without_penalty():
    row = one(SALE | {"evidence_quote": "Yes"})
    assert row["quote_verified"] is None and row["confidence"] == 0.9


def test_rule6_reask_called_once_and_result_used():
    calls = []
    fixed = CallExtraction(consent="yes", entries=[Entry(**SALE)])

    def reask(errors):
        calls.append(errors)
        return fixed

    result = run([SALE | {"evidence_quote": "made up words"}], reask=reask)
    assert len(calls) == 1 and "entry 0" in calls[0][0]
    assert result.entries[0]["quote_verified"] is True


def test_rule6_reask_failure_still_marks_unverified():
    def reask(errors):
        raise ExtractionRefused("cyber")

    result = run([SALE | {"evidence_quote": "made up words"}], reask=reask)
    assert result.entries[0]["quote_verified"] is False and result.needs_review


def test_rule7_low_disease_confidence_becomes_not_sure():
    obs = BASE | {"kind": "observation", "likely_disease": "coffee_leaf_rust", "disease_confidence": 0.4,
                  "evidence_quote": "orange powder under them"}
    assert one(obs)["likely_disease"] == "not_sure"
    assert one(obs | {"disease_confidence": 0.8})["likely_disease"] == "coffee_leaf_rust"


def test_rule8_consent_no_writes_nothing():
    result = run([SALE], consent="no")
    assert result.entries == [] and result.consent == "no"


def test_rule9_review_flag():
    assert not run([SALE]).needs_review
    assert run([SALE | {"confidence": 0.5}]).needs_review
    assert run([SALE], identified_by="location").needs_review
    assert not run([SALE], identified_by="pin").needs_review


def test_confidence_never_raised():
    assert one(SALE | {"confidence": 0.3, "price_total": 18_000_000})["confidence"] == 0.3

"""Regression tests for data/coffee-diseases.json as the hotline consumes it (#45).

The extraction's likely_disease Literal (#59) and the agent's knowledge file (#46)
are both built from this file, so it must agree with hotline.enums and with the
ids that docs/hotline-spec.md section 8 tells the agent to name.
"""

import csv
import json
import re
from pathlib import Path

import pytest

from hotline.enums import Symptom

HOTLINE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = HOTLINE_DIR.parent
DISEASES_PATH = REPO_ROOT / "data" / "coffee-diseases.json"
EVAL_PATH = REPO_ROOT / "data" / "disease-eval.csv"
SPEC_PATH = REPO_ROOT / "docs" / "hotline-spec.md"

FALLBACK_ID = "not_sure"
ID_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
TWIG_BORER = "black_coffee_twig_borer"
PRACTICE_IDS = ("low_soil_fertility", "old_unpruned_trees", "weed_competition", "poor_harvest_practice")
NEW_IDS = (TWIG_BORER, *PRACTICE_IDS)
FARMER_FACING_FIELDS = ("farmer_advice_en", "tell_apart_question", "escalate_when", "farmer_words", "key_signs")

# Spec section 8, guardrail 1: no product, active ingredient, dose or mix rate in farmer text.
CHEMICAL_TERMS = re.compile(
    r"\b(?:copper|bordeaux|fungicides?|insecticides?|herbicides?|pesticides?|nematicides?|"
    r"weed ?killers?|glyphosate|round-?up|imidacloprid|confidor|kohinor|imax|tebuconazole|"
    r"chlorpyrifos|dursban|mancozeb|cypermethrin|npk|urea|potash|epsom|"
    r"dose|doses|dosage|mix rate|g/l|ml/l|per litre|per liter)\b"
    r"|\b\d+(?:\.\d+)?\s?(?:ml|g|kg|l|cc|litres?|liters?|%)(?=\W|$)",
    re.IGNORECASE,
)
SPRAY_OR_CHEMICAL = re.compile(r"\b(?:spray\w*|chemicals?)\b", re.IGNORECASE)


def load_rows():
    with DISEASES_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


def load_eval_rows():
    with EVAL_PATH.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def spec_section_8_ids():
    """Backticked ids in the spec's top-5, short-list and new-rows lines (before the knowledge file layout)."""
    text = SPEC_PATH.read_text(encoding="utf-8")
    start = text.index("## §8")
    end = text.index("**`knowledge/", start)
    return {token for token in re.findall(r"`([a-z0-9_]+)`", text[start:end]) if ID_PATTERN.match(token)}


def farmer_texts(row):
    for field in FARMER_FACING_FIELDS:
        value = row[field]
        for text in value if isinstance(value, list) else [value]:
            yield field, text


@pytest.fixture(scope="module")
def rows():
    return load_rows()


@pytest.fixture(scope="module")
def by_id(rows):
    return {row["id"]: row for row in rows}


def test_ids_are_unique_snake_case_strings(rows):
    ids = [row["id"] for row in rows]
    assert len(ids) == len(set(ids)), "duplicate ids would collapse the likely_disease Literal"
    for row_id in ids:
        assert isinstance(row_id, str) and ID_PATTERN.match(row_id), row_id


def test_not_sure_is_the_single_fallback_and_stays_last(rows):
    assert [row["id"] for row in rows if row["kind"] == "fallback"] == [FALLBACK_ID]
    assert rows[-1]["id"] == FALLBACK_ID


def test_the_five_uganda_rows_exist_with_the_agreed_kind(by_id):
    assert set(NEW_IDS) <= set(by_id)
    assert by_id[TWIG_BORER]["kind"] == "pest"
    for row_id in NEW_IDS:
        row = by_id[row_id]
        if row_id != TWIG_BORER:
            assert row["kind"] == "disorder", row_id
        assert row["in_bracol"] is False, row_id
        assert row["swahili_name"] is None, f"{row_id}: Kiswahili names only from a source"
        assert row["sources"], f"{row_id}: every problem row is cited"


def test_every_id_the_spec_tells_the_agent_to_name_exists(by_id):
    named = spec_section_8_ids()
    assert set(NEW_IDS) <= named, "spec section 8 parser no longer finds the new rows"
    assert named - set(by_id) == set(), "spec section 8 names an id that is not in the data"


def test_symptom_categories_use_the_hotline_symptom_enum(rows):
    allowed = {symptom.value for symptom in Symptom}
    assert len(allowed) == 9
    for row in rows:
        assert set(row["symptom_categories"]) <= allowed, row["id"]
        if row["kind"] != "fallback":
            assert row["symptom_categories"], row["id"]


def test_every_look_alike_resolves_to_another_row(rows, by_id):
    for row in rows:
        for look_alike in row["look_alikes"]:
            assert look_alike in by_id, f"{row['id']} -> {look_alike}"
            assert look_alike != row["id"]
            assert look_alike != FALLBACK_ID


def test_requested_look_alike_back_links(by_id):
    pairs = [
        (TWIG_BORER, "coffee_wilt_disease"),
        (TWIG_BORER, "overbearing_dieback"),
        ("old_unpruned_trees", "overbearing_dieback"),
        ("low_soil_fertility", "nitrogen_deficiency"),
    ]
    for a, b in pairs:
        assert b in by_id[a]["look_alikes"], f"{a} -> {b}"
        assert a in by_id[b]["look_alikes"], f"{b} -> {a}"


def test_no_chemical_product_or_dose_in_farmer_advice(rows):
    for row in rows:
        hits = [m.group(0) for m in CHEMICAL_TERMS.finditer(row["farmer_advice_en"])]
        assert hits == [], f"{row['id']}: {hits}"


def test_new_rows_never_mention_spraying_or_chemicals_to_the_farmer(by_id):
    for row_id in NEW_IDS:
        for field, text in farmer_texts(by_id[row_id]):
            assert CHEMICAL_TERMS.search(text) is None, (row_id, field, text)
            assert SPRAY_OR_CHEMICAL.search(text) is None, (row_id, field, text)


def test_urgency_twig_borer_soon_practice_causes_routine_wilt_still_urgent(by_id):
    assert by_id[TWIG_BORER]["urgency"] == "soon"
    for row_id in PRACTICE_IDS:
        assert by_id[row_id]["urgency"] == "routine", row_id
    assert by_id["coffee_wilt_disease"]["urgency"] == "urgent"


def test_twig_borer_signs_and_advice_match_the_ucda_handbook(by_id):
    row = by_id[TWIG_BORER]
    assert row["scientific_name"] == "Xylosandrus compactus"
    assert "underside" in row["tell_apart_question"]
    assert any("underside" in sign for sign in row["key_signs"])
    advice = row["farmer_advice_en"]
    assert "below the hole" in advice
    assert re.search(r"\bburn\b", advice)
    assert "extension officer" in advice
    # A drying twig with no hole may be coffee wilt disease, which is urgent.
    assert "coffee wilt" in row["escalate_when"]


def test_every_new_row_says_when_to_call_the_officer(by_id):
    for row_id in NEW_IDS:
        row = by_id[row_id]
        assert "extension officer" in row["farmer_advice_en"], row_id
        assert row["escalate_when"].strip(), row_id


def test_eval_phrases_cover_the_new_rows(by_id):
    eval_rows = load_eval_rows()
    for row in eval_rows:
        assert row["expected_id"] in by_id, row["phrase"]
        assert row["is_synthetic"] == "true", row["phrase"]
    new_rows = [row for row in eval_rows if row["expected_id"] in NEW_IDS]
    assert len(new_rows) >= 10
    assert {row["expected_id"] for row in new_rows} == set(NEW_IDS)
    tell_apart = [
        row for row in eval_rows
        if row["expected_id"] in {TWIG_BORER, FALLBACK_ID}
        and row["symptom"] == "wilting"
        and row["not_sure_ok"] == "true"
        and "wilt" in row["note"]
    ]
    assert tell_apart, "need a twig-borer-vs-wilt phrase where not_sure is an acceptable answer"

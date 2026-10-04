"""Regression tests for knowledge/coffee-problems-uganda.md (#46): ids come from the JSON."""

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
KNOWLEDGE_PATH = REPO_ROOT / "knowledge" / "coffee-problems-uganda.md"
DISEASES_PATH = REPO_ROOT / "data" / "coffee-diseases.json"

TOP_IDS = (
    "coffee_wilt_disease",
    "black_coffee_twig_borer",
    "coffee_leaf_rust",
    "brown_eye_spot",
    "coffee_berry_disease",
)
SHORT_IDS = (
    "low_soil_fertility",
    "drought_stress",
    "waterlogging",
    "old_unpruned_trees",
    "weed_competition",
    "poor_harvest_practice",
    "coffee_berry_borer",
)
HEADINGS = (
    "## 1 Triage",
    "## 2 Top 5",
    "## 3 Short list",
    "## 4 Good practice",
    "## 5 Words",
    "## 6 Sources",
)
ID_TOKEN = re.compile(r"`([a-z][a-z0-9]*(?:_[a-z0-9]+)+)`")
CHEMICAL_TERMS = re.compile(
    r"\b(?:copper|bordeaux|fungicides?|insecticides?|herbicides?|pesticides?|nematicides?|"
    r"weed ?killers?|glyphosate|round-?up|imidacloprid|confidor|kohinor|imax|tebuconazole|"
    r"chlorpyrifos|dursban|mancozeb|cypermethrin|npk|urea|potash|epsom|spray\w*|chemicals?|"
    r"dose|doses|dosage|mix rate|g/l|ml/l|per litre|per liter)\b"
    r"|\b\d+(?:\.\d+)?\s?(?:ml|g|kg|l|cc|litres?|liters?|%)(?=\W|$)",
    re.IGNORECASE,
)


def split_sections(text):
    """Map each '## N ...' heading line to its body."""
    parts = re.split(r"^(## .*)$", text, flags=re.MULTILINE)
    return {parts[i].strip(): parts[i + 1] for i in range(1, len(parts) - 1, 2)}


def section(text, prefix):
    for heading, body in split_sections(text).items():
        if heading.startswith(prefix):
            return body
    raise AssertionError(f"missing section {prefix}")


def ids_in_sections_1_to_3(text):
    body = "".join(section(text, p) for p in HEADINGS[:3])
    return set(ID_TOKEN.findall(body))


def missing_ids(text, known_ids):
    return sorted(ids_in_sections_1_to_3(text) - set(known_ids))


@pytest.fixture(scope="module")
def knowledge():
    return KNOWLEDGE_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def json_ids():
    return {row["id"] for row in json.loads(DISEASES_PATH.read_text(encoding="utf-8"))}


def test_headings_exist_in_order(knowledge):
    positions = [knowledge.index(h) for h in HEADINGS]
    assert positions == sorted(positions)


def test_every_backticked_id_exists_in_json(knowledge, json_ids):
    assert ids_in_sections_1_to_3(knowledge)
    assert missing_ids(knowledge, json_ids) == []


def test_top5_have_entries_in_section_2(knowledge):
    body = section(knowledge, "## 2 Top 5")
    entries = [line for line in body.splitlines() if line.startswith("### ")]
    assert len(entries) == 5
    for pid in TOP_IDS:
        assert any(f"`{pid}`" in e for e in entries), pid


def test_short_list_ids_in_section_3(knowledge):
    body = section(knowledge, "## 3 Short list")
    for pid in SHORT_IDS:
        assert f"`{pid}`" in body, pid


def test_entries_have_every_field(knowledge):
    fields = ("**What:**", "**Where / which coffee:**", "**Farmer says (EN | SW):**", "**Ask to tell apart:**",
              "**Look-alikes:**", "**Do now and prevent", "**Call the officer", "**Sources:**")
    for heading in HEADINGS[1:3]:
        for entry in re.split(r"^###+ ", section(knowledge, heading), flags=re.MULTILINE)[1:]:
            for f in fields:
                assert f in entry, (entry.splitlines()[0], f)


def test_header_notes_speaker_check(knowledge):
    assert "Ugandan Kiswahili speaker" in section(knowledge, "## 0")


def test_no_banned_chemical_terms(knowledge):
    body = knowledge.split("## 6 Sources")[0]
    assert CHEMICAL_TERMS.findall(body) == []


def test_wilt_requires_officer_confirmation_before_uprooting(knowledge):
    body = section(knowledge, "## 2 Top 5")
    wilt = body.split("### ")[1]
    assert "confirms" in wilt and "before uprooting" in wilt


def test_renamed_id_in_json_copy_fails_check(knowledge, tmp_path):
    rows = json.loads(DISEASES_PATH.read_text(encoding="utf-8"))
    renamed = [dict(r, id="renamed_rust") if r["id"] == "coffee_leaf_rust" else r for r in rows]
    copy = tmp_path / "coffee-diseases.json"
    copy.write_text(json.dumps(renamed), encoding="utf-8")
    ids = {r["id"] for r in json.loads(copy.read_text(encoding="utf-8"))}
    assert missing_ids(knowledge, ids) == ["coffee_leaf_rust"]

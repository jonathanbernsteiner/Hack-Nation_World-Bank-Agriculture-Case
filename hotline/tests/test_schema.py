import json
import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from hotline import enums
from hotline.schema import DISEASE_IDS, EXTRACTION_ONLY_FIELDS, CallExtraction, Entry, json_schema, to_entry_row

ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = ROOT / "supabase" / "migrations"
SPEC_FIELDS = [
    "kind", "plot", "crop", "coffee_form", "coffee_type", "amount", "unit", "kg_per_unit", "price_total",
    "price_per_unit", "currency", "date_sold", "buyer_type", "buyer_name", "paid_how", "activity", "input",
    "quantity", "yield_amount", "disease_detected", "symptom", "likely_disease", "disease_confidence",
    "evidence_quote", "evidence_turn", "description", "confidence"]
UNSUPPORTED = {"minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "multipleOf", "minLength",
               "maxLength", "minItems", "maxItems", "pattern", "default", "oneOf"}


def blank(**over):
    data = {name: None for name in SPEC_FIELDS} | {"kind": "sale", "confidence": 0.9}
    return data | over


def test_disease_ids_match_repo_json():
    ids = [row["id"] for row in json.loads((ROOT / "data" / "coffee-diseases.json").read_text())]
    assert list(DISEASE_IDS) == ids
    assert "not_sure" in DISEASE_IDS


def test_fields_equal_spec_and_all_required():
    assert list(Entry.model_fields) == SPEC_FIELDS
    assert json_schema()["$defs"]["Entry"]["required"] == SPEC_FIELDS


@pytest.mark.parametrize("field,enum", [("kind", enums.Kind), ("unit", enums.Unit), ("currency", enums.Currency),
                                        ("coffee_form", enums.CoffeeForm), ("coffee_type", enums.CoffeeType),
                                        ("buyer_type", enums.BuyerType), ("paid_how", enums.PaidHow),
                                        ("activity", enums.Activity), ("symptom", enums.Symptom)])
def test_literals_equal_enums_and_reject_invalid(field, enum):
    values = [m.value for m in enum]
    prop = json_schema()["$defs"]["Entry"]["properties"][field]
    found = prop.get("enum") or next(o["enum"] for o in prop["anyOf"] if "enum" in o)
    assert found == values
    with pytest.raises(ValidationError):
        Entry(**blank(**{field: "bogus"}))


def test_consent_and_disease_validated():
    with pytest.raises(ValidationError):
        CallExtraction(consent="maybe", entries=[])
    with pytest.raises(ValidationError):
        Entry(**blank(likely_disease="made_up"))
    Entry(**blank(likely_disease="not_sure"))


def test_missing_field_rejected():
    data = blank()
    del data["plot"]
    with pytest.raises(ValidationError):
        Entry(**data)


def _walk(node):
    if isinstance(node, dict):
        yield node
        for v in node.values():
            yield from _walk(v)
    elif isinstance(node, list):
        for v in node:
            yield from _walk(v)


def test_json_schema_uses_only_supported_keywords():
    for node in _walk(json_schema()):
        if "properties" in node:  # a schema object, not a properties map
            assert node.get("additionalProperties") is False
            assert set(node["required"]) == set(node["properties"])
        assert not (UNSUPPORTED & set(node) - set(node.get("properties", {}))), node
        if node.get("format"):
            assert node["format"] == "date"


def test_to_entry_row_drops_extraction_only_and_fits_columns():
    row = to_entry_row(Entry(**blank(kg_per_unit=60, price_per_unit=1, evidence_turn=3, date_sold="2026-10-01")))
    assert not set(EXTRACTION_ONLY_FIELDS) & set(row)
    assert row["date_sold"] == "2026-10-01"
    sql = re.sub(r"--[^\n]*", "", "\n".join(p.read_text() for p in sorted(MIGRATIONS.glob("*.sql"))))
    table = re.search(r"create table public\.entries \((.*?)\n\);", sql, re.S).group(1)
    columns = set(re.findall(r"^\s+(\w+)\s+(?:text|bigint|double|numeric|boolean|real|date)", table, re.M))
    columns |= set(re.findall(r"add column (\w+)", sql.split("alter table public.entries", 1)[1]))
    assert set(row) <= columns, set(row) - columns

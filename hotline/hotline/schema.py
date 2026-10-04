"""Extraction schema (spec section 7): what the model returns and what verify.py checks.

Every Entry field is required but nullable, so the model must answer each one explicitly.
Allowed values come from enums.py and data/disease_ids.json; nothing is retyped by hand."""

import json
from datetime import date
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from hotline.enums import (Activity, BuyerType, CoffeeForm, CoffeeType, Consent, Currency, Kind,
                           PaidHow, Symptom, Unit)

DISEASE_IDS_PATH = Path(__file__).resolve().parent / "data" / "disease_ids.json"
DISEASE_IDS: tuple[str, ...] = tuple(json.loads(DISEASE_IDS_PATH.read_text(encoding="utf-8")))

# Fields that exist only so the model never does arithmetic; they are never stored.
EXTRACTION_ONLY_FIELDS = ("kg_per_unit", "price_per_unit", "evidence_turn")


def _literal(enum: type[StrEnum]) -> Any:
    return Literal[tuple(member.value for member in enum)]  # type: ignore[valid-type]


KindT = _literal(Kind)
UnitT = _literal(Unit)
CurrencyT = _literal(Currency)
BuyerTypeT = _literal(BuyerType)
PaidHowT = _literal(PaidHow)
ActivityT = _literal(Activity)
SymptomT = _literal(Symptom)
CoffeeFormT = _literal(CoffeeForm)
CoffeeTypeT = _literal(CoffeeType)
ConsentT = _literal(Consent)
DiseaseT = Literal[DISEASE_IDS]  # type: ignore[valid-type]


class Entry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: KindT
    plot: str | None
    crop: str | None
    coffee_form: CoffeeFormT | None
    coffee_type: CoffeeTypeT | None
    amount: float | None
    unit: UnitT | None
    kg_per_unit: float | None
    price_total: float | None
    price_per_unit: float | None
    currency: CurrencyT | None
    date_sold: date | None
    buyer_type: BuyerTypeT | None
    buyer_name: str | None
    paid_how: PaidHowT | None
    activity: ActivityT | None
    input: str | None
    quantity: float | None
    yield_amount: float | None
    disease_detected: bool | None
    symptom: SymptomT | None
    likely_disease: DiseaseT | None
    disease_confidence: float | None
    evidence_quote: str | None
    evidence_turn: int | None
    description: str | None
    confidence: float


class CallExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    consent: ConsentT
    entries: list[Entry]


def json_schema() -> dict[str, Any]:
    """The JSON schema sent as output_config.format. Pydantic emits additionalProperties:false,
    anyOf [type, null] for nullable fields and $defs/$ref; no numeric or string constraints."""
    return CallExtraction.model_json_schema()


def to_entry_row(entry: Entry | dict[str, Any]) -> dict[str, Any]:
    """An entry as a dict without the extraction-only fields (dates as ISO strings)."""
    data = entry.model_dump(mode="json") if isinstance(entry, Entry) else dict(entry)
    return {key: value for key, value in data.items() if key not in EXTRACTION_ONLY_FIELDS}

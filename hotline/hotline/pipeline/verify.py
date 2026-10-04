"""Verify an extraction in code, not in the model (spec section 7, Verify steps 1-9).

verify() returns DB-ready entry dicts (keys = the entries columns except id, call_id,
farmer_id, is_synthetic), the call consent, flags explaining every change, and whether the call
needs human review. Confidence is only ever lowered."""

import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Callable

from hotline.bands import band_for, in_band
from hotline.pipeline.extract import ExtractionError
from hotline.schema import CallExtraction, Entry

CAPPED_CONFIDENCE = 0.5
REVIEW_THRESHOLD = 0.6
PRICE_TOLERANCE = 0.02
MEDIAN_TOLERANCE = 0.005
MAX_QUOTE_WORDS = 12
MIN_PROPER_LINE_WORDS = 3  # a quote can only be a proper part of a line with at least 3 words
MAX_DATE_AGE_DAYS = 400
MEDIAN_KEY = "median_ugx_per_kg"

COMMON = {"kind", "plot", "crop", "evidence_quote", "evidence_turn", "description", "confidence"}
KEEP_BY_KIND = {
    "sale": COMMON | {"coffee_form", "coffee_type", "amount", "unit", "kg_per_unit", "price_total",
                      "price_per_unit", "currency", "date_sold", "buyer_type", "buyer_name", "paid_how"},
    "harvest": COMMON | {"coffee_form", "coffee_type", "yield_amount", "unit"},
    "observation": COMMON | {"coffee_type", "disease_detected", "symptom", "likely_disease",
                             "disease_confidence"},
    "activity": COMMON | {"activity", "input", "quantity"},
}
ENTRY_COLUMNS = (
    "kind", "plot", "crop", "coffee_form", "coffee_type", "amount", "unit", "amount_kg", "price_total",
    "currency", "date_sold", "buyer_type", "buyer_name", "paid_how", "activity", "input", "quantity",
    "yield_amount", "disease_detected", "symptom", "evidence_quote", "description", "quote_verified",
    "likely_disease", "disease_confidence", "confidence")

ReaskFn = Callable[[list[str]], CallExtraction]


@dataclass(frozen=True)
class VerifyResult:
    consent: str
    entries: list[dict[str, Any]]
    flags: list[str] = field(default_factory=list)
    needs_review: bool = False


# ---- text helpers -------------------------------------------------------------------------

def _tokens(text: str) -> list[str]:
    """Lowercase words with digit separators removed ("1,800,000" -> "1800000")."""
    flat = re.sub(r"(?<=\d),(?=\d{3}\b)", "", text.lower())
    return re.findall(r"\w+", flat)


def _contains(haystack: list[str], needle: list[str]) -> bool:
    size = len(needle)
    return any(haystack[i:i + size] == needle for i in range(len(haystack) - size + 1))


def _farmer_lines(lines_en: list[dict[str, Any]]) -> list[list[str]]:
    return [_tokens(line["en"]) for line in lines_en if line.get("role") == "farmer"]


def _agent_lines(lines_en: list[dict[str, Any]]) -> list[list[str]]:
    return [_tokens(line["en"]) for line in lines_en if line.get("role") == "agent"]


# ---- steps ----------------------------------------------------------------------------------

def _null_inapplicable(data: dict[str, Any], flags: list[str], label: str) -> dict[str, Any]:
    keep = KEEP_BY_KIND[data["kind"]]
    nulled = [k for k, v in data.items() if k not in keep and v is not None]
    if nulled:
        flags.append(f"{label}: nulled fields not used by kind {data['kind']}: {', '.join(sorted(nulled))}")
    return {k: (v if k in keep else None) for k, v in data.items()}


def _positive(value: Any) -> float | None:
    return value if isinstance(value, (int, float)) and value > 0 else None


def _money(data: dict[str, Any], flags: list[str], label: str) -> dict[str, Any]:
    """amount_kg and price_total computed here; the model never does arithmetic."""
    out = dict(data, amount_kg=None)
    if out["kind"] != "sale":
        return out
    amount, per_kg, stated = _positive(out["amount"]), _positive(out["kg_per_unit"]), _positive(out["price_total"])
    if amount and out["unit"] == "kg":
        out["amount_kg"] = amount
    elif amount and per_kg:
        out["amount_kg"] = amount * per_kg
    per_unit = _positive(out["price_per_unit"])
    computed = per_unit * amount if per_unit and amount else None
    out["price_total"] = stated or computed
    if stated and computed and abs(stated - computed) / stated > PRICE_TOLERANCE:
        flags.append(f"{label}: stated total {stated} and per-unit total {computed} disagree by over 2%")
        out["confidence"] = min(out["confidence"], CAPPED_CONFIDENCE)
    return out


def _caps(data: dict[str, Any], flags: list[str], label: str, medians: list[float],
          farmer_text: str) -> dict[str, Any]:
    """Band check (3) and echoed-median check (4) on a sale's price per kg."""
    if data["kind"] != "sale" or not data["amount_kg"] or not data["price_total"]:
        return data
    per_kg = data["price_total"] / data["amount_kg"]
    reasons = []
    form = data["coffee_form"]
    if data["currency"] == "UGX" and form and band_for(form) and not in_band(form, per_kg):
        reasons.append(f"price {per_kg:.0f} UGX/kg outside the {form} band")
    for median in medians:
        number = str(int(round(median)))
        if abs(per_kg - median) <= MEDIAN_TOLERANCE * median and not re.search(
                rf"(?<!\d){number}(?!\d)", farmer_text):
            reasons.append(f"price per kg equals the agent's median {number} that the farmer never said")
    flags.extend(f"{label}: {r}" for r in reasons)
    return dict(data, confidence=min(data["confidence"], CAPPED_CONFIDENCE)) if reasons else data


def _date(data: dict[str, Any], flags: list[str], label: str, call_date: date) -> dict[str, Any]:
    sold = data["date_sold"]
    if sold is None or call_date - timedelta(days=MAX_DATE_AGE_DAYS) <= sold <= call_date:
        return data
    flags.append(f"{label}: date_sold {sold} outside the allowed range, set to null")
    return dict(data, date_sold=None)


def quote_error(quote: str | None, farmer: list[list[str]], agent: list[list[str]]) -> str | None:
    """None when the quote passes or is absent, "skip" when it cannot be checked (the Farmer line is
    too short to quote a part of), otherwise the error text."""
    if not quote:
        return None
    words = _tokens(quote)
    if not 1 <= len(words) <= MAX_QUOTE_WORDS:
        return f"quote must be 1-{MAX_QUOTE_WORDS} words, got {len(words)}"
    hits = [line for line in farmer if _contains(line, words)]
    if not hits:
        where = "an Agent line, not a Farmer line" if any(_contains(a, words) for a in agent) else "no Farmer line"
        return f"quote '{quote}' was found in {where}"
    if any(len(line) > len(words) for line in hits):
        return None
    return "skip" if all(len(line) < MIN_PROPER_LINE_WORDS for line in hits) else \
        f"quote '{quote}' is the whole Farmer line; quote only part of it"


def _quote(data: dict[str, Any], error: str | None) -> dict[str, Any]:
    if not data["evidence_quote"] or error == "skip":
        return dict(data, quote_verified=None)
    if error is None:
        return dict(data, quote_verified=True)
    return dict(data, quote_verified=False, confidence=min(data["confidence"], CAPPED_CONFIDENCE))


def _diagnosis(data: dict[str, Any], flags: list[str], label: str) -> dict[str, Any]:
    conf = data["disease_confidence"]
    if data["kind"] == "observation" and conf is not None and conf < REVIEW_THRESHOLD \
            and data["likely_disease"] != "not_sure":
        flags.append(f"{label}: disease_confidence {conf} below {REVIEW_THRESHOLD}, likely_disease set to not_sure")
        return dict(data, likely_disease="not_sure")
    return data


# ---- entry point ------------------------------------------------------------------------------

def _find_medians(value: Any) -> list[float]:
    """Every median_ugx_per_kg number anywhere in tool_results (village_price, other_prices[])."""
    if isinstance(value, dict):
        found = [value[MEDIAN_KEY]] if isinstance(value.get(MEDIAN_KEY), (int, float)) else []
        return found + [m for v in value.values() for m in _find_medians(v)]
    if isinstance(value, list):
        return [m for v in value for m in _find_medians(v)]
    return []


def _quote_errors(extraction: CallExtraction, lines_en: list[dict[str, Any]]) -> list[str | None]:
    farmer, agent = _farmer_lines(lines_en), _agent_lines(lines_en)
    return [quote_error(e.evidence_quote, farmer, agent) for e in extraction.entries]


def _unit_interval(value: float | None) -> float | None:
    """Clamp a score to [0, 1]: the entries table CHECKs both scores, and the schema can't."""
    return None if value is None else min(max(value, 0.0), 1.0)


def _verify_entry(entry: Entry, index: int, error: str | None, call_date: date, medians: list[float],
                  farmer_text: str, flags: list[str]) -> dict[str, Any]:
    label = f"entry {index}"
    raw = entry.model_dump()
    data = dict(raw, confidence=_unit_interval(raw["confidence"]),
                disease_confidence=_unit_interval(raw["disease_confidence"]))
    data = _null_inapplicable(data, flags, label)
    data = _money(data, flags, label)
    data = _caps(data, flags, label, medians, farmer_text)
    data = _date(data, flags, label, call_date)
    if error and error != "skip":
        flags.append(f"{label}: {error}")
    data = _diagnosis(_quote(data, error), flags, label)
    return {key: data[key] for key in ENTRY_COLUMNS}


def verify(
    extraction: CallExtraction,
    lines_en: list[dict[str, Any]],
    call_date: date,
    *,
    tool_results: Any = None,
    identified_by: str | None = None,
    reask: ReaskFn | None = None,
) -> VerifyResult:
    """`reask(errors)` (optional) returns a corrected CallExtraction; it is called at most once."""
    if extraction.consent == "no":
        return VerifyResult("no", [], ["consent is no: no entries written"])
    errors = _quote_errors(extraction, lines_en)
    failed = [f"entry {i}: {e}" for i, e in enumerate(errors) if e and e != "skip"]
    flags: list[str] = []
    if failed and reask is not None:
        try:
            extraction = reask(failed)
            errors = _quote_errors(extraction, lines_en)
            flags.append("quotes re-asked once")
        except ExtractionError as error:
            flags.append(f"quote re-ask failed: {error}")
    if extraction.consent == "no":
        return VerifyResult("no", [], flags + ["consent is no: no entries written"])
    medians = _find_medians(tool_results)
    farmer_text = " ".join(" ".join(t) for t in _farmer_lines(lines_en))
    entries = [_verify_entry(e, i, err, call_date, medians, farmer_text, flags)
               for i, (e, err) in enumerate(zip(extraction.entries, errors))]
    if extraction.consent == "unclear":
        flags.append("consent unclear")
    review = identified_by == "location" or any(
        e["confidence"] < REVIEW_THRESHOLD or e["quote_verified"] is False for e in entries)
    return VerifyResult(extraction.consent, entries, flags, review)

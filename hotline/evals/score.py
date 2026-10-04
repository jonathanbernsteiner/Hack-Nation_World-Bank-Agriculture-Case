"""Deterministic scorer for the accuracy loop (spec section 9). No LLM, no network.

Metric: entries are aligned per call and per kind by brute force (best matched-field count,
tie-break fewer numeric errors). Field accuracy = correct scored fields / all scored fields of
gold entries, plus the scored fields of unmatched predicted entries, plus consent once per call.

Error types (gold vs predicted): wrong_value, null_vs_value (gold has a value, prediction is
null), value_vs_null (gold is null, prediction has a value), missing_entry, extra_entry.
The error table holds only kinds, field names, error types and tag counts, never any string
taken from a transcript, gold value or prediction.
"""

from __future__ import annotations

import itertools
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from typing import Any

SCORED_FIELDS: dict[str, tuple[str, ...]] = {
    "sale": (
        "crop", "coffee_form", "amount_kg", "price_total", "currency",
        "date_sold", "buyer_type", "buyer_name", "paid_how",
    ),
    "harvest": ("crop", "yield_amount", "unit"),
    "activity": ("activity", "input", "quantity", "plot"),
    "observation": ("crop", "plot", "symptom", "disease_detected", "likely_disease"),
}
NUMERIC_FIELDS = frozenset({"amount_kg", "price_total", "yield_amount", "quantity"})
FREE_TEXT_FIELDS = frozenset({"crop", "plot", "buyer_name", "input"})
REL_TOLERANCE = 0.01
SMALL_VALUE = 50
SMALL_ABS_TOLERANCE = 0.5
MAX_BRUTE_FORCE = 7
QUOTE_MIN_WORDS, QUOTE_MAX_WORDS = 1, 12
TRAP_TAGS = frozenset({"no_sale_trap", "intended_sale", "echo_median", "not_sold"})
PASS_FIELD_ACCURACY = 0.95
PASS_QUOTE_VALIDITY = 0.95

_PUNCT = re.compile(r"[^\w\s]", re.UNICODE)
_SPACE = re.compile(r"\s+")
_DIGIT_SEP = re.compile(r"(?<=\d)[,.\s](?=\d{3}\b)")


def normalise(text: Any) -> str:
    """Lowercase, strip, drop punctuation, collapse whitespace."""
    return _SPACE.sub(" ", _PUNCT.sub("", str(text).lower())).strip()


def _normalise_for_quote(text: str) -> str:
    return normalise(_DIGIT_SEP.sub("", text))


def _plain(value: Any) -> Any:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, bool) or value is None or isinstance(value, (int, float)):
        return value
    return str(value)


def numbers_match(gold: float, pred: float) -> bool:
    if abs(gold) < SMALL_VALUE:
        return abs(gold - pred) <= SMALL_ABS_TOLERANCE
    return abs(gold - pred) <= REL_TOLERANCE * abs(gold)


def compare_field(name: str, gold: Any, pred: Any, alts: list[str] | None = None) -> str | None:
    """None when the field is correct, else the error type."""
    gold, pred = _plain(gold), _plain(pred)
    if gold is None and pred is None:
        return None
    if gold is None:
        return "value_vs_null"
    if pred is None:
        return "null_vs_value"
    if name in NUMERIC_FIELDS:
        try:
            return None if numbers_match(float(gold), float(pred)) else "wrong_value"
        except (TypeError, ValueError):
            return "wrong_value"
    if name in FREE_TEXT_FIELDS:
        options = {normalise(gold), *(normalise(a) for a in alts or [])}
        return None if normalise(pred) in options else "wrong_value"
    return None if gold == pred else "wrong_value"


def _entry_errors(kind: str, gold: dict, pred: dict, alts: dict) -> dict[str, str | None]:
    return {
        f: compare_field(f, gold.get(f), pred.get(f), alts.get(f))
        for f in SCORED_FIELDS[kind]
    }


def _pair_key(errors: dict[str, str | None]) -> tuple[int, int]:
    matched = sum(1 for e in errors.values() if e is None)
    numeric_errors = sum(1 for f, e in errors.items() if e is not None and f in NUMERIC_FIELDS)
    return matched, -numeric_errors


def _align(kind: str, golds: list[dict], preds: list[dict], alts: dict) -> list[tuple[int, int]]:
    """Best one-to-one (gold index, pred index) pairs; brute force, deterministic."""
    if not golds or not preds:
        return []
    table = [[_entry_errors(kind, g, p, alts) for p in preds] for g in golds]
    if max(len(golds), len(preds)) > MAX_BRUTE_FORCE:
        return _greedy(table)
    if len(golds) <= len(preds):
        options = (list(enumerate(perm)) for perm in itertools.permutations(range(len(preds)), len(golds)))
    else:
        options = (
            [(g, p) for p, g in enumerate(perm)]
            for perm in itertools.permutations(range(len(golds)), len(preds))
        )
    best: list[tuple[int, int]] = []
    best_key: tuple[int, int] | None = None
    for pairs in options:
        totals = [_pair_key(table[g][p]) for g, p in pairs]
        key = (sum(t[0] for t in totals), sum(t[1] for t in totals))
        if best_key is None or key > best_key:
            best, best_key = list(pairs), key
    return best


def _greedy(table: list[list[dict]]) -> list[tuple[int, int]]:
    pairs: list[tuple[int, int]] = []
    used_p: set[int] = set()
    for g, row in enumerate(table):
        candidates = [(p, _pair_key(row[p])) for p in range(len(row)) if p not in used_p]
        if not candidates:
            break
        p, _ = max(candidates, key=lambda c: c[1])
        used_p.add(p)
        pairs.append((g, p))
    return pairs


def _farmer_lines(lines_en: list[Any]) -> list[str]:
    out: list[str] = []
    for line in lines_en or []:
        if isinstance(line, str):
            m = re.match(r"\s*(Agent|Farmer)\s*:\s*(.*)", line, re.DOTALL)
            if m and m.group(1) == "Farmer":
                out.append(m.group(2))
            continue
        role = str(line.get("role") or line.get("speaker") or "").lower()
        if role == "farmer":
            out.append(str(line.get("en") or line.get("text") or line.get("sw") or ""))
    return out


def quote_is_valid(quote: Any, lines_en: list[Any]) -> bool:
    """Spec section 7: 1-12 words, exact substring of one Farmer line, never the whole line."""
    if not isinstance(quote, str) or not quote.strip():
        return False
    if not QUOTE_MIN_WORDS <= len(quote.split()) <= QUOTE_MAX_WORDS:
        return False
    needle = _normalise_for_quote(quote)
    if not needle:
        return False
    for line in _farmer_lines(lines_en):
        hay = _normalise_for_quote(line)
        if needle in hay and needle != hay:
            return True
    return False


@dataclass
class CallScore:
    call_id: str
    fields_total: int = 0
    fields_correct: int = 0
    phantom_sales: int = 0
    quotes_total: int = 0
    quotes_valid: int = 0
    tags: list[str] = field(default_factory=list)
    errors: list[tuple[str, str, str]] = field(default_factory=list)  # (kind, field, error_type)


def _as_dict(entry: Any) -> dict:
    return entry if isinstance(entry, dict) else dict(vars(entry))


def score_call(gold_call: dict, consent: str | None, entries: list[Any], lines_en: list[Any]) -> CallScore:
    """Score one call. gold_call is a dev-set file: gold.consent, gold.entries, free_text_alts,
    quote_possible, tags. entries and lines_en come from RunResult."""
    gold = gold_call["gold"]
    alts = gold_call.get("free_text_alts") or {}
    tags = list(gold_call.get("tags") or [])
    score = CallScore(call_id=str(gold_call.get("id", "")), tags=tags)

    score.fields_total += 1  # consent
    if consent == gold["consent"]:
        score.fields_correct += 1
    else:
        score.errors.append(("call", "consent", "wrong_value"))

    gold_entries = [_as_dict(e) for e in gold.get("entries", [])]
    pred_entries = [_as_dict(e) for e in entries or []]
    matched_pred: dict[int, int] = {}  # gold index -> pred index (global indices)
    unmatched_pred_sales = 0

    for kind, fields in SCORED_FIELDS.items():
        g_idx = [i for i, e in enumerate(gold_entries) if e.get("kind") == kind]
        p_idx = [i for i, e in enumerate(pred_entries) if e.get("kind") == kind]
        pairs = _align(kind, [gold_entries[i] for i in g_idx], [pred_entries[i] for i in p_idx], alts)
        used_g = {g for g, _ in pairs}
        used_p = {p for _, p in pairs}
        for g, p in pairs:
            matched_pred[g_idx[g]] = p_idx[p]
            for name, err in _entry_errors(kind, gold_entries[g_idx[g]], pred_entries[p_idx[p]], alts).items():
                score.fields_total += 1
                if err is None:
                    score.fields_correct += 1
                else:
                    score.errors.append((kind, name, err))
        for g in range(len(g_idx)):
            if g not in used_g:
                score.fields_total += len(fields)
                score.errors.extend((kind, name, "missing_entry") for name in fields)
        for p in range(len(p_idx)):
            if p not in used_p:
                score.fields_total += len(fields)
                score.errors.extend((kind, name, "extra_entry") for name in fields)
                if kind == "sale":
                    unmatched_pred_sales += 1

    gold_has_sale = any(e.get("kind") == "sale" for e in gold_entries)
    if unmatched_pred_sales and (not gold_has_sale or TRAP_TAGS.intersection(tags)):
        score.phantom_sales = unmatched_pred_sales

    if gold_call.get("quote_possible", True):
        for g_i in range(len(gold_entries)):
            score.quotes_total += 1
            p_i = matched_pred.get(g_i)
            if p_i is not None and quote_is_valid(pred_entries[p_i].get("evidence_quote"), lines_en):
                score.quotes_valid += 1
    return score


def summarise(scores: list[CallScore]) -> dict:
    """Aggregate call scores into the metric, the three pass conditions and the error table."""
    total = sum(s.fields_total for s in scores)
    correct = sum(s.fields_correct for s in scores)
    quotes_total = sum(s.quotes_total for s in scores)
    quotes_valid = sum(s.quotes_valid for s in scores)
    phantom = sum(s.phantom_sales for s in scores)
    accuracy = correct / total if total else 1.0
    quote_validity = quotes_valid / quotes_total if quotes_total else 1.0
    dims = Counter((k, f, t) for s in scores for k, f, t in s.errors)
    tag_wrong: Counter[str] = Counter()
    tag_calls: Counter[str] = Counter()
    for s in scores:
        for tag in set(s.tags):
            tag_calls[tag] += 1
            tag_wrong[tag] += len(s.errors)
    return {
        "calls": len(scores),
        "fields_total": total,
        "fields_correct": correct,
        "field_accuracy": accuracy,
        "phantom_sales": phantom,
        "quotes_total": quotes_total,
        "quotes_valid": quotes_valid,
        "quote_validity": quote_validity,
        "pass": {
            "field_accuracy": accuracy >= PASS_FIELD_ACCURACY,
            "zero_phantom_sales": phantom == 0,
            "quote_validity": quote_validity >= PASS_QUOTE_VALIDITY,
        },
        "passed": accuracy >= PASS_FIELD_ACCURACY and phantom == 0 and quote_validity >= PASS_QUOTE_VALIDITY,
        "error_table": {
            "by_dimension": [
                {"kind": k, "field": f, "error_type": t, "count": n}
                for (k, f, t), n in sorted(dims.items())
            ],
            "by_tag": {
                tag: {"calls": tag_calls[tag], "wrong_fields": tag_wrong[tag]}
                for tag in sorted(tag_calls)
            },
        },
    }

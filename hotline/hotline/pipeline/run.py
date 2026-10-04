"""The pure post-call pipeline: translate -> extract -> verify (spec section 7).

No database access. Production (process.py) and the evals call this one function, so the
accuracy loop measures exactly what runs in production. Translation, extraction and
verification are injectable so tests use fakes; the defaults import the real modules lazily.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Callable

ENGLISH_SPEAKERS = {"agent": "Agent", "farmer": "Farmer"}


@dataclass(frozen=True)
class RunResult:
    lines_en: list[dict]  # the stored lines ({i, role, sw, t}) plus en
    transcript_en: str
    extraction: dict  # raw model output, kept for audit
    consent: str
    entries: list[dict]  # verified entries, ready for the entries table (minus ids)
    status: str  # 'processed' | 'needs_review'


def _as_dict(value: Any) -> dict:
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    raise TypeError(f"cannot convert {type(value).__name__} to a dict")


def _field(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)


def _default_translator(lines: list[dict]) -> list[str]:
    from hotline.pipeline.translate import translate_lines

    return translate_lines(lines)


def _default_extractor(lines_en: list[dict], call_date: date) -> Any:
    from hotline.pipeline import extract

    return extract.extract_entries(lines_en, call_date)


def _default_verifier(
    extraction: Any, *, lines: list[dict], call_date: date, tool_results: list[dict], identified_by: str | None
) -> Any:
    """verify.verify(extraction, lines_en, call_date, *, tool_results, identified_by, reask) from #59;
    its reask takes only the error list, so the lines, date and previous answer are bound here."""
    from hotline.pipeline import extract, verify

    return verify.verify(
        extraction,
        lines,
        call_date,
        tool_results=tool_results,
        identified_by=identified_by,
        reask=lambda errors: extract.reask(lines, call_date, extraction, errors),
    )


def _render(lines_en: list[dict]) -> str:
    return "\n".join(f"{ENGLISH_SPEAKERS.get(line['role'], 'Farmer')}: {line['en']}" for line in lines_en)


def _numbered(lines: list[dict]) -> list[dict]:
    """Copies of the stored lines (keeping t and any other key) with i filled in."""
    return [{**line, "i": line.get("i", position)} for position, line in enumerate(lines)]


def run_call(
    lines: list[dict],
    call_date: date,
    *,
    tool_results: list[dict] | None = None,
    identified_by: str | None = None,
    translator: Callable[[list[dict]], list[str]] | None = None,
    extractor: Callable[[list[dict], date], Any] | None = None,
    verifier: Callable[..., Any] | None = None,
) -> RunResult:
    source = _numbered(lines)
    english = (translator or _default_translator)(source)
    if len(english) != len(source):
        raise ValueError("translator returned a different number of lines")
    lines_en = [{**line, "en": text} for line, text in zip(source, english)]

    raw = (extractor or _default_extractor)(lines_en, call_date)
    verified = (verifier or _default_verifier)(
        raw,
        lines=lines_en,
        call_date=call_date,
        tool_results=tool_results or [],
        identified_by=identified_by,
    )
    consent = _field(verified, "consent") or _field(raw, "consent") or "unclear"
    # Spec section 7 Verify step 8: consent "no" means no entries, and the call is still processed.
    entries = [] if consent == "no" else [_as_dict(entry) for entry in _field(verified, "entries", [])]
    # verify.py flags review on the result (location id, low confidence, unverified quote).
    needs_review = consent != "no" and (
        bool(_field(verified, "needs_review")) or any(entry.get("needs_review") for entry in entries)
    )
    return RunResult(
        lines_en=lines_en,
        transcript_en=_render(lines_en),
        extraction=_as_dict(raw),
        consent=consent,
        entries=entries,
        status="needs_review" if needs_review else "processed",
    )

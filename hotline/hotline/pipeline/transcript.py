"""ElevenLabs post-call webhook payload to clean transcript lines (spec section 7).

Pure functions over dicts: no I/O, no network, no env reads. Every PIN is
redacted to ``[PIN]``, tool-call parameters are stripped, and the caller id and
phone number fields (``metadata.phone_call``, ``system__caller_id``) are never
read.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from datetime import datetime, timedelta, timezone
from typing import Any, Literal, TypedDict

PIN_TOKEN = "[PIN]"
MULTIPLIERS = {"double": 2, "triple": 3}
KAMPALA_TZ = timezone(timedelta(hours=3), "Africa/Kampala")  # no DST in Uganda
MIN_PIN_DIGITS = 4
MAX_PIN_DIGITS = 8
MIN_PARTIAL_RUN = 3  # digit words in a row that look like part of a PIN

DIGIT_WORDS = {
    "sifuri": "0",
    "sufuri": "0",
    "moja": "1",
    "mbili": "2",
    "tatu": "3",
    "nne": "4",
    "tano": "5",
    "sita": "6",
    "saba": "7",
    "nane": "8",
    "tisa": "9",
    "zero": "0",
    "ziro": "0",
    "one": "1",
    "two": "2",
    "three": "3",
    "four": "4",
    "five": "5",
    "six": "6",
    "seven": "7",
    "eight": "8",
    "nine": "9",
}
ROLE_MAP = {"agent": "agent", "user": "farmer"}
DROPPED_RESULT_KEYS = frozenset(
    {"call_sid", "caller_id", "system__caller_id", "external_number", "phone", "phone_number"}
)

_TOKEN = re.compile(r"\d+|[^\W\d_]+", re.UNICODE)
_GAP = re.compile(r"[\W_]*(?:\bna\b[\W_]*)?", re.IGNORECASE)
_PIN_KEY = re.compile(r"(?:^|_)pin(?:$|_)", re.IGNORECASE)
_PIN_IN_TEXT = re.compile(r'("?pin"?\s*[:=]\s*"?)\d+(?:[ .\-]\d+){0,7}', re.IGNORECASE)
_DIGITS_ONLY = re.compile(r"\d+")
_PHONE = re.compile(r"\+\d{6,}")


class Line(TypedDict):
    i: int
    role: Literal["agent", "farmer"]
    sw: str
    t: float | None


class CallMeta(TypedDict):
    conversation_id: str | None
    received_at: datetime | None
    duration_secs: int | None
    call_date_kampala: str | None


def _turns(data: dict) -> list[dict]:
    turns = data.get("transcript") or []
    return [t for t in turns if isinstance(t, dict)]


def _message(turn: dict) -> str:
    message = turn.get("message")
    return message.strip() if isinstance(message, str) else ""


def _walk_pin_values(node: Any) -> Iterable[str]:
    """Yield digit strings stored under any key named like ``pin``."""
    if isinstance(node, dict):
        for key, value in node.items():
            if _PIN_KEY.search(str(key)) and isinstance(value, (str, int)):
                digits = "".join(d for d in map(_digits_of, _TOKEN.finditer(str(value))) if d.isdigit())
                if digits:
                    yield digits
            else:
                yield from _walk_pin_values(value)
    elif isinstance(node, list):
        for item in node:
            yield from _walk_pin_values(item)


def _parse_json(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except ValueError:
        return value


def _tool_items(turn: dict, field: str) -> list[dict]:
    return [x for x in (turn.get(field) or []) if isinstance(x, dict)]


def _labelled_digits(match: re.Match) -> str:
    return re.sub(r"\D", "", match.group(0)[len(match.group(1)) :])


def collect_pins(data: dict) -> set[str]:
    """PINs seen in tool params, tool results and keypad-style farmer turns."""
    pins: set[str] = set()
    for turn in _turns(data):
        for call in _tool_items(turn, "tool_calls"):
            pins.update(_walk_pin_values(_parse_json(call.get("params_as_json"))))
        for result in _tool_items(turn, "tool_results"):
            value = _parse_json(result.get("result_value"))
            pins.update(_walk_pin_values(value))
            if isinstance(value, str):
                pins.update(_labelled_digits(m) for m in _PIN_IN_TEXT.finditer(value))
        message = _message(turn)
        is_keypad = (
            turn.get("role") == "user"
            and turn.get("source_medium") == "dtmf"
            and _DIGITS_ONLY.fullmatch(message)
        )
        if is_keypad and MIN_PIN_DIGITS <= len(message) <= MAX_PIN_DIGITS:
            pins.add(message)
    return {p for p in pins if len(p) >= MIN_PARTIAL_RUN}


def _runs(text: str) -> list[list[re.Match]]:
    """Group consecutive digit or digit-word tokens separated only by gaps."""
    runs: list[list[re.Match]] = []
    current: list[re.Match] = []
    for match in _TOKEN.finditer(text):
        token = match.group(0).lower()
        if token == "na":  # "and": allowed between digits, checked by _GAP
            continue
        if not (token.isdigit() or token in DIGIT_WORDS or token in MULTIPLIERS):
            current = []
            continue
        if current and _GAP.fullmatch(text[current[-1].end() : match.start()]):
            current.append(match)
        else:
            current = [match]
            runs.append(current)
    return runs


def _digits_of(match: re.Match) -> str:
    token = match.group(0).lower()
    return DIGIT_WORDS.get(token, token)


def _run_parts(run: list[re.Match]) -> list[str]:
    """Digit string per token; "double"/"triple" repeat the next digit, so they yield ""."""
    parts: list[str] = []
    repeat = 1
    for m in run:
        token = m.group(0).lower()
        if token in MULTIPLIERS:
            repeat = MULTIPLIERS[token]
            parts.append("")
        else:
            parts.append(_digits_of(m) * repeat)
            repeat = 1
    return parts


def _pin_spans(run: list[re.Match], pins: list[str]) -> list[tuple[int, int]]:
    """Token index ranges [a, b) of a run that spell a PIN (or a PIN part)."""
    parts = _run_parts(run)
    all_words = all(m.group(0).lower() in DIGIT_WORDS or m.group(0).lower() in MULTIPLIERS for m in run)
    spans: list[tuple[int, int]] = []
    for start in range(len(parts)):
        acc = ""
        for end in range(start, len(parts)):
            acc += parts[end]
            if not parts[end]:  # a dangling "double"/"triple" is not part of a span
                continue
            if acc in pins:
                spans.append((start, end + 1))
            elif all_words and end + 1 - start >= MIN_PARTIAL_RUN:
                # spoken digits only: the start or end of a PIN split across turns
                is_head = end == len(parts) - 1 and any(p.startswith(acc) for p in pins)
                is_tail = start == 0 and any(p.endswith(acc) for p in pins)
                if is_head or is_tail:
                    spans.append((start, end + 1))
    return spans


def _merge(spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
    merged: list[tuple[int, int]] = []
    for a, b in sorted(spans):
        if merged and a < merged[-1][1]:
            merged[-1] = (merged[-1][0], max(b, merged[-1][1]))
        else:
            merged.append((a, b))
    return merged


def _redact_text(text: str, pins: Iterable[str]) -> str:
    pin_list = sorted(set(pins), key=len, reverse=True)
    text = _PIN_IN_TEXT.sub(lambda m: m.group(1) + PIN_TOKEN, text)
    if not pin_list:
        return text
    pieces: list[tuple[int, int]] = []
    for run in _runs(text):
        for a, b in _merge(_pin_spans(run, pin_list)):
            pieces.append((run[a].start(), run[b - 1].end()))
    for start, end in sorted(pieces, reverse=True):
        text = text[:start] + PIN_TOKEN + text[end:]
    return text


def redact_pins(lines: list[Line], pins: set[str]) -> list[Line]:
    """Return new lines with every PIN replaced by ``[PIN]`` (digits, spaced, words)."""
    return [{**line, "sw": _redact_text(line["sw"], pins)} for line in lines]


def to_lines(data: dict) -> list[Line]:
    """Numbered, PIN-redacted lines from the non-empty agent and user turns."""
    lines: list[Line] = []
    for turn in _turns(data):
        role = ROLE_MAP.get(turn.get("role"))
        text = _message(turn)
        if role is None or not text:
            continue
        t = turn.get("time_in_call_secs")
        lines.append(
            {
                "i": len(lines),
                "role": role,
                "sw": text,
                "t": float(t) if isinstance(t, (int, float)) else None,
            }
        )
    return redact_pins(lines, collect_pins(data))


def render(lines: list[Line], lang: str = "sw") -> str:
    """``Agent: ...`` / ``Farmer: ...``, one line per turn, from ``sw`` or ``en``."""
    return "\n".join(f"{line['role'].capitalize()}: {line.get(lang, '')}" for line in lines)


def _scrub_value(node: Any, pins: set[str]) -> Any:
    if isinstance(node, dict):
        return {
            key: PIN_TOKEN if _PIN_KEY.search(str(key)) else _scrub_value(value, pins)
            for key, value in node.items()
            if str(key).lower() not in DROPPED_RESULT_KEYS
        }
    if isinstance(node, list):
        return [_scrub_value(item, pins) for item in node]
    if isinstance(node, str):
        return _PHONE.sub("[PHONE]", _redact_text(node, pins))
    return node


def scrub_tool_results(data: dict) -> list[dict]:
    """Tool calls with results, parameters stripped and PINs replaced by ``[PIN]``.

    One item per call: ``{tool_name, request_id, t, is_error, result}``. ``null``
    and ``[]`` tool lists are treated the same.
    """
    pins = collect_pins(data)
    scrubbed: list[dict] = []
    results = {
        r.get("request_id"): r for turn in _turns(data) for r in _tool_items(turn, "tool_results")
    }
    for turn in _turns(data):
        for call in _tool_items(turn, "tool_calls"):
            result = results.get(call.get("request_id"), {})
            scrubbed.append(
                {
                    "tool_name": call.get("tool_name"),
                    "request_id": call.get("request_id"),
                    "t": turn.get("time_in_call_secs"),
                    "is_error": result.get("is_error"),
                    "result": _scrub_value(_parse_json(result.get("result_value")), pins),
                }
            )
    return scrubbed


def call_meta(data: dict) -> CallMeta:
    """Ids and times; the Kampala date is UTC+3 (so 22:30 UTC is the next day)."""
    metadata = data.get("metadata") or {}
    start = metadata.get("start_time_unix_secs")
    received = datetime.fromtimestamp(start, tz=timezone.utc) if isinstance(start, (int, float)) else None
    return {
        "conversation_id": data.get("conversation_id"),
        "received_at": received,
        "duration_secs": metadata.get("call_duration_secs"),
        "call_date_kampala": received.astimezone(KAMPALA_TZ).strftime("%Y-%m-%d") if received else None,
    }

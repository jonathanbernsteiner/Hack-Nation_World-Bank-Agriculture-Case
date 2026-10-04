"""How a farmer sounds across their recent calls, read by Claude from the English transcripts.

Shown on the farmer profile page only; nothing is written to the database. Results are cached
in memory per farmer and set of call ids, so a new call triggers one fresh read."""

import json
import os
from typing import Any

import anthropic

MODEL_ENV = "ANTHROPIC_EXTRACT_MODEL"
EFFORT = "low"
MAX_TOKENS = 8_000
TIMEOUT_SECS = 60.0
SDK_RETRIES = 1
MAX_CALLS = 6
MAX_CHARS_PER_CALL = 3_000
LABELS = ("positive", "neutral", "mixed", "negative")

PROMPT = """You read a coffee farmer's recent phone calls to a farm hotline (English transcripts, newest first).
Judge how the farmer feels about their coffee, prices and livelihood, from the farmer's own words only.
The agent's lines are context, not the farmer's mood. Do not invent facts that are not in the calls.
Return:
- overall: one of positive, neutral, mixed, negative;
- score: a number from -1 (very negative) to 1 (very positive);
- summary: one plain sentence (at most 25 words) on the farmer's mood and main concerns;
- calls: one item per call with its id, a sentiment label and a reason of at most 12 words."""

SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "overall": {"type": "string", "enum": list(LABELS)},
        "score": {"type": "number"},
        "summary": {"type": "string"},
        "calls": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "sentiment": {"type": "string", "enum": list(LABELS)},
                    "reason": {"type": "string"},
                },
                "required": ["id", "sentiment", "reason"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["overall", "score", "summary", "calls"],
    "additionalProperties": False,
}

_cache: dict[tuple, dict] = {}


def call_text(call: dict) -> str:
    """'Agent: ...' / 'Farmer: ...' lines in English, trimmed to MAX_CHARS_PER_CALL."""
    lines = call.get("transcript_lines")
    if isinstance(lines, str):
        try:
            lines = json.loads(lines)
        except ValueError:
            lines = None
    if not isinstance(lines, list):
        return ""
    out = []
    for line in lines:
        if not isinstance(line, dict):
            continue
        text = line.get("en") or line.get("sw")
        if text:
            out.append(f"{'Farmer' if line.get('role') == 'farmer' else 'Agent'}: {text}")
    return "\n".join(out)[:MAX_CHARS_PER_CALL]


def _source(calls: list[dict]) -> list[dict]:
    picked = [{"id": c["id"], "text": call_text(c)} for c in calls]
    return [c for c in picked if c["text"]][:MAX_CALLS]


def analyze(farmer_id: int, calls: list[dict], client: Any = None) -> dict | None:
    """{overall, score, summary, calls: [{id, sentiment, reason}]}, or None without usable calls.
    Raises on API or config errors; the route turns those into an 'unavailable' message."""
    source = _source(calls)
    if not source:
        return None
    key = (farmer_id, tuple(c["id"] for c in source))
    if key in _cache:
        return _cache[key]
    model = os.environ.get(MODEL_ENV)
    if not model:
        raise RuntimeError(f"{MODEL_ENV} is not set")
    client = client or anthropic.Anthropic(max_retries=SDK_RETRIES, timeout=TIMEOUT_SECS)
    response = client.messages.create(
        model=model,
        max_tokens=MAX_TOKENS,
        system=PROMPT,
        messages=[{"role": "user", "content": json.dumps(source, ensure_ascii=False)}],
        output_config={"effort": EFFORT, "format": {"type": "json_schema", "schema": SCHEMA}},
    )
    if response.stop_reason in ("refusal", "max_tokens"):
        raise RuntimeError(f"sentiment stopped: {response.stop_reason}")
    text = "".join(block.text for block in response.content if block.type == "text")
    result = json.loads(text)
    result["score"] = max(-1.0, min(1.0, float(result["score"])))
    _cache[key] = result
    return result

"""Kiswahili -> English translation of call transcript lines with Claude (Anthropic API only).

One Messages API call with a structured output; the returned line indices must equal the input
indices (quotes and the side-by-side demo view rely on line i == line i). Refusals and
max_tokens stops raise typed errors; they are never retried on another model."""

import hashlib
import json
import os
from pathlib import Path
from typing import Any

import anthropic

PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "translate_sw_en.md"
MODEL_ENV = "ANTHROPIC_TRANSLATE_MODEL"
DEFAULT_EFFORT = "low"
MAX_TOKENS = 20_000  # Opus 5.5 always thinks; leaves room for a 10-minute call
TIMEOUT_SECS = 120.0
SDK_RETRIES = 2
SPEAKERS = ("Agent", "Farmer")
ROLE_TO_SPEAKER = {"agent": "Agent", "farmer": "Farmer"}

TURNS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "turns": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "i": {"type": "integer"},
                    "speaker": {"type": "string", "enum": list(SPEAKERS)},
                    "text": {"type": "string"},
                },
                "required": ["i", "speaker", "text"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["turns"],
    "additionalProperties": False,
}


class TranslationError(Exception):
    """Base class for translation failures."""


class TranslationMisaligned(TranslationError):
    """The model's lines did not match the input lines one to one, even after a retry."""


class TranslationRefused(TranslationError):
    """The model declined the request (stop_reason == "refusal"). #66 maps this to needs_review."""

    def __init__(self, category: str | None = None):
        super().__init__(f"translation refused (category: {category})")
        self.category = category


class TranslationTruncated(TranslationError):
    """The response hit max_tokens. #66 maps this to needs_review."""


class TranslationConfigError(TranslationError):
    """A required setting (the model name) is missing."""


class TranslationInputError(TranslationError):
    """An input line has an unknown role or no Kiswahili text; raised before any model call."""


def _field(line: Any, name: str) -> Any:
    return line.get(name) if isinstance(line, dict) else getattr(line, name, None)


def _source_turns(lines: list[Any]) -> list[dict[str, Any]]:
    turns = []
    for index, line in enumerate(lines):
        role = _field(line, "role")
        speaker = ROLE_TO_SPEAKER.get(role) if isinstance(role, str) else None
        if speaker is None:
            raise TranslationInputError(f"line {index} has an unknown role (expected agent or farmer)")
        sw = _field(line, "sw")
        if not isinstance(sw, str):
            raise TranslationInputError(f"line {index} has no sw text (expected a string)")
        turns.append({"i": index, "speaker": speaker, "text": sw})
    return turns


def cache_key(model: str, effort: str, prompt: str, turns: list[dict[str, Any]]) -> str:
    prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    payload = json.dumps(turns, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(f"{model}\n{effort}\n{prompt_hash}\n{payload}".encode("utf-8")).hexdigest()


def _alignment_error(source: list[dict[str, Any]], data: Any) -> str | None:
    turns = data.get("turns") if isinstance(data, dict) else None
    if not isinstance(turns, list):
        return 'the response must be a JSON object {"turns": [...]}'
    if len(turns) != len(source):
        return f"expected {len(source)} turns, got {len(turns)}"
    for expected, got in zip(source, turns):
        if not isinstance(got, dict) or got.get("i") != expected["i"]:
            return f"turn at position {expected['i']} must have i={expected['i']}"
        if got.get("speaker") != expected["speaker"]:
            return f"turn i={expected['i']} must have speaker {expected['speaker']}"
        if not isinstance(got.get("text"), str) or not got["text"].strip():
            return f"turn i={expected['i']} must have non-empty text"
    return None


def _request(model: str, effort: str, prompt: str, user_content: str) -> dict[str, Any]:
    """The exact kwargs for messages.create: no temperature, no fallbacks, effort explicit."""
    return {
        "model": model,
        "max_tokens": MAX_TOKENS,
        "system": prompt,
        "messages": [{"role": "user", "content": user_content}],
        "output_config": {"effort": effort, "format": {"type": "json_schema", "schema": TURNS_SCHEMA}},
    }


def _call(client: Any, request: dict[str, Any]) -> Any:
    """One model call; returns the parsed JSON, or None when the text is not valid JSON."""
    response = client.messages.create(**request)
    if response.stop_reason == "refusal":
        details = getattr(response, "stop_details", None)
        raise TranslationRefused(getattr(details, "category", None))
    if response.stop_reason == "max_tokens":
        raise TranslationTruncated(f"response hit max_tokens ({MAX_TOKENS})")
    text = "".join(block.text for block in response.content if block.type == "text")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _read_cache(path: Path) -> list[str] | None:
    try:
        cached = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None
    return cached if isinstance(cached, list) and all(isinstance(t, str) for t in cached) else None


def translate_lines(
    lines: list[Any],
    *,
    client: Any = None,
    model: str | None = None,
    effort: str = DEFAULT_EFFORT,
    cache_dir: Path | None = None,
) -> list[str]:
    """Translate Kiswahili lines (each with `role` and `sw`) to English; len(result) == len(lines).

    `model` defaults to $ANTHROPIC_TRANSLATE_MODEL. `cache_dir` turns on the on-disk cache
    (evals only; production passes None). Raises TranslationMisaligned, TranslationRefused,
    TranslationTruncated, TranslationConfigError or TranslationInputError."""
    if not lines:
        return []
    model = model or os.environ.get(MODEL_ENV)
    if not model:
        raise TranslationConfigError(f"{MODEL_ENV} is not set")
    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    source = _source_turns(lines)

    cache_path = None
    if cache_dir is not None:
        cache_path = Path(cache_dir) / f"{cache_key(model, effort, prompt, source)}.json"
        cached = _read_cache(cache_path)
        if cached is not None and len(cached) == len(lines):
            return cached

    client = client or anthropic.Anthropic(max_retries=SDK_RETRIES, timeout=TIMEOUT_SECS)
    user_content = json.dumps(source, ensure_ascii=False)
    error = None
    for attempt in range(2):
        content = user_content
        if error:
            content += f"\n\nYour previous answer was rejected: {error}. Return exactly one turn per input line."
        data = _call(client, _request(model, effort, prompt, content))
        error = _alignment_error(source, data) if data is not None else "the response was not valid JSON"
        if error is None:
            result = [turn["text"] for turn in data["turns"]]
            if cache_path is not None:
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                cache_path.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
            return result
    raise TranslationMisaligned(error)

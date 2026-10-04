"""Call extraction with Claude (Anthropic API only): English transcript lines -> CallExtraction.

One Messages API call with a structured output (schema.json_schema()). Effort is explicit,
temperature and fallbacks are never sent. Refusals and max_tokens stops raise typed errors."""

import json
import os
from datetime import date
from pathlib import Path
from typing import Any

import anthropic
from pydantic import ValidationError

from hotline.schema import CallExtraction, json_schema

PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "extract_entries.md"
MODEL_ENV = "ANTHROPIC_EXTRACT_MODEL"
DEFAULT_EFFORT = "high"
MAX_TOKENS = 32_000  # Opus 5.5 always thinks; leaves room for a long call
TIMEOUT_SECS = 120.0
SDK_RETRIES = 2
SPEAKERS = {"agent": "Agent", "farmer": "Farmer"}


class ExtractionError(Exception):
    """Base class for extraction failures."""


class ExtractionRefused(ExtractionError):
    """The model declined the request (stop_reason == "refusal"). #66 maps this to needs_review."""

    def __init__(self, category: str | None = None):
        super().__init__(f"extraction refused (category: {category})")
        self.category = category


class ExtractionTruncated(ExtractionError):
    """The response hit max_tokens. #66 maps this to needs_review."""


class ExtractionInvalid(ExtractionError):
    """The response was not valid JSON for CallExtraction."""


class ExtractionConfigError(ExtractionError):
    """A required setting (the model name) is missing."""


class ExtractionInputError(ExtractionError):
    """An input line has an unknown role or no English text; raised before any model call."""


def render_lines(lines_en: list[dict[str, Any]]) -> str:
    rendered = []
    for line in lines_en:
        speaker = SPEAKERS.get(line.get("role"))
        if speaker is None or not isinstance(line.get("en"), str):
            raise ExtractionInputError(f"line {line.get('i')} needs role agent|farmer and an en string")
        rendered.append(f"[{line['i']}] {speaker}: {line['en']}")
    return "\n".join(rendered)


def build_user_content(lines_en: list[dict[str, Any]], call_date: date) -> str:
    return f"Call date: {call_date.isoformat()} ({call_date.strftime('%A')})\n\n{render_lines(lines_en)}"


def build_request(model: str, user_content: str, effort: str = DEFAULT_EFFORT) -> dict[str, Any]:
    """The exact kwargs for messages.create: no temperature, no fallbacks, effort explicit."""
    return {
        "model": model,
        "max_tokens": MAX_TOKENS,
        "system": PROMPT_PATH.read_text(encoding="utf-8"),
        "messages": [{"role": "user", "content": user_content}],
        "output_config": {"effort": effort, "format": {"type": "json_schema", "schema": json_schema()}},
    }


def _resolve(client: Any, model: str | None) -> tuple[Any, str]:
    model = model or os.environ.get(MODEL_ENV)
    if not model:
        raise ExtractionConfigError(f"{MODEL_ENV} is not set")
    return client or anthropic.Anthropic(max_retries=SDK_RETRIES, timeout=TIMEOUT_SECS), model


def _run(client: Any, request: dict[str, Any]) -> CallExtraction:
    response = client.messages.create(**request)
    if response.stop_reason == "refusal":
        details = getattr(response, "stop_details", None)
        raise ExtractionRefused(getattr(details, "category", None))
    if response.stop_reason == "max_tokens":
        raise ExtractionTruncated(f"response hit max_tokens ({MAX_TOKENS})")
    text = "".join(block.text for block in response.content if block.type == "text")
    try:
        return CallExtraction.model_validate_json(text)
    except ValidationError as error:
        raise ExtractionInvalid(str(error)) from error


def extract_entries(
    lines_en: list[dict[str, Any]],
    call_date: date,
    *,
    client: Any = None,
    model: str | None = None,
) -> CallExtraction:
    """lines_en items are {i, role: 'agent'|'farmer', en}. `model` defaults to $ANTHROPIC_EXTRACT_MODEL."""
    client, model = _resolve(client, model)
    return _run(client, build_request(model, build_user_content(lines_en, call_date)))


def reask(
    lines_en: list[dict[str, Any]],
    call_date: date,
    previous: CallExtraction,
    errors: list[str],
    *,
    client: Any = None,
    model: str | None = None,
) -> CallExtraction:
    """Send the previous JSON and a compact error list; get a corrected full CallExtraction."""
    client, model = _resolve(client, model)
    content = (
        build_user_content(lines_en, call_date)
        + "\n\nYour previous answer:\n"
        + json.dumps(previous.model_dump(mode="json"), ensure_ascii=False)
        + "\n\nIt has these errors:\n"
        + "\n".join(f"- {e}" for e in errors)
        + "\n\nReturn the corrected full answer."
    )
    return _run(client, build_request(model, content))

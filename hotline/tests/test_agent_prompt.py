"""Regression tests for the agent prompt and first message (#47)."""

import re
from pathlib import Path

import pytest

HOTLINE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = HOTLINE_DIR.parent
PROMPT_PATH = HOTLINE_DIR / "agent" / "prompt.md"
FIRST_MESSAGE_PATH = HOTLINE_DIR / "agent" / "first_message_en.txt"
SPEC_PATH = REPO_ROOT / "docs" / "hotline-spec.md"

KNOWLEDGE_MARKER = "<!-- KNOWLEDGE -->"
TOOL_NAMES = {"identify_farmer", "find_farmer_by_location", "register_farmer", "get_weather_forecast"}
ALLOWED_DOUBLE_BRACE_VARIABLES: set[str] = set()
MAX_FIRST_MESSAGE_CHARS = 400

CHEMICAL_TERMS = re.compile(
    r"\b(?:copper|bordeaux|fungicides?|insecticides?|herbicides?|pesticides?|nematicides?|"
    r"weed ?killers?|glyphosate|round-?up|imidacloprid|confidor|kohinor|imax|tebuconazole|"
    r"chlorpyrifos|dursban|mancozeb|cypermethrin|npk|urea|potash|epsom|spray\w*|"
    r"dose|doses|dosage|mix rate|g/l|ml/l|per litre|per liter)\b",
    re.IGNORECASE,
)


@pytest.fixture(scope="module")
def prompt():
    return PROMPT_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def first_message():
    return FIRST_MESSAGE_PATH.read_text(encoding="utf-8").strip()


def spec_guardrails():
    spec = SPEC_PATH.read_text(encoding="utf-8")
    block = spec.split("**Restricted mode:**")[1].split("- **First message**")[0]
    items = re.findall(r"^\s+(\d+)\. (.+)$", block, flags=re.MULTILINE)
    return [text.strip() for _, text in items]


def test_tool_names_mentioned_are_exactly_the_four(prompt):
    assert set(re.findall(r"`(\w+)\(", prompt)) == TOOL_NAMES


def test_knowledge_marker_exactly_once(prompt):
    assert prompt.count(KNOWLEDGE_MARKER) == 1
    assert f"\n{KNOWLEDGE_MARKER}\n" in prompt


def test_all_ten_guardrails_verbatim(prompt):
    guardrails = spec_guardrails()
    assert len(guardrails) == 10
    for number, text in enumerate(guardrails, 1):
        assert f"{number}. {text}" in prompt, number


def test_no_unknown_double_braces(prompt):
    found = set(re.findall(r"\{\{\s*([^}]*?)\s*\}\}", prompt))
    assert found <= ALLOWED_DOUBLE_BRACE_VARIABLES


def test_first_message_shape(first_message):
    assert first_message
    assert "computer" in first_message
    assert len(first_message) < MAX_FIRST_MESSAGE_CHARS
    for needle in ("I forgot", "I'm new", "record"):
        assert needle in first_message


def test_no_banned_chemical_terms_outside_guardrail_one(prompt):
    allowed_line = next(line for line in prompt.splitlines() if line.startswith("1. Never name a pesticide"))
    text = prompt.replace(allowed_line, "")
    assert CHEMICAL_TERMS.findall(text) == []
    assert CHEMICAL_TERMS.findall(FIRST_MESSAGE_PATH.read_text(encoding="utf-8")) == []


@pytest.mark.parametrize(
    "status",
    ["not_found", "locked", "ambiguous", "possible_duplicate", "need_district", "unknown_location", "unavailable"],
)
def test_prompt_handles_every_tool_status(prompt, status):
    assert f"`{status}`" in prompt


def test_prices_come_from_numeric_fields(prompt):
    assert "median_ugx_per_kg" in prompt and "`pin`" in prompt


def test_first_message_offers_keypad_and_spoken_pin(first_message):
    # Spec §8: "press or say your four-digit PIN". Keypad delivery on the imported
    # Twilio number is unverified (#39), so the spoken fallback must be announced.
    assert "press" in first_message and "say" in first_message


def test_sample_lines_carry_no_canned_money_figures(prompt):
    # Guardrail 6: a concrete figure in a sample line can be parroted when a tool fails.
    assert re.findall(r"\b(?:elfu|laki|milioni)\b", prompt, flags=re.IGNORECASE) == []

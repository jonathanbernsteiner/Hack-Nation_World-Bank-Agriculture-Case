"""The pipeline prompts load and carry no dev-call identifiers (issue #65).

Dev names, places and buyer names may appear only inside a marked example block
(`<!-- example:begin -->` ... `<!-- example:end -->`), at most 2 of them.
"""

import json
import re
from pathlib import Path

import pytest

HOTLINE_DIR = Path(__file__).resolve().parents[1]
PROMPTS_DIR = HOTLINE_DIR / "hotline" / "prompts"
DEV_DIR = HOTLINE_DIR / "evals" / "dev"
PROMPT_FILES = ("extract_entries.md", "translate_sw_en.md")
IDENTIFIER_KEYS = frozenset({"first_name", "village", "area", "district", "place"})
FREE_TEXT_ALT_KEYS = ("buyer_name", "plot")
EXAMPLE_BLOCK = re.compile(r"<!-- example:begin -->.*?<!-- example:end -->", re.DOTALL)
MAX_EXAMPLES = 2


def _strings(value, keys):
    if isinstance(value, dict):
        for key, item in value.items():
            if key in keys and isinstance(item, str):
                yield item
            else:
                yield from _strings(item, keys)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item, keys)


def _tool_values(call: dict) -> set[str]:
    found = set()
    for turn in call["conversation"].get("transcript") or []:
        for result in turn.get("tool_results") or []:
            try:
                payload = json.loads(result.get("result_value") or "null")
            except json.JSONDecodeError:
                continue
            for text in _strings(payload, IDENTIFIER_KEYS):
                found.update(part.strip() for part in text.split(","))
    return found


def dev_identifiers() -> set[str]:
    found: set[str] = set()
    for path in sorted(DEV_DIR.glob("*.json")):
        call = json.loads(path.read_text(encoding="utf-8"))
        found |= _tool_values(call)
        found.update(e["buyer_name"] for e in call["gold"]["entries"] if e.get("buyer_name"))
        for key in FREE_TEXT_ALT_KEYS:
            found.update((call.get("free_text_alts") or {}).get(key, []))
    return {text for text in found if text}


def _outside_examples(text: str) -> str:
    return EXAMPLE_BLOCK.sub(" ", text)


@pytest.mark.parametrize("name", PROMPT_FILES)
def test_prompt_loads(name):
    assert (PROMPTS_DIR / name).read_text(encoding="utf-8").strip()


def test_dev_identifiers_found():
    assert len(dev_identifiers()) >= 10  # the scan below is only meaningful with real identifiers


@pytest.mark.parametrize("name", PROMPT_FILES)
def test_no_dev_identifiers_outside_examples(name):
    text = _outside_examples((PROMPTS_DIR / name).read_text(encoding="utf-8")).lower()
    leaked = sorted(i for i in dev_identifiers() if re.search(rf"(?<!\w){re.escape(i.lower())}(?!\w)", text))
    assert leaked == []


@pytest.mark.parametrize("name", PROMPT_FILES)
def test_at_most_two_examples(name):
    text = (PROMPTS_DIR / name).read_text(encoding="utf-8")
    assert len(EXAMPLE_BLOCK.findall(text)) <= MAX_EXAMPLES


def test_scan_catches_a_leak():
    leak = f"rule text about {sorted(dev_identifiers())[0]} here"
    assert any(re.search(rf"(?<!\w){re.escape(i.lower())}(?!\w)", leak.lower()) for i in dev_identifiers())

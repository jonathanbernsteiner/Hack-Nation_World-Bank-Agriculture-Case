import json
import os
from types import SimpleNamespace

import pytest

from hotline.pipeline import translate as tr

LINES = [
    {"i": 0, "role": "agent", "sw": "Habari, ulikuza nini?"},
    {"i": 1, "role": "farmer", "sw": "Niliuza kilo mia tatu za kiboko."},
]


def _reply(turns, stop_reason="end_turn", category=None):
    text = turns if isinstance(turns, str) else json.dumps({"turns": turns})
    return SimpleNamespace(
        stop_reason=stop_reason,
        stop_details=SimpleNamespace(category=category) if stop_reason == "refusal" else None,
        content=[SimpleNamespace(type="text", text=text)],
    )


GOOD = _reply(
    [
        {"i": 0, "speaker": "Agent", "text": "Hello, what did you grow?"},
        {"i": 1, "speaker": "Farmer", "text": "I sold 300 kilos of kiboko."},
    ]
)
BAD = _reply([{"i": 0, "speaker": "Agent", "text": "Hello"}])


class FakeClient:
    def __init__(self, *replies):
        self.replies = list(replies)
        self.calls = []
        self.messages = self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.replies.pop(0)


@pytest.fixture(autouse=True)
def model_env(monkeypatch):
    monkeypatch.setenv(tr.MODEL_ENV, "claude-opus-5-5")


def test_aligned_response_returns_text_in_order():
    client = FakeClient(GOOD)
    assert tr.translate_lines(LINES, client=client) == ["Hello, what did you grow?", "I sold 300 kilos of kiboko."]
    assert len(client.calls) == 1


def test_empty_input_makes_no_call():
    client = FakeClient()
    assert tr.translate_lines([], client=client) == []
    assert client.calls == []


def test_misaligned_then_aligned_retries_once_with_error():
    client = FakeClient(BAD, GOOD)
    assert len(tr.translate_lines(LINES, client=client)) == 2
    assert len(client.calls) == 2
    assert "rejected" in client.calls[1]["messages"][0]["content"]
    assert "expected 2 turns, got 1" in client.calls[1]["messages"][0]["content"]


def test_misaligned_twice_raises():
    client = FakeClient(BAD, BAD)
    with pytest.raises(tr.TranslationMisaligned):
        tr.translate_lines(LINES, client=client)
    assert len(client.calls) == 2


def test_wrong_index_wrong_speaker_and_bad_json_are_misaligned():
    swapped = _reply(
        [{"i": 1, "speaker": "Agent", "text": "x"}, {"i": 0, "speaker": "Farmer", "text": "y"}]
    )
    wrong_speaker = _reply(
        [{"i": 0, "speaker": "Farmer", "text": "x"}, {"i": 1, "speaker": "Farmer", "text": "y"}]
    )
    for first in (swapped, wrong_speaker, _reply("not json")):
        with pytest.raises(tr.TranslationMisaligned):
            tr.translate_lines(LINES, client=FakeClient(first, first))


def test_refusal_raises_without_retry():
    client = FakeClient(_reply([], stop_reason="refusal", category="general_harms"))
    with pytest.raises(tr.TranslationRefused) as info:
        tr.translate_lines(LINES, client=client)
    assert info.value.category == "general_harms"
    assert len(client.calls) == 1


def test_max_tokens_raises():
    with pytest.raises(tr.TranslationTruncated):
        tr.translate_lines(LINES, client=FakeClient(_reply([], stop_reason="max_tokens")))


def test_request_kwargs(monkeypatch):
    monkeypatch.setenv(tr.MODEL_ENV, "claude-test-model")
    client = FakeClient(GOOD)
    tr.translate_lines(LINES, client=client)
    kwargs = client.calls[0]
    assert kwargs["model"] == "claude-test-model"
    assert kwargs["output_config"]["effort"] == "low"
    assert kwargs["output_config"]["format"]["type"] == "json_schema"
    assert "temperature" not in kwargs
    assert "fallbacks" not in kwargs and "betas" not in kwargs
    assert kwargs["max_tokens"] >= 16_000
    assert "milioni moja na laki nane" in kwargs["system"]
    assert "[unclear]" in kwargs["system"]


def test_missing_model_env_raises(monkeypatch):
    monkeypatch.delenv(tr.MODEL_ENV)
    with pytest.raises(tr.TranslationConfigError):
        tr.translate_lines(LINES, client=FakeClient(GOOD))


def test_cache_key_changes_with_prompt_and_model():
    turns = tr._source_turns(LINES)
    base = tr.cache_key("m", "low", "prompt", turns)
    assert base == tr.cache_key("m", "low", "prompt", turns)
    assert base != tr.cache_key("m", "low", "prompt v2", turns)
    assert base != tr.cache_key("other", "low", "prompt", turns)
    assert base != tr.cache_key("m", "high", "prompt", turns)


def test_cache_hit_skips_the_call_and_prompt_change_misses(tmp_path, monkeypatch):
    first = FakeClient(GOOD)
    tr.translate_lines(LINES, client=first, cache_dir=tmp_path)
    assert len(list(tmp_path.glob("*.json"))) == 1

    second = FakeClient()
    assert tr.translate_lines(LINES, client=second, cache_dir=tmp_path)[0].startswith("Hello")
    assert second.calls == []

    changed = tmp_path / "translate.md"
    changed.write_text(tr.PROMPT_PATH.read_text() + "\nextra rule\n")
    monkeypatch.setattr(tr, "PROMPT_PATH", changed)
    third = FakeClient(GOOD)
    tr.translate_lines(LINES, client=third, cache_dir=tmp_path)
    assert len(third.calls) == 1


def test_no_cache_without_cache_dir(tmp_path):
    tr.translate_lines(LINES, client=FakeClient(GOOD))
    assert list(tmp_path.iterdir()) == []


@pytest.mark.live
def test_live_number_words():
    lines = [
        {"i": 0, "role": "farmer", "sw": "Niliuza kilo mia tatu za kiboko jana kwa shilingi milioni moja na laki nane"},
        {"i": 1, "role": "agent", "sw": "Sawa, asante."},
        {"i": 2, "role": "farmer", "sw": "Nilipata elfu sita na nusu kwa kilo."},
        {"i": 3, "role": "agent", "sw": "Je, ulimuuzia mchuuzi?"},
    ]
    out = tr.translate_lines(lines)
    print(out)
    assert len(out) == 4
    assert "300" in out[0] and "kiboko" in out[0].lower() and "1,800,000" in out[0]
    assert "6,500" in out[2]
    assert "middleman" in out[3].lower()

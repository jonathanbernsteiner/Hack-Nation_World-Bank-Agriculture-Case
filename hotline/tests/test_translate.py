import json
import os
from pathlib import Path
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


# Review regression tests (#58): pin the API contract, privacy and failure paths.

EXPECTED = ["Hello, what did you grow?", "I sold 300 kilos of kiboko."]


def test_only_index_speaker_and_kiswahili_text_reach_the_model():
    lines = [
        {"i": 7, "role": "agent", "sw": "Habari?", "t": 1.5, "caller_id": "+256700000000"},
        SimpleNamespace(i=8, role="farmer", sw="Niliuza kahawa kavu.", t=3.0, phone="+256700000001"),
    ]
    client = FakeClient(GOOD)
    assert tr.translate_lines(lines, client=client) == EXPECTED
    request = client.calls[0]
    assert json.loads(request["messages"][0]["content"]) == [
        {"i": 0, "speaker": "Agent", "text": "Habari?"},
        {"i": 1, "speaker": "Farmer", "text": "Niliuza kahawa kavu."},
    ]
    assert "+256" not in json.dumps(request)


def test_every_attempt_sends_only_the_allowed_request_keys():
    client = FakeClient(BAD, GOOD)
    tr.translate_lines(LINES, client=client)
    assert len(client.calls) == 2
    for kwargs in client.calls:
        # No temperature, fallbacks, betas or thinking override on any attempt.
        assert set(kwargs) == {"model", "max_tokens", "system", "messages", "output_config"}
        assert set(kwargs["output_config"]) == {"effort", "format"}
        assert kwargs["output_config"]["effort"] == "low"
        assert kwargs["model"] == "claude-opus-5-5"


def test_retry_is_single_turn_and_resends_the_full_transcript():
    client = FakeClient(BAD, GOOD)
    tr.translate_lines(LINES, client=client)
    first, second = (call["messages"] for call in client.calls)
    assert len(second) == 1 and second[0]["role"] == "user"
    assert second[0]["content"].startswith(first[0]["content"])


def test_refusal_on_the_retry_stops_without_a_third_call():
    client = FakeClient(BAD, _reply([], stop_reason="refusal", category="bio"))
    with pytest.raises(tr.TranslationRefused) as info:
        tr.translate_lines(LINES, client=client)
    assert info.value.category == "bio"
    assert len(client.calls) == 2


def test_max_tokens_on_the_retry_raises_truncated():
    client = FakeClient(BAD, _reply([], stop_reason="max_tokens"))
    with pytest.raises(tr.TranslationTruncated):
        tr.translate_lines(LINES, client=client)
    assert len(client.calls) == 2


def test_refusal_without_stop_details_has_no_category():
    reply = SimpleNamespace(stop_reason="refusal", stop_details=None, content=[])
    with pytest.raises(tr.TranslationRefused) as info:
        tr.translate_lines(LINES, client=FakeClient(reply))
    assert info.value.category is None


def test_thinking_blocks_before_the_json_are_ignored():
    thinking = SimpleNamespace(type="thinking", thinking="", signature="sig")
    reply = SimpleNamespace(stop_reason="end_turn", stop_details=None, content=[thinking, *GOOD.content])
    assert tr.translate_lines(LINES, client=FakeClient(reply)) == EXPECTED


def test_typed_errors_share_the_base_and_never_echo_the_transcript():
    for cls in (tr.TranslationMisaligned, tr.TranslationRefused, tr.TranslationTruncated, tr.TranslationConfigError):
        assert issubclass(cls, tr.TranslationError)
    with pytest.raises(tr.TranslationMisaligned) as info:
        tr.translate_lines(LINES, client=FakeClient(BAD, BAD))
    for line in LINES:
        assert line["sw"] not in str(info.value)


@pytest.mark.parametrize("value", [None, ""])
def test_missing_or_empty_model_env_makes_no_call(monkeypatch, value):
    if value is None:
        monkeypatch.delenv(tr.MODEL_ENV)
    else:
        monkeypatch.setenv(tr.MODEL_ENV, value)
    client = FakeClient(GOOD)
    with pytest.raises(tr.TranslationConfigError):
        tr.translate_lines(LINES, client=client)
    assert client.calls == []


def test_default_client_uses_spec_timeout_and_retries(monkeypatch):
    made = []

    def factory(**kwargs):
        made.append(kwargs)
        return FakeClient(GOOD)

    monkeypatch.setattr(tr.anthropic, "Anthropic", factory)
    assert tr.translate_lines(LINES) == EXPECTED
    assert made == [{"max_retries": 2, "timeout": 120.0}]


def test_output_schema_matches_the_spec_contract():
    schema = tr.TURNS_SCHEMA
    assert schema["required"] == ["turns"] and schema["additionalProperties"] is False
    item = schema["properties"]["turns"]["items"]
    assert set(item["required"]) == {"i", "speaker", "text"}
    assert item["additionalProperties"] is False
    assert item["properties"]["i"]["type"] == "integer"
    assert item["properties"]["speaker"]["enum"] == ["Agent", "Farmer"]


@pytest.mark.parametrize(
    "needle",
    [
        "milioni moja na laki nane", "1,800,000", "elfu sita na nusu", "6,500", "mitwalo ebiri", "20,000",
        "arithmetic", "shilingi", "shillings", "gunia", "bag", "debe", "tin", "kiboko", "mbuni",
        "kahawa kavu", "kahawa iliyokobolewa", "FAQ", "mchuuzi", "middleman", "verbatim", "[unclear]", "[PIN]",
    ],
)
def test_prompt_keeps_every_spec_translation_rule(needle):
    assert needle in tr.PROMPT_PATH.read_text(encoding="utf-8")


def test_corrupt_or_stale_cache_is_ignored_and_rewritten(tmp_path):
    tr.translate_lines(LINES, client=FakeClient(GOOD), cache_dir=tmp_path)
    (path,) = tmp_path.glob("*.json")
    for bad in ("{not json", json.dumps(["only one"]), json.dumps({"turns": []}), json.dumps([1, 2])):
        path.write_text(bad, encoding="utf-8")
        client = FakeClient(GOOD)
        assert tr.translate_lines(LINES, client=client, cache_dir=tmp_path) == EXPECTED
        assert len(client.calls) == 1
    assert json.loads(path.read_text(encoding="utf-8")) == EXPECTED


def test_cache_is_keyed_by_transcript_and_model(tmp_path, monkeypatch):
    tr.translate_lines(LINES, client=FakeClient(GOOD), cache_dir=tmp_path)
    edited = [LINES[0], {**LINES[1], "sw": "Niliuza kilo mia nne za kiboko."}]
    client = FakeClient(GOOD)
    tr.translate_lines(edited, client=client, cache_dir=tmp_path)
    assert len(client.calls) == 1
    monkeypatch.setenv(tr.MODEL_ENV, "claude-other-model")
    client = FakeClient(GOOD)
    tr.translate_lines(LINES, client=client, cache_dir=tmp_path)
    assert len(client.calls) == 1
    assert len(list(tmp_path.glob("*.json"))) == 3


def test_failed_translation_is_never_cached(tmp_path):
    with pytest.raises(tr.TranslationMisaligned):
        tr.translate_lines(LINES, client=FakeClient(BAD, BAD), cache_dir=tmp_path)
    with pytest.raises(tr.TranslationRefused):
        tr.translate_lines(LINES, client=FakeClient(_reply([], stop_reason="refusal")), cache_dir=tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_no_cache_io_without_cache_dir(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("the cache was touched without cache_dir")

    monkeypatch.setattr(tr, "_read_cache", fail)
    monkeypatch.setattr(tr.Path, "write_text", fail)
    monkeypatch.setattr(tr.Path, "mkdir", fail)
    assert tr.translate_lines(LINES, client=FakeClient(GOOD)) == EXPECTED


EMPTY = _reply(
    [
        {"i": 0, "speaker": "Agent", "text": "Hello... I sold 300 kilos of kiboko."},
        {"i": 1, "speaker": "Farmer", "text": ""},
    ]
)
BLANK = _reply(
    [
        {"i": 0, "speaker": "Agent", "text": "Hello"},
        {"i": 1, "speaker": "Farmer", "text": "   "},
    ]
)


def test_empty_turn_then_good_retries_and_returns_good():
    client = FakeClient(EMPTY, GOOD)
    assert tr.translate_lines(LINES, client=client)[1] == "I sold 300 kilos of kiboko."
    assert len(client.calls) == 2
    assert "non-empty text" in client.calls[1]["messages"][0]["content"]


@pytest.mark.parametrize("bad", [EMPTY, BLANK])
def test_empty_turn_twice_raises_misaligned(bad):
    client = FakeClient(bad, bad)
    with pytest.raises(tr.TranslationMisaligned):
        tr.translate_lines(LINES, client=client)
    assert len(client.calls) == 2


@pytest.mark.parametrize(
    "bad_line",
    [
        {"role": "user", "sw": "x"},
        {"role": None, "sw": "x"},
        {"sw": "x"},
        {"role": "farmer"},
        {"role": "farmer", "sw": None},
        {"role": "farmer", "sw": 5},
    ],
)
def test_bad_input_line_raises_before_any_call(bad_line, monkeypatch):
    def boom(*args, **kwargs):
        raise AssertionError("client must not be built")

    monkeypatch.setattr(tr.anthropic, "Anthropic", boom)
    client = FakeClient(GOOD)
    with pytest.raises(tr.TranslationInputError, match="line 1"):
        tr.translate_lines([LINES[0], bad_line], client=client)
    with pytest.raises(tr.TranslationInputError):
        tr.translate_lines([LINES[0], bad_line])
    assert client.calls == []


# Review cycle 2 regression tests (#58): split lines, input privacy, the R2 line shape, deployment.


def test_extra_turn_is_rejected_and_the_rejected_answer_is_not_echoed():
    split = _reply(
        [
            {"i": 0, "speaker": "Agent", "text": "Hello, what did you grow?"},
            {"i": 1, "speaker": "Farmer", "text": "I sold 300 kilos"},
            {"i": 2, "speaker": "Farmer", "text": "of kiboko."},
        ]
    )
    client = FakeClient(split, split)
    with pytest.raises(tr.TranslationMisaligned, match="expected 2 turns, got 3"):
        tr.translate_lines(LINES, client=client)
    retry = client.calls[1]["messages"][0]["content"]
    assert "expected 2 turns, got 3" in retry
    assert "I sold 300 kilos" not in retry


@pytest.mark.parametrize(
    "turns",
    [
        [{"i": 0, "speaker": "Agent", "text": "Hello"}, "I sold."],
        [{"i": 0, "speaker": "Agent", "text": "Hello"}, {"i": 1, "speaker": "Farmer", "text": None}],
        [{"i": 0, "speaker": "Agent", "text": "Hello"}, {"i": 1, "text": "I sold."}],
        [{"i": 0, "speaker": "Agent", "text": "Hello"}, {"speaker": "Farmer", "text": "I sold."}],
    ],
    ids=["turn-not-object", "null-text", "missing-speaker", "missing-i"],
)
def test_malformed_turns_are_retried_then_misaligned(turns):
    client = FakeClient(_reply(turns), _reply(turns))
    with pytest.raises(tr.TranslationMisaligned):
        tr.translate_lines(LINES, client=client)
    assert len(client.calls) == 2


def test_bare_list_response_is_misaligned():
    bare = _reply(json.dumps([{"i": 0, "speaker": "Agent", "text": "a"}, {"i": 1, "speaker": "Farmer", "text": "b"}]))
    with pytest.raises(tr.TranslationMisaligned, match="turns"):
        tr.translate_lines(LINES, client=FakeClient(bare, bare))


@pytest.mark.parametrize(
    "bad_line",
    [
        {"role": "+256700000001", "sw": "x"},
        {"role": "farmer", "sw": {"phone": "+256700000001"}},
        {"role": "farmer", "sw": ["+256700000001"]},
    ],
)
def test_input_error_names_the_line_but_never_its_values(bad_line):
    # The message becomes calls.last_error, so it must not carry caller data.
    client = FakeClient(GOOD)
    with pytest.raises(tr.TranslationInputError) as info:
        tr.translate_lines([LINES[0], bad_line], client=client)
    assert "line 1" in str(info.value)
    assert "+256" not in str(info.value)
    assert client.calls == []


def test_r2_line_shape_keeps_pin_placeholders_verbatim_on_every_attempt():
    # The #57 Line shape: {i, role, sw, t}; [PIN] must reach the model unchanged and t must not.
    lines = [
        {"i": 0, "role": "agent", "sw": "Tafadhali sema PIN yako.", "t": 0.0},
        {"i": 1, "role": "farmer", "sw": "Ni [PIN].", "t": 4.25},
    ]
    client = FakeClient(BAD, GOOD)
    tr.translate_lines(lines, client=client)
    for call in client.calls:
        sent = json.loads(call["messages"][0]["content"].split("\n\nYour previous answer")[0])
        assert sent[1] == {"i": 1, "speaker": "Farmer", "text": "Ni [PIN]."}
        assert all(set(turn) == {"i", "speaker", "text"} for turn in sent)


def test_str_enum_roles_are_accepted():
    from enum import StrEnum

    class Role(StrEnum):
        AGENT = "agent"
        FARMER = "farmer"

    lines = [{"role": Role.AGENT, "sw": LINES[0]["sw"]}, {"role": Role.FARMER, "sw": LINES[1]["sw"]}]
    client = FakeClient(GOOD)
    assert tr.translate_lines(lines, client=client) == EXPECTED
    assert [t["speaker"] for t in json.loads(client.calls[0]["messages"][0]["content"])] == ["Agent", "Farmer"]


def test_explicit_model_overrides_env_and_needs_no_env(monkeypatch):
    client = FakeClient(GOOD, GOOD)
    assert tr.translate_lines(LINES, client=client, model="claude-eval-model") == EXPECTED
    monkeypatch.delenv(tr.MODEL_ENV)
    assert tr.translate_lines(LINES, client=client, model="claude-eval-model") == EXPECTED
    assert [call["model"] for call in client.calls] == ["claude-eval-model", "claude-eval-model"]


def test_prompt_file_ships_with_the_vercel_function():
    # Production reads the prompt from disk; an excludeFiles glob that matched it would only fail at runtime.
    import fnmatch

    project_root = Path(tr.__file__).resolve().parents[2]
    relative = tr.PROMPT_PATH.resolve().relative_to(project_root).as_posix()
    assert tr.PROMPT_PATH.is_file()
    config = json.loads((project_root / "vercel.json").read_text(encoding="utf-8"))
    for function in config.get("functions", {}).values():
        excluded = function.get("excludeFiles", "")
        for pattern in excluded.strip("{}").split(","):
            assert not (pattern and fnmatch.fnmatchcase(relative, pattern)), (relative, pattern)

from datetime import date

import pytest

from hotline.pipeline.run import run_call

LINES = [
    {"i": 0, "role": "agent", "sw": "Habari", "t": 0},
    {"i": 1, "role": "farmer", "sw": "Nimeuza kilo hamsini", "t": 3},
]


def fake_translator(lines):
    return [f"en{line['i']}" for line in lines]


def fake_extractor(lines_en, call_date):
    assert lines_en[1]["en"] == "en1" and call_date == date(2026, 10, 3)
    return {"consent": "yes", "entries": [{"kind": "sale"}]}


def make_verifier(needs_review=False):
    def verifier(extraction, **kwargs):
        assert kwargs["identified_by"] == "pin" and kwargs["tool_results"] == []
        assert [line["en"] for line in kwargs["lines_en"]] == ["en0", "en1"]
        return {"consent": "yes", "entries": [{"kind": "sale"}], "flags": [], "needs_review": needs_review}

    return verifier


def run(**overrides):
    kwargs = dict(translator=fake_translator, extractor=fake_extractor, verifier=make_verifier(), identified_by="pin")
    return run_call(LINES, date(2026, 10, 3), **{**kwargs, **overrides})


def test_run_call_composes_steps():
    result = run()
    assert result.transcript_en == "Agent: en0\nFarmer: en1"
    assert [line["en"] for line in result.lines_en] == ["en0", "en1"]
    assert result.consent == "yes" and result.status == "processed"
    assert result.entries[0]["kind"] == "sale"
    assert result.extraction["consent"] == "yes"


def test_run_call_flags_review():
    assert run(verifier=make_verifier(needs_review=True)).status == "needs_review"


def test_run_call_rejects_misaligned_translation():
    with pytest.raises(ValueError):
        run(translator=lambda lines: ["only one"])


def test_run_call_does_not_mutate_input():
    run()
    assert "en" not in LINES[0]

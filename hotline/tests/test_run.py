import sys
import types
from datetime import date

import pytest

import hotline.pipeline

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
        assert [line["en"] for line in kwargs["lines"]] == ["en0", "en1"]
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


def test_run_call_keeps_stored_line_keys():
    # transcript_lines is overwritten with lines_en on save; t must survive (spec section 4).
    assert [line["t"] for line in run().lines_en] == [0, 3]


def test_consent_no_writes_no_entries_and_is_processed():
    def verifier(extraction, **kwargs):
        return {"consent": "no", "entries": [{"kind": "sale", "needs_review": True}]}

    result = run(verifier=verifier)
    assert result.consent == "no" and result.entries == [] and result.status == "processed"


def test_default_verifier_matches_verify_py_and_honours_its_review_flag(monkeypatch):
    # The real verify.verify (#59) takes lines_en/call_date positionally, a one-argument reask,
    # and flags review on the result, not on each entry. A mismatch here fails every live call.
    seen = {}
    raw = {"consent": "yes", "entries": [{"kind": "sale"}]}

    def fake_verify(extraction, lines_en, call_date, *, tool_results=None, identified_by=None, reask=None):
        seen["corrected"] = reask(["entry 0: quote not found"])
        return types.SimpleNamespace(consent="yes", entries=[{"kind": "sale"}], needs_review=True)

    def fake_reask(lines_en, call_date, previous, errors):
        seen["reask"] = (call_date, previous, errors)
        return raw

    fakes = {
        "verify": types.SimpleNamespace(verify=fake_verify),
        "extract": types.SimpleNamespace(extract_entries=lambda lines_en, call_date: raw, reask=fake_reask),
    }
    for name, module in fakes.items():
        monkeypatch.setitem(sys.modules, f"hotline.pipeline.{name}", module)
        monkeypatch.setattr(hotline.pipeline, name, module, raising=False)

    result = run_call(LINES, date(2026, 10, 3), translator=fake_translator, identified_by="location")
    assert result.status == "needs_review"
    assert seen["reask"] == (date(2026, 10, 3), raw, ["entry 0: quote not found"])

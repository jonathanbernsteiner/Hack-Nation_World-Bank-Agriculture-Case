import json
import os
from datetime import date
from types import SimpleNamespace

import pytest

from hotline.pipeline import extract as ex
from hotline.schema import CallExtraction, json_schema

LINES = [
    {"i": 0, "role": "agent", "en": "The median is 5900 shillings per kilo."},
    {"i": 1, "role": "farmer", "en": "I sold 300 kilos of kiboko for 1,800,000 shillings."},
]
ENTRY = {k: None for k in ["plot", "crop", "coffee_form", "coffee_type", "amount", "unit", "kg_per_unit",
         "price_total", "price_per_unit", "currency", "date_sold", "buyer_type", "buyer_name", "paid_how",
         "activity", "input", "quantity", "yield_amount", "disease_detected", "symptom", "likely_disease",
         "disease_confidence", "evidence_quote", "evidence_turn", "description"]} | {"kind": "sale", "confidence": 0.9}
GOOD = {"consent": "yes", "entries": [ENTRY | {"crop": "coffee", "amount": 300, "unit": "kg"}]}


def reply(payload, stop_reason="end_turn", category=None):
    text = payload if isinstance(payload, str) else json.dumps(payload)
    return SimpleNamespace(stop_reason=stop_reason,
                           stop_details=SimpleNamespace(category=category) if stop_reason == "refusal" else None,
                           content=[SimpleNamespace(type="text", text=text)])


class FakeClient:
    def __init__(self, *replies):
        self.replies, self.calls, self.messages = list(replies), [], self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.replies.pop(0)


@pytest.fixture(autouse=True)
def model_env(monkeypatch):
    monkeypatch.setenv(ex.MODEL_ENV, "claude-opus-5-5")


def test_parses_into_call_extraction():
    result = ex.extract_entries(LINES, date(2026, 10, 3), client=FakeClient(reply(GOOD)))
    assert isinstance(result, CallExtraction) and result.entries[0].amount == 300


def test_request_kwargs():
    client = FakeClient(reply(GOOD))
    ex.extract_entries(LINES, date(2026, 10, 3), client=client)
    kwargs = client.calls[0]
    assert kwargs["model"] == "claude-opus-5-5"
    assert kwargs["output_config"] == {"effort": "high", "format": {"type": "json_schema", "schema": json_schema()}}
    assert "temperature" not in kwargs and "fallbacks" not in kwargs and "betas" not in kwargs
    content = kwargs["messages"][0]["content"]
    assert "2026-10-03 (Saturday)" in content and "[1] Farmer: I sold 300" in content


def test_refusal_and_truncation_are_typed():
    with pytest.raises(ex.ExtractionRefused) as info:
        ex.extract_entries(LINES, date(2026, 10, 3), client=FakeClient(reply("", "refusal", "cyber")))
    assert info.value.category == "cyber"
    with pytest.raises(ex.ExtractionTruncated):
        ex.extract_entries(LINES, date(2026, 10, 3), client=FakeClient(reply("{", "max_tokens")))


def test_invalid_json_and_config_and_input_errors():
    with pytest.raises(ex.ExtractionInvalid):
        ex.extract_entries(LINES, date(2026, 10, 3), client=FakeClient(reply({"consent": "yes"})))
    with pytest.raises(ex.ExtractionConfigError):
        os.environ.pop(ex.MODEL_ENV)
        ex.extract_entries(LINES, date(2026, 10, 3), client=FakeClient())
    with pytest.raises(ex.ExtractionInputError):
        ex.render_lines([{"i": 0, "role": "bot", "en": "x"}])


def test_reask_includes_previous_json_and_errors():
    client = FakeClient(reply(GOOD))
    previous = CallExtraction.model_validate(GOOD)
    ex.reask(LINES, date(2026, 10, 3), previous, ["entry 0: quote not found in Farmer line 1"], client=client)
    content = client.calls[0]["messages"][0]["content"]
    assert "entry 0: quote not found in Farmer line 1" in content and '"amount": 300' in content


@pytest.mark.live
@pytest.mark.skipif(not os.environ.get("RUN_LIVE"), reason="set RUN_LIVE=1")
def test_live_sale_and_agent_median_is_no_sale():
    sale = ex.extract_entries(LINES[1:] + [{"i": 2, "role": "farmer", "en": "My coffee leaves have orange powder."}],
                              date(2026, 10, 3), model=os.environ.get(ex.MODEL_ENV, "claude-opus-5-5"))
    assert [e.kind for e in sale.entries].count("sale") == 1
    agent_only = ex.extract_entries(LINES[:1] + [{"i": 1, "role": "farmer", "en": "OK, thanks, I have not sold yet."}],
                                    date(2026, 10, 3))
    assert not [e for e in agent_only.entries if e.kind == "sale"]

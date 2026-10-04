"""Farmer profile page (/demo/farmer/{id}) and the sentiment read."""

import base64
import dataclasses
import json
import types
from datetime import date, datetime, timezone

import pytest
from fastapi.testclient import TestClient

from hotline import config, main, sentiment
from hotline.routes import demo, farmer

AUTH = {"Authorization": "Basic " + base64.b64encode(b"judge:pw").decode()}
TODAY = date(2026, 10, 4)


def _entry(id_, call_id, day, kind="sale", **fields):
    base = {"id": id_, "call_id": call_id, "entry_date": day, "kind": kind, "crop": "coffee", "coffee_form": "kiboko",
            "amount": None, "unit": "kg", "amount_kg": None, "price_total": None, "currency": "UGX", "buyer_type": None,
            "paid_how": None, "yield_amount": None, "symptom": None, "likely_disease": None, "description": None,
            "evidence_quote": None, "quote_verified": True, "confidence": 0.9, "identified_by": "pin"}
    return {**base, **fields}


ENTRIES = [
    _entry(5, 9, date(2026, 10, 3), amount_kg=300, price_total=1_800_000, buyer_type="middleman",
           paid_how="mobile_money", evidence_quote="<b>300 kilos</b>"),
    _entry(4, 8, date(2026, 7, 18), amount_kg=400, price_total=2_120_000),
    _entry(3, 7, date(2026, 6, 1), amount_kg=100, price_total=600_000, quote_verified=False),  # flagged: not counted
    _entry(2, 6, date(2025, 12, 1), kind="harvest", amount_kg=None, yield_amount=1500),
    _entry(1, 5, date(2025, 3, 1), amount_kg=200, price_total=1_400_000),
]


def _view():
    calls = [{"id": 9, "received_at": datetime(2026, 10, 4, 6, 0, tzinfo=timezone.utc), "status": "processed",
              "identified_by": "pin", "is_synthetic": True, "duration_secs": 180,
              "transcript_lines": [{"i": 0, "role": "farmer", "sw": "<script>x</script>", "en": "I sold 300 kilos"}]}]
    profile = {"id": 413, "name": "Nakato <i>", "is_synthetic": True, "lat": -0.49, "lon": 31.84, "village_id": 1,
               "village": "Kyabakuza", "parish": "Kasaali", "sub_county": "Kyanamukaaka", "district": "Masaka",
               "region": "Central", "coffee_type": "robusta", "village_lat": -0.48, "village_lon": 31.83,
               "first_call_at": datetime(2025, 1, 3, 6, 0, tzinfo=timezone.utc)}
    return {"farmer": profile, "entries": ENTRIES, "calls": calls, "today": TODAY, "form": "kiboko",
            "median": {"median_ugx_per_kg": 5950, "n_sales": 28, "level": "village", "area": "Kyabakuza"}}


def test_yearly_sums_counted_entries_per_coffee_year():
    years = {y["year"]: y for y in farmer.yearly(ENTRIES)}
    assert years["2025/26"]["harvest_kg"] == 1500
    assert years["2025/26"]["sold_kg"] == 400 and years["2025/26"]["income_ugx"] == 2_120_000  # flagged sale left out
    assert years["2026/27"]["income_ugx"] == 1_800_000
    assert years["2024/25"]["avg_ugx_per_kg"] == 7000


def test_monthly_covers_window_and_skips_flagged_sales():
    series = farmer.monthly(ENTRIES, TODAY, months=6)
    assert series["labels"] == ["May 26", "Jun 26", "Jul 26", "Aug 26", "Sep 26", "Oct 26"]
    assert series["kg"] == [0, 0, 400, 0, 0, 300]
    assert series["income"][-1] == 1_800_000


def test_price_points_oldest_first():
    assert farmer.price_points(ENTRIES) == [
        {"x": "Mar 25", "y": 7000}, {"x": "Jul 26", "y": 5300}, {"x": "Oct 26", "y": 6000}]


def test_main_form_by_kg():
    assert farmer.main_form(ENTRIES) == "kiboko"
    assert farmer.main_form([]) == "kiboko"


@pytest.fixture
def client(monkeypatch):
    settings = dataclasses.replace(config.settings, demo_user="judge", demo_password="pw")
    monkeypatch.setattr(config, "settings", settings)
    monkeypatch.setattr(farmer, "_load", lambda farmer_id: _view() if farmer_id == 413 else None)
    monkeypatch.setattr(farmer, "_load_calls", lambda farmer_id: _view()["calls"])
    return TestClient(main.app)


def test_profile_requires_auth(client):
    assert client.get("/demo/farmer/413").status_code == 401
    assert client.get("/demo/farmer/413/sentiment").status_code == 401


def test_profile_renders_escaped_with_new_badge(client):
    body = client.get("/demo/farmer/413", headers=AUTH).text
    assert "<script>x</script>" not in body and "&lt;script&gt;" in body
    assert "Nakato &lt;i&gt;" in body and "&lt;b&gt;300 kilos&lt;/b&gt;" in body
    assert body.count("class='pill new'>New") == 1  # only the newest call's entry
    assert "First called on 2025-01-03" in body
    assert "tile.openstreetmap.org" in body and "OpenStreetMap contributors" in body
    assert "pin_hash" not in body


def test_profile_data_script_cannot_break_out(client):
    body = client.get("/demo/farmer/413", headers=AUTH).text
    data = body.split("id=profile-data>", 1)[1].split("</script>", 1)[0]
    assert json.loads(data.replace("<\\/", "</"))["median"] == 5950.0


def test_unknown_farmer_is_404(client):
    assert client.get("/demo/farmer/1", headers=AUTH).status_code == 404


def test_sentiment_errors_become_a_message(client, monkeypatch):
    def boom(*_args, **_kwargs):
        raise RuntimeError("api down")
    monkeypatch.setattr(sentiment, "analyze", boom)
    assert client.get("/demo/farmer/413/sentiment", headers=AUTH).json() == {"message": "Sentiment unavailable right now."}


def test_demo_links_caller_to_profile():
    call = {"id": 1, "farmer_id": 413, "received_at": None, "status": "processed", "identified_by": "pin",
            "first_name": "Nakato", "village": "Kyabakuza", "transcript_lines": []}
    block = demo._call_block(call, [])
    assert "<a class=who href=/demo/farmer/413>Nakato</a>" in block and "Kyabakuza" in block


class FakeClient:
    def __init__(self, payload):
        self.calls = 0
        self.payload = payload
        self.messages = self

    def create(self, **kwargs):
        self.calls += 1
        self.kwargs = kwargs
        text = types.SimpleNamespace(type="text", text=json.dumps(self.payload))
        return types.SimpleNamespace(stop_reason="end_turn", content=[text])


def test_sentiment_uses_english_lines_and_caches(monkeypatch):
    monkeypatch.setenv(sentiment.MODEL_ENV, "claude-opus-5-5")
    monkeypatch.setattr(sentiment, "_cache", {})
    fake = FakeClient({"overall": "positive", "score": 3, "summary": "Happy.", "calls": []})
    calls = [{"id": 7, "transcript_lines": [{"role": "farmer", "sw": "nzuri", "en": "good"}]}, {"id": 8, "transcript_lines": []}]
    result = sentiment.analyze(413, calls, client=fake)
    assert result["score"] == 1.0  # clamped
    assert json.loads(fake.kwargs["messages"][0]["content"]) == [{"id": 7, "text": "Farmer: good"}]
    assert "temperature" not in fake.kwargs
    sentiment.analyze(413, calls, client=fake)
    assert fake.calls == 1


def test_sentiment_none_without_transcripts():
    assert sentiment.analyze(413, [{"id": 1, "transcript_lines": None}], client=object()) is None

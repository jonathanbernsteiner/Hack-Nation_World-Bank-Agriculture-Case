import base64
import dataclasses
import sys
import types
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

import hotline
from hotline import config, main
from hotline.routes import demo

AUTH = {"Authorization": "Basic " + base64.b64encode(b"judge:pw").decode()}
PIN = "9001"


def _view(**call_overrides):
    call = {
        "id": 1,
        "received_at": datetime(2026, 10, 3, 9, 0, tzinfo=timezone.utc),
        "status": "processed",
        "identified_by": "pin",
        "is_synthetic": True,
        "first_name": "Nakato",
        "village": "Kyabakuza",
        "transcript_lines": [{"i": 0, "role": "farmer", "sw": "<script>alert(1)</script>", "en": "hello [PIN]"}],
        **call_overrides,
    }
    entry = {"call_id": 1, "kind": "sale", "coffee_form": "kiboko", "amount_kg": 300, "price_total": 1800000,
             "currency": "UGX", "evidence_quote": "<b>300 kilo</b>", "quote_verified": True, "confidence": 0.9}
    return {"calls": [call], "entries": [entry], "medians": []}


@pytest.fixture
def client(monkeypatch):
    settings = dataclasses.replace(
        config.settings, demo_user="judge", demo_password="pw", elevenlabs_agent_id="agent_abc"
    )
    monkeypatch.setattr(config, "settings", settings)
    monkeypatch.setattr(demo, "_load", lambda: _view())
    return TestClient(main.app)


def test_requires_auth(client):
    assert client.get("/demo").status_code == 401
    wrong = {"Authorization": "Basic " + base64.b64encode(b"judge:nope").decode()}
    assert client.get("/demo", headers=wrong).status_code == 401


def test_renders_badge_footer_refresh(client):
    body = client.get("/demo", headers=AUTH).text
    assert "SYNTHETIC" in body
    assert "Open-Meteo.com (CC BY 4.0)" in body
    assert "http-equiv=refresh content=10" in body
    assert "12:00" in body  # 09:00 UTC is 12:00 in Kampala


def test_html_is_escaped(client):
    body = client.get("/demo", headers=AUTH).text
    assert "<script>alert(1)</script>" not in body
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in body
    assert "<b>300 kilo</b>" not in body


def test_no_pin_material(client):
    body = client.get("/demo", headers=AUTH).text.lower()
    assert "pin_hash" not in body
    assert PIN not in body


def test_non_synthetic_has_no_badge(client, monkeypatch):
    monkeypatch.setattr(demo, "_load", lambda: _view(is_synthetic=False))
    assert "SYNTHETIC</span>" not in client.get("/demo", headers=AUTH).text


@pytest.mark.parametrize(
    ("entry", "call", "expected"),
    [
        ({"confidence": 0.5}, {"identified_by": "pin"}, True),
        ({"confidence": 0.6}, {"identified_by": "pin"}, False),
        ({"quote_verified": False}, {"identified_by": "pin"}, True),
        ({"quote_verified": None, "confidence": None}, {"identified_by": "pin"}, False),
        ({"confidence": 0.9, "quote_verified": True}, {"identified_by": "location"}, True),
    ],
)
def test_review_flag(entry, call, expected):
    assert demo.needs_review(entry, call) is expected


def test_review_badge_and_unverified_mark_rendered():
    view = _view(identified_by="location")
    view["entries"][0]["quote_verified"] = False
    page = demo.render_page(view)
    assert "Needs review" in page and "&#10007;" in page


def test_widget_only_on_public_page_without_refresh(client, monkeypatch):
    """The 10 s refresh on /demo would end a widget call, so the widget lives on / (no refresh, no ledger)."""
    def _no_db():
        raise AssertionError("/ must not read the ledger")

    monkeypatch.setattr(demo, "_load", _no_db)
    public = client.get("/")
    assert public.status_code == 200
    assert '<elevenlabs-convai agent-id="agent_abc">' in public.text
    assert "http-equiv=refresh" not in public.text
    assert "Nakato" not in public.text and "Open-Meteo.com (CC BY 4.0)" in public.text

    monkeypatch.setattr(demo, "_load", lambda: _view())
    judge = client.get("/demo", headers=AUTH).text
    assert "<elevenlabs-convai" not in judge
    assert "href=/" in judge


def test_amounts_are_readable():
    view = _view()
    view["entries"][0].update(amount_kg=300.0, price_total=Decimal("1800000.00"))
    view["medians"] = [{"village": "Kyabakuza", "forms": [
        {"form": "kiboko", "median_ugx_per_kg": 5900, "n_sales": 12, "level": "village", "area": "Kyabakuza"}]}]
    page = demo.render_page(view)
    assert "300 kg" in page and "1,800,000 UGX" in page and "5,900 UGX/kg" in page


def test_medians_load_rows_once_per_district(monkeypatch):
    calls_made = []
    fake = types.SimpleNamespace(
        load_sale_rows=lambda conn, district, as_of: calls_made.append(district) or [],
        village_price=lambda rows, home, form, as_of: {"form": form, "median_ugx_per_kg": 1},
    )
    monkeypatch.setitem(sys.modules, "hotline.prices", fake)
    monkeypatch.setattr(hotline, "prices", fake, raising=False)
    calls = [
        {"village_id": 1, "village": "Kyabakuza", "district": "Masaka"},
        {"village_id": 2, "village": "V2", "district": "Masaka"},
        {"village_id": 3, "village": "V3", "district": "Mubende"},
    ]
    medians = demo._village_medians(None, calls, date(2026, 10, 3))
    assert sorted(calls_made) == ["Masaka", "Mubende"]
    assert [m["village"] for m in medians] == ["Kyabakuza", "V2", "V3"]

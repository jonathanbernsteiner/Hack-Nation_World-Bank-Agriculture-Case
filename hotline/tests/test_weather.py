import dataclasses
import os
import time
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest
from fastapi.testclient import TestClient

from hotline import config, weather
from hotline.main import app
from hotline.routes.tools import weather as route

SECRET = "tool-secret-value"
REAL_FARMER_PLACE = route.farmer_place
URL = "/api/tools/get_weather_forecast"
HEADERS = {"X-Hotline-Tool-Secret": SECRET}
MASAKA = {"conversation_id": "conv_1", "call_sid": "", "district": "Masaka"}

DAILY = {
    "time": [f"2026-10-{5 + i:02d}" for i in range(7)],
    "precipitation_sum": [0.0, 0.9, 1.0, 12.34, 20.0, 25.5, None],
    "precipitation_probability_max": [5, 20, 50, 80, 90, 95, None],
    "temperature_2m_max": [27.0, 27.4, 26.0, 25.0, 24.0, 23.0, 28.0],
    "temperature_2m_min": [17.0, 17.0, 16.0, 16.0, 15.0, 15.0, 18.0],
}


class FakeOpenMeteo:
    def __init__(self, daily=DAILY, delay=0.0, status=200):
        self.daily, self.delay, self.status, self.requests = daily, delay, status, []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        time.sleep(self.delay)
        return httpx.Response(self.status, json={"daily": self.daily})


@pytest.fixture(autouse=True)
def isolated(monkeypatch):
    monkeypatch.setattr(config, "settings", dataclasses.replace(config.settings, hotline_tool_secret=SECRET))
    monkeypatch.setattr(route, "farmer_place", lambda conversation_id, conn=None: None)
    weather.clear_cache()
    yield
    weather.set_client(None)
    weather.clear_cache()


@pytest.fixture
def api():
    return TestClient(app)


def install(fake: FakeOpenMeteo) -> FakeOpenMeteo:
    weather.set_client(httpx.Client(transport=httpx.MockTransport(fake)))
    return fake


def test_summary_counts_and_seven_days(api):
    install(FakeOpenMeteo())
    body = api.post(URL, json=MASAKA, headers=HEADERS).json()
    assert body["status"] == "ok"
    assert body["place"] == "Masaka"
    assert len(body["days"]) == 7
    # 1.0, 12.34, 20.0, 25.5 are rain days (>=1 mm); 0.9 is not; 20.0 and 25.5 are heavy.
    assert body["summary"] == {"rain_days": 4, "total_rain_mm": 59.7, "heavy_rain_days": 2}
    assert body["days"][3] == {
        "date": "2026-10-08", "rain_mm": 12.3, "rain_chance_pct": 80, "tmin_c": 16, "tmax_c": 25,
    }


def test_null_precipitation_counts_as_zero(api):
    install(FakeOpenMeteo())
    last = api.post(URL, json=MASAKA, headers=HEADERS).json()["days"][6]
    assert last["rain_mm"] == 0 and last["rain_chance_pct"] is None


def test_summarize_tolerates_short_and_missing_arrays():
    result = weather.summarize({"time": ["2026-10-05", "2026-10-06"], "precipitation_sum": [3.0]})
    assert result["summary"] == {"rain_days": 1, "total_rain_mm": 3, "heavy_rain_days": 0}
    assert result["days"][1]["rain_mm"] == 0


def test_attribution_and_request_parameters(api):
    fake = install(FakeOpenMeteo())
    body = api.post(URL, json=MASAKA, headers=HEADERS).json()
    assert body["source"] == "Open-Meteo (CC BY 4.0)"
    params = dict(fake.requests[0].url.params)
    assert params["timezone"] == "Africa/Kampala" and params["forecast_days"] == "7"
    assert "precipitation_sum" in params["daily"]


def test_cache_hit_makes_no_second_request(api):
    fake = install(FakeOpenMeteo())
    api.post(URL, json=MASAKA, headers=HEADERS)
    again = api.post(URL, json={**MASAKA, "district": "masaka "}, headers=HEADERS).json()
    assert again["status"] == "ok" and len(fake.requests) == 1


def test_cache_expires_after_an_hour():
    fake = install(FakeOpenMeteo())
    weather.forecast(-0.33, 31.73, now=lambda: 1000.0)
    weather.forecast(-0.33, 31.73, now=lambda: 1000.0 + weather.CACHE_TTL_S - 1)
    assert len(fake.requests) == 1
    weather.forecast(-0.33, 31.73, now=lambda: 1000.0 + weather.CACHE_TTL_S + 1)
    assert len(fake.requests) == 2


def test_timeout_returns_unavailable_in_time(api):
    install(FakeOpenMeteo(delay=4.0))
    started = time.monotonic()
    response = api.post(URL, json=MASAKA, headers=HEADERS)
    assert response.status_code == 200 and response.json() == {"status": "unavailable"}
    assert time.monotonic() - started < 3.5


@pytest.mark.parametrize("status", [500, 429])
def test_http_errors_return_unavailable(api, status):
    install(FakeOpenMeteo(status=status))
    assert api.post(URL, json=MASAKA, headers=HEADERS).json() == {"status": "unavailable"}


def test_garbage_payload_returns_unavailable(api):
    weather.set_client(httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, text="oops"))))
    assert api.post(URL, json=MASAKA, headers=HEADERS).json() == {"status": "unavailable"}


@pytest.mark.parametrize("headers", [{}, {"X-Hotline-Tool-Secret": "wrong"}])
def test_bad_secret_is_401(api, headers):
    fake = install(FakeOpenMeteo())
    assert api.post(URL, json=MASAKA, headers=headers).status_code == 401
    assert fake.requests == []


@pytest.mark.parametrize("district", [None, "", "Atlantis"])
def test_unknown_location(api, district):
    fake = install(FakeOpenMeteo())
    body = api.post(URL, json={"conversation_id": "conv_x", "district": district}, headers=HEADERS)
    assert body.status_code == 200 and body.json() == {"status": "unknown_location"}
    assert fake.requests == []


def test_identified_farmer_village_wins_over_district(api, monkeypatch):
    fake = install(FakeOpenMeteo())
    monkeypatch.setattr(route, "farmer_place", lambda cid, conn=None: route.Place(-0.3, 31.7, "Kyabakuza, Masaka"))
    body = api.post(URL, json={**MASAKA, "district": "Gulu"}, headers=HEADERS).json()
    assert body["place"] == "Kyabakuza, Masaka"
    assert dict(fake.requests[0].url.params)["latitude"] == "-0.3"
    assert set(body) == {"status", "place", "source", "days", "summary"}


def test_database_error_falls_back_to_district(api, monkeypatch):
    install(FakeOpenMeteo())

    def boom(cid, conn=None):
        raise RuntimeError("postgres://user:password@host/db")

    monkeypatch.setattr(route, "farmer_place", boom)
    assert api.post(URL, json=MASAKA, headers=HEADERS).json()["place"] == "Masaka"
    body = api.post(URL, json={"conversation_id": "c"}, headers=HEADERS)
    assert body.status_code == 200 and body.json() == {"status": "unknown_location"}


def test_district_lookup_is_case_insensitive():
    lat, lon, name = weather.district_centroid("  mAsAkA ")
    assert name == "Masaka" and -1 < lat < 0 and 31 < lon < 32
    assert weather.district_centroid(None) is None


class FakeConn:
    def __init__(self, row):
        self.row = row

    def execute(self, sql, params):
        return self

    def fetchone(self):
        return self.row


def test_farmer_place_uses_village_then_district_centroid():
    assert REAL_FARMER_PLACE("c", FakeConn(("Kyabakuza", "Masaka", -0.3, 31.7))).label == "Kyabakuza, Masaka"
    assert REAL_FARMER_PLACE("c", FakeConn(("Kyabakuza", "Masaka", None, None))).label == "Masaka"
    assert REAL_FARMER_PLACE("c", FakeConn(None)) is None
    assert REAL_FARMER_PLACE(None) is None


@pytest.mark.supabase
def test_farmer_place_from_real_schema(db):
    village_id = db.execute(
        "insert into public.villages (region, district, sub_county, parish, village, lat, lon, is_synthetic)"
        " values ('Central', 'Masaka', 'sc', 'p', 'Testville', -0.31, 31.74, true) returning id"
    ).fetchone()[0]
    farmer_id = db.execute(
        "insert into public.farmers (name, pin_hash, village_id, is_synthetic)"
        " values ('Test', 'weather-test-hash', %s, true) returning id", (village_id,)
    ).fetchone()[0]
    db.execute("insert into public.calls (farmer_id, conversation_id, is_synthetic) values (%s, 'conv_weather_test', true)",
               (farmer_id,))
    place = REAL_FARMER_PLACE("conv_weather_test", db)
    assert (place.label, place.lat, place.lon) == ("Testville, Masaka", -0.31, 31.74)
    assert REAL_FARMER_PLACE("conv_unknown", db) is None


@pytest.mark.live
def test_live_open_meteo_smoke():
    assert os.environ.get("RUN_LIVE") == "1"
    weather.set_client(None)
    result = weather.forecast(-0.33, 31.73)
    assert result is not None and len(result["days"]) == 7


# --- Review regressions (cycle 1) -------------------------------------------------


def test_failed_fetch_is_not_cached(api):
    """A cached failure would silence the forecast for a whole hour after one bad answer."""
    install(FakeOpenMeteo(status=500))
    assert api.post(URL, json=MASAKA, headers=HEADERS).json() == {"status": "unavailable"}
    healthy = install(FakeOpenMeteo())
    assert api.post(URL, json=MASAKA, headers=HEADERS).json()["status"] == "ok"
    assert len(healthy.requests) == 1


def test_timed_out_fetch_is_not_cached(monkeypatch):
    monkeypatch.setattr(weather, "TIMEOUT_S", 0.2)
    install(FakeOpenMeteo(delay=0.6))
    assert weather.forecast(-0.33, 31.73) is None
    healthy = install(FakeOpenMeteo())
    assert weather.forecast(-0.33, 31.73) is not None
    assert len(healthy.requests) == 1


def test_deadline_holds_when_every_worker_is_busy(monkeypatch):
    """More slow calls than workers: queued calls must still give up at the deadline."""
    deadline = 0.3
    pool = ThreadPoolExecutor(max_workers=2)
    monkeypatch.setattr(weather, "_executor", pool)
    monkeypatch.setattr(weather, "TIMEOUT_S", deadline)
    install(FakeOpenMeteo(delay=1.5))

    def timed(i: int):
        started = time.monotonic()
        return weather.forecast(0.1 * i, 32.0), time.monotonic() - started

    try:
        with ThreadPoolExecutor(max_workers=5) as callers:
            results = list(callers.map(timed, range(5)))
    finally:
        pool.shutdown(wait=False, cancel_futures=True)
    assert [result for result, _ in results] == [None] * 5
    assert max(elapsed for _, elapsed in results) < deadline + 0.5


@pytest.mark.parametrize("payload", [{}, {"daily": None}, [], {"daily": "oops"}])
def test_malformed_open_meteo_payload_is_unavailable_not_500(api, payload):
    weather.set_client(httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=payload))))
    response = api.post(URL, json=MASAKA, headers=HEADERS)
    assert response.status_code == 200 and response.json() == {"status": "unavailable"}


class RecordingConnection:
    """Stands in for `db.connect()`: records the SQL and parameters, returns one row."""

    def __init__(self, row):
        self.row, self.calls = row, []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params):
        self.calls.append((sql, params))
        return self

    def fetchone(self):
        return self.row


def test_route_farmer_lookup_binds_conversation_id_and_returns_place_only(api, monkeypatch):
    """Real route wiring: the id is a bound parameter, and only the place label leaves the server."""
    from hotline import db as hotline_db

    fake = install(FakeOpenMeteo())
    connection = RecordingConnection(("Kyabakuza", "Masaka", -0.31, 31.74))
    monkeypatch.setattr(route, "farmer_place", REAL_FARMER_PLACE)
    monkeypatch.setattr(hotline_db, "connect", lambda: connection)
    hostile_id = "conv_1' or '1'='1"
    body = api.post(URL, json={"conversation_id": hostile_id, "district": "Gulu"}, headers=HEADERS).json()

    sql, params = connection.calls[0]
    assert params == (hostile_id,) and hostile_id not in sql
    select_list = sql.lower().split("from")[0]
    for column in ("farmer_id", "pin", "name", "phone"):
        assert column not in select_list
    assert set(body) == {"status", "place", "source", "days", "summary"}
    assert body["place"] == "Kyabakuza, Masaka"
    assert dict(fake.requests[0].url.params)["latitude"] == "-0.31"


def test_unconfigured_database_falls_back_to_request_district(api, monkeypatch):
    """No DATABASE_URL (e.g. a misconfigured deploy) must not turn into a 500."""
    monkeypatch.setattr(route, "farmer_place", REAL_FARMER_PLACE)
    monkeypatch.setattr(config, "settings", dataclasses.replace(config.settings, database_url=None))
    install(FakeOpenMeteo())
    response = api.post(URL, json=MASAKA, headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["status"] == "ok" and response.json()["place"] == "Masaka"


def test_missing_temperature_is_not_reported_as_zero_degrees(api):
    daily = {**DAILY, "temperature_2m_max": [*DAILY["temperature_2m_max"][:6], None],
             "temperature_2m_min": [*DAILY["temperature_2m_min"][:6], None]}
    install(FakeOpenMeteo(daily=daily))
    last = api.post(URL, json=MASAKA, headers=HEADERS).json()["days"][6]
    assert last["tmin_c"] is None and last["tmax_c"] is None


@pytest.mark.parametrize("daily", [{}, {"time": None}])
def test_payload_without_dates_is_unavailable(api, daily):
    install(FakeOpenMeteo(daily=daily))
    assert api.post(URL, json=MASAKA, headers=HEADERS).json() == {"status": "unavailable"}

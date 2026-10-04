"""7-day forecast from Open-Meteo (free, no key, CC BY 4.0).

`forecast` never raises: it returns the summarized forecast or None when Open-Meteo is
slow, down or returns something unusable. The 3 s limit is a hard end-to-end deadline
(httpx timeouts apply per phase, so the call also runs under a future timeout)."""

import csv
import logging
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from functools import lru_cache
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
SOURCE = "Open-Meteo (CC BY 4.0)"
TIMEOUT_S = 3.0
CACHE_TTL_S = 3600
RAIN_DAY_MM = 1.0
HEAVY_RAIN_MM = 20.0
FORECAST_DAYS = 7
DISTRICTS_CSV = Path(__file__).parent / "data" / "uganda_districts.csv"
DAILY_FIELDS = "precipitation_sum,precipitation_probability_max,temperature_2m_max,temperature_2m_min"

_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="weather")
_client: httpx.Client | None = None
_cache: dict[tuple[float, float], tuple[float, dict]] = {}
_lock = threading.Lock()


def get_client() -> httpx.Client:
    """The shared client. Tests replace it with `set_client(httpx.Client(transport=...))`."""
    global _client
    with _lock:
        if _client is None:
            _client = httpx.Client(timeout=TIMEOUT_S)
        return _client


def set_client(client: httpx.Client | None) -> None:
    global _client
    with _lock:
        _client = client


def clear_cache() -> None:
    with _lock:
        _cache.clear()


def _num(value) -> float:
    """Missing precipitation (null) counts as 0 mm."""
    return float(value) if isinstance(value, int | float) and not isinstance(value, bool) else 0.0


def _maybe(value):
    """Rounded number, or None when the source value is missing (never invent a figure)."""
    if not isinstance(value, int | float) or isinstance(value, bool):
        return None
    return _round(float(value))


def _round(value: float):
    rounded = round(value, 1)
    return int(rounded) if rounded == int(rounded) else rounded


def _maybe_int(value) -> int | None:
    number = _maybe(value)
    return None if number is None else int(round(number))


def summarize(daily: dict) -> dict:
    """Turn Open-Meteo's parallel daily arrays into `days[]` plus a `summary`."""
    dates = daily.get("time") or []

    def column(name: str) -> list:
        values = daily.get(name) or []
        return [values[i] if i < len(values) else None for i in range(len(dates))]

    rain, chance = column("precipitation_sum"), column("precipitation_probability_max")
    tmax, tmin = column("temperature_2m_max"), column("temperature_2m_min")
    days = [
        {
            "date": dates[i],
            "rain_mm": _round(_num(rain[i])),
            "rain_chance_pct": _maybe_int(chance[i]),
            "tmin_c": _maybe(tmin[i]),
            "tmax_c": _maybe(tmax[i]),
        }
        for i in range(len(dates))
    ]
    amounts = [_num(r) for r in rain]
    return {
        "days": days,
        "summary": {
            "rain_days": sum(1 for a in amounts if a >= RAIN_DAY_MM),
            "total_rain_mm": _round(sum(amounts)),
            "heavy_rain_days": sum(1 for a in amounts if a >= HEAVY_RAIN_MM),
        },
    }


def _fetch(lat: float, lon: float, client: httpx.Client) -> dict:
    response = client.get(
        OPEN_METEO_URL,
        params={
            "latitude": lat,
            "longitude": lon,
            "daily": DAILY_FIELDS,
            "timezone": "Africa/Kampala",
            "forecast_days": FORECAST_DAYS,
        },
        timeout=TIMEOUT_S,
    )
    response.raise_for_status()
    result = summarize(response.json()["daily"])
    if len(result["days"]) < FORECAST_DAYS:
        raise ValueError("incomplete forecast")
    return result


def forecast(lat: float, lon: float, now: Callable[[], float] = time.monotonic) -> dict | None:
    """Cached (1 h per rounded coordinate pair) forecast, or None if unavailable."""
    key = (round(lat, 2), round(lon, 2))
    with _lock:
        hit = _cache.get(key)
    if hit and now() - hit[0] < CACHE_TTL_S:
        return hit[1]
    try:
        result = _executor.submit(_fetch, lat, lon, get_client()).result(timeout=TIMEOUT_S)
    except FutureTimeout:
        logger.warning("open-meteo: deadline of %.1fs exceeded", TIMEOUT_S)
        return None
    except Exception as exc:  # network, HTTP status, bad JSON: all mean "unavailable"
        logger.warning("open-meteo: %s", type(exc).__name__)
        return None
    with _lock:
        _cache[key] = (now(), result)
    return result


@lru_cache(maxsize=1)
def _district_centroids() -> dict[str, tuple[float, float, str]]:
    with DISTRICTS_CSV.open(encoding="utf-8", newline="") as handle:
        rows = csv.DictReader(line for line in handle if not line.startswith("#"))
        return {
            row["district"].strip().casefold(): (float(row["lat"]), float(row["lon"]), row["district"].strip())
            for row in rows
        }


def district_centroid(name: str | None) -> tuple[float, float, str] | None:
    """(lat, lon, canonical name) for an exact, case-insensitive district name."""
    if not name or not name.strip():
        return None
    return _district_centroids().get(name.strip().casefold())

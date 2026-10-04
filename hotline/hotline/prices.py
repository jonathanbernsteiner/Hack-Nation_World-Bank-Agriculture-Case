"""Village coffee price median with a fallback chain (spec section 5).

Pure Python so it is unit-testable without a database. `load_sale_rows` only fetches
rows from the coffee_sale_prices view; it takes an explicit connection."""

import statistics
from collections.abc import Iterable, Mapping
from datetime import date, timedelta
from typing import Any, TypedDict

from hotline import config
from hotline.bands import BANDS, in_band
from hotline.numbers_sw import to_words

WINDOW_DAYS = 365
MIN_SALES = 3
MIN_FARMERS = 3
ROUND_TO_UGX = 50
MIN_SALES_FOR_QUARTILES = 5  # below this p25/p75 plus the median would reveal single prices
LEVELS = ("village", "parish", "sub_county", "district")
NATIONAL_SOURCE_URL = "https://ugandacoffee.go.ug/sites/default/files/2026-04/05-February%202026%20Report%20pptx.pptx_final.pdf"
NATIONAL_LEVEL = "national_reference"
# A reference from the UCDA monthly report for February 2026 (figures checked against the
# PDF), not a village median. There is no national red_cherry figure in the report, so a
# red_cherry caller can get median_ugx_per_kg None at national level.
NATIONAL_REFERENCE: dict[str, dict[str, Any]] = {
    "kiboko": {"median_ugx_per_kg": 5_750, "month": "2026-02", "source_url": NATIONAL_SOURCE_URL},
    "faq": {"median_ugx_per_kg": 12_250, "month": "2026-02", "source_url": NATIONAL_SOURCE_URL},
    "parchment": {"median_ugx_per_kg": 15_500, "month": "2026-02", "source_url": NATIONAL_SOURCE_URL},
    "drugar": {"median_ugx_per_kg": 14_500, "month": "2026-02", "source_url": NATIONAL_SOURCE_URL},
}
NATIONAL_AREA = "Uganda"



class Home(TypedDict, total=False):
    """The caller's home area (spec section 5)."""

    village_id: int | None
    village: str | None
    parish: str | None
    sub_county: str | None
    district: str | None


class SaleRow(TypedDict, total=False):
    """A row of the coffee_sale_prices view."""

    farmer_id: int
    is_synthetic: bool
    coffee_form: str
    sale_date: date
    amount_kg: float
    price_total: float
    village_id: int | None
    region: str | None
    district: str | None
    sub_county: str | None
    parish: str | None
    village: str | None


_SALE_COLUMNS = (
    "farmer_id, is_synthetic, coffee_form, sale_date, amount_kg, price_total, "
    "village_id, region, district, sub_county, parish, village"
)
_SALE_QUERY = (
    f"select {_SALE_COLUMNS} from coffee_sale_prices "
    "where district = %s and sale_date > %s and sale_date <= %s and (not is_synthetic or %s)"
)


def window_for(as_of: date) -> tuple[date, date]:
    """Inclusive 365-day window ending at as_of: a sale 365 days earlier is in, 366 out."""
    return as_of - timedelta(days=WINDOW_DAYS), as_of


def load_sale_rows(conn, district: str, as_of: date, include_synthetic: bool | None = None) -> list[dict]:
    """Rows of the home district in the window. Parameterised SQL; caller owns the connection."""
    if include_synthetic is None:
        include_synthetic = config.settings.price_include_synthetic
    start, end = window_for(as_of)
    exclusive_start = start - timedelta(days=1)
    with conn.cursor() as cur:
        cur.execute(_SALE_QUERY, (district, exclusive_start, end, include_synthetic))
        names = [col.name for col in cur.description]
        return [dict(zip(names, row, strict=True)) for row in cur.fetchall()]


def round_ugx(value: float) -> int:
    """Round half up to the nearest 50 UGX."""
    return int(value / ROUND_TO_UGX + 0.5) * ROUND_TO_UGX


def _quartiles(values: list[float]) -> tuple[float, float]:
    if len(values) < 2:
        return values[0], values[0]
    q = statistics.quantiles(values, n=4, method="inclusive")
    return q[0], q[2]


def _per_kg(row: Mapping[str, Any]) -> float | None:
    try:
        return float(row["price_total"]) / float(row["amount_kg"])
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        return None


def _usable_rows(rows: Iterable[SaleRow], home: Home, form: str, as_of: date, include_synthetic: bool):
    start, end = window_for(as_of)
    usable = []
    for row in rows:
        price = _per_kg(row)
        if price is None or str(row.get("coffee_form")) != form or not in_band(form, price):
            continue
        if not start <= row["sale_date"] <= end:
            continue
        if row.get("district") != home.get("district"):
            continue
        if row.get("is_synthetic") and not include_synthetic:
            continue
        usable.append((row, price))
    return usable


def _matches(row: Mapping, home: Home, level: str) -> bool:
    if level == "village":
        return home.get("village_id") is not None and row.get("village_id") == home["village_id"]
    if home.get(level) is None or row.get(level) != home[level]:
        return False
    # parish names repeat across sub-counties, so a parish match needs the same sub-county
    return level != "parish" or (home.get("sub_county") is not None and row.get("sub_county") == home["sub_county"])


def _result(form: str, level: str, area: str, matched: list[tuple[Mapping, float]], as_of: date) -> dict:
    prices = [price for _, price in matched]
    p25, p75 = _quartiles(prices) if len(prices) >= MIN_SALES_FOR_QUARTILES else (None, None)
    median = round_ugx(statistics.median(prices))
    start, end = window_for(as_of)
    return {
        "form": form,
        "median_ugx_per_kg": median,
        "p25": None if p25 is None else round_ugx(p25),
        "p75": None if p75 is None else round_ugx(p75),
        "n_sales": len(matched),
        "n_farmers": len({row["farmer_id"] for row, _ in matched}),
        "level": level,
        "area": area,
        "window": {"from": start.isoformat(), "to": end.isoformat()},
        "includes_synthetic": any(bool(row.get("is_synthetic")) for row, _ in matched),
        "median_words_sw": to_words(median),
    }


def _national(form: str, as_of: date) -> dict:
    start, end = window_for(as_of)
    ref = NATIONAL_REFERENCE.get(form)
    median = ref["median_ugx_per_kg"] if ref else None
    return {
        "form": form,
        "median_ugx_per_kg": median,
        "p25": None,
        "p75": None,
        "n_sales": 0,
        "n_farmers": 0,
        "level": NATIONAL_LEVEL,
        "area": NATIONAL_AREA,
        "window": {"from": start.isoformat(), "to": end.isoformat()},
        "includes_synthetic": False,
        "median_words_sw": to_words(median) if median else None,
        "is_reference": True,
        "reference_month": ref["month"] if ref else None,
        "reference_source_url": ref["source_url"] if ref else None,
    }


def _local_price(usable: list, home: Home, form: str, as_of: date) -> dict | None:
    for level in LEVELS:
        matched = [(row, price) for row, price in usable if _matches(row, home, level)]
        farmers = {row["farmer_id"] for row, _ in matched}
        if len(matched) >= MIN_SALES and len(farmers) >= MIN_FARMERS:
            area = home.get(level) if level != "village" else home.get("village")
            return _result(form, level, str(area), matched, as_of)
    return None


def village_price(
    rows: Iterable[SaleRow],
    home: Home,
    form: str,
    as_of: date,
    include_synthetic: bool | None = None,
) -> dict:
    """Median UGX/kg for `form` around `home` (keys village_id, village, parish,
    sub_county, district). Never includes farmer ids or individual prices."""
    if include_synthetic is None:
        include_synthetic = config.settings.price_include_synthetic
    usable = _usable_rows(rows, home, form, as_of, include_synthetic)
    return _local_price(usable, home, form, as_of) or _national(form, as_of)


def prices_for(
    rows: Iterable[SaleRow],
    home: Home,
    main_form: str,
    as_of: date,
    include_synthetic: bool | None = None,
) -> dict:
    """{'village_price': main form, 'other_prices': other forms with a local median}."""
    if include_synthetic is None:
        include_synthetic = config.settings.price_include_synthetic
    materialised = list(rows)
    main = village_price(materialised, home, main_form, as_of, include_synthetic)
    others = []
    for form in BANDS:
        if form == main_form:
            continue
        usable = _usable_rows(materialised, home, form, as_of, include_synthetic)
        local = _local_price(usable, home, form, as_of)
        if local:
            others.append({k: local[k] for k in ("form", "median_ugx_per_kg", "n_sales", "level", "median_words_sw")})
    return {"village_price": main, "other_prices": others}

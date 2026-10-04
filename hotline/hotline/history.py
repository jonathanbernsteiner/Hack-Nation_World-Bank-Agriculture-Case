"""A caller's own history (2 coffee years, last sales, past problems) and anonymous
nearby problem reports. The aggregations are pure functions over plain row dicts;
only load_history / load_nearby touch the database.

Privacy: the output never contains a buyer_name, a farmer name or a farmer id.
Nearby reports never count a group below MIN_NEARBY_FARMS farms and never include
the caller.

Row dicts (as returned by load_history / load_nearby) use these keys:
  entry_date (date), kind, crop, amount_kg, price_total, coffee_form, buyer_type,
  yield_amount, symptom, likely_disease, farmer_id, district, sub_county, parish.
"""

from collections import defaultdict
from datetime import date, timedelta
from typing import Any

from psycopg.rows import dict_row

COFFEE_YEAR_START_MONTH = 10  # coffee year runs October to September
COFFEE_YEARS_SHOWN = 2
PRICE_ROUNDING_UGX = 50
HISTORY_MONTHS = 24
NEARBY_DAYS = 30
MIN_NEARBY_FARMS = 2
DEFAULT_LIST_LENGTH = 3
NOT_SURE = "not_sure"

Row = dict[str, Any]

# The date rule matches the coffee_sale_prices view (#42).
_ENTRY_DATE_SQL = "coalesce(e.date_sold, (c.received_at at time zone 'Africa/Kampala')::date)"
# Location-login calls go to the review queue (spec 6, 7.9), so they stay out of history.
_REVIEWED_SQL = ("e.quote_verified is not false and coalesce(e.confidence, 1) >= 0.6 "
                 "and c.identified_by is distinct from 'location'")

_HISTORY_SQL = f"""
select e.id, {_ENTRY_DATE_SQL} as entry_date, e.kind, e.crop, e.amount_kg, e.price_total,
       e.coffee_form, e.buyer_type, e.yield_amount, e.unit, e.currency, e.symptom, e.likely_disease
from public.entries e join public.calls c on c.id = e.call_id
where e.farmer_id = %(farmer_id)s
  and {_REVIEWED_SQL}
  and {_ENTRY_DATE_SQL} >= %(since)s and {_ENTRY_DATE_SQL} <= %(as_of)s
"""

_NEARBY_SQL = f"""
select e.farmer_id, {_ENTRY_DATE_SQL} as entry_date, e.kind, e.symptom, e.likely_disease,
       v.district, v.sub_county, v.parish
from public.entries e
join public.calls c on c.id = e.call_id
join public.farmers f on f.id = e.farmer_id
join public.villages v on v.id = f.village_id
where e.kind = 'observation'
  and e.farmer_id <> %(farmer_id)s
  and v.district = %(district)s and v.sub_county = %(sub_county)s
  and {_REVIEWED_SQL}
  and {_ENTRY_DATE_SQL} >= %(since)s and {_ENTRY_DATE_SQL} <= %(as_of)s
"""


def _coffee_year_start(day: date) -> int:
    return day.year if day.month >= COFFEE_YEAR_START_MONTH else day.year - 1


def _coffee_year_label(start: int) -> str:
    return f"{start}/{(start + 1) % 100:02d}"


def _is_coffee(row: Row) -> bool:
    return (row.get("crop") or "").lower() == "coffee"


def _round_price(value: float) -> int:
    return int(round(value / PRICE_ROUNDING_UGX) * PRICE_ROUNDING_UGX)


def _is_ugx(row: Row) -> bool:
    return row.get("currency") == "UGX"


def _positive(value: Any) -> float | None:
    return float(value) if value is not None and float(value) > 0 else None


def _year_summary(start: int, rows: list[Row]) -> Row:
    harvest_kg = sum(float(r["yield_amount"]) for r in rows
                     if r["kind"] == "harvest" and r.get("unit") == "kg"
                     and r.get("yield_amount") is not None)
    kg_sales = [r for r in rows if r["kind"] == "sale" and _positive(r.get("amount_kg"))]
    sold_kg = sum(float(r["amount_kg"]) for r in kg_sales)
    priced = [r for r in kg_sales if r.get("price_total") is not None and _is_ugx(r)]
    priced_kg = sum(float(r["amount_kg"]) for r in priced)
    avg = _round_price(sum(float(r["price_total"]) for r in priced) / priced_kg) if priced_kg else None
    return {
        "year": _coffee_year_label(start),
        "harvest_kg": round(harvest_kg),
        "sold_kg": round(sold_kg),
        "avg_ugx_per_kg": avg,
    }


def coffee_years(rows: list[Row], as_of: date) -> list[Row]:
    """The 2 newest coffee years (Oct-Sep) with data among current, current-1 and current-2."""
    current = _coffee_year_start(as_of)
    starts = [current - offset for offset in range(COFFEE_YEARS_SHOWN + 1)]
    by_year: dict[int, list[Row]] = defaultdict(list)
    for row in rows:
        start = _coffee_year_start(row["entry_date"])
        if _is_coffee(row) and start in starts and row["entry_date"] <= as_of:
            by_year[start].append(row)
    with_data = [start for start in starts if by_year[start]]
    return [_year_summary(start, by_year[start]) for start in with_data[:COFFEE_YEARS_SHOWN]]


def _newest_first(rows: list[Row]) -> list[Row]:
    return sorted(rows, key=lambda r: (r["entry_date"], r.get("id") or 0), reverse=True)


def last_sales(rows: list[Row], n: int = DEFAULT_LIST_LENGTH) -> list[Row]:
    sales = _newest_first([r for r in rows if r["kind"] == "sale" and _is_coffee(r)])[:n]
    out = []
    for r in sales:
        kg = _positive(r.get("amount_kg"))
        price = r.get("price_total")
        out.append({
            "date": r["entry_date"].isoformat(),
            "form": r.get("coffee_form"),
            "kg": round(kg) if kg else None,
            "ugx_per_kg": _round_price(float(price) / kg) if kg and price is not None and _is_ugx(r) else None,
            "buyer": r.get("buyer_type"),  # type only, never buyer_name
        })
    return out


def problems(rows: list[Row], n: int = DEFAULT_LIST_LENGTH) -> list[Row]:
    observations = _newest_first([r for r in rows if r["kind"] == "observation"])[:n]
    return [{"date": r["entry_date"].isoformat(), "symptom": r.get("symptom"),
             "likely": r.get("likely_disease")} for r in observations]


def _problem_label(row: Row) -> str | None:
    likely = row.get("likely_disease")
    return likely if likely and likely != NOT_SURE else row.get("symptom")


def _qualifying_groups(rows: list[Row]) -> dict[str, int]:
    farms: dict[str, set] = defaultdict(set)
    for row in rows:
        label = _problem_label(row)
        if label:
            farms[label].add(row["farmer_id"])
    return {label: len(ids) for label, ids in farms.items() if len(ids) >= MIN_NEARBY_FARMS}


def nearby_reports(rows: list[Row], home: Row, as_of: date,
                   exclude_farmer_id: int | None = None) -> list[Row]:
    """Anonymous problem groups reported by >=2 other farms in the last 30 days.
    Each label is reported at the narrowest level (parish, then sub-county) that qualifies."""
    since = as_of - timedelta(days=NEARBY_DAYS)
    recent = [r for r in rows
              if r["kind"] == "observation" and since <= r["entry_date"] <= as_of
              and r["farmer_id"] != exclude_farmer_id
              and r.get("district") == home.get("district")
              and r.get("sub_county") == home.get("sub_county")]
    in_parish = [r for r in recent if r.get("parish") == home.get("parish")]
    parish_groups = _qualifying_groups(in_parish)
    subcounty_groups = {label: farms for label, farms in _qualifying_groups(recent).items()
                        if label not in parish_groups}
    reports = [{"likely": label, "farms": farms, "level": level, "last_days": NEARBY_DAYS}
               for level, groups in (("parish", parish_groups), ("sub_county", subcounty_groups))
               for label, farms in groups.items()]
    return sorted(reports, key=lambda r: (r["level"] != "parish", -r["farms"], r["likely"]))


def _first_of_month_ago(day: date, months: int) -> date:
    total = day.year * 12 + day.month - 1 - months
    year, month = divmod(total, 12)
    return date(year, month + 1, 1)


def _fetch(conn, sql: str, params: Row) -> list[Row]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql, params)
        return list(cur.fetchall())


def load_history(conn, farmer_id: int, as_of: date) -> list[Row]:
    """The caller's own entries (and only theirs) from the last 24 months."""
    return _fetch(conn, _HISTORY_SQL, {
        "farmer_id": farmer_id, "since": _first_of_month_ago(as_of, HISTORY_MONTHS), "as_of": as_of})


def load_nearby(conn, farmer_id: int, home: Row, as_of: date) -> list[Row]:
    """Observation entries of other farmers in the home sub-county, last 30 days."""
    return _fetch(conn, _NEARBY_SQL, {
        "farmer_id": farmer_id, "district": home["district"], "sub_county": home["sub_county"],
        "since": as_of - timedelta(days=NEARBY_DAYS), "as_of": as_of})


def summarize(conn, farmer_id: int, home: Row, as_of: date, totals_only: bool = False) -> Row:
    """History for the identify_farmer response. totals_only (location login) gives
    coffee_years only."""
    history = load_history(conn, farmer_id, as_of)
    years = coffee_years(history, as_of)
    if totals_only:
        return {"coffee_years": years}
    nearby = load_nearby(conn, farmer_id, home, as_of)
    return {
        "coffee_years": years,
        "last_sales": last_sales(history),
        "problems": problems(history),
        "nearby_reports": nearby_reports(nearby, home, as_of, exclude_farmer_id=farmer_id),
    }

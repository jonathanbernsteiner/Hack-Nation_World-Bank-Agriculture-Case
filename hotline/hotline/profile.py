"""The farmer profile the identity tools return (spec section 6, "found" shape without status).

Privacy: never returns farmer_id, pin_hash, the full name or any other farmer's data."""

from collections import Counter
from datetime import date, datetime, timedelta, timezone
from typing import Any

from hotline import history, prices

KAMPALA_UTC_OFFSET_HOURS = 3  # Uganda has no daylight saving time
DEFAULT_MAIN_FORM = "kiboko"
DEFAULT_MAIN_FORM_BY_TYPE = {"robusta": "kiboko", "arabica": "parchment"}
IDENTIFIED_BY_LOCATION = "location"

_FARMER_SQL = """
select f.name, f.is_synthetic, v.id, v.village, v.parish, v.sub_county, v.district, v.region,
       v.coffee_type
from farmers f left join villages v on v.id = f.village_id
where f.id = %s
"""

_FORMS_SQL = """
select coffee_form from entries
where farmer_id = %s and kind = 'sale' and crop = 'coffee' and coffee_form is not null
  and coffee_form <> 'other'
"""


def kampala_today() -> date:
    return (datetime.now(timezone.utc) + timedelta(hours=KAMPALA_UTC_OFFSET_HOURS)).date()


def first_name_of(full_name: str) -> str:
    """Only the first token ever leaves the server."""
    parts = (full_name or "").split()
    return parts[0] if parts else ""


def _main_form(conn: Any, farmer_id: int, coffee_type: str | None) -> str:
    forms = [row[0] for row in conn.execute(_FORMS_SQL, (farmer_id,)).fetchall()]
    if forms:
        return Counter(forms).most_common(1)[0][0]
    return DEFAULT_MAIN_FORM_BY_TYPE.get(coffee_type or "", DEFAULT_MAIN_FORM)


def _load_farmer(conn: Any, farmer_id: int) -> tuple[dict, dict, bool]:
    row = conn.execute(_FARMER_SQL, (farmer_id,)).fetchone()
    if row is None:
        raise LookupError("farmer not found")
    name, is_synthetic, village_id, village, parish, sub_county, district, region, coffee_type = row
    home = {
        "village_id": village_id,
        "village": village,
        "parish": parish,
        "sub_county": sub_county,
        "district": district,
    }
    public = {
        "first_name": first_name_of(name),
        "village": village,
        "parish": parish,
        "sub_county": sub_county,
        "district": district,
        "region": region,
        "coffee_type": coffee_type,
    }
    return home, public, bool(is_synthetic)


def _price_block(conn: Any, home: dict, main_form: str, as_of: date) -> dict:
    if not home.get("district"):
        return {"village_price": None, "other_prices": []}
    rows = prices.load_sale_rows(conn, home["district"], as_of)
    return prices.prices_for(rows, home, main_form, as_of)


def is_synthetic_farmer(conn: Any, farmer_id: int) -> bool:
    return _load_farmer(conn, farmer_id)[2]


def build_profile(conn: Any, farmer_id: int, *, as_of: date, identified_by: str) -> dict:
    home, public, _ = _load_farmer(conn, farmer_id)
    main_form = _main_form(conn, farmer_id, public["coffee_type"])
    is_location = identified_by == IDENTIFIED_BY_LOCATION
    summary = history.summarize(conn, farmer_id, home, as_of, totals_only=is_location)
    profile = {
        "identified_by": identified_by,
        "farmer": {**public, "main_form": main_form},
        **_price_block(conn, home, main_form, as_of),
        "history": {k: v for k, v in summary.items() if k != "nearby_reports"},
    }
    if not is_location:
        profile["nearby_reports"] = summary.get("nearby_reports", [])
    return profile

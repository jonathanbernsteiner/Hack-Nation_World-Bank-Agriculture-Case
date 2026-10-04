"""Offline checks for the map expansion plan: planted cases, price index, payload size. No database.

The warning rules mirror dashboard/lib/aggregate.ts (problemWarnings, priceWarnings) and types.ts.
"""

import json
from collections import Counter, defaultdict
from datetime import date, timedelta
from statistics import median

from farm_ledger.enums import CoffeeForm

from . import supabase as loader
from .anchors import anchor_price
from .map_expansion import (
    AS_OF, DEMO_DISTRICTS, LAST_ANCHOR_DAY, MAX_FARMERS, PIN_RANGE, PLANTED_PRICE_DISTRICT, SALES_START,
    WILT_DISTRICT, WILT_PARISH, Plan, plan_counts)

PROBLEM_WINDOW_DAYS, PROBLEM_MIN_FARMERS, PROBLEM_BASELINE_WEEKS = 30, 3, 12
PRICE_WINDOW_DAYS, PRICE_LOW_INDEX, MIN_SALES, MIN_FARMERS = 90, 0.85, 3, 3
YEAR_START = date(2025, 11, 1)  # dashboard "last 12 months" window: first of the month 11 months back
ID_OFFSET = 1000  # representative database ids for the payload estimate


def _index(price_per_kg: float, day: date, form: str) -> float:
    return price_per_kg / anchor_price(min(day, LAST_ANCHOR_DAY), CoffeeForm(form))


def sale_rows(plan: Plan) -> list[dict]:
    rows = []
    for c in plan.calls:
        for e in c.entries:
            if e["kind"] == "sale":
                per_kg = e["price_total"] / e["amount_kg"]
                rows.append({
                    "farmer": c.farmer, "village": plan.farmers[c.farmer].village, "date": e["date_sold"],
                    "form": e["coffee_form"], "ugx": per_kg, "kg": e["amount_kg"], "buyer": e["buyer_type"],
                    "index": _index(per_kg, e["date_sold"], e["coffee_form"])})
    return rows


def problem_rows(plan: Plan) -> list[dict]:
    return [{"farmer": c.farmer, "village": plan.farmers[c.farmer].village, "date": c.received_at.date(),
             "problem": e["likely_disease"]}
            for c in plan.calls for e in c.entries if e["kind"] == "observation"]


def _enough(sales: list[dict]) -> bool:
    return len(sales) >= MIN_SALES and len({s["farmer"] for s in sales}) >= MIN_FARMERS


def district_indexes(plan: Plan, sales: list[dict]) -> dict[str, float]:
    start = AS_OF - timedelta(days=PRICE_WINDOW_DAYS - 1)
    by_district = defaultdict(list)
    for s in sales:
        if start <= s["date"] <= AS_OF:
            by_district[plan.villages[s["village"]].district].append(s)
    return {d: median(s["index"] for s in rows) for d, rows in by_district.items() if _enough(rows)}


def buyer_indexes(sales: list[dict]) -> dict[str, float]:
    year = [s for s in sales if YEAR_START <= s["date"] <= AS_OF]
    return {b: median(s["index"] for s in year if s["buyer"] == b) for b in ("middleman", "cooperative", "other")}


def problem_warnings(plan: Plan, reports: list[dict], today: date) -> list[tuple[str, str, int, int]]:
    """(district/sub-county/parish, problem, recent farmers, baseline farmers) that the dashboard would warn about."""
    window_start = today - timedelta(days=PROBLEM_WINDOW_DAYS - 1)
    baseline_start = window_start - timedelta(weeks=PROBLEM_BASELINE_WEEKS)
    recent, baseline = defaultdict(set), defaultdict(set)
    for r in reports:
        if not baseline_start <= r["date"] <= today:
            continue
        v = plan.villages[r["village"]]
        key = ("/".join((v.district, v.sub_county, v.parish)), r["problem"])
        (recent if r["date"] >= window_start else baseline)[key].add(r["farmer"])
    return [(k[0], k[1], len(f), len(baseline[k])) for k, f in recent.items()
            if len(f) >= PROBLEM_MIN_FARMERS and len(f) > len(baseline[k])]


def stray_warning_days(plan: Plan, reports: list[dict]) -> int:
    """Days, from the first full window on, where a parish other than the planted one would warn."""
    first = SALES_START + timedelta(days=PROBLEM_WINDOW_DAYS - 1)
    days = (first + timedelta(days=n) for n in range((AS_OF - first).days + 1))
    return sum(1 for d in days for w in problem_warnings(plan, reports, d) if not w[0].endswith(f"/{WILT_PARISH}"))


def plan_failures(plan: Plan) -> list[str]:
    sales, reports = sale_rows(plan), problem_rows(plan)
    failures = []
    if any(v.district in DEMO_DISTRICTS for v in plan.villages):
        failures.append("a demo district is used")
    pins = [f.pin for f in plan.farmers]
    if len(set(pins)) != len(pins) or any(not PIN_RANGE[0] <= int(p) <= PIN_RANGE[1] for p in pins):
        failures.append("PINs are not unique or leave the allowed range")
    if len(pins) > MAX_FARMERS:
        failures.append("too many farmers for the 4-digit PIN space")
    warnings = problem_warnings(plan, reports, AS_OF)
    if [(w[0].split("/")[0], w[0].split("/")[2]) for w in warnings] != [(WILT_DISTRICT, WILT_PARISH)]:
        failures.append(f"expected exactly the Ibanda/{WILT_PARISH} problem cluster, got {[w[:2] for w in warnings]}")
    if stray_warning_days(plan, reports):
        failures.append("another parish formed a problem cluster in an earlier 30-day window")
    low = [d for d, i in district_indexes(plan, sales).items() if i <= PRICE_LOW_INDEX]
    if low != [PLANTED_PRICE_DISTRICT]:
        failures.append(f"expected only {PLANTED_PRICE_DISTRICT} as a low-price district, got {low}")
    return failures


def _payload_kb(plan: Plan, sales: list[dict], reports: list[dict]) -> tuple[int, int, int]:
    """Rows and approximate JSON size of the dashboard payload (sales + problems + farmers + villages)."""
    docs = {
        "sales": [{"farmerId": ID_OFFSET + s["farmer"], "villageId": ID_OFFSET + s["village"], "date": s["date"].isoformat(),
                   "form": s["form"], "ugxPerKg": round(s["ugx"]), "kg": s["kg"], "buyerType": s["buyer"]} for s in sales],
        "problems": [{"farmerId": ID_OFFSET + r["farmer"], "villageId": ID_OFFSET + r["village"],
                      "date": r["date"].isoformat(), "problem": r["problem"]} for r in reports],
        "farmers": [{"id": ID_OFFSET + i, "firstName": f.name.split()[0], "villageId": ID_OFFSET + f.village,
                     "registeredAt": f.created_at.isoformat(), "callCount": 5, "lastCallAt": f.created_at.isoformat(),
                     "isSynthetic": True} for i, f in enumerate(plan.farmers)],
        "villages": [{"id": ID_OFFSET + i, "region": v.region, "district": v.district, "subCounty": v.sub_county,
                      "parish": v.parish, "village": v.village, "lat": v.lat, "lon": v.lon,
                      "coffeeType": v.coffee_type, "isVerified": True, "isSynthetic": True}
                     for i, v in enumerate(plan.villages)],
    }
    return len(docs["sales"]), len(docs["problems"]), len(json.dumps(docs)) // 1024


def _registrations_by_month(plan: Plan) -> list[int]:
    months = Counter(f.created_at.strftime("%Y-%m") for f in plan.farmers)
    return [months[m] for m in sorted(months)]


def describe(plan: Plan, failures: list[str]) -> str:
    sales, reports = sale_rows(plan), problem_rows(plan)
    indexes = district_indexes(plan, sales)
    buyers = buyer_indexes(sales)
    ranked = sorted(indexes.items(), key=lambda kv: kv[1])
    per_farmer = Counter(s["farmer"] for s in sales)
    parish_sizes = Counter((v.district, v.sub_county, v.parish) for v in plan.villages)
    per_district = Counter(plan.villages[f.village].district for f in plan.farmers)
    sale_rows_n, problem_rows_n, kb = _payload_kb(plan, sales, reports)
    gap = (buyers["middleman"] / buyers["cooperative"] - 1) * 100
    return "\n".join([
        loader.format_counts("would insert", plan_counts(plan)),
        f"parishes={len(parish_sizes)} farmers/village={min(v.farmer_count for v in plan.villages)}-"
        f"{max(v.farmer_count for v in plan.villages)} sales/farmer={min(per_farmer.values())}-{max(per_farmer.values())}"
        f" problem reports={len(reports)} (1 per {len(plan.farmers) / len(reports):.1f} farmers)",
        f"registrations per month (oldest to newest): {_registrations_by_month(plan)}",
        f"median price index, last 12 months: middleman={buyers['middleman']:.3f} cooperative={buyers['cooperative']:.3f}"
        f" other={buyers['other']:.3f} (middleman {gap:+.0f}% vs cooperative)",
        "lowest district indexes, last 90 days: " + ", ".join(f"{d}={i:.3f}" for d, i in ranked[:5]),
        f"highest: {ranked[-1][0]}={ranked[-1][1]:.3f}; low-price districts (<= {PRICE_LOW_INDEX}): "
        f"{[d for d, i in ranked if i <= PRICE_LOW_INDEX]}",
        f"problem warnings today: {problem_warnings(plan, reports, AS_OF)}; stray warning days since "
        f"{SALES_START + timedelta(days=PROBLEM_WINDOW_DAYS - 1)}: {stray_warning_days(plan, reports)}",
        f"dashboard payload estimate: {sale_rows_n} sale rows + {problem_rows_n} problem rows, ~{kb} KB JSON "
        f"(all rows incl. farmers and villages)",
        loader.format_counts("farmers by district", per_district),
        "checks: " + ("OK" if not failures else "FAILED: " + "; ".join(failures)),
    ])

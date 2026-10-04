"""GET /demo/farmer/{id}: one farmer's profile for the judge screen, behind the same Basic auth as /demo.

Map of the farm (Leaflet + OpenStreetMap), yield and income per coffee year, monthly sales,
price received against the village median, every record with its quote, recent call
transcripts, and a sentiment read loaded separately from /demo/farmer/{id}/sentiment.

Never selects pin_hash, PINs, phone numbers or buyer names. Every value is escaped by `_e`."""

import json
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

from hotline import db, history, security, sentiment
from hotline.routes.demo import KAMPALA_TZ, _e, _kampala, _num, _page, _rows, _transcript, needs_review

router = APIRouter()

CALLS_SHOWN = 10
MONTHS_SHOWN = 24
LEAFLET = "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4"
CHART_JS = "https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"

_FARMER_SQL = (
    "select f.id, f.name, f.is_synthetic, f.lat, f.lon, v.id as village_id, v.village, "
    "v.parish, v.sub_county, v.district, v.region, v.coffee_type, v.lat as village_lat, v.lon as village_lon, "
    "(select min(received_at) from calls where farmer_id = f.id) as first_call_at "
    "from farmers f left join villages v on v.id = f.village_id where f.id = %s"
)
_ENTRIES_SQL = (
    "select e.id, e.call_id, coalesce(e.date_sold, (c.received_at at time zone 'Africa/Kampala')::date) as entry_date, "
    "e.kind, e.crop, e.coffee_form, e.amount, e.unit, e.amount_kg, e.price_total, e.currency, e.buyer_type, "
    "e.paid_how, e.yield_amount, e.symptom, e.likely_disease, e.description, e.evidence_quote, e.quote_verified, "
    "e.confidence, c.identified_by from entries e join calls c on c.id = e.call_id "
    "where e.farmer_id = %s order by entry_date desc, e.id desc"
)
_CALLS_SQL = (
    "select id, received_at, status, identified_by, is_synthetic, transcript_lines, duration_secs "
    "from calls where farmer_id = %s order by received_at desc limit %s"
)


# --- data -------------------------------------------------------------------------------------


def _counts(entry: dict) -> bool:
    """Same rule as the agent's history (history._REVIEWED_SQL): flagged entries stay out of totals."""
    return not needs_review(entry, entry)


def _sale_kg(entry: dict) -> float | None:
    kg = entry.get("amount_kg") or (entry.get("amount") if entry.get("unit") == "kg" else None)
    return float(kg) if kg and float(kg) > 0 else None


def _coffee_sales(entries: list[dict]) -> list[dict]:
    return [
        e for e in entries
        if e["kind"] == "sale" and _counts(e) and _sale_kg(e) and e.get("price_total") is not None
        and e.get("currency") == "UGX" and ((e.get("crop") or "coffee").lower() == "coffee" or e.get("coffee_form"))
    ]


def yearly(entries: list[dict]) -> list[dict]:
    """Per coffee year (Oct-Sep), oldest first: harvest kg, sold kg, income and average UGX/kg."""
    counted = [e for e in entries if _counts(e)]
    starts = sorted({history._coffee_year_start(e["entry_date"]) for e in counted})
    out = []
    for start in starts:
        rows = [e for e in counted if history._coffee_year_start(e["entry_date"]) == start]
        summary = history._year_summary(start, rows)
        summary["income_ugx"] = round(sum(float(e["price_total"]) for e in _coffee_sales(rows)))
        out.append(summary)
    return out


def monthly(entries: list[dict], today: date, months: int = MONTHS_SHOWN) -> dict:
    """The last `months` calendar months: kg sold and income per month."""
    keys = []
    year, month = today.year, today.month
    for _ in range(months):
        keys.append(f"{year:04d}-{month:02d}")
        year, month = (year, month - 1) if month > 1 else (year - 1, 12)
    keys.reverse()
    kg = dict.fromkeys(keys, 0.0)
    income = dict.fromkeys(keys, 0.0)
    for sale in _coffee_sales(entries):
        key = sale["entry_date"].strftime("%Y-%m")
        if key in kg:
            kg[key] += _sale_kg(sale)
            income[key] += float(sale["price_total"])
    return {"labels": keys, "kg": [round(kg[k]) for k in keys], "income": [round(income[k]) for k in keys]}


def price_points(entries: list[dict]) -> list[dict]:
    """Each sale's UGX/kg, oldest first."""
    sales = sorted(_coffee_sales(entries), key=lambda e: (e["entry_date"], e["id"]))
    return [{"x": s["entry_date"].isoformat(), "y": round(float(s["price_total"]) / _sale_kg(s))} for s in sales]


def _median(conn, farmer: dict, form: str, today: date) -> dict | None:
    if not farmer.get("district"):
        return None
    try:
        from hotline import prices
    except ImportError:
        return None
    return prices.village_price(prices.load_sale_rows(conn, farmer["district"], today), farmer, form, today)


def main_form(entries: list[dict]) -> str:
    forms: dict[str, float] = {}
    for sale in _coffee_sales(entries):
        if sale.get("coffee_form"):
            forms[sale["coffee_form"]] = forms.get(sale["coffee_form"], 0) + _sale_kg(sale)
    return max(forms, key=forms.get) if forms else "kiboko"


def load_profile(conn, farmer_id: int, today: date | None = None) -> dict | None:
    today = today or datetime.now(KAMPALA_TZ).date()
    found = _rows(conn, _FARMER_SQL, (farmer_id,))
    if not found:
        return None
    farmer = found[0]
    entries = _rows(conn, _ENTRIES_SQL, (farmer_id,))
    calls = _rows(conn, _CALLS_SQL, (farmer_id, CALLS_SHOWN))
    form = main_form(entries)
    return {"farmer": farmer, "entries": entries, "calls": calls, "today": today,
            "form": form, "median": _median(conn, farmer, form, today)}


# --- rendering --------------------------------------------------------------------------------


def _tile(label: str, value: str, note: str = "") -> str:
    note_html = f"<div class=note>{_e(note)}</div>" if note else ""
    return f"<div class=tile><div class=label>{_e(label)}</div><div class=value>{_e(value)}</div>{note_html}</div>"


def _tiles(view: dict, years: list[dict]) -> str:
    sales = _coffee_sales(view["entries"])
    kg = sum(_sale_kg(s) for s in sales)
    income = sum(float(s["price_total"]) for s in sales)
    harvests = [y["harvest_kg"] for y in years if y["harvest_kg"]]
    median = view.get("median") or {}
    her_avg = round(income / kg) if kg else None
    vs = ""
    if her_avg and median.get("median_ugx_per_kg"):
        diff = her_avg - float(median["median_ugx_per_kg"])
        vs = f"{'+' if diff >= 0 else '-'}{_num(abs(diff))} vs {median.get('level') or 'local'} median"
    return "<div class=tiles>" + "".join([
        _tile("Average harvest", f"{_num(sum(harvests) / len(harvests))} kg/yr" if harvests else "n/a",
              f"{len(harvests)} coffee years"),
        _tile("Coffee sold", f"{_num(kg)} kg", f"{len(sales)} sales"),
        _tile("Income from coffee", f"{_num(income)} UGX", "all recorded sales"),
        _tile("Her average price", f"{_num(her_avg)} UGX/kg" if her_avg else "n/a", vs),
        _tile(f"Village median ({view['form']})",
              f"{_num(median['median_ugx_per_kg'])} UGX/kg" if median.get("median_ugx_per_kg") else "n/a",
              f"n={median.get('n_sales')}, {median.get('area') or ''}" if median.get("n_sales") else ""),
        _tile("Calls", str(len(view["calls"])) + ("+" if len(view["calls"]) == CALLS_SHOWN else ""),
              f"last {_kampala(view['calls'][0]['received_at'])}" if view["calls"] else ""),
    ]) + "</div>"


def _record(entry: dict, latest_call_id: Any) -> str:
    new = " <span class=new>NEW</span>" if entry["call_id"] == latest_call_id else ""
    flag = " <span class=flag>REVIEW</span>" if needs_review(entry, entry) else ""
    kg = _sale_kg(entry)
    what = ", ".join(_e(x) for x in (
        entry.get("coffee_form") or entry.get("crop"),
        f"{_num(kg)} kg" if kg else None,
        f"{_num(entry['yield_amount'])} {entry.get('unit') or ''} harvested" if entry.get("yield_amount") else None,
        f"{_num(entry['price_total'])} {entry.get('currency') or ''}" if entry.get("price_total") is not None else None,
        f"{_num(float(entry['price_total']) / kg)}/kg" if kg and entry.get("price_total") is not None else None,
        (entry.get("buyer_type") or "").replace("_", " ") or None,
        (entry.get("paid_how") or "").replace("_", " ") or None,
        (entry.get("likely_disease") or "").replace("_", " ") or entry.get("symptom"),
    ) if x)
    mark = {True: "&#10003;", False: "&#10007;"}.get(entry.get("quote_verified"), "")
    quote = f"<div class=quote>{mark} &ldquo;{_e(entry['evidence_quote'])}&rdquo;</div>" if entry.get("evidence_quote") else ""
    return (f"<tr{' class=hl' if new else ''}><td>{_e(entry['entry_date'].isoformat())}</td>"
            f"<td><b>{_e(entry['kind'])}</b>{new}{flag}</td><td>{what}{quote}</td></tr>")


def _calls(calls: list[dict]) -> str:
    if not calls:
        return "<p class=muted>No calls yet.</p>"
    blocks = []
    for index, call in enumerate(calls):
        badge = " <span class=synthetic>SYNTHETIC</span>" if call.get("is_synthetic") else ""
        mood = f" <span class=mood data-call={_e(call['id'])}></span>"
        blocks.append(
            f"<details{' open' if index == 0 else ''}><summary>{_e(_kampala(call.get('received_at')))} &middot; "
            f"{_e(call.get('status'))} &middot; by {_e(call.get('identified_by') or 'n/a')}{badge}{mood}</summary>"
            f"{_transcript(call)}</details>"
        )
    return "".join(blocks)


def _json_script(data: Any) -> str:
    text = json.dumps(data, default=str).replace("</", "<\\/")
    return f"<script type=application/json id=profile-data>{text}</script>"


_PROFILE_CSS = (
    "<style>.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:8px;margin:12px 0}"
    ".tile{border:1px solid #ddd;border-radius:8px;padding:8px 12px}.label,.note{color:#777;font-size:12px}"
    ".value{font-size:20px;font-weight:600}.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}"
    "@media(max-width:800px){.grid{grid-template-columns:1fr}}#map{height:300px;border-radius:8px}"
    ".box{border:1px solid #ddd;border-radius:8px;padding:8px 12px}.new{background:#bbf7d0;padding:1px 6px;"
    "border-radius:4px;font-size:12px}tr.hl{background:#f0fdf4}details{border:1px solid #ddd;border-radius:8px;"
    "padding:6px 12px;margin:8px 0}summary{cursor:pointer}.mood{font-size:12px;padding:1px 6px;border-radius:4px}"
    ".positive{background:#bbf7d0}.neutral{background:#e5e7eb}.mixed{background:#fde68a}.negative{background:#fecaca}"
    ".chart{position:relative;height:280px;min-width:0}.grid>div{min-width:0}</style>"
)

_PROFILE_JS = """
<script>
(function () {
  var d = JSON.parse(document.getElementById('profile-data').textContent);
  if (window.L && d.lat != null) {
    var map = L.map('map').setView([d.lat, d.lon], 13);
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors'}).addTo(map);
    L.marker([d.lat, d.lon]).addTo(map).bindPopup(d.place).openPopup();
  } else { document.getElementById('map').textContent = 'No location on file.'; }
  if (window.Chart) {
    Chart.defaults.maintainAspectRatio = false;
    new Chart(document.getElementById('yearly'), {data: {labels: d.years.map(function (y) { return y.year; }),
      datasets: [
        {type: 'bar', label: 'Harvest (kg)', data: d.years.map(function (y) { return y.harvest_kg; }), yAxisID: 'kg', backgroundColor: '#86efac'},
        {type: 'bar', label: 'Sold (kg)', data: d.years.map(function (y) { return y.sold_kg; }), yAxisID: 'kg', backgroundColor: '#60a5fa'},
        {type: 'line', label: 'Income (UGX)', data: d.years.map(function (y) { return y.income_ugx; }), yAxisID: 'ugx', borderColor: '#f59e0b', backgroundColor: '#f59e0b'}]},
      options: {scales: {kg: {position: 'left', title: {display: true, text: 'kg'}},
        ugx: {position: 'right', beginAtZero: true, grid: {drawOnChartArea: false}, title: {display: true, text: 'UGX'}}}}});
    new Chart(document.getElementById('monthly'), {data: {labels: d.monthly.labels, datasets: [
        {type: 'bar', label: 'Sold (kg)', data: d.monthly.kg, yAxisID: 'kg', backgroundColor: '#60a5fa'},
        {type: 'line', label: 'Income (UGX)', data: d.monthly.income, yAxisID: 'ugx', borderColor: '#f59e0b', backgroundColor: '#f59e0b', tension: 0.2}]},
      options: {scales: {kg: {position: 'left', beginAtZero: true}, ugx: {position: 'right', beginAtZero: true, grid: {drawOnChartArea: false}}}}});
    var sets = [{type: 'line', label: 'Her price (UGX/kg)', data: d.prices.map(function (p) { return p.y; }),
      borderColor: '#2563eb', backgroundColor: '#2563eb', tension: 0.2}];
    if (d.median) sets.push({type: 'line', label: 'Village median', data: d.prices.map(function () { return d.median; }),
      borderColor: '#9ca3af', borderDash: [6, 4], pointRadius: 0});
    new Chart(document.getElementById('prices'), {data: {labels: d.prices.map(function (p) { return p.x; }), datasets: sets}});
  }
  var box = document.getElementById('sentiment');
  fetch(d.sentimentUrl, {credentials: 'same-origin'}).then(function (r) { return r.json(); }).then(function (s) {
    if (!s || !s.overall) { box.textContent = (s && s.message) || 'Sentiment unavailable.'; return; }
    box.innerHTML = '';
    var tag = document.createElement('span'); tag.className = 'mood ' + s.overall;
    tag.textContent = s.overall + ' (' + s.score.toFixed(2) + ')';
    var text = document.createElement('p'); text.textContent = s.summary;
    box.appendChild(tag); box.appendChild(text);
    (s.calls || []).forEach(function (c) {
      var el = document.querySelector('.mood[data-call="' + c.id + '"]');
      if (el) { el.className = 'mood ' + c.sentiment; el.textContent = c.sentiment; el.title = c.reason; }
    });
  }).catch(function () { box.textContent = 'Sentiment unavailable.'; });
})();
</script>
"""


def render_profile(view: dict) -> str:
    farmer, entries, calls = view["farmer"], view["entries"], view["calls"]
    years = yearly(entries)
    place = ", ".join(x for x in (farmer.get("village"), farmer.get("parish"), farmer.get("sub_county"),
                                  farmer.get("district"), farmer.get("region")) if x)
    lat = farmer.get("lat") if farmer.get("lat") is not None else farmer.get("village_lat")
    lon = farmer.get("lon") if farmer.get("lon") is not None else farmer.get("village_lon")
    median = (view.get("median") or {}).get("median_ugx_per_kg")
    data = {
        "lat": lat, "lon": lon, "place": f"{farmer['name']}, {place}", "years": years,
        "monthly": monthly(entries, view["today"]), "prices": price_points(entries),
        "median": float(median) if median else None, "sentimentUrl": f"/demo/farmer/{farmer['id']}/sentiment",
    }
    badge = " <span class=synthetic>SYNTHETIC</span>" if farmer.get("is_synthetic") else ""
    latest = calls[0]["id"] if calls else None
    records = "".join(_record(e, latest) for e in entries) or "<tr><td class=muted>No records yet.</td></tr>"
    body = (
        f"<p><a href=/demo>&larr; All calls</a></p>"
        f"<p>{_e(place)}{badge} &middot; {_e(farmer.get('coffee_type') or 'coffee')} &middot; mostly {_e(view['form'])}"
        f" &middot; first call {_e(_kampala(farmer.get('first_call_at'))[:10] or 'n/a')}</p>"
        f"{_tiles(view, years)}"
        f"<div class=grid><div><h2>Farm location</h2><div id=map></div></div>"
        f"<div><h2>Sentiment</h2><div class=box id=sentiment>Reading her recent calls&hellip;</div>"
        f"<h2>Yield and income by coffee year</h2><div class=chart><canvas id=yearly></canvas></div></div></div>"
        f"<div class=grid><div><h2>Monthly sales</h2><div class=chart><canvas id=monthly></canvas></div></div>"
        f"<div><h2>Price received vs village median</h2><div class=chart><canvas id=prices></canvas></div></div></div>"
        f"<h2>Records</h2><table>{records}</table>"
        f"<h2>Recent calls</h2>{_calls(calls)}"
        f"{_json_script(data)}"
    )
    head = (f"<link rel=stylesheet href={LEAFLET}/leaflet.min.css>{_PROFILE_CSS}"
            f"<script src={LEAFLET}/leaflet.min.js></script><script src={CHART_JS}></script>")
    page = _page(farmer["name"], body + _PROFILE_JS, refresh=False)
    return page.replace("</head>", head + "</head>", 1)


# --- routes -----------------------------------------------------------------------------------


def _load(farmer_id: int) -> dict | None:
    with db.connect() as conn:
        return load_profile(conn, farmer_id)


def _load_calls(farmer_id: int) -> list[dict]:
    with db.connect() as conn:
        return _rows(conn, _CALLS_SQL, (farmer_id, CALLS_SHOWN))


@router.get("/demo/farmer/{farmer_id}", response_class=HTMLResponse,
            dependencies=[Depends(security.require_demo_basic_auth)])
def farmer_page(farmer_id: int) -> HTMLResponse:
    view = _load(farmer_id)
    if view is None:
        raise HTTPException(status_code=404, detail="farmer not found")
    return HTMLResponse(render_profile(view))


@router.get("/demo/farmer/{farmer_id}/sentiment", dependencies=[Depends(security.require_demo_basic_auth)])
def farmer_sentiment(farmer_id: int) -> JSONResponse:
    try:
        result = sentiment.analyze(farmer_id, _load_calls(farmer_id))
    except Exception:
        return JSONResponse({"message": "Sentiment unavailable right now."})
    return JSONResponse(result or {"message": "No call transcripts yet."})

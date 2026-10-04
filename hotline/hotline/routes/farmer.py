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
from hotline.routes import demo
from hotline.routes.demo import KAMPALA_TZ, _e, _kampala, _num, _page, _rows, needs_review

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
    labels = [date(int(k[:4]), int(k[5:]), 1).strftime("%b %y") for k in keys]
    return {"labels": labels, "kg": [round(kg[k]) for k in keys], "income": [round(income[k]) for k in keys]}


def price_points(entries: list[dict]) -> list[dict]:
    """Each sale's UGX/kg, oldest first."""
    sales = sorted(_coffee_sales(entries), key=lambda e: (e["entry_date"], e["id"]))
    return [{"x": s["entry_date"].strftime("%b %y"), "y": round(float(s["price_total"]) / _sale_kg(s))} for s in sales]


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
            "form": form, "median": _median(conn, farmer, form, today), "farmers": demo.recent_farmers(conn)}


# --- rendering --------------------------------------------------------------------------------


def _kpis(view: dict, years: list[dict]) -> str:
    sales = _coffee_sales(view["entries"])
    kg = sum(_sale_kg(s) for s in sales)
    income = sum(float(s["price_total"]) for s in sales)
    harvests = [y["harvest_kg"] for y in years if y["harvest_kg"]]
    median = view.get("median") or {}
    her_avg = round(income / kg) if kg else None
    diff = her_avg - float(median["median_ugx_per_kg"]) if her_avg and median.get("median_ugx_per_kg") else None
    return "<section class=kpis>" + "".join([
        demo.kpi("Average harvest", "leaf", f"{_num(sum(harvests) / len(harvests))} kg" if harvests else "n/a",
                 f"{len(harvests)} coffee years", "on record"),
        demo.kpi("Coffee sold", "box", f"{_num(kg)} kg", f"{len(sales)}", "sales"),
        demo.kpi("Earned from coffee", "coins", f"{demo.compact(income)} UGX", f"{_num(income)}", "UGX in total"),
        demo.kpi("Her average price", "trend", f"{_num(her_avg)} UGX/kg" if her_avg else "n/a",
                 f"{'+' if diff >= 0 else '-'}{_num(abs(diff))}" if diff is not None else "",
                 "vs village median" if diff is not None else ""),
        demo.kpi("Village median", "check",
                 f"{_num(median['median_ugx_per_kg'])} UGX/kg" if median.get("median_ugx_per_kg") else "n/a",
                 f"{median.get('n_sales')} sales" if median.get("n_sales") else "",
                 f"of {view['form']} in {median.get('area')}" if median.get("n_sales") else ""),
    ]) + "</section>"


def _record(entry: dict, latest_call_id: Any) -> str:
    new = entry["call_id"] == latest_call_id
    kind = demo._kind(entry)
    head, details = demo._facts(entry)
    pills = (demo._pill("New", "new") if new else "") + (demo._pill("Needs review", "warn") if needs_review(entry, entry) else "")
    quote = entry.get("evidence_quote")
    mark = {True: "<span class=ok-mark>&#10003;</span> ", False: "<span class=bad-mark>&#10007;</span> "}.get(entry.get("quote_verified"), "")
    sub = " ".join(details) or demo.KIND_LABELS.get(kind, "Record")
    if quote:
        sub += f"<span class=rq>{mark}&ldquo;{_e(quote)}&rdquo;</span>"
    return (f"<li class='row k-{kind}{' hl' if new else ''}'><span class=avatar><i class=dot></i></span>"
            f"<span class=row-main><b>{head}</b><small>{sub}</small></span>"
            f"<span class=row-side><b>{demo.KIND_LABELS.get(kind, 'Record')}</b>"
            f"<small>{_e(entry['entry_date'].strftime('%d %b %Y'))}</small></span>{pills}</li>")


def _calls(calls: list[dict], entries: list[dict]) -> str:
    if not calls:
        return "<p class=muted>No calls yet.</p>"
    by_call: dict[Any, list[dict]] = {}
    for entry in entries:
        by_call.setdefault(entry["call_id"], []).append(entry)
    blocks = []
    for index, call in enumerate(calls):
        mood = f"<span class=mood data-call={_e(call['id'])}></span>"
        status, tone = demo.STATUS_LABELS.get(call.get("status"), (call.get("status") or "", ""))
        blocks.append(
            f"<details class='card pcall'{' open' if index == 0 else ''}><summary><time>{_e(demo._when(call.get('received_at')))}</time>"
            f"{demo._pill(status, tone)}{mood}{demo._synthetic(call)}</summary>"
            f"{demo._transcript(call, by_call.get(call['id'], []))}</details>"
        )
    return "".join(blocks)


def _json_script(data: Any) -> str:
    text = json.dumps(data, default=str).replace("</", "<\\/")
    return f"<script type=application/json id=profile-data>{text}</script>"


_PROFILE_CSS = """<style>
.hero{display:flex;align-items:center;gap:16px}
.hero .avatar{width:56px;height:56px;border-radius:16px;font-size:24px}
#map{height:300px;border-radius:12px;margin:6px 14px 14px}
.gauge-wrap{display:flex;flex-direction:column;align-items:center;padding:4px 18px 16px}
.gauge{width:100%;max-width:340px}
.gauge-label{margin-top:-58px;text-align:center}
.gauge-value{font-size:30px;font-weight:600;letter-spacing:-.01em;text-transform:capitalize}
.gauge-note{color:var(--muted);font-size:12.5px}
.gauge-ends{display:flex;justify-content:space-between;width:100%;max-width:340px;color:var(--muted);font-size:12.5px;margin-top:12px}
.summary{margin:14px 0 0;text-align:center;max-width:52ch;color:#3A3A52}
.mood{font-size:12px;padding:2px 9px;border-radius:999px;text-transform:capitalize;font-weight:500}
.mood:empty{display:none}
.positive{background:var(--green-tint);color:var(--green)}.neutral{background:#F1F0F6;color:#4A4A62}
.mixed{background:var(--amber-tint);color:var(--amber)}.negative{background:var(--red-tint);color:var(--red)}
.pill.new{background:var(--purple);color:#fff}
.row.hl{background:#F6F4FF}
.row .avatar .dot{width:12px;height:12px}
.k-observation .avatar{background:var(--red-tint)}.k-harvest .avatar{background:var(--peach-tint)}
.pcall{margin-bottom:10px;overflow:hidden}
.pcall summary{cursor:pointer;padding:12px 18px;display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.pcall time{font-weight:600;margin-right:4px}
.pcall .convo{border-top:1px solid var(--line)}
.records-card .list{max-height:262px;overflow:auto}
.rq{display:block;font-style:italic;color:#4A4A62;white-space:normal}
</style>"""

_PROFILE_JS = """
<script>
(function () {
  var d = JSON.parse(document.getElementById('profile-data').textContent);
  if (window.L && d.lat != null) {
    var map = L.map('map', {scrollWheelZoom: false}).setView([d.lat, d.lon], 13);
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors'}).addTo(map);
    L.circleMarker([d.lat, d.lon], {radius: 10, color: '#fff', weight: 3, fillColor: '#5B4FE0', fillOpacity: 1})
      .addTo(map).bindPopup(d.place).openPopup();
  } else { document.getElementById('map').textContent = 'No location on file.'; }
  if (window.Chart) {
    Chart.defaults.maintainAspectRatio = false;
    Chart.defaults.animation = false;
    Chart.defaults.font.family = "'Plus Jakarta Sans', system-ui, sans-serif";
    Chart.defaults.color = '#6E6E85';
    Chart.defaults.plugins.legend.display = false;
    var grid = {color: '#F1F0F6'};
    new Chart(document.getElementById('yearly'), {data: {labels: d.years.map(function (y) { return y.year; }),
      datasets: [
        {type: 'bar', label: 'Harvest (kg)', data: d.years.map(function (y) { return y.harvest_kg; }), yAxisID: 'kg', backgroundColor: '#F4B98A', borderRadius: 6, maxBarThickness: 34},
        {type: 'bar', label: 'Sold (kg)', data: d.years.map(function (y) { return y.sold_kg; }), yAxisID: 'kg', backgroundColor: '#5B4FE0', borderRadius: 6, maxBarThickness: 34},
        {type: 'line', label: 'Earned (UGX)', data: d.years.map(function (y) { return y.income_ugx; }), yAxisID: 'ugx', borderColor: '#1E9E5A', backgroundColor: '#1E9E5A', borderWidth: 2, tension: 0.4}]},
      options: {interaction: {mode: 'index', intersect: false}, scales: {x: {grid: {display: false}}, kg: {beginAtZero: true, grid: grid},
        ugx: {position: 'right', beginAtZero: true, grid: {drawOnChartArea: false}}}}});
    new Chart(document.getElementById('monthly'), {data: {labels: d.monthly.labels, datasets: [
        {type: 'bar', label: 'Sold (kg)', data: d.monthly.kg, yAxisID: 'kg', backgroundColor: '#5B4FE0', borderRadius: 4, maxBarThickness: 18},
        {type: 'bar', label: 'Earned (UGX)', data: d.monthly.income, yAxisID: 'ugx', backgroundColor: '#F4B98A', borderRadius: 4, maxBarThickness: 18}]},
      options: {interaction: {mode: 'index', intersect: false}, scales: {x: {grid: {display: false}, ticks: {maxRotation: 0, autoSkipPadding: 12}}, kg: {beginAtZero: true, grid: grid},
        ugx: {position: 'right', beginAtZero: true, grid: {drawOnChartArea: false}}}}});
    var sets = [{type: 'line', label: 'Her price (UGX/kg)', data: d.prices.map(function (p) { return p.y; }),
      borderColor: '#5B4FE0', backgroundColor: '#5B4FE0', borderWidth: 2, tension: 0.4, pointRadius: 3}];
    if (d.median) sets.push({type: 'line', label: 'Village median now', data: d.prices.map(function () { return d.median; }),
      borderColor: '#F4B98A', borderDash: [6, 4], borderWidth: 2, pointRadius: 0});
    new Chart(document.getElementById('prices'), {data: {labels: d.prices.map(function (p) { return p.x; }), datasets: sets},
      options: {interaction: {mode: 'index', intersect: false}, scales: {x: {grid: {display: false}, ticks: {maxRotation: 0, autoSkipPadding: 12}}, y: {grid: grid}}}});
  }
  function gauge(score) {
    var segs = 22, filled = Math.round((score + 1) / 2 * segs), out = '';
    for (var i = 0; i < segs; i++) {
      var a = Math.PI - (i + 0.5) * Math.PI / segs, c = Math.cos(a), s = Math.sin(a);
      out += '<line x1="' + (150 + 92 * c).toFixed(1) + '" y1="' + (150 - 92 * s).toFixed(1) + '" x2="' + (150 + 136 * c).toFixed(1) +
        '" y2="' + (150 - 136 * s).toFixed(1) + '" stroke="' + (i < filled ? '#6A5EE8' : '#E7E6EE') +
        '" stroke-width="13" stroke-linecap="round"/>';
    }
    return '<svg class=gauge viewBox="0 0 300 160" role="img" aria-label="Sentiment gauge">' + out + '</svg>';
  }
  var box = document.getElementById('sentiment');
  fetch(d.sentimentUrl, {credentials: 'same-origin'}).then(function (r) { return r.json(); }).then(function (s) {
    if (!s || !s.overall) { box.innerHTML = '<p class="muted pad">' + ((s && s.message) || 'Sentiment is not available right now.') + '</p>'; return; }
    var pct = Math.round((s.score + 1) / 2 * 100);
    box.innerHTML = gauge(s.score) + '<div class=gauge-label><div class=gauge-value></div><div class=gauge-note></div></div>' +
      '<div class=gauge-ends><span>Negative</span><span>Positive</span></div><p class=summary></p>';
    box.querySelector('.gauge-value').textContent = pct + '%';
    box.querySelector('.gauge-note').textContent = s.overall;
    box.querySelector('.summary').textContent = s.summary;
    (s.calls || []).forEach(function (c) {
      var el = document.querySelector('.mood[data-call="' + c.id + '"]');
      if (el) { el.className = 'mood ' + c.sentiment; el.textContent = c.sentiment; el.title = c.reason; }
    });
  }).catch(function () { box.innerHTML = '<p class="muted pad">Sentiment is not available right now.</p>'; });
})();
</script>
"""


def render_profile(view: dict) -> str:
    farmer, entries, calls = view["farmer"], view["entries"], view["calls"]
    years = yearly(entries)
    place = ", ".join(x for x in (farmer.get("village"), farmer.get("parish"), farmer.get("sub_county"),
                                  farmer.get("district")) if x)
    lat = farmer.get("lat") if farmer.get("lat") is not None else farmer.get("village_lat")
    lon = farmer.get("lon") if farmer.get("lon") is not None else farmer.get("village_lon")
    median = (view.get("median") or {}).get("median_ugx_per_kg")
    data = {
        "lat": lat, "lon": lon, "place": f"{farmer['name']}, {farmer.get('village') or ''}", "years": years,
        "monthly": monthly(entries, view["today"]), "prices": price_points(entries),
        "median": float(median) if median else None, "sentimentUrl": f"/demo/farmer/{farmer['id']}/sentiment",
    }
    first = _kampala(farmer.get("first_call_at"))[:10]
    latest = calls[0]["id"] if calls else None
    records = "".join(_record(e, latest) for e in entries) or "<li class=muted>No records yet.</li>"

    def legend(*items):
        return "<span class=legend>" + "".join(f"<span><i style=background:{c}></i>{t}</span>" for t, c in items) + "</span>"

    body = (
        f"<div class=top><div class=hero>{demo._avatar(farmer['name'])}<div><h1>{_e(farmer['name'])}{demo._synthetic(farmer)}</h1>"
        f"<p class=sub-title>Grows {_e(farmer.get('coffee_type') or 'coffee')} in {_e(place)}, mostly sold as {_e(view['form'])}."
        f"{' First called on ' + _e(first) + '.' if first else ''}</p></div></div>"
        "<a class=live href=/demo>Back to live calls</a></div>"
        f"{_kpis(view, years)}"
        "<div class=grid2><div class=card><div class=card-head><h2>Farm location</h2></div><div id=map></div></div>"
        "<div class=card><div class=card-head><h2>How she sounds lately</h2><span class=legend>From her last 6 calls</span></div>"
        "<div class=gauge-wrap id=sentiment><p class='muted pad'>Reading her recent calls&hellip;</p></div></div></div>"
        "<div class=grid2><div class=card><div class=card-head><h2>Harvest, sales and earnings</h2>"
        + legend(("Harvest", "#F4B98A"), ("Sold", "#5B4FE0"), ("Earned", "#1E9E5A")) +
        "</div><div class=chart><canvas id=yearly></canvas></div></div>"
        "<div class=card><div class=card-head><h2>Her price against the village median</h2>"
        + legend(("Her price", "#5B4FE0"), ("Median now", "#F4B98A")) +
        "</div><div class=chart><canvas id=prices></canvas></div></div></div>"
        "<div class=grid2><div class=card><div class=card-head><h2>Sales by month</h2>"
        + legend(("Sold (kg)", "#5B4FE0"), ("Earned (UGX)", "#F4B98A")) +
        "</div><div class=chart><canvas id=monthly></canvas></div></div>"
        f"<div class='card records-card'><div class=card-head><h2>Farm record</h2></div><ul class=list>{records}</ul></div></div>"
        f"<div class=section-title><h2>Recent calls</h2></div>{_calls(calls, entries)}"
        f"{_json_script(data)}"
    )
    head = (f"<link rel=stylesheet href={LEAFLET}/leaflet.min.css>{_PROFILE_CSS}"
            f"<script src={LEAFLET}/leaflet.min.js></script><script src={CHART_JS}></script>")
    return _page(farmer["name"], body + _PROFILE_JS, refresh=False, head=head, active=f"farmer-{farmer['id']}",
                 farmers=view.get("farmers"))


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

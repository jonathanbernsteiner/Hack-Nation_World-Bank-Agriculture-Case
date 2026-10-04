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


def _figure(value: str, label: str, note: str = "") -> str:
    note_html = f"<span class=fig-note>{_e(note)}</span>" if note else ""
    return f"<div class=fig><span class=fig-value>{_e(value)}</span><span class=fig-label>{_e(label)}</span>{note_html}</div>"


def _figures(view: dict, years: list[dict]) -> str:
    sales = _coffee_sales(view["entries"])
    kg = sum(_sale_kg(s) for s in sales)
    income = sum(float(s["price_total"]) for s in sales)
    harvests = [y["harvest_kg"] for y in years if y["harvest_kg"]]
    median = view.get("median") or {}
    her_avg = round(income / kg) if kg else None
    vs = ""
    if her_avg and median.get("median_ugx_per_kg"):
        diff = her_avg - float(median["median_ugx_per_kg"])
        vs = f"{_num(abs(diff))} {'above' if diff >= 0 else 'below'} the village median"
    return "<section class=figures>" + "".join([
        _figure(f"{_num(sum(harvests) / len(harvests))} kg" if harvests else "n/a", "harvest a year",
                f"average of {len(harvests)} coffee years"),
        _figure(f"{_num(kg)} kg", "coffee sold", f"{len(sales)} sales"),
        _figure(f"{_num(income)} UGX", "earned from coffee", "all recorded sales"),
        _figure(f"{_num(her_avg)} UGX/kg" if her_avg else "n/a", "her average price", vs),
        _figure(f"{_num(median['median_ugx_per_kg'])} UGX/kg" if median.get("median_ugx_per_kg") else "n/a",
                f"{view['form']} median nearby", f"{median.get('n_sales')} sales in {median.get('area')}" if median.get("n_sales") else ""),
    ]) + "</section>"


def _record(entry: dict, latest_call_id: Any) -> str:
    new = entry["call_id"] == latest_call_id
    kind = demo._kind(entry)
    head, details = demo._facts(entry)
    flag = " <span class=flag>Needs review</span>" if needs_review(entry, entry) else ""
    new_tag = " <span class=new>New</span>" if new else ""
    quote = entry.get("evidence_quote")
    mark = {True: "<span class=ok-mark>&#10003;</span>", False: "<span class=bad-mark>&#10007;</span>"}.get(entry.get("quote_verified"), "")
    quote_html = f"<span class=rq>{mark} &ldquo;{_e(quote)}&rdquo;</span>" if quote else ""
    rest = "".join(f"<span class=rd>{d}</span>" for d in details)
    return (f"<tr class='k-{kind}{' hl' if new else ''}'><td class=rdate>{_e(entry['entry_date'].strftime('%d %b %Y'))}</td>"
            f"<td><span class=dot></span>{demo.KIND_LABELS.get(kind, 'Record')}{new_tag}{flag}</td>"
            f"<td><b>{head}</b>{rest}{quote_html}</td></tr>")


def _calls(calls: list[dict], entries: list[dict]) -> str:
    if not calls:
        return "<p class=muted>No calls yet.</p>"
    by_call: dict[Any, list[dict]] = {}
    for entry in entries:
        by_call.setdefault(entry["call_id"], []).append(entry)
    blocks = []
    for index, call in enumerate(calls):
        badge = " <span class=synthetic>SYNTHETIC</span>" if call.get("is_synthetic") else ""
        mood = f"<span class=mood data-call={_e(call['id'])}></span>"
        status, tone = demo.STATUS_LABELS.get(call.get("status"), (call.get("status") or "", ""))
        blocks.append(
            f"<details class=pcall{' open' if index == 0 else ''}><summary><time>{_e(demo._when(call.get('received_at')))}</time>"
            f"<span class='chip {tone}'>{_e(status)}</span>{mood}{badge}</summary>"
            f"{demo._transcript(call, by_call.get(call['id'], []))}</details>"
        )
    return "".join(blocks)


def _json_script(data: Any) -> str:
    text = json.dumps(data, default=str).replace("</", "<\\/")
    return f"<script type=application/json id=profile-data>{text}</script>"


_PROFILE_CSS = """<style>
.lede{color:var(--muted);margin:-8px 0 20px;font-size:16px}
.back{display:inline-block;margin-top:20px;font-size:14px}
.figures{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));background:var(--paper);border:1px solid var(--line);
border-radius:16px;margin:0 0 20px}
.fig{padding:16px 18px;border-left:1px solid var(--line);display:flex;flex-direction:column;gap:2px}
.fig:first-child{border-left:0}
.fig-value{font-size:24px;font-weight:700;letter-spacing:-.01em;line-height:1.15}
.fig-label{font-size:14px}.fig-note{font-size:12.5px;color:var(--muted)}
@media(max-width:900px){.figures{grid-template-columns:repeat(2,minmax(0,1fr))}.fig{border-left:0;border-top:1px solid var(--line)}
.fig:nth-child(-n+2){border-top:0}}
.two{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:20px;margin-bottom:20px}
@media(max-width:900px){.two{grid-template-columns:1fr}}
.two>.panel{min-width:0}
#map{height:320px;border-radius:10px;border:1px solid var(--line)}
.mood-big{display:flex;align-items:baseline;gap:10px;margin-bottom:6px}
.mood-word{font-size:28px;font-weight:700;text-transform:capitalize;letter-spacing:-.01em}
.mood-score{color:var(--muted);font-size:14px}
.summary{font-family:'Source Serif 4',Georgia,serif;font-style:italic;font-size:18px;line-height:1.5;margin:0 0 16px;max-width:60ch}
.mood{font-size:12px;padding:1px 8px;border-radius:999px;text-transform:capitalize}
.mood:empty{display:none}
.positive{background:var(--leaf-tint);color:var(--leaf)}.neutral{background:#E6E9E5;color:#3E4A43}
.mixed{background:var(--husk-tint);color:#6B4D16}.negative{background:var(--cherry-tint);color:#7A1F18}
.chart{position:relative;height:280px;min-width:0}
.ledger{width:100%;border-collapse:collapse;background:var(--paper);border:1px solid var(--line);border-radius:16px;overflow:hidden}
.ledger td{padding:10px 14px;border-top:1px solid var(--line);vertical-align:top}
.ledger tr:first-child td{border-top:0}
.rdate{white-space:nowrap;color:var(--muted);width:110px}
.ledger td:nth-child(2){white-space:nowrap;width:150px}
.dot{display:inline-block;width:9px;height:9px;border-radius:50%;background:var(--leaf-2);margin-right:8px}
.k-observation .dot{background:var(--cherry)}.k-harvest .dot{background:var(--husk)}.k-activity .dot,.k-other .dot{background:var(--muted)}
.rd{display:block;color:#3A4A40}.rq{display:block;font-family:'Source Serif 4',Georgia,serif;font-style:italic;color:#3B4A41;margin-top:2px}
tr.hl{background:#FBEFED}tr.hl td:first-child{box-shadow:inset 4px 0 0 var(--cherry)}
.new{background:var(--cherry);color:#fff;border-radius:999px;padding:0 8px;font-size:12px;margin-left:6px}
.flag{margin-left:6px}
.pcall{background:var(--paper);border:1px solid var(--line);border-radius:12px;margin:0 0 10px;overflow:hidden}
.pcall summary{cursor:pointer;padding:12px 18px;display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.pcall time{font-weight:600;margin-right:4px}
.pcall .convo{border-top:1px solid var(--line)}
section.block{margin:28px 0}
@media(max-width:700px){.ledger td:nth-child(2){white-space:normal;width:auto}.rdate{width:auto}}
</style>"""

_PROFILE_JS = """
<script>
(function () {
  var d = JSON.parse(document.getElementById('profile-data').textContent);
  var css = getComputedStyle(document.documentElement);
  function v(name) { return css.getPropertyValue(name).trim(); }
  if (window.L && d.lat != null) {
    var map = L.map('map', {scrollWheelZoom: false}).setView([d.lat, d.lon], 13);
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors'}).addTo(map);
    L.circleMarker([d.lat, d.lon], {radius: 10, color: '#fff', weight: 3, fillColor: v('--cherry'), fillOpacity: 1})
      .addTo(map).bindPopup(d.place).openPopup();
  } else { document.getElementById('map').textContent = 'No location on file.'; }
  if (window.Chart) {
    Chart.defaults.maintainAspectRatio = false;
    Chart.defaults.font.family = "'Schibsted Grotesk', system-ui, sans-serif";
    Chart.defaults.color = v('--muted');
    Chart.defaults.plugins.legend.labels.boxWidth = 12;
    var grid = {color: v('--line')};
    new Chart(document.getElementById('yearly'), {data: {labels: d.years.map(function (y) { return y.year; }),
      datasets: [
        {type: 'bar', label: 'Harvest (kg)', data: d.years.map(function (y) { return y.harvest_kg; }), yAxisID: 'kg', backgroundColor: v('--husk'), borderRadius: 4},
        {type: 'bar', label: 'Sold (kg)', data: d.years.map(function (y) { return y.sold_kg; }), yAxisID: 'kg', backgroundColor: v('--leaf-2'), borderRadius: 4},
        {type: 'line', label: 'Earned (UGX)', data: d.years.map(function (y) { return y.income_ugx; }), yAxisID: 'ugx', borderColor: v('--cherry'), backgroundColor: v('--cherry'), borderWidth: 2.5}]},
      options: {scales: {x: {grid: {display: false}}, kg: {position: 'left', beginAtZero: true, grid: grid, title: {display: true, text: 'kg'}},
        ugx: {position: 'right', beginAtZero: true, grid: {drawOnChartArea: false}, title: {display: true, text: 'UGX'}}}}});
    new Chart(document.getElementById('monthly'), {data: {labels: d.monthly.labels, datasets: [
        {type: 'bar', label: 'Sold (kg)', data: d.monthly.kg, yAxisID: 'kg', backgroundColor: v('--leaf-2'), borderRadius: 3},
        {type: 'line', label: 'Earned (UGX)', data: d.monthly.income, yAxisID: 'ugx', borderColor: v('--cherry'), backgroundColor: v('--cherry'), borderWidth: 2, tension: 0.25, pointRadius: 2}]},
      options: {scales: {x: {grid: {display: false}}, kg: {position: 'left', beginAtZero: true, grid: grid},
        ugx: {position: 'right', beginAtZero: true, grid: {drawOnChartArea: false}}}}});
    var sets = [{type: 'line', label: 'Her price (UGX/kg)', data: d.prices.map(function (p) { return p.y; }),
      borderColor: v('--leaf-2'), backgroundColor: v('--leaf-2'), borderWidth: 2.5, tension: 0.25}];
    if (d.median) sets.push({type: 'line', label: 'Village median now', data: d.prices.map(function () { return d.median; }),
      borderColor: v('--husk'), borderDash: [6, 4], borderWidth: 2, pointRadius: 0});
    new Chart(document.getElementById('prices'), {data: {labels: d.prices.map(function (p) { return p.x; }), datasets: sets},
      options: {scales: {x: {grid: {display: false}}, y: {grid: grid}}}});
  }
  var box = document.getElementById('sentiment');
  fetch(d.sentimentUrl, {credentials: 'same-origin'}).then(function (r) { return r.json(); }).then(function (s) {
    if (!s || !s.overall) { box.textContent = (s && s.message) || 'Sentiment is not available right now.'; return; }
    box.innerHTML = '';
    var top = document.createElement('div'); top.className = 'mood-big';
    var word = document.createElement('span'); word.className = 'mood-word'; word.textContent = s.overall;
    var score = document.createElement('span'); score.className = 'mood-score';
    score.textContent = 'score ' + s.score.toFixed(2) + ' from -1 to 1';
    top.appendChild(word); top.appendChild(score);
    var text = document.createElement('p'); text.className = 'summary'; text.textContent = s.summary;
    box.appendChild(top); box.appendChild(text);
    (s.calls || []).forEach(function (c) {
      var el = document.querySelector('.mood[data-call="' + c.id + '"]');
      if (el) { el.className = 'mood ' + c.sentiment; el.textContent = c.sentiment; el.title = c.reason; }
    });
  }).catch(function () { box.textContent = 'Sentiment is not available right now.'; });
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
    badge = " <span class=synthetic>SYNTHETIC</span>" if farmer.get("is_synthetic") else ""
    first = _kampala(farmer.get("first_call_at"))[:10]
    latest = calls[0]["id"] if calls else None
    records = "".join(_record(e, latest) for e in entries) or "<tr><td class=muted>No records yet.</td></tr>"
    body = (
        "<a class=back href=/demo>All calls</a>"
        f"<h1>{_e(farmer['name'])}{badge}</h1>"
        f"<p class=lede>Grows {_e(farmer.get('coffee_type') or 'coffee')} in {_e(place)}, mostly sold as {_e(view['form'])}."
        f"{' First called on ' + _e(first) + '.' if first else ''}</p>"
        f"{_figures(view, years)}"
        "<div class=two><div class=panel><h2>Farm location</h2><div id=map></div></div>"
        "<div class=panel><h2>How she sounds lately</h2><div id=sentiment><p class=muted>Reading her recent calls&hellip;</p></div>"
        "<h2>Harvest, sales and earnings by coffee year</h2><div class=chart><canvas id=yearly></canvas></div></div></div>"
        "<div class=two><div class=panel><h2>Sales by month</h2><div class=chart><canvas id=monthly></canvas></div></div>"
        "<div class=panel><h2>Her price per kilo against the village median</h2><div class=chart><canvas id=prices></canvas></div></div></div>"
        f"<section class=block><h2>Farm record</h2><table class=ledger>{records}</table></section>"
        f"<section class=block><h2>Recent calls</h2>{_calls(calls, entries)}</section>"
        f"{_json_script(data)}"
    )
    head = (f"<link rel=stylesheet href={LEAFLET}/leaflet.min.css>{_PROFILE_CSS}"
            f"<script src={LEAFLET}/leaflet.min.js></script><script src={CHART_JS}></script>")
    return _page(farmer["name"], body + _PROFILE_JS, refresh=False, head=head,
                 tagline="Farmer profile built from her calls to the coffee line.")


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

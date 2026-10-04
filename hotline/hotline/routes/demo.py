"""GET /demo: read-only, server-rendered judge screen behind Basic auth (spec section 11).
GET /: public call page with the ElevenLabs widget only (no ledger data, no refresh).

Never selects pin_hash, PINs or phone numbers. Every value is escaped by `_e`."""

import html
import json
from datetime import date, datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from hotline import config, db, security

router = APIRouter()

KAMPALA_TZ = timezone(timedelta(hours=3), "Africa/Kampala")  # no DST in Uganda
CALL_LIMIT = 20
REFRESH_SECS = 10
LOW_CONFIDENCE = 0.6
MEDIAN_FORMS = ("kiboko", "faq", "parchment")
WIDGET_SCRIPT = "https://unpkg.com/@elevenlabs/convai-widget-embed"

_CALLS_SQL = (
    "select c.id, c.farmer_id, c.received_at, c.status, c.identified_by, c.is_synthetic, c.transcript_lines, "
    "split_part(f.name, ' ', 1) as first_name, v.village, v.parish, v.sub_county, v.district, v.id as village_id "
    "from calls c left join farmers f on f.id = c.farmer_id left join villages v on v.id = f.village_id "
    "order by c.received_at desc limit %s"
)
_ENTRIES_SQL = (
    "select call_id, kind, crop, coffee_form, amount, unit, amount_kg, price_total, currency, "
    "likely_disease, symptom, description, evidence_quote, quote_verified, confidence "
    "from entries where call_id = any(%s) order by id"
)


def _e(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _num(value: Any) -> str:
    """Readable amounts for the judge screen: Decimal('1800000.00') -> '1,800,000', 300.0 -> '300'."""
    number = float(value)
    return f"{number:,.0f}" if number.is_integer() else f"{number:,.2f}"


def _rows(conn, sql: str, params: tuple) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(sql, params)
        names = [col.name for col in cur.description]
        return [dict(zip(names, row, strict=True)) for row in cur.fetchall()]


def _village_medians(conn, calls: list[dict], today: date) -> list[dict]:
    """Medians via prices.village_price (#43), the same function the agent tool uses."""
    try:
        from hotline import prices
    except ImportError:
        return []
    homes = {c["village_id"]: c for c in calls if c.get("village_id") is not None}
    districts = {home["district"] for home in homes.values()}
    rows_by_district = {d: prices.load_sale_rows(conn, d, today) for d in districts}  # one query per district
    result = []
    for home in homes.values():
        rows = rows_by_district[home["district"]]
        forms = [prices.village_price(rows, home, form, today) for form in MEDIAN_FORMS]
        result.append({"village": home["village"], "forms": forms})
    return result


def load_view(conn, today: date | None = None) -> dict:
    today = today or datetime.now(KAMPALA_TZ).date()
    calls = _rows(conn, _CALLS_SQL, (CALL_LIMIT,))
    ids = [c["id"] for c in calls]
    entries = _rows(conn, _ENTRIES_SQL, (ids,)) if ids else []
    return {"calls": calls, "entries": entries, "medians": _village_medians(conn, calls, today)}


def needs_review(entry: dict, call: dict) -> bool:
    confidence = entry.get("confidence")
    low = confidence is not None and float(confidence) < LOW_CONFIDENCE
    return low or entry.get("quote_verified") is False or call.get("identified_by") == "location"


def _kampala(value: datetime | None) -> str:
    if value is None:
        return ""
    return value.astimezone(KAMPALA_TZ).strftime("%Y-%m-%d %H:%M")


def _lines(call: dict) -> list[dict]:
    raw = call.get("transcript_lines")
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except ValueError:
            return []
    return [x for x in raw if isinstance(x, dict)] if isinstance(raw, list) else []


def _transcript(call: dict) -> str:
    lines = _lines(call)
    if not lines:
        return "<p class=muted>No transcript yet.</p>"
    rows = "".join(
        f"<tr><td class=role>{_e(x.get('role'))}</td><td>{_e(x.get('sw'))}</td><td>{_e(x.get('en'))}</td></tr>"
        for x in lines
    )
    return f"<table class=tr><tr><th></th><th>Kiswahili</th><th>English</th></tr>{rows}</table>"


def _entry(entry: dict, call: dict) -> str:
    quote = entry.get("evidence_quote")
    mark = {True: "&#10003;", False: "&#10007;"}.get(entry.get("quote_verified"), "?")
    flag = " <span class=flag>REVIEW</span>" if needs_review(entry, call) else ""
    kg = entry.get("amount_kg") or (entry["amount"] if entry.get("unit") == "kg" else None)
    detail = ", ".join(
        _e(x)
        for x in (
            entry.get("coffee_form") or entry.get("crop"),
            f"{_num(kg)} kg" if kg else None,
            f"{_num(entry['price_total'])} {entry.get('currency') or ''}".strip() if entry.get("price_total") else None,
            entry.get("likely_disease") or entry.get("symptom"),
            entry.get("description"),
        )
        if x
    )
    quote_html = f"<div class=quote>{mark} &ldquo;{_e(quote)}&rdquo;</div>" if quote else ""
    return f"<li><b>{_e(entry.get('kind'))}</b>: {detail}{flag}{quote_html}</li>"


def _call_block(call: dict, entries: list[dict]) -> str:
    badge = " <span class=synthetic>SYNTHETIC</span>" if call.get("is_synthetic") else ""
    who = " / ".join(_e(x) for x in (call.get("first_name"), call.get("village")) if x) or "unidentified"
    if call.get("farmer_id") is not None:
        who = f"<a href=/demo/farmer/{_e(call['farmer_id'])}>{who}</a>"
    items = "".join(_entry(x, call) for x in entries) or "<li class=muted>No entries.</li>"
    return (
        f"<section class=call><h3>{_e(_kampala(call.get('received_at')))} &middot; {_e(call.get('status'))}"
        f" &middot; by {_e(call.get('identified_by') or 'n/a')} &middot; {who}{badge}</h3>"
        f"{_transcript(call)}<ul>{items}</ul></section>"
    )


def _medians(medians: list[dict]) -> str:
    if not medians:
        return "<p class=muted>No village medians yet.</p>"
    out = []
    for village in medians:
        cells = "".join(
            f"<tr><td>{_e(m['form'])}</td><td>{_e(_num(m['median_ugx_per_kg']))} UGX/kg</td>"
            f"<td>n={_e(m.get('n_sales'))}</td><td>{_e(m.get('level'))}: {_e(m.get('area'))}</td></tr>"
            for m in village["forms"]
        )
        out.append(f"<h3>{_e(village['village'])}</h3><table>{cells}</table>")
    return "".join(out)


def _widget() -> str:
    agent_id = config.settings.elevenlabs_agent_id
    if not agent_id:
        return "<p class=muted>Browser call widget not configured.</p>"
    return f'<elevenlabs-convai agent-id="{_e(agent_id)}"></elevenlabs-convai><script src="{WIDGET_SCRIPT}" async></script>'


_CSS = (
    "body{font:15px system-ui,sans-serif;margin:16px auto;max-width:1100px;padding:0 16px;color:#1b1b1b}"
    "table{border-collapse:collapse;width:100%}td,th{border-bottom:1px solid #ddd;padding:4px 8px;"
    "text-align:left;vertical-align:top}.tr td:nth-child(2),.tr td:nth-child(3){width:45%}"
    ".role,.muted{color:#777}.synthetic{background:#fde68a;padding:1px 6px;border-radius:4px;font-size:12px}"
    ".flag{background:#fecaca;padding:1px 6px;border-radius:4px;font-size:12px}.quote{color:#555;font-size:13px}"
    ".call{border:1px solid #ddd;border-radius:8px;padding:8px 12px;margin:12px 0}footer{color:#777;margin-top:24px}"
)


FOOTER = "<footer>Weather data by Open-Meteo.com (CC BY 4.0). Synthetic demo data.</footer>"
CALL_LINK = (
    "<p><a href=/ target=_blank rel=noopener>Open the call page</a> in a new tab, call there, and watch "
    "this page. (The widget is not on this page: the 10 s refresh would cut the call.)</p>"
)


def _page(title: str, body: str, refresh: bool) -> str:
    meta = f"<meta http-equiv=refresh content={REFRESH_SECS}>" if refresh else ""
    return (
        f"<!doctype html><html lang=en><head><meta charset=utf-8>{meta}"
        f"<meta name=viewport content='width=device-width,initial-scale=1'>"
        f"<title>{_e(title)}</title><style>{_CSS}</style></head><body>"
        f"<h1>{_e(title)}</h1>{body}{FOOTER}</body></html>"
    )


def render_page(view: dict) -> str:
    entries_by_call: dict[Any, list[dict]] = {}
    for entry in view["entries"]:
        entries_by_call.setdefault(entry["call_id"], []).append(entry)
    calls = "".join(_call_block(c, entries_by_call.get(c["id"], [])) for c in view["calls"])
    body = (
        f"<h2>Try a call</h2>{CALL_LINK}"
        f"<h2>Village medians</h2>{_medians(view['medians'])}"
        f"<h2>Latest calls</h2>{calls or '<p class=muted>No calls yet.</p>'}"
    )
    return _page("Hotline demo", body, refresh=True)


def render_call_page() -> str:
    """Public page: the browser widget only. No ledger data, no refresh (a reload would end the call)."""
    body = "<p>Kiswahili coffee price and problem line. Press the button to talk to the agent.</p>" + _widget()
    return _page("Coffee hotline", body, refresh=False)


def _load() -> dict:
    with db.connect() as conn:
        return load_view(conn)


@router.get("/", response_class=HTMLResponse)
def call_page() -> HTMLResponse:
    return HTMLResponse(render_call_page())


@router.get("/demo", response_class=HTMLResponse, dependencies=[Depends(security.require_demo_basic_auth)])
def demo_page() -> HTMLResponse:
    return HTMLResponse(render_page(_load()))

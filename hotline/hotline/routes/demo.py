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


def _when(value: datetime | None) -> str:
    """Readable Kampala time for headings: '4 Oct 2026, 09:16'."""
    if value is None:
        return ""
    local = value.astimezone(KAMPALA_TZ)
    return f"{local.day} {local.strftime('%b %Y, %H:%M')}"


def _lines(call: dict) -> list[dict]:
    raw = call.get("transcript_lines")
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except ValueError:
            return []
    return [x for x in raw if isinstance(x, dict)] if isinstance(raw, list) else []


KIND_LABELS = {"sale": "Sale", "observation": "Problem", "harvest": "Harvest", "activity": "Farm work"}
STATUS_LABELS = {"processed": ("Processed", "ok"), "needs_review": ("Needs review", "warn"),
                 "received": ("Processing", "warn"), "processing": ("Processing", "warn"), "failed": ("Failed", "bad")}
IDENTIFIED_LABELS = {"pin": "Known caller", "location": "Found by location", "registration": "New caller"}


def _kind(entry: dict) -> str:
    kind = entry.get("kind") or "other"
    return kind if kind in KIND_LABELS else "other"


def _highlight(text: str, quotes: list[tuple[str, str]]) -> str:
    """Escape `text` and wrap each evidence quote found in it in a mark coloured by its record kind."""
    out = _e(text)
    for quote, kind in quotes:
        needle = _e(quote)
        at = out.lower().find(needle.lower()) if needle else -1
        if at >= 0:
            out = f"{out[:at]}<mark class=k-{kind}>{out[at:at + len(needle)]}</mark>{out[at + len(needle):]}"
    return out


def _other_language(original: str, english: str) -> bool:
    """True when the spoken text is not just the English line (English calls keep near-identical text)."""
    spoken = set(original.lower().split())
    if not spoken:
        return False
    return len(spoken & set(english.lower().split())) / len(spoken) < 0.5


def _transcript(call: dict, entries: list[dict] | None = None) -> str:
    lines = _lines(call)
    if not lines:
        return "<p class='muted pad'>No transcript yet.</p>"
    quotes = [(e["evidence_quote"], _kind(e)) for e in entries or [] if e.get("evidence_quote")]
    items = []
    for line in lines:
        farmer = line.get("role") == "farmer"
        english, original = line.get("en") or "", line.get("sw") or ""
        text = english or original
        shown = _highlight(text, quotes) if farmer else _e(text)
        extra = f"<p class=orig>Kiswahili: {_e(original)}</p>" if english and _other_language(original, english) else ""
        items.append(f"<li class='line {'farmer' if farmer else 'agent'}'><span class=sp>{'Farmer' if farmer else 'Agent'}</span>"
                     f"<div><p class=t>{shown}</p>{extra}</div></li>")
    return f"<ol class=convo>{''.join(items)}</ol>"


def _facts(entry: dict) -> tuple[str, list[str]]:
    """(headline, detail lines) for one record, already escaped."""
    kg = entry.get("amount_kg") or (entry["amount"] if entry.get("unit") == "kg" else None)
    form = entry.get("coffee_form") or entry.get("crop") or ""
    price = entry.get("price_total")
    currency = entry.get("currency") or ""
    kind = _kind(entry)
    if kind == "sale":
        head = f"{_num(kg)} kg {form}".strip() if kg else (form or "Sale")
        details = []
        if price:
            per_kg = f" ({_num(float(price) / float(kg))} {currency}/kg)" if kg else ""
            details.append(f"{_num(price)} {currency}".strip() + per_kg)
        how = [x.replace("_", " ") for x in (entry.get("buyer_type"), entry.get("paid_how")) if x]
        if how:
            details.append(", ".join(how).capitalize())
        return _e(head), [_e(d) for d in details]
    if kind == "observation":
        head = (entry.get("likely_disease") or entry.get("symptom") or "Problem reported").replace("_", " ")
        return _e(head.capitalize()), [_e(entry["description"])] if entry.get("description") else []
    if kind == "harvest":
        amount = entry.get("yield_amount") or entry.get("amount")
        head = f"{_num(amount)} {entry.get('unit') or ''} harvested".strip() if amount else "Harvest"
        return _e(head), []
    head = (entry.get("activity") or entry.get("description") or kind).replace("_", " ")
    return _e(head.capitalize()), []


def _entry(entry: dict, call: dict) -> str:
    kind = _kind(entry)
    head, details = _facts(entry)
    flag = " <span class=flag>Needs review</span>" if needs_review(entry, call) else ""
    quote = entry.get("evidence_quote")
    mark = {True: "<span class=ok-mark title='Quote found in the call'>&#10003;</span>",
            False: "<span class=bad-mark title='Quote not found in the call'>&#10007;</span>"}.get(entry.get("quote_verified"), "")
    quote_html = f"<blockquote>{mark} &ldquo;{_e(quote)}&rdquo;</blockquote>" if quote else ""
    lines = "".join(f"<p>{d}</p>" for d in details)
    return (f"<div class='slip k-{kind}'><p class=slip-kind>{KIND_LABELS.get(kind, 'Record')}{flag}</p>"
            f"<p class=slip-main>{head}</p>{lines}{quote_html}</div>")


def _records(call: dict, entries: list[dict]) -> str:
    if entries:
        return "".join(_entry(x, call) for x in entries)
    if call.get("status") in ("received", "processing"):
        return "<p class=muted>Reading the call. Records usually appear 1 to 2 minutes after hang-up.</p>"
    return "<p class=muted>Nothing recorded from this call.</p>"


def _call_block(call: dict, entries: list[dict], open_: bool = True) -> str:
    badge = " <span class=synthetic>SYNTHETIC</span>" if call.get("is_synthetic") else ""
    name = _e(call.get("first_name") or "Unknown caller")
    if call.get("farmer_id") is not None:
        name = f"<a class=who href=/demo/farmer/{_e(call['farmer_id'])}>{name}</a>"
    else:
        name = f"<span class=who>{name}</span>"
    place = f"<span class=place>{_e(call['village'])}</span>" if call.get("village") else ""
    status, tone = STATUS_LABELS.get(call.get("status"), (call.get("status") or "Unknown", ""))
    who_by = IDENTIFIED_LABELS.get(call.get("identified_by"))
    chips = f"<span class='chip {tone}'>{_e(status)}</span>" + (f"<span class=chip>{_e(who_by)}</span>" if who_by else "")
    convo = _transcript(call, entries)
    if not open_:
        convo = f"<details class=older><summary>Show the conversation</summary>{convo}</details>"
    return (
        f"<article class=call><header class=call-head><div>{name}{place}</div>"
        f"<div class=meta><time>{_e(_when(call.get('received_at')))}</time>{chips}{badge}</div></header>"
        f"<div class=call-body><div class=talk>{convo}</div>"
        f"<div class=records><h3>Recorded from this call</h3>{_records(call, entries)}</div></div></article>"
    )


def _price_note(m: dict) -> str:
    if m.get("level") == "national_reference" or not m.get("n_sales"):
        return "national reference price"
    area = "" if m.get("level") == "village" else f", {_e(m.get('area') or m.get('level'))}"
    return f"{_e(m['n_sales'])} sales{area}"


def _medians(medians: list[dict]) -> str:
    if not medians:
        return "<p class=muted>No village prices yet.</p>"
    out = []
    for village in medians:
        rows = "".join(
            f"<tr><td>{_e(m['form'])}<span class=sub>{_price_note(m)}</span></td>"
            f"<td class=num>{_e(_num(m['median_ugx_per_kg']))} UGX/kg</td></tr>"
            for m in village["forms"] if m.get("median_ugx_per_kg")
        )
        out.append(f"<h3>{_e(village['village'])}</h3><table class=prices>{rows}</table>")
    return "".join(out)


def _widget() -> str:
    agent_id = config.settings.elevenlabs_agent_id
    if not agent_id:
        return "<p class=muted>The browser call button is not set up.</p>"
    return f'<elevenlabs-convai agent-id="{_e(agent_id)}"></elevenlabs-convai><script src="{WIDGET_SCRIPT}" async></script>'


FONTS = ("https://fonts.googleapis.com/css2?family=Schibsted+Grotesk:wght@400;500;600;700"
         "&family=Source+Serif+4:ital,opsz,wght@1,8..60,400&display=swap")

_CSS = """
:root{--leaf:#1F4D3A;--leaf-2:#2E6B50;--leaf-tint:#DCEBE1;--canopy:#E8EDE6;--paper:#FFFFFF;--cherry:#B8322A;
--cherry-tint:#F6DEDA;--husk:#B98A3E;--husk-tint:#F3E7D0;--ink:#18241D;--muted:#5C6B61;--line:#D3DBD2;color-scheme:light}
*{box-sizing:border-box}
body{margin:0;background:var(--canopy);color:var(--ink);font:15px/1.5 'Schibsted Grotesk',system-ui,sans-serif}
.prices td.num,.meta time,.slip-main,.fig-value,.rdate{font-variant-numeric:tabular-nums}
a{color:var(--leaf-2)}a:focus-visible,summary:focus-visible{outline:2px solid var(--cherry);outline-offset:2px;border-radius:4px}
.band{background:var(--leaf);color:#fff}
.band .wrap{display:flex;flex-wrap:wrap;align-items:baseline;gap:4px 20px;padding-top:14px;padding-bottom:14px}
.brand{font-weight:700;font-size:18px;color:#fff;text-decoration:none;letter-spacing:-.01em}
.band p{margin:0;color:#CFE0D5;font-size:14px}
.wrap{max-width:1240px;margin:0 auto;padding-left:24px;padding-right:24px}
@media(max-width:600px){.wrap{padding-left:16px;padding-right:16px}}
h1{font-size:34px;line-height:1.1;letter-spacing:-.02em;margin:28px 0 18px;font-weight:700}
h2{font-size:17px;line-height:1.3;margin:0 0 12px;font-weight:600}
h3{font-size:13.5px;margin:0 0 10px;font-weight:600;color:var(--muted)}
.muted{color:var(--muted)}.pad{padding:16px 20px;margin:0}
.layout{display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:24px;align-items:start}
@media(max-width:900px){.layout{grid-template-columns:1fr}}
aside{position:sticky;top:16px;display:grid;gap:16px}
.panel{background:var(--paper);border:1px solid var(--line);border-radius:12px;padding:16px 18px}
.panel p{margin:0 0 8px}
.call{background:var(--paper);border:1px solid var(--line);border-radius:16px;margin:0 0 20px;overflow:hidden}
.call-head{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:center;gap:8px 16px;
padding:14px 20px;border-bottom:1px solid var(--line)}
.who{font-size:20px;font-weight:700;color:var(--ink);text-decoration:none}a.who:hover{text-decoration:underline}
.place{color:var(--muted);margin-left:8px}
.meta{display:flex;flex-wrap:wrap;gap:6px;align-items:center;color:var(--muted);font-size:13px}
.meta time{margin-right:4px}
.chip{border:1px solid var(--line);border-radius:999px;padding:1px 10px;font-size:12.5px;color:var(--ink);background:var(--canopy)}
.chip.ok{background:var(--leaf-tint);border-color:#B5D3C0}.chip.warn{background:var(--husk-tint);border-color:#E2CB9E}
.chip.bad{background:var(--cherry-tint);border-color:#E9B3AC}
.synthetic{font-size:11px;letter-spacing:.04em;background:#FFF3C4;border:1px solid #E8D27A;border-radius:4px;padding:0 6px;color:#5E4B00}
.call-body{display:grid;grid-template-columns:minmax(0,1.55fr) minmax(0,1fr)}
@media(max-width:760px){.call-body{grid-template-columns:1fr}.records{border-left:0;border-top:1px solid var(--line)}}
.convo{list-style:none;margin:0;padding:16px 20px;max-height:480px;overflow:auto;display:grid;gap:10px}
.line{display:grid;grid-template-columns:60px minmax(0,1fr);gap:12px}
.sp{font-size:12.5px;color:var(--muted);padding-top:3px}
.line p{margin:0;max-width:64ch}
.line.farmer .t{font-family:'Source Serif 4',Georgia,serif;font-style:italic;font-size:16.5px;line-height:1.5}
.line.farmer .sp{color:var(--leaf-2);font-weight:600}
.line.agent .t{color:#3A4A40}
.orig{font-size:13px;color:var(--muted)}
mark{background:var(--leaf-tint);color:inherit;border-radius:3px;padding:0 2px;box-shadow:inset 0 -2px 0 var(--leaf-2)}
mark.k-observation{background:var(--cherry-tint);box-shadow:inset 0 -2px 0 var(--cherry)}
mark.k-harvest{background:var(--husk-tint);box-shadow:inset 0 -2px 0 var(--husk)}
.records{background:#F6F8F5;border-left:1px solid var(--line);padding:16px 20px;display:grid;gap:16px;align-content:start}
.records h3{margin:0}
.slip{border-left:4px solid var(--leaf-2);padding:0 0 0 12px}
.slip.k-observation{border-color:var(--cherry)}.slip.k-harvest{border-color:var(--husk)}.slip.k-activity,.slip.k-other{border-color:var(--muted)}
.slip p{margin:0}
.slip-kind{font-size:13px;color:var(--muted);display:flex;gap:8px;align-items:center}
.slip-main{font-size:19px;font-weight:700;line-height:1.3;margin:2px 0 2px!important}
.slip blockquote{margin:6px 0 0;font-family:'Source Serif 4',Georgia,serif;font-style:italic;color:#3B4A41;font-size:14.5px}
.flag{background:var(--cherry-tint);color:#7A1F18;border-radius:999px;padding:0 8px;font-size:12px}
.ok-mark{color:var(--leaf-2);font-style:normal;font-weight:700}.bad-mark{color:var(--cherry);font-style:normal;font-weight:700}
details.older summary{cursor:pointer;padding:14px 20px;color:var(--leaf-2);font-weight:500}
table.prices{width:100%;border-collapse:collapse;margin-bottom:12px}
.prices td{padding:7px 0;border-top:1px solid var(--line);vertical-align:top}
.prices td.num{text-align:right;font-weight:600;white-space:nowrap}
.sub{display:block;font-size:12.5px;color:var(--muted)}
footer{color:var(--muted);font-size:13px;padding-top:24px;padding-bottom:32px}
"""

FOOTER = "<footer class=wrap>Weather data by Open-Meteo.com (CC BY 4.0). Synthetic demo data.</footer>"
CALL_LINK = (
    "<p><a href=/ target=_blank rel=noopener>Open the call page</a> in a new tab and talk to the agent there. "
    "The call shows up here when you hang up.</p>"
    "<p class=muted>Or phone +1 628 272 9173.</p>"
)


def _page(title: str, body: str, refresh: bool, head: str = "", tagline: str = "") -> str:
    meta = f"<meta http-equiv=refresh content={REFRESH_SECS}>" if refresh else ""
    tag = f"<p>{_e(tagline)}</p>" if tagline else ""
    return (
        f"<!doctype html><html lang=en><head><meta charset=utf-8>{meta}"
        f"<meta name=viewport content='width=device-width,initial-scale=1'>"
        f"<link rel=preconnect href=https://fonts.gstatic.com crossorigin><link rel=stylesheet href='{FONTS}'>"
        f"<title>{_e(title)}</title><style>{_CSS}</style>{head}</head><body>"
        f"<header class=band><div class=wrap><a class=brand href=/demo>Coffee line</a>{tag}</div></header>"
        f"<main class=wrap>{body}</main>{FOOTER}</body></html>"
    )


def render_page(view: dict) -> str:
    entries_by_call: dict[Any, list[dict]] = {}
    for entry in view["entries"]:
        entries_by_call.setdefault(entry["call_id"], []).append(entry)
    calls = "".join(_call_block(c, entries_by_call.get(c["id"], []), open_=i == 0) for i, c in enumerate(view["calls"]))
    body = (
        "<h1>Latest calls</h1><div class=layout>"
        f"<section>{calls or '<p class=muted>No calls yet. Make a test call to see one here.</p>'}</section>"
        f"<aside><div class=panel><h2>Village prices, last 12 months</h2>{_medians(view['medians'])}</div>"
        f"<div class=panel><h2>Make a test call</h2>{CALL_LINK}</div></aside></div>"
    )
    return _page("Latest calls", body, refresh=True,
                 tagline="Calls from coffee farmers in Uganda, turned into farm records. Updates every 10 seconds.")


def render_call_page() -> str:
    """Public page: the browser widget only. No ledger data, no refresh (a reload would end the call)."""
    body = ("<h1>Talk to the coffee line</h1><div class=panel style='max-width:640px'>"
            "<p>Ask about coffee prices in your village, report a sale, or describe a problem with your trees. "
            "Press the button at the bottom of the page and allow the microphone.</p></div>" + _widget())
    return _page("Coffee line", body, refresh=False, tagline="Coffee prices, farm records and crop advice by phone.")


def _load() -> dict:
    with db.connect() as conn:
        return load_view(conn)


@router.get("/", response_class=HTMLResponse)
def call_page() -> HTMLResponse:
    return HTMLResponse(render_call_page())


@router.get("/demo", response_class=HTMLResponse, dependencies=[Depends(security.require_demo_basic_auth)])
def demo_page() -> HTMLResponse:
    return HTMLResponse(render_page(_load()))

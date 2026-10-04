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
    "select call_id, kind, crop, coffee_form, amount, unit, amount_kg, price_total, currency, buyer_type, paid_how, "
    "yield_amount, activity, likely_disease, symptom, description, evidence_quote, quote_verified, confidence "
    "from entries where call_id = any(%s) order by id"
)


_KAMPALA_DAY = "(c.received_at at time zone 'Africa/Kampala')::date"
_STATS_SQL = f"""
select (select count(*) from calls c where {_KAMPALA_DAY} = %(today)s) as calls_today,
       (select count(*) from calls c where {_KAMPALA_DAY} > %(today)s - 7) as calls_week,
       count(*) as records,
       count(*) filter (where {_KAMPALA_DAY} = %(today)s) as records_today,
       coalesce(sum(e.amount_kg) filter (where e.kind = 'sale' and {_KAMPALA_DAY} > %(today)s - 30), 0) as kg_30d,
       coalesce(sum(e.price_total) filter (where e.kind = 'sale' and e.currency = 'UGX'
                                           and {_KAMPALA_DAY} > %(today)s - 30), 0) as ugx_30d,
       count(*) filter (where e.evidence_quote is not null) as quotes,
       count(*) filter (where e.evidence_quote is not null and e.quote_verified) as verified
from entries e join calls c on c.id = e.call_id
"""
_TREND_SQL = f"""
select to_char(m, 'Mon YY') as label,
       (select count(*) from calls c where date_trunc('month', {_KAMPALA_DAY}) = m) as calls,
       (select coalesce(sum(e.amount_kg), 0) from entries e join calls c on c.id = e.call_id
         where e.kind = 'sale' and date_trunc('month', coalesce(e.date_sold, {_KAMPALA_DAY})) = m) as kg
from generate_series(date_trunc('month', %(today)s::date) - interval '11 months',
                     date_trunc('month', %(today)s::date), interval '1 month') as m
order by m
"""
_FARMERS_SQL = (
    "select f.id, split_part(f.name, ' ', 1) as first_name, v.village, max(c.received_at) as last_call "
    "from calls c join farmers f on f.id = c.farmer_id left join villages v on v.id = f.village_id "
    "where c.source is distinct from 'synthetic' or c.received_at > now() - interval '30 days' "
    "group by f.id, f.name, v.village order by last_call desc limit 5"
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
    return {"calls": calls, "entries": entries, "medians": _village_medians(conn, calls, today),
            "stats": _rows(conn, _STATS_SQL, {"today": today})[0], "trend": _rows(conn, _TREND_SQL, {"today": today}),
            "farmers": recent_farmers(conn)}


def recent_farmers(conn) -> list[dict]:
    """The last few farmers who called, for the sidebar."""
    return _rows(conn, _FARMERS_SQL, ())


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

_ICON_PATHS = {
    "grid": '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/>'
            '<rect x="14" y="14" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/>',
    "phone": '<path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 '
             '2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .4 1.9.7 2.8a2 2 0 0 1-.5 2.1L8.1 9.9a16 16 0 0 0 6 6l1.3-1.3a2 2 '
             '0 0 1 2.1-.4c.9.3 1.8.6 2.8.7a2 2 0 0 1 1.7 2z"/>',
    "file": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6M16 13H8M16 17H8"/>',
    "box": '<path d="M21 8 12 3 3 8v8l9 5 9-5z"/><path d="m3 8 9 5 9-5M12 13v8"/>',
    "check": '<path d="M22 11.1V12a10 10 0 1 1-5.9-9.1"/><path d="M22 4 12 14l-3-3"/>',
    "trend": '<path d="m22 7-8.5 8.5-5-5L2 17"/><path d="M16 7h6v6"/>',
    "user": '<path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
    "coins": '<circle cx="8" cy="8" r="6"/><path d="M18.1 10.4A6 6 0 1 1 10.3 18M7 6h1v4"/>',
    "leaf": '<path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.5 19 2c1 2 2 4.2 2 8 0 5.5-4.8 10-10 10Z"/>'
            '<path d="M2 21c0-3 1.9-5.4 5.1-6C9.5 14.5 12 13 13 12"/>',
    "smile": '<circle cx="12" cy="12" r="10"/><path d="M8 14s1.5 2 4 2 4-2 4-2M9 9h.01M15 9h.01"/>',
}


def _icon(name: str) -> str:
    return (f'<svg class=ic viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
            f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{_ICON_PATHS[name]}</svg>')


LOGO = ('<svg viewBox="0 0 32 32" width="30" height="30" aria-hidden="true"><rect width="32" height="32" rx="9" fill="#5B4FE0"/>'
        '<ellipse cx="16" cy="16" rx="7.5" ry="10" transform="rotate(30 16 16)" fill="#fff"/>'
        '<path d="M12.2 9.6c3.6 2.2 4.4 6.9 1.6 12.6" stroke="#5B4FE0" stroke-width="1.8" fill="none" '
        'stroke-linecap="round" transform="rotate(8 16 16)"/></svg>')


def _kind(entry: dict) -> str:
    kind = entry.get("kind") or "other"
    return kind if kind in KIND_LABELS else "other"


def _other_language(original: str, english: str) -> bool:
    """True when the spoken text is not just the English line (English calls keep near-identical text)."""
    spoken = set(original.lower().split())
    if not spoken:
        return False
    return len(spoken & set(english.lower().split())) / len(spoken) < 0.5


def _highlight(text: str, quotes: list[tuple[str, str]]) -> str:
    """Escape `text` and wrap each evidence quote found in it in a mark coloured by its record kind."""
    out = _e(text)
    for quote, kind in quotes:
        needle = _e(quote)
        at = out.lower().find(needle.lower()) if needle else -1
        if at >= 0:
            out = f"{out[:at]}<mark class=k-{kind}>{out[at:at + len(needle)]}</mark>{out[at + len(needle):]}"
    return out


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
                     f"<div class=bubble><p class=t>{shown}</p>{extra}</div></li>")
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


def compact(value: Any) -> str:
    """Short money for cards: 18248500 -> '18.2M', 920000 -> '920k', 850 -> '850'."""
    number = float(value)
    for size, suffix in ((1e9, "B"), (1e6, "M"), (1e3, "k")):
        if abs(number) >= size:
            return f"{number / size:.1f}".rstrip("0").rstrip(".") + suffix
    return _num(number)


def _pill(text: str, tone: str = "") -> str:
    return f"<span class='pill {tone}'>{_e(text)}</span>"


def _entry(entry: dict, call: dict) -> str:
    kind = _kind(entry)
    head, details = _facts(entry)
    flag = _pill("Needs review", "warn") if needs_review(entry, call) else ""
    quote = entry.get("evidence_quote")
    mark = {True: "<span class=ok-mark title='Quote found in the call'>&#10003;</span>",
            False: "<span class=bad-mark title='Quote not found in the call'>&#10007;</span>"}.get(entry.get("quote_verified"), "")
    quote_html = f"<blockquote>{mark} &ldquo;{_e(quote)}&rdquo;</blockquote>" if quote else ""
    lines = "".join(f"<p>{d}</p>" for d in details)
    return (f"<div class='slip k-{kind}'><div class=slip-top><span class=kind><i class=dot></i>"
            f"{KIND_LABELS.get(kind, 'Record')}</span>{flag}</div>"
            f"<p class=slip-main>{head}</p>{lines}{quote_html}</div>")


def _records(call: dict, entries: list[dict]) -> str:
    if entries:
        return "".join(_entry(x, call) for x in entries)
    if call.get("status") in ("received", "processing"):
        return "<p class=muted>Reading the call. Records usually appear 1 to 2 minutes after hang-up.</p>"
    return "<p class=muted>Nothing recorded from this call.</p>"


def _synthetic(row: dict) -> str:
    return " <span class=synthetic>Synthetic</span>" if row.get("is_synthetic") else ""


def _call_block(call: dict, entries: list[dict], open_: bool = True) -> str:
    name = _e(call.get("first_name") or "Unknown caller")
    if call.get("farmer_id") is not None:
        name = f"<a class=who href=/demo/farmer/{_e(call['farmer_id'])}>{name}</a>"
    else:
        name = f"<span class=who>{name}</span>"
    place = f"<span class=place>{_e(call['village'])}</span>" if call.get("village") else ""
    status, tone = STATUS_LABELS.get(call.get("status"), (call.get("status") or "Unknown", ""))
    who_by = IDENTIFIED_LABELS.get(call.get("identified_by"))
    pills = _pill(status, tone) + (_pill(who_by) if who_by else "")
    convo = _transcript(call, entries)
    if not open_:
        convo = f"<details class=older><summary>Show the conversation</summary>{convo}</details>"
    return (
        f"<article class='card call' id=call-{_e(call['id'])}><header class=call-head><div>{name}{place}</div>"
        f"<div class=meta><time>{_e(_when(call.get('received_at')))}</time>{pills}{_synthetic(call)}</div></header>"
        f"<div class=call-body><div class=talk>{convo}</div>"
        f"<div class=records><h3>Recorded from this call</h3>{_records(call, entries)}</div></div></article>"
    )


def _summary(entries: list[dict]) -> str:
    """One short line for the calls list: what the call produced."""
    parts = []
    for entry in entries:
        head, _ = _facts(entry)
        parts.append(head if _kind(entry) != "sale" else f"Sold {head}")
    return ", ".join(parts[:2]) or "No records"


def _avatar(name: str | None) -> str:
    return f"<span class=avatar>{_e((name or '?')[:1].upper())}</span>"


def _call_row(call: dict, entries: list[dict]) -> str:
    status, tone = STATUS_LABELS.get(call.get("status"), (call.get("status") or "Unknown", ""))
    when = call.get("received_at")
    sub = ", ".join(x for x in (call.get("village"), when.astimezone(KAMPALA_TZ).strftime("%d %b, %H:%M") if when else "") if x)
    return (f"<li><a class=row href=#call-{_e(call['id'])}>{_avatar(call.get('first_name'))}"
            f"<span class=row-main><b>{_e(call.get('first_name') or 'Unknown caller')}</b><small>{_e(sub)}</small></span>"
            f"<span class=row-side><b>{_summary(entries)}</b><small>{len(entries)} records</small></span>"
            f"{_pill(status, tone)}</a></li>")


def _price_note(m: dict) -> str:
    if m.get("level") == "national_reference" or not m.get("n_sales"):
        return "national reference price"
    area = "" if m.get("level") == "village" else f", {_e(m.get('area') or m.get('level'))}"
    return f"{_e(m['n_sales'])} sales{area}"


def _medians(medians: list[dict]) -> str:
    if not medians:
        return "<p class=muted>No village prices yet.</p>"
    rows = []
    for village in medians:
        for m in village["forms"]:
            if not m.get("median_ugx_per_kg"):
                continue
            local = m.get("level") not in ("national_reference", None) and m.get("n_sales")
            rows.append(
                f"<li class=row><span class=row-main><b>{_e(village['village'])}</b><small>{_e(m['form'])}</small></span>"
                f"<span class=row-side><b>{_e(_num(m['median_ugx_per_kg']))} UGX/kg</b><small>{_price_note(m)}</small></span>"
                f"{_pill('Local' if local else 'Reference', 'ok' if local else '')}</li>")
    return f"<ul class=list>{''.join(rows)}</ul>"


def _widget() -> str:
    agent_id = config.settings.elevenlabs_agent_id
    if not agent_id:
        return "<p class=muted>The browser call button is not set up.</p>"
    return f'<elevenlabs-convai agent-id="{_e(agent_id)}"></elevenlabs-convai><script src="{WIDGET_SCRIPT}" async></script>'


def kpi(label: str, icon: str, value: str, delta: str = "", rest: str = "") -> str:
    note = f"<p class=delta><b>{_e(delta)}</b> {_e(rest)}</p>" if (delta or rest) else ""
    return (f"<div class='card kpi'><div class=kpi-top><span>{_e(label)}</span><span class=icon-chip>{_icon(icon)}</span></div>"
            f"<p class=kpi-value>{_e(value)}</p>{note}</div>")


def _kpis(view: dict) -> str:
    stats = view.get("stats")
    if not stats:
        return ""
    quotes = stats.get("quotes") or 0
    rate = f"{100 * (stats.get('verified') or 0) / quotes:.0f}%" if quotes else "n/a"
    first = next((m for v in view.get("medians", []) for m in v["forms"] if m.get("n_sales")), None)
    median_card = (kpi(f"Village median, {first['form']}", "coins", f"{_num(first['median_ugx_per_kg'])} UGX",
                       f"{first['n_sales']} sales", f"in {first.get('area')}") if first
                   else kpi("Village median", "coins", "n/a"))
    return "<section class=kpis>" + "".join([
        kpi("Calls today", "phone", str(stats["calls_today"]), f"{stats['calls_week']}", "in the last 7 days"),
        kpi("Records captured", "file", _num(stats["records"]), f"+{stats['records_today']}", "today"),
        kpi("Coffee sold, 30 days", "box", f"{_num(stats['kg_30d'])} kg", f"{compact(stats['ugx_30d'])} UGX", "paid to farmers"),
        kpi("Quotes verified", "check", rate, f"{stats.get('verified') or 0}", f"of {quotes} quotes"),
        median_card,
    ]) + "</section>"


FONTS = "https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap"
CHART_JS = "https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"

_CSS = """
:root{--bg:#EEEDF7;--card:#FFFFFF;--line:#ECEBF3;--ink:#17172B;--muted:#6E6E85;--purple:#5B4FE0;--purple-2:#7B70F0;
--purple-tint:#ECEAFD;--peach:#F4B98A;--peach-tint:#FDF0E5;--green:#1E9E5A;--green-tint:#E5F6EC;--amber:#D9831F;
--amber-tint:#FDF1E1;--red:#D6453D;--red-tint:#FCE8E6;color-scheme:light}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.5 'Plus Jakarta Sans',system-ui,sans-serif}
a{color:var(--purple)}a:focus-visible,summary:focus-visible{outline:2px solid var(--purple);outline-offset:2px;border-radius:6px}
.shell{display:grid;grid-template-columns:248px minmax(0,1fr);min-height:100vh;max-width:1480px;margin:0 auto}
.side{background:linear-gradient(180deg,#FFFFFF 0%,#F1EFFD 100%);border-right:1px solid var(--line);padding:24px 16px;
display:flex;flex-direction:column;gap:6px;position:sticky;top:0;height:100vh}
.logo{display:flex;align-items:center;gap:10px;font-weight:700;font-size:20px;color:var(--ink);text-decoration:none;
padding:0 10px 22px}
.nav{display:flex;align-items:center;gap:10px;padding:9px 12px;border-radius:10px;color:#3A3A52;text-decoration:none;font-weight:500}
.nav:hover{background:#F3F1FE}.nav.on{background:var(--purple-tint);color:var(--purple)}
.nav-head{font-size:12.5px;color:var(--muted);padding:16px 12px 4px}
.nav small{margin-left:auto;color:var(--muted);font-size:12px}
.ic{width:18px;height:18px;flex:none}
.promo{margin-top:auto;text-align:center;padding:16px 8px 4px}
.promo-art{width:56px;height:56px;margin:0 auto 10px;border-radius:16px;background:var(--purple-tint);display:grid;place-items:center;color:var(--purple)}
.promo-art .ic{width:28px;height:28px}
.promo b{display:block;font-size:15px;margin-bottom:4px}.promo p{margin:0 0 12px;color:var(--muted);font-size:12.5px}
.btn{display:block;background:#111;color:#fff;border-radius:999px;padding:10px 16px;text-decoration:none;font-weight:600;font-size:13px}
.main{padding:28px 32px 40px;min-width:0}
.top{display:flex;flex-wrap:wrap;gap:8px;align-items:center;justify-content:space-between;margin-bottom:22px}
.live{display:inline-flex;align-items:center;gap:8px;background:var(--card);border:1px solid var(--line);border-radius:999px;
padding:7px 14px;color:var(--muted);font-size:13px}
.live i{width:8px;height:8px;border-radius:50%;background:var(--green)}
h1{font-size:28px;line-height:1.2;margin:0;font-weight:600;letter-spacing:-.01em}
.sub-title{margin:4px 0 0;color:var(--muted)}
h2{font-size:17px;font-weight:600;margin:0}
h3{font-size:13px;font-weight:600;color:var(--muted);margin:0 0 10px}
.muted{color:var(--muted)}.pad{padding:16px 20px;margin:0}
.card{background:var(--card);border:1px solid var(--line);border-radius:16px}
.card-head{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:8px;padding:16px 18px 6px}
.legend{display:flex;gap:14px;color:var(--muted);font-size:12.5px}.legend i{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:6px}
.kpis{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:14px;margin-bottom:16px}
@media(max-width:1200px){.kpis{grid-template-columns:repeat(3,minmax(0,1fr))}}
@media(max-width:700px){.kpis{grid-template-columns:repeat(2,minmax(0,1fr))}}
.kpi{padding:14px 16px}
.kpi-top{display:flex;justify-content:space-between;align-items:center;gap:8px;color:#3A3A52;font-size:13px}
.icon-chip{width:30px;height:30px;border-radius:9px;border:1px solid var(--line);display:grid;place-items:center;color:var(--ink);
box-shadow:0 1px 2px rgba(23,23,43,.06)}.icon-chip .ic{width:16px;height:16px}
.kpi-value{font-size:24px;font-weight:600;margin:10px 0 2px;letter-spacing:-.01em;font-variant-numeric:tabular-nums}
.delta{margin:0;font-size:12px;color:var(--muted)}.delta b{color:var(--green);font-weight:600}
.grid2{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:16px;margin-bottom:16px}
@media(max-width:1000px){.grid2{grid-template-columns:1fr}}
.list{list-style:none;margin:0;padding:4px 10px 10px}
.row{display:flex;align-items:center;gap:12px;padding:10px 8px;border-radius:10px;color:inherit;text-decoration:none}
a.row:hover{background:#F7F6FD}
.list li+li{border-top:1px solid #F3F2F8}
.row-main,.row-side{display:flex;flex-direction:column;min-width:0}.row-main{flex:1}.row-side{text-align:right}
.row b{font-weight:600}.row small{color:var(--muted);font-size:12px}
.row-main b,.row-side b,.row small{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.avatar{width:36px;height:36px;border-radius:10px;background:var(--purple-tint);color:var(--purple);display:grid;place-items:center;
font-weight:700;flex:none}
.pill{border-radius:999px;padding:2px 10px;font-size:12px;font-weight:500;background:#F1F0F6;color:#4A4A62;white-space:nowrap}
.pill.ok{background:var(--green-tint);color:var(--green)}.pill.warn{background:var(--amber-tint);color:var(--amber)}
.pill.bad{background:var(--red-tint);color:var(--red)}
.synthetic{font-size:11.5px;background:#FFF6D6;color:#8A6A00;border-radius:999px;padding:2px 9px;font-weight:500}
.chart{position:relative;height:260px;padding:6px 14px 14px}
.call{overflow:hidden;margin-bottom:16px}
.call-head{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:center;gap:8px 16px;padding:14px 20px;border-bottom:1px solid var(--line)}
.who{font-size:18px;font-weight:600;color:var(--ink);text-decoration:none}a.who:hover{color:var(--purple)}
.place{color:var(--muted);margin-left:8px}
.meta{display:flex;flex-wrap:wrap;gap:6px;align-items:center;color:var(--muted);font-size:13px}.meta time{margin-right:4px}
.call-body{display:grid;grid-template-columns:minmax(0,1.6fr) minmax(0,1fr)}
@media(max-width:800px){.call-body{grid-template-columns:1fr}.records{border-left:0!important;border-top:1px solid var(--line)}}
.convo{list-style:none;margin:0;padding:16px 20px;max-height:480px;overflow:auto;display:flex;flex-direction:column;gap:10px}
.line{display:flex;flex-direction:column;max-width:82%}
.line.farmer{align-self:flex-end;align-items:flex-end}
.sp{font-size:11.5px;color:var(--muted);margin:0 6px 2px}
.bubble{background:#F4F3F9;border-radius:14px 14px 14px 4px;padding:8px 12px}
.line.farmer .bubble{background:var(--purple-tint);border-radius:14px 14px 4px 14px}
.bubble p{margin:0}.line.farmer .t{color:#2A2366}
.orig{font-size:12px;color:var(--muted);margin-top:4px!important}
mark{background:#D7D2FB;color:inherit;border-radius:4px;padding:0 2px;box-shadow:inset 0 -2px 0 var(--purple)}
mark.k-observation{background:#F9D3CF;box-shadow:inset 0 -2px 0 var(--red)}
mark.k-harvest{background:#FBE1C8;box-shadow:inset 0 -2px 0 var(--peach)}
.records{border-left:1px solid var(--line);padding:16px 20px;display:flex;flex-direction:column;gap:12px;background:#FBFAFE}
.records h3{margin:0}
.slip{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 14px}
.slip p{margin:0}.slip-top{display:flex;justify-content:space-between;align-items:center;gap:8px}
.kind{font-size:12.5px;color:var(--muted);display:flex;align-items:center;gap:6px}
.dot{display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--purple)}
.k-observation .dot{background:var(--red)}.k-harvest .dot{background:var(--peach)}.k-activity .dot,.k-other .dot{background:var(--muted)}
.slip-main{font-size:17px;font-weight:600;margin:4px 0 2px!important;font-variant-numeric:tabular-nums}
.slip blockquote{margin:8px 0 0;color:#4A4A62;font-size:13px;border-left:3px solid var(--line);padding-left:10px}
.ok-mark{color:var(--green);font-weight:700}.bad-mark{color:var(--red);font-weight:700}
details.older summary{cursor:pointer;padding:14px 20px;color:var(--purple);font-weight:500}
.section-title{display:flex;align-items:baseline;justify-content:space-between;margin:24px 0 12px}
footer{color:var(--muted);font-size:12.5px;margin-top:28px}
@media(max-width:900px){.shell{grid-template-columns:1fr}.side{position:static;height:auto;flex-direction:row;flex-wrap:wrap;
align-items:center;padding:12px 16px}.logo{padding:0 8px 0 0}.nav-head,.promo,.side .farmer-link{display:none}.main{padding:20px 16px}}
"""

FOOTER = "<footer>Weather data by Open-Meteo.com (CC BY 4.0). Synthetic demo data.</footer>"
CALL_LINK = ("<div class=promo><div class=promo-art>" + _icon("phone") + "</div><b>Try the hotline</b>"
             "<p>Phone +1 628 272 9173, or talk to the agent in your browser.</p>"
             "<a class=btn href=/ target=_blank rel=noopener>Open the call page</a></div>")


def _sidebar(active: str, farmers: list[dict] | None) -> str:
    links = [f"<a class='nav{' on' if active == 'calls' else ''}' href=/demo>{_icon('grid')}Live calls</a>"]
    if farmers:
        links.append("<p class=nav-head>Recent callers</p>")
        for f in farmers:
            on = " on" if active == f"farmer-{f['id']}" else ""
            links.append(f"<a class='nav farmer-link{on}' href=/demo/farmer/{_e(f['id'])}>{_icon('user')}"
                         f"{_e(f['first_name'])}<small>{_e(f.get('village') or '')}</small></a>")
    return (f"<nav class=side><a class=logo href=/demo>{LOGO}Coffee line</a>{''.join(links)}{CALL_LINK}</nav>")


def _page(title: str, body: str, refresh: bool, head: str = "", active: str = "", farmers: list[dict] | None = None,
          sidebar: bool = True) -> str:
    meta = f"<meta http-equiv=refresh content={REFRESH_SECS}>" if refresh else ""
    side = _sidebar(active, farmers) if sidebar else ""
    return (
        f"<!doctype html><html lang=en><head><meta charset=utf-8>{meta}"
        f"<meta name=viewport content='width=device-width,initial-scale=1'>"
        f"<link rel=preconnect href=https://fonts.gstatic.com crossorigin><link rel=stylesheet href='{FONTS}'>"
        f"<title>{_e(title)}</title><style>{_CSS}</style>{head}</head><body>"
        f"<div class=shell{'' if sidebar else ' style=grid-template-columns:1fr'}>{side}<main class=main>{body}{FOOTER}</main></div>"
        f"</body></html>"
    )


_TREND_JS = """<script>
(function () {
  var el = document.getElementById('trend-data'); if (!el || !window.Chart) return;
  var d = JSON.parse(el.textContent);
  Chart.defaults.font.family = "'Plus Jakarta Sans', system-ui, sans-serif"; Chart.defaults.color = '#6E6E85';
  new Chart(document.getElementById('trend'), {type: 'line', data: {labels: d.map(function (r) { return r.label; }), datasets: [
    {label: 'Calls', data: d.map(function (r) { return r.calls; }), yAxisID: 'calls', borderColor: '#5B4FE0', backgroundColor: '#5B4FE0',
     tension: 0.4, borderWidth: 2, pointRadius: 0, cubicInterpolationMode: 'monotone'},
    {label: 'Coffee sold (kg)', data: d.map(function (r) { return r.kg; }), yAxisID: 'kg', borderColor: '#F4B98A', backgroundColor: '#F4B98A',
     tension: 0.4, borderWidth: 2, pointRadius: 0, cubicInterpolationMode: 'monotone'}]},
    options: {maintainAspectRatio: false, animation: false, interaction: {mode: 'index', intersect: false},
      plugins: {legend: {display: false}},
      scales: {x: {grid: {color: '#F1F0F6'}}, calls: {beginAtZero: true, grid: {color: '#F1F0F6'}},
               kg: {position: 'right', beginAtZero: true, grid: {drawOnChartArea: false}}}}});
})();
</script>"""


def render_page(view: dict) -> str:
    entries_by_call: dict[Any, list[dict]] = {}
    for entry in view["entries"]:
        entries_by_call.setdefault(entry["call_id"], []).append(entry)
    calls = view["calls"]
    rows = "".join(_call_row(c, entries_by_call.get(c["id"], [])) for c in calls[:6])
    shown = next((c["id"] for c in calls if entries_by_call.get(c["id"])), calls[0]["id"] if calls else None)
    details = "".join(_call_block(c, entries_by_call.get(c["id"], []), open_=c["id"] == shown) for c in calls)
    trend = view.get("trend")
    trend_card = ""
    if trend:
        data = json.dumps(trend, default=float).replace("</", "<\\/")
        trend_card = (
            "<div class='card'><div class=card-head><h2>Calls and coffee sold, last 12 months</h2>"
            "<span class=legend><span><i style=background:#5B4FE0></i>Calls</span>"
            "<span><i style=background:#F4B98A></i>Coffee sold (kg)</span></span></div>"
            f"<div class=chart><canvas id=trend></canvas></div><script type=application/json id=trend-data>{data}</script></div>"
        )
    body = (
        "<div class=top><div><h1>Live calls</h1><p class=sub-title>Farmers' calls turned into farm records, as they happen.</p></div>"
        "<span class=live><i></i>Updates every 10 seconds</span></div>"
        f"{_kpis(view)}"
        "<div class=grid2>"
        f"<div class=card><div class=card-head><h2>Recent calls</h2></div><ul class=list>{rows or '<li class=muted>No calls yet.</li>'}</ul></div>"
        f"<div class=card><div class=card-head><h2>Village prices, last 12 months</h2></div>{_medians(view['medians'])}</div>"
        "</div>"
        f"{trend_card}"
        f"<div class=section-title><h2>Call details</h2></div>{details or '<p class=muted>No calls yet.</p>'}"
    )
    head = f"<script src={CHART_JS}></script>" if trend else ""
    return _page("Live calls", body + (_TREND_JS if trend else ""), refresh=True, head=head, active="calls",
                 farmers=view.get("farmers"))


def render_call_page() -> str:
    """Public page: the browser widget only. No ledger data, no refresh (a reload would end the call)."""
    body = ("<div class=top><div><h1>Talk to the coffee line</h1>"
            "<p class=sub-title>Coffee prices, farm records and crop advice by phone.</p></div></div>"
            "<div class=card style='max-width:640px;padding:18px 20px'><p style=margin:0>Ask about coffee prices in your village, "
            "report a sale, or describe a problem with your trees. Press the button at the bottom of the page and allow the "
            "microphone.</p></div>" + _widget())
    return _page("Coffee line", body, refresh=False, sidebar=False)


def _load() -> dict:
    with db.connect() as conn:
        return load_view(conn)


@router.get("/", response_class=HTMLResponse)
def call_page() -> HTMLResponse:
    return HTMLResponse(render_call_page())


@router.get("/demo", response_class=HTMLResponse, dependencies=[Depends(security.require_demo_basic_auth)])
def demo_page() -> HTMLResponse:
    return HTMLResponse(render_page(_load()))

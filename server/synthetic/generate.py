"""SYNTHETIC Uganda coffee history for the hotline demo (#20, spec section 10). Pure data.

`generate_season()` returns 6 villages, 21 farmers and their calls, Oct 2024 - 3 Oct 2026,
with a fixed seed so every run is identical. It writes nothing to any database: the
loader is #44. Every village, farmer and call is labelled `is_synthetic`.

A call carries the live `calls` columns (source, status, identified_by, consent,
transcript_lines, ...) and its entries are dicts keyed by the live `entries` columns,
all values from the fixed lists in farm_ledger.enums and the migrations.

Prices: anchor (UCDA monthly report, see anchors.py) x buyer effect (cooperative +4%,
middleman -6%) x village effect (within +-3%) x jitter (+-5%), rounded to 50 UGX/kg.

Planted cases (each is a call with `planted` set):
  twig_borer_cluster  3 farms in Kasaali parish (Masaka), 12-26 Sep 2026: the demo cluster
  distress_sale       a Mubende kiboko sale at -35% of the month's anchor
  low_confidence      one FAQ sale with confidence 0.46 and "[unclear]" in the transcript
  price_slip          a Bushenyi sale whose price_total has an extra zero (x10)
  bag_without_kg      a Bushenyi sale of one bag with no weight, so no amount_kg
  yield_drop          two farmers (Mubende, Bududa) whose 2026 fly-crop harvest is 50-60% of 2025's
  wilt, leaf_rust, berry_disease   two reports each, never 3 farms in one parish
Nakato (PIN 9001, Kyabakuza) has a last sale of 400 kg at 5,300 UGX/kg on 18 Jul 2026.
"""

import random
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime, time, timedelta

from farm_ledger import BuyerType, Currency, Kind, PaidHow, Unit
from farm_ledger.db import ENTRY_FIELDS
from farm_ledger.enums import CoffeeForm

from .anchors import anchor_price
from .transcripts import OBSERVATIONS, bag_sale_turns, harvest_turns, observation_turns, render, sale_turns
from .villages import VILLAGES, Village

SEED = 20261004
AS_OF = date(2026, 10, 3)  # "today" for every relative date, so runs are reproducible
PERIOD_START = date(2024, 10, 1)
PIN_START = 9001  # synthetic PINs are 9001-9021; new registrations never get 9000-9099
GPS_JITTER = 0.01  # degrees, about 1 km
PRICE_JITTER = 0.05
PRICE_STEP = 50  # UGX per kg
BUYER_EFFECT = {BuyerType.COOPERATIVE: 1.04, BuyerType.MIDDLEMAN: 0.94, BuyerType.OTHER: 1.0}
DISTRESS_FACTOR = 0.65
SLIP_FACTOR = 10
SEASON_LEAD_DAYS = 30  # a season counts once it started this long before AS_OF
FIRST_LOT_DELAY, LAST_LOT_DELAY = 10, 15  # days after the season start / end
SOLD_SHARE = (0.85, 0.95)
LOT_COUNTS = (2, 3, 3, 4)
LOT_KG = {  # (min, max) kg of one sale, per coffee form (issue #20)
    CoffeeForm.KIBOKO: (150, 600), CoffeeForm.FAQ: (80, 300), CoffeeForm.PARCHMENT: (60, 250),
}
KG_STEP = 5
NORMAL_CONFIDENCE = (0.80, 0.98)
LOW_CONFIDENCE = 0.46
BAG_KG = 55  # only used to size the bag sale's price; the entry has no weight
CALL_HOURS_UTC = (14, 16)  # 17:00-19:59 in Kampala
MIDDLEMEN = ("Ssebugwawo", "Okello", "Kiiza", "Wasswa")

# Call and village fields: the fixed lists in supabase/migrations/20261004040000_uganda_hotline.sql.
SOURCE, STATUS, IDENTIFIED_BY, CONSENT, LANGUAGE = "synthetic", "processed", "pin", "yes", "sw"

ENTRY_COLUMNS = (*ENTRY_FIELDS, "coffee_form", "coffee_type", "amount_kg")


@dataclass(frozen=True)
class Farmer:
    name: str  # first name only
    pin: str
    village: int  # index into Season.villages
    lat: float
    lon: float
    is_synthetic: bool = True


@dataclass(frozen=True)
class Call:
    farmer: int  # index into Season.farmers
    received_at: datetime  # timezone-aware, UTC
    duration_secs: int
    transcript_lines: tuple[dict, ...]  # {i, role: agent|farmer, sw, en, t}
    transcript_sw: str
    transcript_en: str
    entries: tuple[dict, ...]  # keyed by ENTRY_COLUMNS
    planted: str | None = None  # the planted case this call carries, if any
    season: str | None = None  # "main-2025": set on harvest calls
    source: str = SOURCE
    status: str = STATUS
    identified_by: str = IDENTIFIED_BY
    consent: str = CONSENT
    language: str = LANGUAGE
    is_synthetic: bool = True


@dataclass(frozen=True)
class Season:
    villages: tuple[Village, ...]
    farmers: tuple[Farmer, ...]
    calls: tuple[Call, ...]


@dataclass(frozen=True)
class Lot:
    day: date
    kg: int
    buyer: BuyerType
    price: int | None = None  # UGX per kg; None means: from the anchor
    factor: float = 1.0
    planted: str | None = None


# Planted lots replace one routine lot: (farmer, season label, year) -> (lot index, changes).
PLANTED_LOTS = {
    ("Byaruhanga", "main", 2025): (1, {"factor": DISTRESS_FACTOR, "planted": "distress_sale"}),
    ("Namatovu", "fly", 2025): (0, {"planted": "low_confidence"}),
    ("Atuhaire", "main", 2025): (1, {"planted": "price_slip"}),
    ("Tumwebaze", "fly", 2026): (0, {"planted": "bag_without_kg"}),
}
# The demo farmer's season: three lots, the last one 400 kg at 5,300 UGX/kg to a middleman.
DEMO_SEASON = ("Nakato", "main", 2026)
DEMO_HARVEST_KG = 1050
DEMO_LOTS = (
    Lot(date(2026, 6, 6), 250, BuyerType.COOPERATIVE),
    Lot(date(2026, 6, 27), 300, BuyerType.COOPERATIVE),
    Lot(date(2026, 7, 18), 400, BuyerType.MIDDLEMAN, price=5300),
)
HARVEST_FACTOR = {
    ("Tumusiime", "fly", 2026): (0.5, "yield_drop"),
    ("Wamoto", "fly", 2026): (0.6, "yield_drop"),
}
# (farmer, case, day, planted tag): disease reports. Only the twig borer reaches 3 farms.
REPORTS = (
    ("Kasule", "twig_borer", date(2026, 9, 12), "twig_borer_cluster"),
    ("Namusoke", "twig_borer", date(2026, 9, 19), "twig_borer_cluster"),
    ("Nalwoga", "twig_borer", date(2026, 9, 26), "twig_borer_cluster"),
    ("Tumusiime", "wilt", date(2026, 6, 20), "wilt"),
    ("Nabirye", "wilt", date(2026, 7, 11), "wilt"),
    ("Mafabi", "leaf_rust", date(2025, 12, 9), "leaf_rust"),
    ("Nambozo", "leaf_rust", date(2026, 3, 4), "leaf_rust"),
    ("Wamoto", "berry_disease", date(2026, 4, 22), "berry_disease"),
    ("Nandutu", "berry_disease", date(2026, 5, 13), "berry_disease"),
)


def generate_season(seed: int = SEED) -> Season:
    rng = random.Random(seed)
    farmers = _farmers(rng)
    index = {f.name: i for i, f in enumerate(farmers)}
    calls = [call for i, farmer in enumerate(farmers) for call in _farmer_calls(rng, i, farmer)]
    calls += [_report_call(rng, farmers, index[name], key, day, tag) for name, key, day, tag in REPORTS]
    return Season(VILLAGES, farmers, tuple(sorted(calls, key=lambda c: (c.received_at, c.farmer))))


def _farmers(rng) -> tuple[Farmer, ...]:
    names = [(v_index, name) for v_index, v in enumerate(VILLAGES) for name in v.farmers]
    return tuple(
        Farmer(name, str(PIN_START + i), v_index,
               round(VILLAGES[v_index].lat + rng.uniform(-GPS_JITTER, GPS_JITTER), 5),
               round(VILLAGES[v_index].lon + rng.uniform(-GPS_JITTER, GPS_JITTER), 5))
        for i, (v_index, name) in enumerate(names)
    )


def _month_end(year: int, month: int) -> date:
    return date(year + month // 12, month % 12 + 1, 1) - timedelta(days=1)


def _occurrences(village: Village):
    """(season, year, start, end) for each crop season in the period, oldest first."""
    found = []
    for year in range(PERIOD_START.year, AS_OF.year + 1):
        for season in village.seasons:
            start = date(year, season.start_month, 1)
            end_year = year if season.end_month >= season.start_month else year + 1
            if PERIOD_START <= start <= AS_OF - timedelta(days=SEASON_LEAD_DAYS):
                found.append((season, year, start, _month_end(end_year, season.end_month)))
    return sorted(found, key=lambda o: o[2])


def _confidence(rng) -> float:
    return round(rng.uniform(*NORMAL_CONFIDENCE), 2)


def _entry(**fields) -> dict:
    return {column: fields.get(column) for column in ENTRY_COLUMNS}


def _make_call(rng, farmer: int, day: date, middle, entries, **labels) -> Call:
    lines, sw, en, secs = render(middle)
    at = datetime.combine(day, time(rng.randint(*CALL_HOURS_UTC), rng.randint(0, 59)), tzinfo=UTC)
    return Call(farmer, at, secs, tuple(lines), sw, en, tuple(entries), **labels)


def _farmer_calls(rng, index: int, farmer: Farmer) -> list[Call]:
    village = VILLAGES[farmer.village]
    annual = round(rng.randint(*village.annual_kg), -1)
    calls = []
    for season, year, start, end in _occurrences(village):
        key = (farmer.name, season.label, year)
        kg = round(annual * season.share * rng.uniform(0.88, 1.12), -1)
        factor, tag = HARVEST_FACTOR.get(key, (1.0, None))
        kg = DEMO_HARVEST_KG if key == DEMO_SEASON else int(kg * factor)
        harvest_day = min(start + (end - start) // 2 + timedelta(days=rng.randint(-7, 7)), AS_OF)
        calls.append(_harvest_call(rng, index, village, harvest_day, kg, f"{season.label}-{year}", tag))
        calls += [_sale_call(rng, index, village, lot) for lot in _lots(rng, key, village, start, end, kg)]
    return calls


def _lots(rng, key, village: Village, start: date, end: date, harvest_kg: int) -> list[Lot]:
    """The sales of one season. The rng draws happen even for fixed lots, so the others don't shift."""
    first = start + timedelta(days=FIRST_LOT_DELAY)
    last = min(end + timedelta(days=LAST_LOT_DELAY), AS_OF - timedelta(days=1))
    sellable = harvest_kg * rng.uniform(*SOLD_SHARE)
    min_kg, max_kg = LOT_KG[village.form]
    count = max(-(-int(sellable) // max_kg), min(rng.choice(LOT_COUNTS), int(sellable) // min_kg), 1)
    offsets = rng.sample(range((last - first).days + 1), count)
    days = sorted(first + timedelta(days=d) for d in offsets)
    weights = [rng.uniform(0.6, 1.4) for _ in days]
    kinds, shares = zip(*village.buyer_weights, strict=True)
    buyers = [rng.choices(kinds, shares)[0] for _ in days]
    sizes = _lot_sizes(sellable, weights, min_kg, max_kg)
    lots = [Lot(day, kg, buyer) for day, kg, buyer in zip(days, sizes, buyers, strict=True)]
    if key == DEMO_SEASON:
        return list(DEMO_LOTS)
    if key in PLANTED_LOTS:
        position, changes = PLANTED_LOTS[key]
        lots[position] = replace(lots[position], **changes)
    return lots


def _lot_sizes(sellable: float, weights: list[float], min_kg: int, max_kg: int) -> list[int]:
    """Every lot gets min_kg, the rest of what is sellable is shared by weight, no lot above max_kg.
    The total never exceeds `sellable` (a farmer with less than min_kg sells one smaller lot)."""
    if sellable < min_kg:
        return [int(sellable // KG_STEP) * KG_STEP]
    spare = sellable - min_kg * len(weights)
    return [
        min_kg + min(max_kg - min_kg, int(spare * w / sum(weights) // KG_STEP) * KG_STEP)
        for w in weights
    ]


def _unit_price(rng, village: Village, lot: Lot) -> int:
    if lot.price:
        return lot.price
    base = anchor_price(lot.day, village.form) * BUYER_EFFECT[lot.buyer] * (1 + village.effect)
    jittered = base * rng.uniform(1 - PRICE_JITTER, 1 + PRICE_JITTER) * lot.factor
    return int(round(jittered / PRICE_STEP) * PRICE_STEP)


def _paid_how(rng, buyer: BuyerType) -> PaidHow:
    if buyer == BuyerType.COOPERATIVE:
        return rng.choices([PaidHow.MOBILE_MONEY, PaidHow.CASH], [0.8, 0.2])[0]
    if buyer == BuyerType.MIDDLEMAN:
        return rng.choices([PaidHow.CASH, PaidHow.MOBILE_MONEY], [0.7, 0.3])[0]
    return PaidHow.CASH


def _sale_call(rng, farmer: int, village: Village, lot: Lot) -> Call:
    price = _unit_price(rng, village, lot)
    buyer_name = rng.choice(MIDDLEMEN) if lot.buyer == BuyerType.MIDDLEMAN else None
    paid = _paid_how(rng, lot.buyer)
    confidence = _confidence(rng)
    common = {
        "kind": Kind.SALE.value, "crop": "coffee", "currency": Currency.UGX.value,
        "date_sold": lot.day, "coffee_form": village.form.value, "coffee_type": village.coffee_type.value,
        "quote_verified": True, "confidence": confidence,
    }
    if lot.planted == "bag_without_kg":
        total = round(price * BAG_KG, -3)
        middle, quote = bag_sale_turns(village.form, total, buyer_name or MIDDLEMEN[0])
        entry = _entry(**common, amount=1, unit=Unit.BAG.value, price_total=total,
                       buyer_type=BuyerType.MIDDLEMAN.value, buyer_name=buyer_name or MIDDLEMEN[0], paid_how=PaidHow.CASH.value, evidence_quote=quote,
                       description=f"Sold one bag of {village.form.value} for {total:,} UGX; no weight given.")
        return _make_call(rng, farmer, lot.day, middle, (entry,), planted=lot.planted)
    unclear = lot.planted == "low_confidence"
    middle, quote = sale_turns(lot.kg, village.form, price, lot.buyer, buyer_name, paid,
                               distress=lot.planted == "distress_sale", unclear_price=unclear)
    total = price * lot.kg * (SLIP_FACTOR if lot.planted == "price_slip" else 1)  # the slip is in the entry only
    entry = _entry(**common, amount=lot.kg, unit=Unit.KG.value, amount_kg=lot.kg, price_total=total,
                   buyer_type=lot.buyer.value, buyer_name=buyer_name, paid_how=paid.value, evidence_quote=quote,
                   description=f"Sold {lot.kg} kg of {village.form.value} at {price:,} UGX per kg.")
    if unclear:
        entry = {**entry, "confidence": LOW_CONFIDENCE}
    return _make_call(rng, farmer, lot.day, middle, (entry,), planted=lot.planted)


def _harvest_call(rng, farmer: int, village: Village, day: date, kg: int, season: str, planted) -> Call:
    middle, quote = harvest_turns(kg, village.form)
    entry = _entry(kind=Kind.HARVEST.value, crop="coffee", yield_amount=kg, unit=Unit.KG.value,
                   coffee_form=village.form.value, coffee_type=village.coffee_type.value, evidence_quote=quote,
                   quote_verified=True, description=f"Harvested {kg} kg of {village.form.value} ({season}).",
                   confidence=_confidence(rng))
    return _make_call(rng, farmer, day, middle, (entry,), planted=planted, season=season)


def _report_call(rng, farmers, farmer: int, key: str, day: date, tag: str) -> Call:
    case = OBSERVATIONS[key]
    village = VILLAGES[farmers[farmer].village]
    entry = _entry(kind=Kind.OBSERVATION.value, crop="coffee", coffee_type=village.coffee_type.value,
                   disease_detected=True, symptom=case.symptom, likely_disease=case.likely_disease,
                   disease_confidence=case.disease_confidence, evidence_quote=case.quote, quote_verified=True,
                   description=case.farmer[1], confidence=_confidence(rng))
    return _make_call(rng, farmer, day, observation_turns(case), (entry,), planted=tag)

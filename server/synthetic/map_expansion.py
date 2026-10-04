"""SYNTHETIC map-dashboard expansion: ~22 villages in 14 more coffee districts. Additive, reversible.

CLI (run from server/, psycopg needed: `uv run --with "psycopg[binary]" python -m ...`):
  --dry-run  print counts, no DB access
  --apply    remove the previous expansion rows, then insert, in ONE transaction (idempotent)
  --remove   delete exactly the expansion rows (entries, calls, farmers, villages)

Rows are identified by the village keys below and by calls.conversation_id 'synmap-%'. The five
demo districts (Masaka, Mubende, Bududa, Zombo, Bushenyi) are never used. Nothing prints a secret.

Planted: Kayunga prices (factor 0.80, ~80% middlemen) and a coffee wilt cluster in Ibanda /
Kikyenkye parish (4 farmers, 2026-09-16 .. 2026-10-01).
"""

import argparse
import csv
import hashlib
import json
import os
import random
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path

from . import supabase as loader
from .anchors import anchor_price
from farm_ledger.enums import CoffeeForm

SEED = 20261005
AS_OF = date(2026, 10, 3)
LAST_DAY = AS_OF - timedelta(days=1)
LAST_ANCHOR_DAY = date(2026, 9, 30)  # no October anchor yet
SALES_START = date(2025, 10, 4)  # 12 months before AS_OF
RECENT_DAYS = 30
RECENT_FARMERS = 15
FARMER_HISTORY_DAYS = 548  # ~18 months
CONVERSATION_PREFIX = "synmap-"
COORD_OFFSET = 0.12
DISTRICTS_CSV = Path(__file__).resolve().parents[2] / "hotline/hotline/data/uganda_districts.csv"
ENV_PATH = Path(__file__).resolve().parents[2].parent / "Hack-Nation_World-Bank-Agriculture-Case/.env"
DEMO_DISTRICTS = ("Masaka", "Mubende", "Bududa", "Zombo", "Bushenyi")
PIN_RANGE = (1000, 8999)  # never 9000-9099 (synthetic demo farmers)
CALL_HOURS_UTC = (6, 14)  # 09:00-17:59 Kampala
KG_RANGE = (50, 600)

PLANTED_PRICE_DISTRICT = "Kayunga"
PLANTED_FACTOR = 0.80
PLANTED_MIDDLEMAN_SHARE = 0.80
WILT_DISTRICT, WILT_PARISH = "Ibanda", "Kikyenkye"
WILT_DAYS = (date(2026, 9, 16), date(2026, 9, 21), date(2026, 9, 26), date(2026, 10, 1))
WILT_QUIET_FROM = date(2026, 6, 23)  # 12 weeks before the first wilt report: no problems in the parish
BACKGROUND_GAP_DAYS = 95

ARABICA = {"Mbale", "Sironko", "Kapchorwa", "Nebbi", "Kasese"}
# (district, sub_county, parish, village, farmer_count or None for random 3-9)
VILLAGE_SPECS = (
    ("Mbale", "Bungokho", "Namabasa", "Bukonde", None), ("Mbale", "Busiu", "Bumbo", "Nakitale", None),
    ("Sironko", "Budadiri", "Buwalasi", "Masaaba", None), ("Sironko", "Bukhulo", "Bukiende", "Kapsinda", None),
    ("Kapchorwa", "Tegeres", "Kaptanya", "Chebonet", None),
    ("Nebbi", "Paidha", "Akaba", "Orussi", None),
    ("Kasese", "Bugoye", "Maliba", "Kyarumba", None),
    ("Ibanda", "Ishongororo", WILT_PARISH, "Kitojo", 6), ("Ibanda", "Ishongororo", WILT_PARISH, "Rwamuhanda", 5),
    ("Ibanda", "Nyamarebe", "Kyeizooba", "Nyakashambya", None),
    ("Mitooma", "Kashenshero", "Rurehe", "Bugongi", None),
    ("Ntungamo", "Rubaare", "Nyakyera", "Kagarama", None), ("Ntungamo", "Rubaare", "Rugarama", "Kibingo", None),
    ("Mukono", "Kyampisi", "Ngogwe", "Lwanyonyi", None), ("Mukono", "Nama", "Kasawo", "Kasenge", None),
    ("Luwero", "Kikyusa", "Bamunanika", "Kalagala", None),
    ("Mityana", "Kalangaalo", "Bulera", "Kisoga", None),
    ("Kayunga", "Busaana", "Kangulumira", "Kitimbwa", None), ("Kayunga", "Busaana", "Kangulumira", "Nakalanga", None),
    ("Kayunga", "Nazigo", "Kasana", "Bukolwa", None),
    ("Lwengo", "Kkingo", "Kyazanga", "Nakiwala", None),
    ("Kamuli", "Namasagali", "Kitayundwa", "Bukoona", None), ("Kamuli", "Balawoli", "Butansi", "Kagulu", None),
    ("Rakai", "Kyalulangira", "Kasasa", "Nsambya", None), ("Rakai", "Kakuuto", "Kibanda", "Kyamuyimbwa", None),
    ("Kyenjojo", "Butunduzi", "Kihuura", "Rwenjaza", None), ("Kyenjojo", "Kyarusozi", "Nyantungo", "Kabagole", None),
    ("Mbale", "Wanale", "Bunambutye", "Namatala", None), ("Kasese", "Rukoki", "Kisinga", "Kithoma", None),
    ("Sironko", "Zesui", "Bumasikye", "Bufumbo", None), ("Mukono", "Goma", "Seeta", "Nakisunga", None),
)
REGION_PROBLEMS = {  # background disease priors by zone
    "elgon": ("coffee_leaf_rust", "coffee_berry_disease"),
    "southwest": ("coffee_wilt_disease", "black_coffee_twig_borer"),
    "central": ("black_coffee_twig_borer",),
    "westnile": ("coffee_leaf_rust",),
    "rwenzori": ("coffee_leaf_rust", "coffee_berry_disease"),
    "eastern": ("coffee_leaf_rust", "black_coffee_twig_borer"),
}
ZONE = {
    **dict.fromkeys(("Mbale", "Sironko", "Kapchorwa"), "elgon"), "Nebbi": "westnile", "Kasese": "rwenzori",
    **dict.fromkeys(("Ibanda", "Mitooma", "Ntungamo"), "southwest"),
    **dict.fromkeys(("Mukono", "Luwero", "Mityana", "Kayunga", "Lwengo"), "central"), "Kamuli": "eastern", "Rakai": "central", "Kyenjojo": "southwest",
}
DISEASE = {  # likely_disease -> (symptom, Swahili, English)
    "coffee_wilt_disease": ("wilting", "Miti ya kahawa inanyauka na majani yanakauka.", "The coffee trees are wilting and the leaves dry up."),
    "coffee_leaf_rust": ("powder_or_rust", "Majani yana vumbi la rangi ya machungwa upande wa chini.", "The leaves have orange powder underneath."),
    "coffee_berry_disease": ("fruit_spots", "Matunda ya kahawa yana madoa meusi.", "The coffee berries have dark spots."),
    "black_coffee_twig_borer": ("wilting", "Matawi yanakauka na kuna vitundu vidogo.", "The twigs are drying with small holes."),
}
FIRST_NAMES = ("Grace", "Moses", "Sarah", "John", "Rose", "Peter", "Agnes", "David", "Mary", "Joseph", "Esther", "Robert",
               "Juliet", "Samuel", "Betty", "Patrick", "Annet", "Isaac", "Joan", "Francis", "Harriet", "Emmanuel",
               "Prossy", "Charles", "Immaculate", "Denis", "Winnie", "Geoffrey", "Scovia", "Richard")
SURNAMES = ("Nakato", "Okello", "Mugisha", "Namukasa", "Tumusiime", "Wanyama", "Kiiza", "Nabirye", "Byaruhanga",
            "Atim", "Ssemwogerere", "Akello", "Kato", "Namubiru", "Muhumuza", "Wasike", "Nalubega", "Opio",
            "Kabagambe", "Nambozo", "Masaba", "Auma", "Turyahabwe", "Nakimera", "Kyomuhendo", "Ochieng", "Babirye",
            "Mwesigwa", "Namatovu", "Khaemba")


@dataclass(frozen=True)
class VillageRow:
    region: str
    district: str
    sub_county: str
    parish: str
    village: str
    lat: float
    lon: float
    coffee_type: str
    farmer_count: int

    @property
    def key(self) -> tuple[str, str, str, str]:
        return (self.district, self.sub_county, self.parish, self.village)


@dataclass(frozen=True)
class FarmerRow:
    name: str
    pin: str
    village: int  # index into Plan.villages
    created_at: datetime
    is_recent: bool


@dataclass(frozen=True)
class CallRow:
    farmer: int
    received_at: datetime
    conversation_id: str
    identified_by: str
    sw: str
    en: str
    duration_secs: int
    entries: tuple[dict, ...]


@dataclass(frozen=True)
class Plan:
    villages: tuple[VillageRow, ...]
    farmers: tuple[FarmerRow, ...]
    calls: tuple[CallRow, ...]


def _read_districts() -> dict[str, tuple[str, float, float]]:
    with DISTRICTS_CSV.open(newline="") as handle:
        rows = csv.DictReader(line for line in handle if not line.startswith("#"))
        return {r["district"]: (r["region"], float(r["lat"]), float(r["lon"])) for r in rows}


def _build_villages(rng: random.Random) -> tuple[VillageRow, ...]:
    centroids = _read_districts()
    villages = []
    for district, sub_county, parish, village, count in VILLAGE_SPECS:
        assert district not in DEMO_DISTRICTS
        region, lat, lon = centroids[district]
        villages.append(VillageRow(
            region, district, sub_county, parish, village,
            round(lat + rng.uniform(-COORD_OFFSET, COORD_OFFSET), 5),
            round(lon + rng.uniform(-COORD_OFFSET, COORD_OFFSET), 5),
            "arabica" if district in ARABICA else "robusta", count or rng.randint(4, 9),
        ))
    return tuple(villages)


def _utc(day: date, rng: random.Random) -> datetime:
    return datetime.combine(day, time(rng.randint(*CALL_HOURS_UTC), rng.randint(0, 59)), tzinfo=UTC)


def _rand_day(rng: random.Random, start: date, end: date) -> date:
    return start + timedelta(days=rng.randint(0, max(0, (end - start).days)))


def _build_farmers(rng: random.Random, villages: tuple[VillageRow, ...]) -> tuple[FarmerRow, ...]:
    slots = [(i, n) for i, v in enumerate(villages) for n in range(v.farmer_count)]
    protected = {s for s in slots if villages[s[0]].parish == WILT_PARISH}
    candidates = [s for s in slots if s not in protected]
    recent = set(rng.sample(candidates, RECENT_FARMERS))
    used_pins: set[str] = set()
    used_names: set[str] = set()
    farmers = []
    for index, slot in slots_with_index(slots):
        while True:
            name = f"{rng.choice(FIRST_NAMES)} {rng.choice(SURNAMES)}"
            if name not in used_names:
                used_names.add(name)
                break
        while True:
            pin = str(rng.randint(*PIN_RANGE))
            if pin not in used_pins:
                used_pins.add(pin)
                break
        is_recent = slot in recent
        if is_recent:
            created = _utc(AS_OF - timedelta(days=rng.randint(3, RECENT_DAYS - 1)), rng)
        elif slot in protected:
            created = _utc(AS_OF - timedelta(days=rng.randint(100, FARMER_HISTORY_DAYS)), rng)
        else:
            created = _utc(AS_OF - timedelta(days=rng.randint(RECENT_DAYS + 1, FARMER_HISTORY_DAYS)), rng)
        farmers.append(FarmerRow(name, pin, slot[0], created, is_recent))
    return tuple(farmers)


def slots_with_index(slots):
    return enumerate(slots)


STICKY_SHARE = 0.75
DISTRESS_P, DISTRESS_RANGE = 0.15, (0.60, 0.75)  # inside the harvest-start windows (~5% of all sales)
HARVEST_STARTS = ((10, 11), (4, 5))  # month ranges where early cash need bites
PRICE_NOISE = 0.07


def _buyer_factor(rng, buyer: str, remote: float) -> float:
    if buyer == "middleman":  # remote villages get the worst middleman prices
        return 0.95 - 0.17 * (0.5 * remote + 0.5 * rng.random())
    if buyer == "cooperative":  # a quarter of co-ops pay a quality / certification premium
        return rng.uniform(1.04, 1.08) if rng.random() < 0.25 else rng.uniform(0.97, 1.04)
    return rng.uniform(0.88, 1.00)


def _pick_buyer(rng, village: VillageRow, remote: float, preferred: str) -> str:
    if village.district == PLANTED_PRICE_DISTRICT:
        return "middleman" if rng.random() < PLANTED_MIDDLEMAN_SHARE else rng.choice(("cooperative", "other"))
    if rng.random() < STICKY_SHARE:
        return preferred
    return "middleman" if rng.random() < 0.40 + 0.30 * remote else rng.choice(("cooperative", "cooperative", "other"))


def _sale_entry(rng, village: VillageRow, day: date, ctx: dict, remote: float, preferred: str) -> dict:
    district_factor = ctx["district"]
    district = village.district
    arabica = village.coffee_type == "arabica"
    if arabica:
        form = CoffeeForm.PARCHMENT
    elif district == PLANTED_PRICE_DISTRICT:
        form = CoffeeForm.KIBOKO
    else:
        form = CoffeeForm.FAQ if rng.random() < 0.30 else CoffeeForm.KIBOKO
    buyer = _pick_buyer(rng, village, remote, preferred)
    kg = rng.randint(*KG_RANGE)
    per_kg = (anchor_price(min(day, LAST_ANCHOR_DAY), form) * district_factor[district]
              * (1.03 - 0.13 * remote) * _buyer_factor(rng, buyer, remote)
              * (1 + rng.uniform(-PRICE_NOISE, PRICE_NOISE)))
    in_start = any(a <= day.month <= b for a, b in HARVEST_STARTS)
    if in_start and rng.random() < DISTRESS_P:
        per_kg *= rng.uniform(*DISTRESS_RANGE)
    return {
        "kind": "sale", "crop": "coffee", "amount": float(kg), "amount_kg": float(kg), "unit": "kg",
        "currency": "UGX", "price_total": round(per_kg * kg), "date_sold": day, "buyer_type": buyer,
        "paid_how": rng.choice(("cash", "mobile_money")), "coffee_form": form.value,
        "coffee_type": village.coffee_type, "quote_verified": True, "confidence": 0.9,
        "evidence_quote": f"I sold {kg} kilos of {form.value} coffee.",
        "description": f"Sold {kg} kg of {form.value} coffee to a {buyer}.",
    }


def _sale_call(entry: dict) -> tuple[str, str]:
    kg, price = int(entry["amount_kg"]), int(entry["price_total"])
    sw = f"Niliuza kilo {kg} za kahawa. Nililipwa shilingi {price}."
    return sw, f"I sold {kg} kilos of coffee. I was paid {price} shillings."


def _problem_entry(disease: str) -> tuple[dict, str, str]:
    symptom, sw, en = DISEASE[disease]
    entry = {
        "kind": "observation", "crop": "coffee", "disease_detected": True, "symptom": symptom,
        "likely_disease": disease, "disease_confidence": 0.7, "confidence": 0.9, "quote_verified": True,
        "evidence_quote": en, "description": f"Farmer reports: {en.lower()}",
    }
    return entry, sw, en


def _calls_for(rng, index, farmer, village, events) -> list[CallRow]:
    ordered = sorted(events, key=lambda e: e[0])
    calls = []
    for n, (at, entries, sw, en) in enumerate(ordered):
        calls.append(CallRow(
            index, at, f"{CONVERSATION_PREFIX}{index:03d}-{n + 1}",
            "registration" if n == 0 else "pin", sw, en, rng.randint(55, 190), tuple(entries),
        ))
    return calls


def build_plan() -> Plan:
    rng = random.Random(SEED)
    villages = _build_villages(rng)
    farmers = _build_farmers(rng, villages)
    factors = {d: round(rng.uniform(0.93, 1.04), 3) for d in sorted({v.district for v in villages})}
    factors[PLANTED_PRICE_DISTRICT] = PLANTED_FACTOR
    remote = [rng.random() for _ in villages]  # 0 = on the tarmac, 1 = far from a district town
    ctx = {"district": factors}
    events: dict[int, list] = {i: [] for i in range(len(farmers))}
    wilt_cluster = [i for i, f in enumerate(farmers) if villages[f.village].parish == WILT_PARISH][:4]
    for i, farmer in enumerate(farmers):
        village = villages[farmer.village]
        start = max(farmer.created_at.date(), SALES_START)
        preferred = "middleman" if rng.random() < 0.40 + 0.30 * remote[farmer.village] else rng.choice(("cooperative", "other"))
        days = [_rand_day(rng, start, LAST_DAY) for _ in range(rng.randint(2, 5))]
        if village.district == PLANTED_PRICE_DISTRICT:
            days[0] = _rand_day(rng, max(start, AS_OF - timedelta(days=85)), LAST_DAY)
        for day in days:
            entry = _sale_entry(rng, village, day, ctx, remote[farmer.village], preferred)
            sw, en = _sale_call(entry)
            events[i].append((_utc(day, rng), [entry], sw, en))
    _add_wilt_cluster(rng, farmers, events, wilt_cluster)
    _add_background_problems(rng, farmers, villages, events, set(wilt_cluster))
    _add_advice_calls(rng, farmers, events)
    calls = [c for i, f in enumerate(farmers) for c in _calls_for(rng, i, f, villages[f.village], events[i])]
    farmers = tuple(_align_created(f, [c for c in calls if c.farmer == i]) for i, f in enumerate(farmers))
    return Plan(villages, farmers, tuple(calls))


def _align_created(farmer: FarmerRow, calls: list[CallRow]) -> FarmerRow:
    first = min(c.received_at for c in calls)
    if farmer.is_recent or first < farmer.created_at:
        return FarmerRow(farmer.name, farmer.pin, farmer.village, min(first, farmer.created_at), farmer.is_recent)
    return farmer


def _add_wilt_cluster(rng, farmers, events, cluster) -> None:
    for i, day in zip(cluster, WILT_DAYS, strict=True):
        entry, sw, en = _problem_entry("coffee_wilt_disease")
        events[i].append((_utc(day, rng), [entry], sw, en))


def _add_background_problems(rng, farmers, villages, events, cluster) -> None:
    parishes: dict[tuple[str, str], list[int]] = {}
    for i, f in enumerate(farmers):
        v = villages[f.village]
        parishes.setdefault((v.district, v.parish), []).append(i)
    for (district, parish), members in sorted(parishes.items()):
        if rng.random() < 0.35:
            continue
        end = WILT_QUIET_FROM - timedelta(days=1) if district == WILT_DISTRICT else AS_OF - timedelta(days=14)
        day = _rand_day(rng, SALES_START, SALES_START + timedelta(days=120))
        while day <= end:
            eligible = [i for i in members if i not in cluster and farmers[i].created_at.date() < day]
            if eligible:
                disease = rng.choice(REGION_PROBLEMS[ZONE[district]])
                entry, sw, en = _problem_entry(disease)
                events[rng.choice(eligible)].append((_utc(day, rng), [entry], sw, en))
            day += timedelta(days=BACKGROUND_GAP_DAYS + rng.randint(0, 40))


def _add_advice_calls(rng, farmers, events) -> None:
    sw, en = "Nataka ushauri wa kupogoa kahawa.", "I would like advice on pruning my coffee."
    for i in rng.sample(range(len(farmers)), 8):
        first = min(e[0] for e in events[i])
        day = _rand_day(rng, max(first.date(), SALES_START), LAST_DAY)
        events[i].append((_utc(day, rng), [], sw, en))


# ---- counting ------------------------------------------------------------------------------

def plan_counts(plan: Plan) -> dict[str, int]:
    return {"villages": len(plan.villages), "farmers": len(plan.farmers), "calls": len(plan.calls),
            "entries": sum(len(c.entries) for c in plan.calls)}


def describe(plan: Plan) -> str:
    per_district = Counter(plan.villages[f.village].district for f in plan.farmers)
    kinds = Counter(e["kind"] for c in plan.calls for e in c.entries)
    return "\n".join([
        loader.format_counts("would insert", plan_counts(plan)),
        loader.format_counts("entries by kind", kinds),
        loader.format_counts("farmers by district", per_district),
    ])


# ---- database ------------------------------------------------------------------------------

REMOVE_STATEMENTS = (
    ("entries", "delete from entries where call_id in (select id from calls where conversation_id like 'synmap-%')"),
    ("calls", "delete from calls where conversation_id like 'synmap-%' and is_synthetic"),
    ("farmers", "delete from farmers where is_synthetic and village_id in "
                "(select id from villages where is_synthetic and (district, sub_county, parish, village) in %s)"),
    ("villages", "delete from villages where is_synthetic and (district, sub_county, parish, village) in %s"),
)
INSERT_EXPANSION_CALL = loader.INSERT_CALL.replace(
    "processed_at)", "processed_at, conversation_id)").replace("%s) returning id", "%s, %s) returning id")
ENTRY_COLUMNS = (
    "kind", "crop", "amount", "amount_kg", "unit", "price_total", "currency", "date_sold", "buyer_type",
    "paid_how", "coffee_form", "coffee_type", "disease_detected", "symptom", "likely_disease",
    "disease_confidence", "evidence_quote", "description", "quote_verified", "confidence",
)
INSERT_EXPANSION_ENTRY = (
    f"insert into entries (call_id, farmer_id, {', '.join(ENTRY_COLUMNS)})"
    f" values (%s, %s, {', '.join(['%s'] * len(ENTRY_COLUMNS))})"
)


def _key_literals() -> str:
    return ", ".join(f"({', '.join(repr(p) for p in (d, s, p, v))})" for d, s, p, v, _ in VILLAGE_SPECS)


def remove_expansion(conn) -> dict[str, int]:
    """Delete only expansion rows. Refuses if a non-expansion row references them."""
    keys = _key_literals()
    blockers = conn.execute(
        "select count(*) from farmers f join villages v on v.id = f.village_id"
        f" where (v.district, v.sub_county, v.parish, v.village) in ({keys}) and not f.is_synthetic").fetchone()[0]
    foreign = conn.execute(
        "select count(*) from calls c join farmers f on f.id = c.farmer_id join villages v on v.id = f.village_id"
        f" where (v.district, v.sub_county, v.parish, v.village) in ({keys})"
        " and (c.conversation_id is null or c.conversation_id not like 'synmap-%')").fetchone()[0]
    if blockers or foreign:
        raise loader.ResetRefused(f"refusing: {blockers} real farmers / {foreign} other calls in expansion villages")
    return {table: conn.execute(sql.replace("%s", f"({keys})")).rowcount for table, sql in REMOVE_STATEMENTS}


def _free_pin(salt: str, pin: str, taken: set[str]) -> str:
    candidate = int(pin)
    while True:
        digest = loader.hash_pin(salt, str(candidate))
        if digest not in taken:
            taken.add(digest)
            return digest
        candidate = candidate + 1 if candidate < PIN_RANGE[1] else PIN_RANGE[0]


def insert_plan(conn, plan: Plan, salt: str) -> dict[str, int]:
    taken = {row[0] for row in conn.execute("select pin_hash from farmers").fetchall()}
    village_ids = [conn.execute(loader.INSERT_VILLAGE, (
        v.region, v.district, v.sub_county, v.parish, v.village, v.lat, v.lon, v.coffee_type)).fetchone()[0]
        for v in plan.villages]
    farmer_ids = []
    for f in plan.farmers:
        v = plan.villages[f.village]
        farmer_ids.append(conn.execute(
            "insert into farmers (name, pin_hash, region, lat, lon, village_id, is_synthetic, created_at)"
            " values (%s, %s, %s, %s, %s, %s, true, %s) returning id",
            (f.name, _free_pin(salt, f.pin, taken), v.region, v.lat, v.lon, village_ids[f.village], f.created_at),
        ).fetchone()[0])
    for call in plan.calls:
        lines = [{"i": 0, "role": "farmer", "sw": call.sw, "en": call.en, "t": 0}]
        call_id = conn.execute(INSERT_EXPANSION_CALL, (
            farmer_ids[call.farmer], call.received_at, "sw", call.sw, call.en, "synthetic", "processed",
            call.identified_by, "yes", call.duration_secs, json.dumps(lines), call.received_at,
            call.conversation_id)).fetchone()[0]
        for entry in call.entries:
            conn.execute(INSERT_EXPANSION_ENTRY,
                         (call_id, farmer_ids[call.farmer], *(entry.get(c) for c in ENTRY_COLUMNS)))
    return plan_counts(plan)


def _load_env() -> None:
    if not ENV_PATH.exists():
        return
    for line in ENV_PATH.read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def _connect(url: str):
    import psycopg

    return psycopg.connect(url, prepare_threshold=None, connect_timeout=10, autocommit=False)


def _parse(argv):
    parser = argparse.ArgumentParser(prog="python -m synthetic.map_expansion", description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    for flag in ("--dry-run", "--apply", "--remove"):
        mode.add_argument(flag, action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse(argv)
    plan = build_plan()
    if args.dry_run:
        print(describe(plan))
        return 0
    _load_env()
    salt, url = os.environ.get("LEDGER_PIN_SALT"), os.environ.get("DATABASE_URL")
    try:
        if not url:
            raise loader.LoadError("DATABASE_URL is not set")
        loader.check_salt_gate(salt, os.environ.get("HOTLINE_ADMIN_SECRET"))
        conn = _connect(url)
        try:
            with conn.transaction():
                deleted = remove_expansion(conn)
                inserted = insert_plan(conn, plan, salt) if args.apply else {}
        finally:
            conn.close()
    except loader.LoadError as error:
        print(f"refused: {error}", file=sys.stderr)
        return 1
    print(loader.format_counts("removed", deleted))
    if inserted:
        print(loader.format_counts("inserted", inserted))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

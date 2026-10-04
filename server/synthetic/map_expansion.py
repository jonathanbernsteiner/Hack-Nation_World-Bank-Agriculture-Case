"""SYNTHETIC map-dashboard expansion: ~2,000 farmers in ~29 more coffee districts. Additive, reversible.

CLI (run from server/, psycopg needed: `uv run --with "psycopg[binary]" python -m ...`):
  --dry-run          print counts and the planted-case checks, no DB access
  --apply            remove the previous expansion rows, then insert, in ONE transaction (idempotent)
  --remove           delete exactly the expansion rows (entries, calls, farmers, villages)
  --farmers N        number of farmers (default 2000, 60-2500); villages and districts scale with N

Expansion rows are identified by calls.conversation_id 'synmap-%' (every expansion farmer has at least
one such call). The five demo districts (Masaka, Mubende, Bududa, Zombo, Bushenyi) are never used.
Nothing prints a secret. Inserts are multi-row VALUES batches, so --apply is a few dozen statements.

PINs: the loader's space is 4 digits (hotline.pins: 0000-9999, 9000-9099 reserved, so 9,900 usable).
Expansion PINs are drawn without replacement from 1000-8999 and de-duplicated against every hash already
in the database. 2,021 farmers fill ~20% of the space, so the hotline's random allocation (50 tries) still
finds a free PIN with probability 1 - 0.2**50. --farmers is capped at 2500 (~25% full) for that reason.

Planted: Kayunga prices (factor 0.80, ~80% middlemen) and a coffee wilt cluster in Ibanda /
Kikyenkye parish (4 farmers, 2026-09-16 .. 2026-10-01). Background problem reports stay >= 95 days
apart inside any parish, so no other parish can reach 3 farms in 30 days.
"""

import argparse
import csv
import json
import math
import os
import random
import sys
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path

from farm_ledger.enums import CoffeeForm

from . import supabase as loader
from .anchors import anchor_price

SEED = 20261005
DEFAULT_FARMERS = 2000
MIN_FARMERS, MAX_FARMERS = 60, 2500  # ~14 farmers x ~200 villages is the layout's ceiling
AS_OF = date(2026, 10, 3)
LAST_DAY = AS_OF - timedelta(days=1)
LAST_ANCHOR_DAY = date(2026, 9, 30)  # no October anchor yet
SALES_START = date(2025, 10, 4)  # 12 months before AS_OF
FARMER_HISTORY_DAYS = 730  # registrations spread over 24 months
GROWTH_EXPONENT = 1.2  # >1 skews registrations to recent months (about 2x more in the last month than the first)
NEW_FARMER_DAYS = 90  # farmers registered this recently have only 2-3 sales
SALES_PER_FARMER = (2, 6)
FARMERS_PER_VILLAGE = (6, 14)
PARISHES_PER_DISTRICT = (3, 6)
VILLAGE_COUNT_CHOICES, VILLAGE_COUNT_WEIGHTS = (1, 2, 3), (5.0, 3.5, 1.5)
FARMERS_PER_PROBLEM_REPORT = 8
FARMERS_PER_ADVICE_CALL = 250
CONVERSATION_PREFIX = "synmap-"
CONVERSATION_LIKE = f"{CONVERSATION_PREFIX}%"
COORD_OFFSET = 0.12
DISTRICTS_CSV = Path(__file__).resolve().parents[2] / "hotline/hotline/data/uganda_districts.csv"
ENV_PATH = Path(__file__).resolve().parents[2].parent / "Hack-Nation_World-Bank-Agriculture-Case/.env"
DEMO_DISTRICTS = ("Masaka", "Mubende", "Bududa", "Zombo", "Bushenyi")
PIN_RANGE = (1000, 8999)  # inclusive; never 9000-9099 (synthetic demo farmers)
CALL_HOURS_UTC = (6, 14)  # 09:00-17:59 Kampala
KG_RANGE = (50, 600)
INSERT_BATCH_ROWS = 400  # rows per multi-row INSERT (<= 22 params each, far below the 65k limit)

PLANTED_PRICE_DISTRICT = "Kayunga"
PLANTED_FACTOR = 0.80
PLANTED_MIDDLEMAN_SHARE = 0.80
OTHER_FACTOR_RANGE = (0.98, 1.05)
WILT_DISTRICT, WILT_SUB_COUNTY, WILT_PARISH = "Ibanda", "Ishongororo", "Kikyenkye"
WILT_VILLAGES = ("Kitojo", "Rwamuhanda")
WILT_DAYS = (date(2026, 9, 16), date(2026, 9, 21), date(2026, 9, 26), date(2026, 10, 1))
WILT_QUIET_FROM = date(2026, 6, 23)  # 12 weeks before the first wilt report: no problems in the district
WILT_MIN_AGE_DAYS = 100
BACKGROUND_GAP_DAYS = 95  # minimum gap between two background reports in one parish
BACKGROUND_GAP_JITTER = 40
BACKGROUND_FIRST_WINDOW = 120
BACKGROUND_STOP_DAYS = 14

# (district, zone, coffee type, sub-counties). Planted districts first; never a reserved demo district.
DISTRICT_SPECS = (
    ("Kayunga", "central", "robusta", ("Busaana", "Nazigo", "Kangulumira", "Bbaale")),
    ("Ibanda", "southwest", "robusta", (WILT_SUB_COUNTY, "Nyamarebe", "Bufunda", "Kicuzi")),
    ("Mbale", "elgon", "arabica", ("Bungokho", "Busiu", "Wanale", "Nakaloke")),
    ("Sironko", "elgon", "arabica", ("Budadiri", "Bukhulo", "Zesui", "Buhugu")),
    ("Kapchorwa", "elgon", "arabica", ("Tegeres", "Kaptanya", "Chema", "Sipi")),
    ("Bulambuli", "elgon", "arabica", ("Buginyanya", "Muyembe", "Bulegeni", "Bukhalu")),
    ("Bukwo", "elgon", "arabica", ("Kortek", "Chesower", "Suam", "Riwo")),
    ("Nebbi", "westnile", "arabica", ("Akworo", "Parombo", "Atego", "Erussi")),
    ("Arua", "westnile", "arabica", ("Ayivu", "Vurra", "Logiri", "Rigbo")),
    ("Kasese", "rwenzori", "arabica", ("Bugoye", "Rukoki", "Maliba", "Kyarumba")),
    ("Bundibugyo", "rwenzori", "robusta", ("Bubandi", "Harugale", "Busaru", "Kasitu")),
    ("Kabarole", "rwenzori", "robusta", ("Harugongo", "Hakibaale", "Mugusu", "Rubona")),
    ("Mitooma", "southwest", "robusta", ("Kashenshero", "Kanyabwanga", "Mutara", "Rutookye")),
    ("Ntungamo", "southwest", "robusta", ("Rubaare", "Ruhaama", "Itojo", "Rwashamaire")),
    ("Rukungiri", "southwest", "robusta", ("Buyanja", "Bwambara", "Nyakagyeme", "Kebisoni")),
    ("Kanungu", "southwest", "robusta", ("Kambuga", "Kihihi", "Nyanga", "Mpungu")),
    ("Sheema", "southwest", "robusta", ("Kabwohe", "Kyangyenyi", "Shuuku", "Kigarama")),
    ("Kyenjojo", "southwest", "robusta", ("Butunduzi", "Kyarusozi", "Mpanga", "Katooke")),
    ("Mukono", "central", "robusta", ("Kyampisi", "Nama", "Goma", "Ngogwe")),
    ("Luwero", "central", "robusta", ("Kikyusa", "Bamunanika", "Zirobwe", "Katikamu")),
    ("Mityana", "central", "robusta", ("Kalangaalo", "Busimbi", "Maanyi", "Ssekanyonyi")),
    ("Lwengo", "central", "robusta", ("Kkingo", "Kyazanga", "Lwengo", "Malongo")),
    ("Rakai", "central", "robusta", ("Kyalulangira", "Kakuuto", "Kacheera", "Ndagwe")),
    ("Kalungu", "central", "robusta", ("Lukaya", "Kyamulibwa", "Bukulula", "Kalungu")),
    ("Bukomansimbi", "central", "robusta", ("Butenga", "Kitanda", "Bigasa", "Mijwala")),
    ("Kyotera", "central", "robusta", ("Kabira", "Kasaali", "Mutukula", "Kalisizo")),
    ("Buikwe", "central", "robusta", ("Najjembe", "Nyenga", "Kawolo", "Ssi-Bukunja")),
    ("Kamuli", "eastern", "robusta", ("Namasagali", "Balawoli", "Nawanyago", "Kitayunjwa")),
    ("Jinja", "eastern", "robusta", ("Budondo", "Butagaya", "Kakira", "Mafubira")),
)
PLANTED_DISTRICTS = (PLANTED_PRICE_DISTRICT, WILT_DISTRICT)
REGION_PROBLEMS = {  # background disease priors by zone: (disease, weight); berry disease is arabica only
    "elgon": (("coffee_leaf_rust", 5), ("coffee_berry_disease", 4)),
    "southwest": (("coffee_wilt_disease", 5), ("black_coffee_twig_borer", 3), ("coffee_leaf_rust", 1)),
    "central": (("black_coffee_twig_borer", 5), ("coffee_wilt_disease", 3), ("coffee_leaf_rust", 1)),
    "westnile": (("coffee_leaf_rust", 5), ("coffee_berry_disease", 3)),
    "rwenzori": (("coffee_leaf_rust", 4), ("coffee_berry_disease", 3), ("black_coffee_twig_borer", 2)),
    "eastern": (("coffee_leaf_rust", 4), ("black_coffee_twig_borer", 3)),
}
ZONE_REPORT_WEIGHT = {"elgon": 1.3, "rwenzori": 1.2, "southwest": 1.1, "central": 0.9, "eastern": 0.9, "westnile": 0.8}
DISEASE = {  # likely_disease -> (symptom, Swahili, English)
    "coffee_wilt_disease": ("wilting", "Miti ya kahawa inanyauka na majani yanakauka.", "The coffee trees are wilting and the leaves dry up."),
    "coffee_leaf_rust": ("powder_or_rust", "Majani yana vumbi la rangi ya machungwa upande wa chini.", "The leaves have orange powder underneath."),
    "coffee_berry_disease": ("fruit_spots", "Matunda ya kahawa yana madoa meusi.", "The coffee berries have dark spots."),
    "black_coffee_twig_borer": ("wilting", "Matawi yanakauka na kuna vitundu vidogo.", "The twigs are drying with small holes."),
}
FIRST_NAMES = (
    "Grace", "Moses", "Sarah", "John", "Rose", "Peter", "Agnes", "David", "Mary", "Joseph", "Esther", "Robert",
    "Juliet", "Samuel", "Betty", "Patrick", "Annet", "Isaac", "Joan", "Francis", "Harriet", "Emmanuel",
    "Prossy", "Charles", "Immaculate", "Denis", "Winnie", "Geoffrey", "Scovia", "Richard", "Juma", "Ruth",
    "Brian", "Doreen", "Fred", "Lydia", "Hassan", "Sharon", "Ibrahim", "Faith", "Godfrey", "Judith", "Alex",
    "Florence", "Henry", "Christine", "Simon", "Evelyne", "Ronald", "Beatrice", "Michael", "Jackline", "Tom",
    "Stella", "Ivan", "Racheal", "Kenneth", "Olivia", "Jimmy", "Gloria")
SURNAMES = (
    "Nakato", "Okello", "Mugisha", "Namukasa", "Tumusiime", "Wanyama", "Kiiza", "Nabirye", "Byaruhanga",
    "Atim", "Ssemwogerere", "Akello", "Kato", "Namubiru", "Muhumuza", "Wasike", "Nalubega", "Opio",
    "Kabagambe", "Nambozo", "Masaba", "Auma", "Turyahabwe", "Nakimera", "Kyomuhendo", "Ochieng", "Babirye",
    "Mwesigwa", "Namatovu", "Khaemba", "Ssekandi", "Nankya", "Tusiime", "Atuhaire", "Kemigisha", "Okumu",
    "Namuddu", "Byamugisha", "Tumwine", "Nakabugo", "Mukasa", "Kasule", "Lubega", "Ochan", "Akena",
    "Natukunda", "Asiimwe", "Kyeyune", "Nsubuga", "Nakalema", "Wabwire", "Mutesi", "Musoke", "Birungi",
    "Ainembabazi", "Kigozi", "Namutebi", "Opolot", "Tendo", "Kizza")
NAME_RETRIES = 30
NAME_SYLLABLES = {  # (starts, middles, ends) per naming style, for invented parish and village names
    "bantu": (("Ka", "Ky", "Nya", "Bu", "Mu", "Ru", "Kiti", "Bwe", "Nka", "Kisi", "Lwa", "Nko", "Mpa", "Bi", "Ki", "Nta", "Ruh", "Kab"),
              ("ngo", "ruma", "sasa", "ndu", "kya", "bale", "gira", "zi", "mbo", "ta", "ki", "ra", "so", "ga", "lu", "ba"),
              ("ra", "nda", "ga", "ko", "ba", "zi", "ngo", "ya", "mi", "si", "li", "ru", "ma", "ka", "re", "bo")),
    "elgon": (("Bu", "Nam", "Ma", "Si", "Ba", "Bukh", "Kap", "Che", "Wa", "Bum"),
              ("ba", "li", "su", "ku", "ma", "bi", "po", "ru", "ka", "wa"),
              ("ba", "li", "ndi", "ngo", "si", "ya", "mbe", "ra", "lo", "ka")),
    "westnile": (("Ang", "Ora", "Pa", "Oko", "Ayi", "Vur", "Lo", "Ri", "Ndu", "Pan"),
                 ("ra", "ko", "ba", "ru", "ni", "wi", "pa", "li", "do", "ge"),
                 ("ni", "ra", "ko", "ya", "ru", "ti", "wa", "ngo", "di", "ru")),
}
NAME_STYLE = {"elgon": "elgon", "westnile": "westnile"}  # every other zone uses "bantu"


@dataclass(frozen=True)
class VillageRow:
    region: str
    district: str
    zone: str
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


# ---- villages ------------------------------------------------------------------------------

def _read_districts() -> dict[str, tuple[str, float, float]]:
    with DISTRICTS_CSV.open(newline="") as handle:
        rows = csv.DictReader(line for line in handle if not line.startswith("#"))
        return {r["district"]: (r["region"], float(r["lat"]), float(r["lon"])) for r in rows}


def _pick_districts(rng: random.Random, farmers: int) -> tuple[tuple, ...]:
    """All districts at the default size; fewer for a smaller run, planted districts always included."""
    wanted = max(len(PLANTED_DISTRICTS) + 1, min(len(DISTRICT_SPECS), math.ceil(len(DISTRICT_SPECS) * farmers / DEFAULT_FARMERS)))
    planted = tuple(s for s in DISTRICT_SPECS if s[0] in PLANTED_DISTRICTS)
    others = [s for s in DISTRICT_SPECS if s[0] not in PLANTED_DISTRICTS]
    chosen = rng.sample(others, wanted - len(planted))
    return planted + tuple(s for s in DISTRICT_SPECS if s in chosen)


class _Namer:
    """Invents unique parish and village names in the naming style of each zone."""

    def __init__(self, rng: random.Random) -> None:
        self._rng, self._used = rng, set()

    def name(self, zone: str) -> str:
        starts, middles, ends = NAME_SYLLABLES[NAME_STYLE.get(zone, "bantu")]
        while True:
            parts = [self._rng.choice(starts), self._rng.choice(middles)]
            if self._rng.random() < 0.6:
                parts.append(self._rng.choice(ends))
            candidate = "".join(parts).capitalize()
            if candidate not in self._used:
                self._used.add(candidate)
                return candidate


def _district_villages(rng, namer, spec, centroid) -> list[VillageRow]:
    district, zone, coffee_type, sub_counties = spec
    region, lat, lon = centroid
    parishes = [(rng.choice(sub_counties), namer.name(zone), None) for _ in range(rng.randint(*PARISHES_PER_DISTRICT))]
    if district == WILT_DISTRICT:
        parishes[0] = (WILT_SUB_COUNTY, WILT_PARISH, WILT_VILLAGES)
    rows = []
    for sub_county, parish, fixed in parishes:
        names = fixed or tuple(
            namer.name(zone) for _ in range(rng.choices(VILLAGE_COUNT_CHOICES, VILLAGE_COUNT_WEIGHTS)[0]))
        for village in names:
            rows.append(VillageRow(
                region, district, zone, sub_county, parish, village,
                round(lat + rng.uniform(-COORD_OFFSET, COORD_OFFSET), 5),
                round(lon + rng.uniform(-COORD_OFFSET, COORD_OFFSET), 5), coffee_type, 0))
    return rows


def _fit_counts(rng: random.Random, villages: int, total: int) -> list[int]:
    """Farmers per village, each in FARMERS_PER_VILLAGE, summing exactly to `total`."""
    low, high = FARMERS_PER_VILLAGE
    counts = [rng.randint(low, high) for _ in range(villages)]
    step = 1 if sum(counts) < total else -1
    while sum(counts) != total:
        movable = [i for i, c in enumerate(counts) if low <= c + step <= high]
        counts[rng.choice(movable)] += step
    return counts


def _build_villages(rng: random.Random, farmers: int) -> tuple[VillageRow, ...]:
    centroids = _read_districts()
    namer = _Namer(rng)
    rows: list[VillageRow] = []
    for spec in _pick_districts(rng, farmers):
        assert spec[0] not in DEMO_DISTRICTS
        rows.extend(_district_villages(rng, namer, spec, centroids[spec[0]]))
    fixed = {WILT_DISTRICT: set(WILT_VILLAGES)}
    while farmers < FARMERS_PER_VILLAGE[0] * len(rows):  # tiny runs: drop a non-fixture village
        drop = next(i for i in range(len(rows) - 1, -1, -1) if rows[i].village not in fixed.get(rows[i].district, ()))
        rows.pop(drop)
    counts = _fit_counts(rng, len(rows), farmers)
    return tuple(replace(v, farmer_count=n) for v, n in zip(rows, counts, strict=True))


# ---- farmers -------------------------------------------------------------------------------

def _utc(day: date, rng: random.Random) -> datetime:
    return datetime.combine(day, time(rng.randint(*CALL_HOURS_UTC), rng.randint(0, 59)), tzinfo=UTC)


def _rand_day(rng: random.Random, start: date, end: date) -> date:
    return start + timedelta(days=rng.randint(0, max(0, (end - start).days)))


def _registration_day(rng: random.Random, min_age: int = 1) -> date:
    """Days ago = history * u**exponent: the density rises toward today (steady growth)."""
    while True:
        age = int(FARMER_HISTORY_DAYS * rng.random() ** GROWTH_EXPONENT)
        if min_age <= age <= FARMER_HISTORY_DAYS:
            return AS_OF - timedelta(days=age)


def _farmer_name(rng: random.Random, used: set[str]) -> str:
    for _ in range(NAME_RETRIES):
        name = f"{rng.choice(FIRST_NAMES)} {rng.choice(SURNAMES)}"
        if name not in used:
            used.add(name)
            return name
    return name  # name pool nearly exhausted (very large runs): allow a repeat


def _build_farmers(rng: random.Random, villages: tuple[VillageRow, ...]) -> tuple[FarmerRow, ...]:
    slots = [i for i, v in enumerate(villages) for _ in range(v.farmer_count)]
    pins = rng.sample(range(PIN_RANGE[0], PIN_RANGE[1] + 1), len(slots))  # unique within the plan
    used_names: set[str] = set()
    farmers = []
    for village, pin in zip(slots, pins, strict=True):
        wilt = villages[village].parish == WILT_PARISH
        created = _utc(_registration_day(rng, WILT_MIN_AGE_DAYS if wilt else 1), rng)
        farmers.append(FarmerRow(_farmer_name(rng, used_names), str(pin), village, created))
    return tuple(farmers)


# ---- sales ---------------------------------------------------------------------------------

STICKY_SHARE = 0.75
DISTRESS_P, DISTRESS_RANGE = 0.15, (0.60, 0.75)  # inside the harvest-start windows (~5% of all sales)
HARVEST_STARTS = ((10, 11), (4, 5))  # month ranges where early cash need bites
PRICE_NOISE = 0.07
MIDDLEMAN_SPREAD = 0.12  # middlemen pay 5-17% under the reference ...
REMOTE_DISCOUNT = 0.08  # ... and remote villages up to 8% less on top


def _buyer_factor(rng, buyer: str, remote: float) -> float:
    if buyer == "middleman":  # remote villages get the worst middleman prices
        return 0.95 - MIDDLEMAN_SPREAD * (0.5 * remote + 0.5 * rng.random())
    if buyer == "cooperative":  # a quarter of co-ops pay a quality / certification premium
        return rng.uniform(1.04, 1.08) if rng.random() < 0.25 else rng.uniform(0.97, 1.04)
    return rng.uniform(0.88, 1.00)


def _pick_buyer(rng, village: VillageRow, remote: float, preferred: str) -> str:
    if village.district == PLANTED_PRICE_DISTRICT:
        return "middleman" if rng.random() < PLANTED_MIDDLEMAN_SHARE else rng.choice(("cooperative", "other"))
    if rng.random() < STICKY_SHARE:
        return preferred
    return "middleman" if rng.random() < 0.40 + 0.30 * remote else rng.choice(("cooperative", "cooperative", "other"))


def _sale_entry(rng, village: VillageRow, day: date, district_factor: float, remote: float, preferred: str) -> dict:
    if village.coffee_type == "arabica":
        form = CoffeeForm.PARCHMENT
    elif village.district == PLANTED_PRICE_DISTRICT:
        form = CoffeeForm.KIBOKO
    else:
        form = CoffeeForm.FAQ if rng.random() < 0.30 else CoffeeForm.KIBOKO
    buyer = _pick_buyer(rng, village, remote, preferred)
    kg = rng.randint(*KG_RANGE)
    per_kg = (anchor_price(min(day, LAST_ANCHOR_DAY), form) * district_factor
              * (1.03 - REMOTE_DISCOUNT * remote) * _buyer_factor(rng, buyer, remote)
              * (1 + rng.uniform(-PRICE_NOISE, PRICE_NOISE)))
    if any(a <= day.month <= b for a, b in HARVEST_STARTS) and rng.random() < DISTRESS_P:
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


def _sale_days(rng, village: VillageRow, start: date) -> list[date]:
    tenure = (LAST_DAY - start).days
    low, high = SALES_PER_FARMER
    count = rng.randint(low, min(high, low + 1) if tenure < NEW_FARMER_DAYS else high)
    days = [_rand_day(rng, start, LAST_DAY) for _ in range(count)]
    if village.district == PLANTED_PRICE_DISTRICT:  # every Kayunga farmer sold within the 90-day price window
        days[0] = _rand_day(rng, max(start, AS_OF - timedelta(days=85)), LAST_DAY)
    return days


# ---- problems ------------------------------------------------------------------------------

def _problem_entry(disease: str) -> tuple[dict, str, str]:
    symptom, sw, en = DISEASE[disease]
    entry = {
        "kind": "observation", "crop": "coffee", "disease_detected": True, "symptom": symptom,
        "likely_disease": disease, "disease_confidence": 0.7, "confidence": 0.9, "quote_verified": True,
        "evidence_quote": en, "description": f"Farmer reports: {en.lower()}",
    }
    return entry, sw, en


def _add_wilt_cluster(rng, events, cluster: list[int]) -> None:
    for i, day in zip(cluster, WILT_DAYS, strict=True):
        entry, sw, en = _problem_entry("coffee_wilt_disease")
        events[i].append((_utc(day, rng), [entry], sw, en))


def _parish_candidates(rng, farmers, villages, cluster: set[int]) -> list[tuple[float, int, date, str]]:
    """One schedule per parish, reports >= BACKGROUND_GAP_DAYS apart, as (sort key, farmer, day, disease)."""
    parishes: dict[tuple[str, str, str], list[int]] = {}
    for i, f in enumerate(farmers):
        v = villages[f.village]
        parishes.setdefault((v.district, v.sub_county, v.parish), []).append(i)
    candidates = []
    for (district, _sub, _parish), members in sorted(parishes.items()):
        zone = villages[farmers[members[0]].village].zone
        arabica = villages[farmers[members[0]].village].coffee_type == "arabica"
        priors = [(d, w) for d, w in REGION_PROBLEMS[zone] if arabica or d != "coffee_berry_disease"]
        end = WILT_QUIET_FROM - timedelta(days=1) if district == WILT_DISTRICT else AS_OF - timedelta(days=BACKGROUND_STOP_DAYS)
        day = _rand_day(rng, SALES_START, SALES_START + timedelta(days=BACKGROUND_FIRST_WINDOW))
        while day <= end:
            eligible = [i for i in members if i not in cluster and farmers[i].created_at.date() < day]
            if eligible:
                disease = rng.choices([d for d, _ in priors], [w for _, w in priors])[0]
                key = rng.random() ** (1 / ZONE_REPORT_WEIGHT[zone])  # higher weight, likelier to be kept
                candidates.append((key, rng.choice(eligible), day, disease))
            day += timedelta(days=BACKGROUND_GAP_DAYS + rng.randint(0, BACKGROUND_GAP_JITTER))
    return candidates


def _add_background_problems(rng, farmers, villages, events, cluster: set[int]) -> None:
    target = max(0, len(farmers) // FARMERS_PER_PROBLEM_REPORT - len(WILT_DAYS))
    kept = sorted(_parish_candidates(rng, farmers, villages, cluster), reverse=True)[:target]
    for _key, farmer, day, disease in sorted(kept, key=lambda c: (c[2], c[1])):
        entry, sw, en = _problem_entry(disease)
        events[farmer].append((_utc(day, rng), [entry], sw, en))


def _add_advice_calls(rng, farmers, events) -> None:
    sw, en = "Nataka ushauri wa kupogoa kahawa.", "I would like advice on pruning my coffee."
    for i in rng.sample(range(len(farmers)), max(1, len(farmers) // FARMERS_PER_ADVICE_CALL)):
        first = min(e[0] for e in events[i])
        events[i].append((_utc(_rand_day(rng, max(first.date(), SALES_START), LAST_DAY), rng), [], sw, en))


# ---- plan ----------------------------------------------------------------------------------

def _calls_for(rng, index: int, events) -> list[CallRow]:
    calls = []
    for n, (at, entries, sw, en) in enumerate(sorted(events, key=lambda e: e[0])):
        calls.append(CallRow(
            index, at, f"{CONVERSATION_PREFIX}{index:04d}-{n + 1}",
            "registration" if n == 0 else "pin", sw, en, rng.randint(55, 190), tuple(entries)))
    return calls


def build_plan(farmers: int = DEFAULT_FARMERS) -> Plan:
    if not MIN_FARMERS <= farmers <= MAX_FARMERS:
        raise ValueError(f"--farmers must be {MIN_FARMERS}-{MAX_FARMERS} (4-digit PIN space), got {farmers}")
    rng = random.Random(SEED)
    villages = _build_villages(rng, farmers)
    people = _build_farmers(rng, villages)
    factors = {d: round(rng.uniform(*OTHER_FACTOR_RANGE), 3) for d in sorted({v.district for v in villages})}
    factors[PLANTED_PRICE_DISTRICT] = PLANTED_FACTOR
    remote = [rng.random() for _ in villages]  # 0 = on the tarmac, 1 = far from a district town
    events: dict[int, list] = {i: [] for i in range(len(people))}
    wilt_cluster = [i for i, f in enumerate(people) if villages[f.village].parish == WILT_PARISH][:len(WILT_DAYS)]
    for i, farmer in enumerate(people):
        village = villages[farmer.village]
        preferred = "middleman" if rng.random() < 0.40 + 0.30 * remote[farmer.village] else rng.choice(("cooperative", "other"))
        for day in _sale_days(rng, village, max(farmer.created_at.date(), SALES_START)):
            entry = _sale_entry(rng, village, day, factors[village.district], remote[farmer.village], preferred)
            sw, en = _sale_call(entry)
            events[i].append((_utc(day, rng), [entry], sw, en))
    _add_wilt_cluster(rng, events, wilt_cluster)
    _add_background_problems(rng, people, villages, events, set(wilt_cluster))
    _add_advice_calls(rng, people, events)
    calls, aligned = [], []
    for i, farmer in enumerate(people):
        own = _calls_for(rng, i, events[i])
        calls.extend(own)
        aligned.append(FarmerRow(farmer.name, farmer.pin, farmer.village, min(own[0].received_at, farmer.created_at)))
    return Plan(villages, tuple(aligned), tuple(calls))


# ---- database ------------------------------------------------------------------------------

ENTRY_COLUMNS = (
    "kind", "crop", "amount", "amount_kg", "unit", "price_total", "currency", "date_sold", "buyer_type",
    "paid_how", "coffee_form", "coffee_type", "disease_detected", "symptom", "likely_disease",
    "disease_confidence", "evidence_quote", "description", "quote_verified", "confidence",
)
INSERT_VILLAGES = (
    "insert into villages (region, district, sub_county, parish, village, lat, lon, coffee_type,"
    " is_verified, is_synthetic) values ")
VILLAGE_ROW = "(%s, %s, %s, %s, %s, %s, %s, %s, true, true)"
INSERT_FARMERS = "insert into farmers (name, pin_hash, region, lat, lon, village_id, is_synthetic, created_at) values "
FARMER_ROW = "(%s, %s, %s, %s, %s, %s, true, %s)"
INSERT_CALLS = (
    "insert into calls (farmer_id, received_at, language, transcript_sw, transcript_en, is_synthetic, source,"
    " status, identified_by, consent, duration_secs, transcript_lines, processed_at, conversation_id) values ")
CALL_ROW = "(%s, %s, 'sw', %s, %s, true, 'synthetic', 'processed', %s, 'yes', %s, %s::jsonb, %s, %s)"
INSERT_ENTRIES = f"insert into entries (call_id, farmer_id, {', '.join(ENTRY_COLUMNS)}) values "
ENTRY_ROW = f"(%s, %s, {', '.join(['%s'] * len(ENTRY_COLUMNS))})"


def _insert_many(conn, head: str, row_template: str, rows: list[tuple]) -> None:
    for start in range(0, len(rows), INSERT_BATCH_ROWS):
        chunk = rows[start:start + INSERT_BATCH_ROWS]
        conn.execute(head + ", ".join([row_template] * len(chunk)), [p for row in chunk for p in row])


def _ids(conn, sql: str, params: tuple) -> dict:
    return {row[1]: row[0] for row in conn.execute(sql, params).fetchall()}


def remove_expansion(conn) -> dict[str, int]:
    """Delete only expansion rows (those reached through 'synmap-%' calls). Refuses if anything else is attached."""
    farmer_ids = [r[0] for r in conn.execute(
        "select distinct farmer_id from calls where conversation_id like %s", (CONVERSATION_LIKE,)).fetchall()]
    village_ids = [r[0] for r in conn.execute(
        "select distinct village_id from farmers where id = any(%s::bigint[]) and village_id is not null",
        (farmer_ids,)).fetchall()]
    demo = conn.execute("select count(*) from villages where id = any(%s::bigint[]) and district = any(%s::text[])",
                        (village_ids, list(DEMO_DISTRICTS))).fetchone()[0]
    strangers = conn.execute(
        "select count(*) from farmers where village_id = any(%s::bigint[]) and (not is_synthetic or id <> all(%s::bigint[]))",
        (village_ids, farmer_ids)).fetchone()[0]
    foreign = conn.execute(
        "select count(*) from calls where farmer_id = any(%s::bigint[])"
        " and (conversation_id is null or conversation_id not like %s)", (farmer_ids, CONVERSATION_LIKE)).fetchone()[0]
    if demo or strangers or foreign:
        raise loader.ResetRefused(
            f"refusing: {demo} demo villages, {strangers} other farmers, {foreign} other calls in expansion rows")
    return {
        "entries": conn.execute("delete from entries where call_id in (select id from calls where conversation_id like %s)",
                                (CONVERSATION_LIKE,)).rowcount,
        "calls": conn.execute("delete from calls where conversation_id like %s and is_synthetic",
                              (CONVERSATION_LIKE,)).rowcount,
        "farmers": conn.execute("delete from farmers where is_synthetic and id = any(%s::bigint[])",
                                (farmer_ids,)).rowcount,
        "villages": conn.execute("delete from villages where is_synthetic and id = any(%s::bigint[])",
                                 (village_ids,)).rowcount,
    }


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
    _insert_many(conn, INSERT_VILLAGES, VILLAGE_ROW, [
        (v.region, v.district, v.sub_county, v.parish, v.village, v.lat, v.lon, v.coffee_type)
        for v in plan.villages])
    districts = sorted({v.district for v in plan.villages})
    village_ids = {
        (d, s, p, v): i for i, d, s, p, v in conn.execute(
            "select id, district, sub_county, parish, village from villages where is_synthetic and district = any(%s::text[])",
            (districts,)).fetchall()}
    hashes = [_free_pin(salt, f.pin, taken) for f in plan.farmers]
    _insert_many(conn, INSERT_FARMERS, FARMER_ROW, [
        (f.name, h, plan.villages[f.village].region, plan.villages[f.village].lat, plan.villages[f.village].lon,
         village_ids[plan.villages[f.village].key], f.created_at) for f, h in zip(plan.farmers, hashes, strict=True)])
    farmer_by_hash = _ids(conn, "select id, pin_hash from farmers where pin_hash = any(%s::text[])", (hashes,))
    farmer_ids = [farmer_by_hash[h] for h in hashes]
    _insert_many(conn, INSERT_CALLS, CALL_ROW, [
        (farmer_ids[c.farmer], c.received_at, c.sw, c.en, c.identified_by, c.duration_secs,
         json.dumps([{"i": 0, "role": "farmer", "sw": c.sw, "en": c.en, "t": 0}]), c.received_at, c.conversation_id)
        for c in plan.calls])
    call_ids = _ids(conn, "select id, conversation_id from calls where conversation_id like %s", (CONVERSATION_LIKE,))
    _insert_many(conn, INSERT_ENTRIES, ENTRY_ROW, [
        (call_ids[c.conversation_id], farmer_ids[c.farmer], *(e.get(col) for col in ENTRY_COLUMNS))
        for c in plan.calls for e in c.entries])
    counts = plan_counts(plan)
    if len(village_ids) < len(plan.villages) or len(farmer_by_hash) != len(plan.farmers) or len(call_ids) != len(plan.calls):
        raise loader.LoadError("inserted row counts do not match the plan; rolled back")
    return counts


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


def plan_counts(plan: Plan) -> dict[str, int]:
    return {"districts": len({v.district for v in plan.villages}), "villages": len(plan.villages),
            "farmers": len(plan.farmers), "calls": len(plan.calls),
            "entries": sum(len(c.entries) for c in plan.calls)}


def _parse(argv):
    parser = argparse.ArgumentParser(prog="python -m synthetic.map_expansion", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group(required=True)
    for flag in ("--dry-run", "--apply", "--remove"):
        mode.add_argument(flag, action="store_true")
    parser.add_argument("--farmers", type=int, default=DEFAULT_FARMERS, metavar="N",
                        help=f"farmers to generate ({MIN_FARMERS}-{MAX_FARMERS}, default {DEFAULT_FARMERS})")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse(argv)
    plan = None if args.remove else build_plan(args.farmers)
    if plan is not None:
        from .map_expansion_checks import describe, plan_failures

        failures = plan_failures(plan)
        if args.dry_run:
            print(describe(plan, failures))
            return 1 if failures else 0
        if failures:
            print("refused: plan checks failed: " + "; ".join(failures), file=sys.stderr)
            return 1
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
                inserted = insert_plan(conn, plan, salt) if plan is not None else {}
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

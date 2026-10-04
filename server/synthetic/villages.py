"""The six SYNTHETIC villages and their farmers (spec section 10).

Districts and sub-counties are real; parishes and villages are invented and labelled
synthetic. District centres come from hotline/hotline/data/uganda_districts.csv (UBOS /
OCHA COD-AB); the village offsets from them are invented. All farmer names are first
names only (the hotline stores a first name) and unique across the season, so a
location login never finds two farmers with the same name.

Season timing follows the notes on issue #20 (UCDA / UIA coffee sector profile) and is
indicative, not field-verified: Masaka's main crop is May-Aug and its fly crop Nov-Feb;
Mubende is the reverse; Bududa's Arabica main crop is Oct-Feb and its fly crop Apr-Jun.
Bushenyi and Zombo are assumed to follow Mubende.
"""

from dataclasses import dataclass

from farm_ledger import BuyerType
from farm_ledger.enums import CoffeeForm, CoffeeType


@dataclass(frozen=True)
class SeasonDef:
    label: str  # "main" or "fly"
    start_month: int
    end_month: int  # may be earlier than start_month: the season runs into next year
    share: float  # of the farmer's annual coffee


MASAKA_SEASONS = (SeasonDef("main", 5, 8, 0.62), SeasonDef("fly", 11, 2, 0.38))
REVERSED_SEASONS = (SeasonDef("main", 11, 2, 0.62), SeasonDef("fly", 5, 8, 0.38))
BUDUDA_SEASONS = (SeasonDef("main", 10, 2, 0.62), SeasonDef("fly", 4, 6, 0.38))

COOP_LEANING = ((BuyerType.COOPERATIVE, 0.6), (BuyerType.MIDDLEMAN, 0.4))
MIDDLEMAN_LEANING = ((BuyerType.MIDDLEMAN, 0.6), (BuyerType.COOPERATIVE, 0.2), (BuyerType.OTHER, 0.2))
MIXED_BUYERS = ((BuyerType.MIDDLEMAN, 0.35), (BuyerType.COOPERATIVE, 0.4), (BuyerType.OTHER, 0.25))


@dataclass(frozen=True)
class Village:
    key: str
    region: str  # Central, Eastern, Northern or Western
    district: str
    sub_county: str
    parish: str
    village: str
    lat: float
    lon: float
    coffee_type: CoffeeType
    form: CoffeeForm  # the form its farmers mostly sell
    effect: float  # price effect of the village, within +-3%
    buyer_weights: tuple[tuple[BuyerType, float], ...]
    annual_kg: tuple[int, int]  # a farmer's coffee per year is between these
    seasons: tuple[SeasonDef, ...]
    farmers: tuple[str, ...]
    is_synthetic: bool = True


VILLAGES = (
    Village("V1", "Central", "Masaka", "Kyanamukaaka", "Kasaali", "Kyabakuza", -0.4862, 31.8325,
            CoffeeType.ROBUSTA, CoffeeForm.KIBOKO, 0.02, MIXED_BUYERS, (900, 1700),
            MASAKA_SEASONS, ("Nakato", "Kasule", "Namusoke", "Ssentamu", "Nabukenya")),
    Village("V2", "Central", "Masaka", "Kyanamukaaka", "Kasaali", "Bukeeri", -0.4905, 31.8398,
            CoffeeType.ROBUSTA, CoffeeForm.FAQ, -0.01, MIDDLEMAN_LEANING, (700, 1400),
            MASAKA_SEASONS, ("Nalwoga", "Mukasa", "Namatovu")),
    Village("V3", "Central", "Mubende", "Kasambya", "Kisita", "Nakyesa", 0.5140, 31.4115,
            CoffeeType.ROBUSTA, CoffeeForm.KIBOKO, -0.02, MIDDLEMAN_LEANING, (800, 1500),
            REVERSED_SEASONS, ("Tumusiime", "Nankya", "Byaruhanga", "Nabirye")),
    Village("V4", "Western", "Bushenyi", "Kyamuhunga", "Bwegiira", "Rwentuha", -0.4754, 30.1710,
            CoffeeType.ROBUSTA, CoffeeForm.KIBOKO, 0.01, MIDDLEMAN_LEANING, (800, 1500),
            REVERSED_SEASONS, ("Atuhaire", "Tumwebaze", "Kemigisha", "Mugisha")),
    Village("V5", "Eastern", "Bududa", "Bukigai", "Bunamwaya", "Namagumba", 1.0262, 34.3907,
            CoffeeType.ARABICA, CoffeeForm.PARCHMENT, 0.02, COOP_LEANING, (350, 800),
            BUDUDA_SEASONS, ("Mafabi", "Nambozo", "Wamoto", "Nandutu")),
    Village("V6", "Northern", "Zombo", "Paidha", "Kei", "Ora", 2.5203, 30.8753,
            CoffeeType.ARABICA, CoffeeForm.PARCHMENT, 0.0, COOP_LEANING, (250, 450),
            REVERSED_SEASONS, ("Aciro",)),
)

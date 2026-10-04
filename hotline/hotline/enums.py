"""Fixed value lists, defined once. db.py turns them into CHECK constraints;
the extraction (#10) imports them to build its JSON schema."""

from enum import StrEnum


class Kind(StrEnum):
    SALE = "sale"
    ACTIVITY = "activity"
    HARVEST = "harvest"
    OBSERVATION = "observation"


class Unit(StrEnum):
    KG = "kg"
    BAG = "bag"
    TIN = "tin"
    BUNCH = "bunch"  # bananas, Swahili "mkungu"
    OTHER = "other"


class Currency(StrEnum):
    KES = "KES"
    UGX = "UGX"
    USD = "USD"
    OTHER = "other"


class BuyerType(StrEnum):
    MIDDLEMAN = "middleman"
    COOPERATIVE = "cooperative"
    OTHER = "other"


class PaidHow(StrEnum):
    CASH = "cash"
    MOBILE_MONEY = "mobile_money"
    OTHER = "other"


class Activity(StrEnum):
    PLANTING = "planting"
    WEEDING = "weeding"
    FERTILISING = "fertilising"
    SPRAYING = "spraying"
    PRUNING = "pruning"
    HARVESTING = "harvesting"
    OTHER = "other"


class Symptom(StrEnum):
    YELLOWING_LEAVES = "yellowing_leaves"
    LEAF_SPOTS = "leaf_spots"
    POWDER_OR_RUST = "powder_or_rust"
    FRUIT_SPOTS = "fruit_spots"
    ROT = "rot"
    WILTING = "wilting"
    PESTS = "pests"
    STUNTED_GROWTH = "stunted_growth"
    OTHER = "other"


class CoffeeForm(StrEnum):
    RED_CHERRY = "red_cherry"
    KIBOKO = "kiboko"  # dried whole cherry
    FAQ = "faq"  # fair average quality hulled coffee
    PARCHMENT = "parchment"
    DRUGAR = "drugar"  # dried unsorted arabica cherry
    OTHER = "other"


class CoffeeType(StrEnum):
    ROBUSTA = "robusta"
    ARABICA = "arabica"


class CallStatus(StrEnum):
    IN_CALL = "in_call"
    RECEIVED = "received"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"


class CallSource(StrEnum):
    ELEVENLABS = "elevenlabs"
    TWILIO = "twilio"
    SYNTHETIC = "synthetic"
    EVAL = "eval"


class IdentifiedBy(StrEnum):
    PIN = "pin"
    LOCATION = "location"
    REGISTRATION = "registration"


class Consent(StrEnum):
    YES = "yes"
    NO = "no"
    UNCLEAR = "unclear"


class Region(StrEnum):
    CENTRAL = "Central"
    EASTERN = "Eastern"
    NORTHERN = "Northern"
    WESTERN = "Western"

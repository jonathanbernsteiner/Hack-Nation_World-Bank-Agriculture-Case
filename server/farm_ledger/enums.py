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

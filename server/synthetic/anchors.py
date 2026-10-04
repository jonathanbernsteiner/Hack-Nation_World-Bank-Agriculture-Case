"""Monthly farm-gate price anchors (UGX per kg) from the UCDA monthly reports.

price_anchors.csv has one row per month, Oct 2024 - Sep 2026. `source` is the URL of the
UCDA report that states the month's figures (the "Farm-gate prices for Robusta Kiboko
averaged ..." line on its first page), or `interpolated` when no report exists yet: the
September 2026 report is not out at AS_OF (2026-10-03), so September carries August's
figures forward. UCDA was merged into MAAIF; its reports are still the published series.
"""

import csv
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from farm_ledger.enums import CoffeeForm

CSV_PATH = Path(__file__).with_name("price_anchors.csv")
INTERPOLATED = "interpolated"
ANCHOR_FORMS = (CoffeeForm.KIBOKO, CoffeeForm.FAQ, CoffeeForm.PARCHMENT, CoffeeForm.DRUGAR)


@dataclass(frozen=True)
class PriceAnchor:
    month: str  # "2026-02"
    ugx_per_kg: dict[str, int]  # form -> price
    source: str  # report URL, or "interpolated"


@cache
def price_anchors() -> dict[str, PriceAnchor]:
    with CSV_PATH.open(newline="") as f:
        return {
            row["month"]: PriceAnchor(
                row["month"], {form.value: int(row[form.value]) for form in ANCHOR_FORMS}, row["source"]
            )
            for row in csv.DictReader(f)
        }


def anchor_price(day, form: CoffeeForm) -> int:
    """The anchor in UGX per kg for the month of `day`."""
    return price_anchors()[f"{day.year}-{day.month:02d}"].ugx_per_kg[form.value]

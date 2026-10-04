"""UGX per kg plausibility bands per coffee form (spec section 5).

The single definition of the bands: prices.py filters with it before taking a median
and verify.py (#61) imports it for the quote check. Do not copy these numbers."""

from types import MappingProxyType

BANDS: "MappingProxyType[str, tuple[int, int]]" = MappingProxyType(
    {
        "kiboko": (2_000, 15_000),
        "faq": (5_000, 25_000),
        "parchment": (6_000, 30_000),
        "drugar": (6_000, 30_000),
        "red_cherry": (800, 8_000),
    }
)


def band_for(form: str) -> tuple[int, int] | None:
    """Inclusive (low, high) UGX/kg for a form, or None for an unknown form."""
    return BANDS.get(str(form))


def in_band(form: str, ugx_per_kg: float) -> bool:
    """True when the price per kg is plausible for the form. Unknown forms never pass."""
    band = band_for(form)
    if band is None:
        return False
    low, high = band
    return low <= ugx_per_kg <= high

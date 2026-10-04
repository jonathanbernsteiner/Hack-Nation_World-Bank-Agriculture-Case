import pytest

from hotline import bands
from hotline.enums import CoffeeForm


def test_bands_match_spec():
    assert dict(bands.BANDS) == {
        "kiboko": (2000, 15000),
        "faq": (5000, 25000),
        "parchment": (6000, 30000),
        "drugar": (6000, 30000),
        "red_cherry": (800, 8000),
    }


def test_every_priced_form_has_a_band():
    priced = {f.value for f in CoffeeForm} - {"other"}
    assert set(bands.BANDS) == priced


@pytest.mark.parametrize(
    ("form", "price", "expected"),
    [
        ("kiboko", 1999, False),
        ("kiboko", 2000, True),
        ("kiboko", 15000, True),
        ("kiboko", 15001, False),
        ("kiboko", 53000, False),  # x10 slip
        ("red_cherry", 800, True),
        ("other", 5000, False),
        ("nonsense", 5000, False),
    ],
)
def test_in_band(form, price, expected):
    assert bands.in_band(form, price) is expected


def test_band_for_accepts_enum_and_unknown():
    assert bands.band_for(CoffeeForm.FAQ) == (5000, 25000)
    assert bands.band_for("x") is None

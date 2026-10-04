import dataclasses
import hashlib
import random
import re
from pathlib import Path

import pytest

from hotline import config, pins

SALT = "test-salt"
LEDGER_DB = Path(__file__).resolve().parents[2] / "server" / "farm_ledger" / "db.py"


@pytest.fixture
def salt(monkeypatch):
    monkeypatch.setattr(config, "settings", dataclasses.replace(config.settings, ledger_pin_salt=SALT))


def test_hash_matches_farm_ledger_formula(salt):
    expected = hashlib.sha256(f"{SALT}:9001".encode()).hexdigest()
    assert pins.hash_pin("9001") == expected
    source = LEDGER_DB.read_text()
    assert 'hashlib.sha256(f"{salt}:{pin}".encode()).hexdigest()' in source


def test_hash_matches_farm_ledger_function(salt, monkeypatch):
    monkeypatch.syspath_prepend(str(LEDGER_DB.parents[1]))
    ledger_db = pytest.importorskip("farm_ledger.db", reason="farm_ledger not importable")

    monkeypatch.setenv("LEDGER_PIN_SALT", SALT)
    assert pins.hash_pin("9001") == ledger_db._hash_pin("9001")


def test_hash_fails_closed_without_salt(monkeypatch):
    monkeypatch.setattr(config, "settings", dataclasses.replace(config.settings, ledger_pin_salt=None))
    with pytest.raises(pins.PinSaltMissing):
        pins.hash_pin("1234")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1234", "1234"),
        (" 12 34 ", "1234"),
        ("12-34", "1234"),
        ("0007", "0007"),
        ("123", None),
        ("12345", None),
        ("", None),
        ("12a4", None),
        ("１２３４", None),  # fullwidth digits are rejected, not normalised
    ],
)
def test_normalize_pin_accepts_4_digits_only(raw, expected):
    assert pins.normalize_pin(raw) == expected


def test_normalize_pin_unicode_digit_rejected():
    assert pins.normalize_pin("９００１") is None


def test_allocate_pin_never_reserved():
    rng = random.Random(1234)
    for _ in range(10_000):
        pin = pins.allocate_pin(None, rng=rng, is_taken=lambda _pin: False)
        assert re.fullmatch(r"\d{4}", pin)
        assert not 9000 <= int(pin) <= 9099


def test_allocate_pin_skips_taken():
    class Rng:
        def __init__(self):
            self.values = iter([1111, 2222, 3333])

        def randrange(self, _start, _stop):
            return next(self.values)

    taken = {"1111", "2222"}
    assert pins.allocate_pin(None, rng=Rng(), is_taken=taken.__contains__) == "3333"


def test_allocate_pin_gives_up_after_50():
    calls = []

    def always_taken(pin):
        calls.append(pin)
        return True

    with pytest.raises(pins.PinAllocationError):
        pins.allocate_pin(None, rng=random.Random(1), is_taken=always_taken)
    assert len(calls) <= 50


def test_allocate_pin_pads_leading_zeros():
    class Rng:
        def randrange(self, _start, _stop):
            return 7

    assert pins.allocate_pin(None, rng=Rng(), is_taken=lambda _p: False) == "0007"


def test_allocate_pin_checks_database_hash(salt):
    seen = []

    class Cursor:
        def fetchone(self):
            return None

    class Conn:
        def execute(self, sql, params):
            seen.append((sql, params))
            return Cursor()

    pin = pins.allocate_pin(Conn(), rng=random.Random(5))
    assert seen[0][0] == "select 1 from farmers where pin_hash = %s"
    assert seen[0][1] == (pins.hash_pin(pin),)


def test_salt_fingerprint_prefix(salt):
    assert pins.salt_fingerprint() == hashlib.sha256(SALT.encode()).hexdigest()[:8]
    assert SALT not in pins.salt_fingerprint()


def test_salt_fingerprint_unset(monkeypatch):
    monkeypatch.setattr(config, "settings", dataclasses.replace(config.settings, ledger_pin_salt=None))
    assert pins.salt_fingerprint() is None

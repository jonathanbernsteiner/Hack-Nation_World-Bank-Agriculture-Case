"""PIN helpers. The hash matches server/farm_ledger/db.py::_hash_pin, but this module
fails closed when the salt is unset (no dev-salt fallback)."""

import hashlib
import secrets
from collections.abc import Callable
from typing import Any

from hotline import config

PIN_LENGTH = 4
PIN_SPACE = 10**PIN_LENGTH
RESERVED_PINS = range(9000, 9100)
MAX_ALLOCATION_TRIES = 50
SALT_FP_LENGTH = 8
_IGNORED_SEPARATORS = str.maketrans("", "", " -")
_rng = secrets.SystemRandom()


class PinSaltMissing(RuntimeError):
    """LEDGER_PIN_SALT is not configured."""


class PinAllocationError(RuntimeError):
    """No free PIN was found within the try limit."""


def hash_pin(pin: str) -> str:
    salt = config.settings.ledger_pin_salt
    if not salt:
        raise PinSaltMissing("LEDGER_PIN_SALT is not set")
    return hashlib.sha256(f"{salt}:{pin}".encode()).hexdigest()


def normalize_pin(raw: str) -> str | None:
    """Strip spaces and dashes, then accept exactly 4 ASCII digits. Non-ASCII digits
    (for example fullwidth) are rejected, not converted."""
    candidate = raw.translate(_IGNORED_SEPARATORS)
    if len(candidate) == PIN_LENGTH and candidate.isascii() and candidate.isdigit():
        return candidate
    return None


def _db_is_taken(conn: Any) -> Callable[[str], bool]:
    def is_taken(pin: str) -> bool:
        row = conn.execute("select 1 from farmers where pin_hash = %s", (hash_pin(pin),)).fetchone()
        return row is not None

    return is_taken


def allocate_pin(
    conn: Any,
    rng: secrets.SystemRandom | Any = _rng,
    is_taken: Callable[[str], bool] | None = None,
) -> str:
    """Random 4-digit PIN outside 9000-9099 and not already used by a farmer."""
    taken = is_taken or _db_is_taken(conn)
    for _ in range(MAX_ALLOCATION_TRIES):
        number = rng.randrange(0, PIN_SPACE)
        if number in RESERVED_PINS:
            continue
        pin = f"{number:0{PIN_LENGTH}d}"
        if not taken(pin):
            return pin
    raise PinAllocationError("no free PIN after %d tries" % MAX_ALLOCATION_TRIES)


def salt_fingerprint() -> str | None:
    salt = config.settings.ledger_pin_salt
    if not salt:
        return None
    return hashlib.sha256(salt.encode()).hexdigest()[:SALT_FP_LENGTH]

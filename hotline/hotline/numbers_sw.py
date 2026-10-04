"""Integers to Kiswahili number words, so the agent never has to read digits.

Forms used (East African usage, consistent with the translation glossary in
prompts/translate_sw_en.md, which maps "milioni moja na laki nane" back to 1,800,000):
- 1,000-99,999: "elfu N" (5,900 = "elfu tano na mia tisa").
- 100,000-999,999: "laki N" for each hundred thousand (100,000 = "laki moja",
  150,000 = "laki moja na elfu hamsini"). We never say "elfu mia moja".
- 1,000,000 and above: "milioni N" (1,800,000 = "milioni moja na laki nane").
Parts are joined with " na " (and).

Different numbers can give the same words (10,002 and 12,000 both read "elfu kumi na
mbili"), so round money to the nearest 50 UGX before calling to_words."""

MAX_VALUE = 999_999_999

_UNITS = {1: "moja", 2: "mbili", 3: "tatu", 4: "nne", 5: "tano", 6: "sita", 7: "saba", 8: "nane", 9: "tisa"}
_TENS = {
    10: "kumi",
    20: "ishirini",
    30: "thelathini",
    40: "arobaini",
    50: "hamsini",
    60: "sitini",
    70: "sabini",
    80: "themanini",
    90: "tisini",
}
_JOIN = " na "


def _below_100(n: int) -> str:
    tens, unit = n - n % 10, n % 10
    if tens == 0:
        return _UNITS[unit]
    return _TENS[tens] + (_JOIN + _UNITS[unit] if unit else "")


def _below_1000(n: int) -> str:
    hundreds, rest = divmod(n, 100)
    parts = []
    if hundreds:
        parts.append(f"mia {_UNITS[hundreds]}")
    if rest:
        parts.append(_below_100(rest))
    return _JOIN.join(parts)


def _below_100_000(n: int) -> str:
    thousands, rest = divmod(n, 1000)
    parts = []
    if thousands:
        parts.append(f"elfu {_below_100(thousands)}")
    if rest:
        parts.append(_below_1000(rest))
    return _JOIN.join(parts)


def _below_million(n: int) -> str:
    lakhs, rest = divmod(n, 100_000)
    parts = []
    if lakhs:
        parts.append(f"laki {_UNITS[lakhs]}")
    if rest:
        parts.append(_below_100_000(rest))
    return _JOIN.join(parts)


def to_words(n: int) -> str:
    """Kiswahili words for a whole number 0..999,999,999. Raises ValueError otherwise."""
    if isinstance(n, bool) or not isinstance(n, int):
        raise ValueError("to_words needs an int")
    if n < 0 or n > MAX_VALUE:
        raise ValueError(f"to_words supports 0..{MAX_VALUE}")
    if n == 0:
        return "sifuri"
    millions, rest = divmod(n, 1_000_000)
    parts = []
    if millions:
        parts.append(f"milioni {_below_1000(millions)}")
    if rest:
        parts.append(_below_million(rest))
    return _JOIN.join(parts)


_DIGIT_WORDS = {"0": "sifuri", **{str(k): v for k, v in _UNITS.items()}}


def digits_to_words(digits: str) -> str:
    """Read digits one by one: "4831" -> "nne, nane, tatu, moja". ValueError if empty or not all 0-9."""
    if not isinstance(digits, str) or not digits or any(c not in _DIGIT_WORDS for c in digits):
        raise ValueError("digits_to_words needs a non-empty string of digits 0-9")
    return ", ".join(_DIGIT_WORDS[c] for c in digits)

from pathlib import Path

import pytest

from hotline.bands import BANDS
from hotline.numbers_sw import to_words


@pytest.mark.parametrize(
    ("n", "words"),
    [
        (0, "sifuri"),
        (1, "moja"),
        (9, "tisa"),
        (10, "kumi"),
        (11, "kumi na moja"),
        (25, "ishirini na tano"),
        (99, "tisini na tisa"),
        (100, "mia moja"),
        (305, "mia tatu na tano"),
        (1000, "elfu moja"),
        (5000, "elfu tano"),
        (5900, "elfu tano na mia tisa"),
        (5750, "elfu tano na mia saba na hamsini"),
        (12300, "elfu kumi na mbili na mia tatu"),
        (12250, "elfu kumi na mbili na mia mbili na hamsini"),
        (100000, "laki moja"),
        (150000, "laki moja na elfu hamsini"),
        (250300, "laki mbili na elfu hamsini na mia tatu"),
        (1000000, "milioni moja"),
        (1800000, "milioni moja na laki nane"),
        (2005000, "milioni mbili na elfu tano"),
    ],
)
def test_to_words_known_answers(n, words):
    assert to_words(n) == words


def test_digits_to_words_pin():
    """Pin the output for a sweep: never a digit, never empty, no double spaces."""
    for n in list(range(0, 2000)) + [5900, 12300, 99999, 100000, 999999, 1800000, 999999999]:
        out = to_words(n)
        assert out and not any(ch.isdigit() for ch in out)
        assert "  " not in out and out == out.strip()


@pytest.mark.parametrize("bad", [-1, 1_000_000_000, 5.5, "5", None, True])
def test_to_words_rejects_bad_input(bad):
    with pytest.raises(ValueError):
        to_words(bad)


# --- Review regression tests (#43) ---


@pytest.mark.parametrize(
    ("n", "words"),
    [(7, "saba"), (20, "ishirini"), (150, "mia moja na hamsini"), (6500, "elfu sita na mia tano")],
)
def test_to_words_remaining_acceptance_answers(n, words):
    """The issue's acceptance list includes 7, 20, 150 and 6500, which the known-answer table skipped."""
    assert to_words(n) == words


def test_laki_form_matches_translate_glossary():
    """#58 turns "milioni moja na laki nane" back into 1,800,000. The words we speak must be that phrase."""
    glossary = Path(__file__).resolve().parents[1] / "hotline" / "prompts" / "translate_sw_en.md"
    assert '"milioni moja na laki nane" -> 1,800,000' in glossary.read_text(encoding="utf-8")
    assert to_words(1_800_000) == "milioni moja na laki nane"


def test_words_are_unique_for_every_price_the_median_can_produce():
    """Medians are multiples of 50 inside a band (max 30,000), so the caller hears a unique phrase.

    to_words is not one-to-one in general ("elfu kumi na mbili" is both 10,002 and 12,000),
    so this pins the range that matters."""
    top = max(high for _, high in BANDS.values())
    seen: dict[str, int] = {}
    for n in range(0, top + 1, 50):
        words = to_words(n)
        assert words not in seen, f"{n} and {seen.get(words)} both read '{words}'"
        seen[words] = n


def test_digits_to_words_reads_a_pin():
    from hotline.numbers_sw import digits_to_words

    assert digits_to_words("4831") == "nne, nane, tatu, moja"
    assert digits_to_words("9001") == "tisa, sifuri, sifuri, moja"


@pytest.mark.parametrize("bad", ["", "12a", "1 2", None, 123])
def test_digits_to_words_rejects_non_digits(bad):
    with pytest.raises(ValueError):
        from hotline.numbers_sw import digits_to_words

        digits_to_words(bad)

import pytest

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

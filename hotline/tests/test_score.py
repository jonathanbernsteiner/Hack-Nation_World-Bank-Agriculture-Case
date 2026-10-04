import json
import sys
from pathlib import Path

import pytest

EVALS = Path(__file__).resolve().parents[1] / "evals"
sys.path.insert(0, str(EVALS))
import score as sc  # noqa: E402

LINES = [
    {"i": 0, "role": "agent", "en": "The median price is 5,000 shillings per kilo."},
    {"i": 1, "role": "farmer", "en": "I sold 300 kilos of kiboko yesterday for 1,500,000 shillings."},
    {"i": 2, "role": "farmer", "en": "My leaves are yellow."},
]


def sale(**kw):
    base = dict(
        kind="sale", crop="coffee", coffee_form="kiboko", amount_kg=300, price_total=1_500_000,
        currency="UGX", date_sold="2026-10-02", buyer_type=None, buyer_name=None, paid_how=None,
        evidence_quote="I sold 300 kilos of kiboko",
    )
    return {**base, **kw}


def obs(**kw):
    base = dict(
        kind="observation", crop="coffee", plot=None, symptom="yellowing_leaves",
        disease_detected=True, likely_disease="not_sure", evidence_quote="leaves are yellow",
    )
    return {**base, **kw}


def call(entries, consent="yes", tags=(), alts=None, quote_possible=True):
    return {
        "id": "t", "gold": {"consent": consent, "entries": entries},
        "free_text_alts": alts or {}, "quote_possible": quote_possible, "tags": list(tags),
    }


def run(gold, pred, consent="yes", lines=LINES):
    return sc.score_call(gold, consent, pred, lines)


def test_perfect_score():
    g = call([sale(), obs()])
    s = run(g, [sale(), obs()])
    assert s.fields_correct == s.fields_total == 9 + 5 + 1
    assert sc.summarise([s])["passed"]


def test_permutation_invariance():
    a, b = sale(), sale(amount_kg=100, price_total=500_000, date_sold="2026-09-01")
    g = call([a, b])
    s1, s2 = run(g, [a, b]), run(g, [b, a])
    assert s1.fields_correct == s2.fields_correct == s1.fields_total
    assert s1.errors == s2.errors == []


def test_missing_entry():
    g = call([sale(), obs()])
    s = run(g, [sale()])
    assert s.fields_total == 15 and s.fields_correct == 10
    assert {e[2] for e in s.errors} == {"missing_entry"}
    assert s.phantom_sales == 0


def test_extra_entry():
    g = call([obs()])
    s = run(g, [obs(), obs(symptom="rot")])
    assert s.fields_total == 11 and s.fields_correct == 6
    assert {e[2] for e in s.errors} == {"extra_entry"}


def test_phantom_sale_when_gold_has_no_sale():
    s = run(call([], tags=["no_sale_trap"]), [sale()])
    assert s.phantom_sales == 1
    assert not sc.summarise([s])["pass"]["zero_phantom_sales"]


def test_phantom_sale_extra_in_trap_call_but_not_in_plain_call():
    plain = run(call([sale()]), [sale(), sale(amount_kg=5)])
    trap = run(call([sale()], tags=["intended_sale"]), [sale(), sale(amount_kg=5)])
    assert plain.phantom_sales == 0
    assert trap.phantom_sales == 1


def test_numeric_tolerance_edges():
    assert sc.numbers_match(1000, 1010)
    assert not sc.numbers_match(1000, 1010.5)
    assert sc.numbers_match(10, 10.5)
    assert not sc.numbers_match(10, 10.6)
    assert sc.compare_field("amount_kg", 300, 303) is None
    assert sc.compare_field("amount_kg", 300, 304) == "wrong_value"
    assert sc.compare_field("amount_kg", None, None) is None
    assert sc.compare_field("amount_kg", 300, None) == "null_vs_value"
    assert sc.compare_field("amount_kg", None, 300) == "value_vs_null"
    assert sc.compare_field("date_sold", "2026-10-02", "2026-10-03") == "wrong_value"


def test_free_text_alts_and_normalisation():
    g = call([sale(buyer_name="Mukasa Traders")], alts={"buyer_name": ["Mukasa and Sons"]})
    assert run(g, [sale(buyer_name="  mukasa   traders. ")]).errors == []
    assert run(g, [sale(buyer_name="Mukasa and Sons")]).errors == []
    assert run(g, [sale(buyer_name="Kato")]).errors == [("sale", "buyer_name", "wrong_value")]


def test_quote_validity_only_over_quote_possible():
    bad = sale(evidence_quote="The median price is 5,000")  # Agent line
    s = run(call([sale()], quote_possible=False), [bad])
    assert s.quotes_total == 0
    s = run(call([sale()]), [bad])
    assert (s.quotes_total, s.quotes_valid) == (1, 0)


def test_quote_rules():
    assert sc.quote_is_valid("sold 300 kilos", LINES)
    assert sc.quote_is_valid("1500000 shillings", LINES)  # digit separators ignored
    assert not sc.quote_is_valid("My leaves are yellow.", LINES)  # whole line
    assert not sc.quote_is_valid("median price", LINES)  # agent line
    assert not sc.quote_is_valid(" ".join(["sold"] * 13), LINES)
    assert not sc.quote_is_valid(None, LINES)


def test_wrong_consent_counts():
    s = run(call([]), [], consent="no")
    assert (s.fields_total, s.fields_correct) == (1, 0)


def test_error_table_has_no_transcript_strings():
    g = call([sale(buyer_name="Secretname")], tags=["clean_sale"])
    s = run(g, [sale(buyer_name="Otherperson", amount_kg=999)])
    table = sc.summarise([s])["error_table"]
    blob = json.dumps(table)
    for leaked in ("Secretname", "Otherperson", "999", "kiboko", "kilos"):
        assert leaked not in blob
    assert table["by_tag"] == {"clean_sale": {"calls": 1, "wrong_fields": 2}}


def test_brute_force_prefers_best_alignment_with_three_entries():
    a, b, c = (sale(amount_kg=n, price_total=n * 5000) for n in (100, 200, 300))
    s = run(call([a, b, c]), [c, a, b])
    assert s.errors == []


@pytest.mark.parametrize("acc,quote,phantom,expected", [(0.96, 1.0, 0, True), (0.94, 1.0, 0, False)])
def test_pass_conditions(acc, quote, phantom, expected):
    s = sc.CallScore("x", fields_total=100, fields_correct=round(acc * 100), quotes_total=1, quotes_valid=1,
                     phantom_sales=phantom)
    assert sc.summarise([s])["passed"] is expected


def test_dev_set_files_are_well_formed():
    dev = EVALS / "dev"
    files = sorted(dev.glob("*.json"))
    assert len(files) == 10
    tags = set()
    for path in files:
        call = json.loads(path.read_text(encoding="utf-8"))
        tags.update(call["tags"])
        assert call["is_synthetic"] is True
        assert set(call["gold"]) == {"consent", "entries"}
        for entry in call["gold"]["entries"]:
            assert set(sc.SCORED_FIELDS[entry["kind"]]) <= set(entry)
        # gold scores 100% against itself
        s = sc.score_call(call, call["gold"]["consent"], call["gold"]["entries"], [])
        assert s.fields_correct == s.fields_total
    assert len(tags) >= 15


def test_run_eval_helpers():
    import run_eval

    call = json.loads((EVALS / "dev" / "d08.json").read_text(encoding="utf-8"))
    assert run_eval.identified_by(call["conversation"]) == "location"
    assert len(run_eval.load_set("dev", limit=3)) == 3
    with pytest.raises(SystemExit):
        run_eval.check_cost(100, 5.0, 0.0)
    assert len(run_eval.prompt_sha()) == run_eval.SHA_LEN


def test_fewer_preds_than_gold_aligns_to_best_gold():
    a, b, c = (sale(amount_kg=n, price_total=n * 5000) for n in (100, 200, 300))
    s = run(call([a, b, c]), [c])
    assert (s.fields_total, s.fields_correct) == (28, 10)
    assert {e[2] for e in s.errors} == {"missing_entry"}


def test_run_result_shaped_inputs_score_perfectly():
    from datetime import date

    lines_en = [
        {"i": 0, "role": "agent", "sw": "-", "t": 0.0, "en": "The median is 5,000 shillings per kilo."},
        {"i": 1, "role": "farmer", "sw": "-", "t": 2.0, "en": "I sold 300 kilos of kiboko yesterday for 1,500,000 shillings."},
    ]
    pred = sale(date_sold=date(2026, 10, 2), amount_kg=300.0, price_total=1_500_000.0, amount=300.0, unit="kg",
                quote_verified=True, confidence=0.9)
    s = run(call([sale()]), [pred], lines=lines_en)
    assert s.errors == [] and (s.quotes_total, s.quotes_valid) == (1, 1)


def test_phantom_sale_in_untagged_call_without_gold_sale():
    s = run(call([], tags=["weather_only"]), [sale()])
    assert s.phantom_sales == 1
    assert not sc.summarise([s])["passed"]


def test_default_budget_covers_one_set_of_ten():
    import run_eval

    assert run_eval.check_cost(10, run_eval.DEFAULT_MAX_COST_USD, 0.0) > 0

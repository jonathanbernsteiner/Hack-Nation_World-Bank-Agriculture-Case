"""The SYNTHETIC map-expansion transcript builder: deterministic and built from each call's own entries."""

from synthetic.map_expansion_transcripts import build_transcript

SALE = {"kind": "sale", "amount_kg": 120, "price_total": 780000, "coffee_form": "kiboko", "buyer_type": "middleman"}
PROBLEM = {"kind": "observation", "likely_disease": "coffee_leaf_rust", "evidence_quote": "The leaves have orange powder underneath."}


def test_sale_transcript_uses_the_call_entries():
    t = build_transcript("synmap-0001-1", (SALE,), "Kitojo", 6400.0)
    farmer = next(line for line in t["lines"] if line["role"] == "farmer")
    assert "120" in farmer["sw"] and "780,000" in farmer["en"] and "6,500 per kilo" in farmer["en"]
    assert t["lines"][0]["role"] == "agent" and t["lines"][-1]["role"] == "agent"
    assert "Kitojo" in t["en"] and "6,400" in t["en"]
    assert t["sw"].startswith("Agent:") and t["en"].startswith("Agent:")


def test_problem_transcript_gives_advice():
    t = build_transcript("synmap-0002-2", (PROBLEM,), "Kitojo", None)
    assert "orange powder" in t["en"] and "copper" in t["en"]


def test_deterministic_and_seeded_by_conversation():
    assert build_transcript("synmap-0001-1", (SALE,), "Kitojo", 6400.0) == build_transcript("synmap-0001-1", (SALE,), "Kitojo", 6400.0)


def test_call_without_entries_asks_for_the_price():
    t = build_transcript("synmap-0003-1", (), "Kitojo", 6400.0)
    assert "price" in t["en"].lower() and len(t["lines"]) >= 4

"""Regression tests for the coffee problem reference (#17).

Stdlib only, so they run without a project environment:

    python3 -m unittest discover -s data/tests -v

They pin the contract that #45 (new rows), #46 (knowledge file) and #59
(likely_disease enum) build on, and the farmer-safety rules from
docs/hotline-spec.md section 8.
"""

import ast
import csv
import json
import re
import unittest
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = DATA_DIR.parent
DISEASES_PATH = DATA_DIR / "coffee-diseases.json"
EVAL_PATH = DATA_DIR / "disease-eval.csv"
README_PATH = DATA_DIR / "README.md"
LEDGER_ENUMS_PATH = REPO_ROOT / "server" / "farm_ledger" / "enums.py"

ROW_KEYS = [
    "id", "kind", "common_name", "scientific_name", "swahili_name",
    "plant_parts", "symptom_categories", "farmer_words", "key_signs",
    "look_alikes", "tell_apart_question", "conditions", "urgency",
    "farmer_advice_en", "officer_note_en", "escalate_when", "regions",
    "in_bracol", "sources",
]
SOURCE_KEYS = {"publisher", "title", "url", "year"}
KINDS = {"disease", "pest", "disorder", "fallback"}
URGENCIES = {"routine", "soon", "urgent"}
PLANT_PARTS = {"leaves", "berries", "stem", "roots", "whole_tree"}
FALLBACK_ID = "not_sure"
EVAL_COLUMNS = ["phrase", "symptom", "expected_id", "not_sure_ok", "is_synthetic", "note"]
ID_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")

# Ids merged with #17. They are frozen: #45 may append rows, never rename these.
FROZEN_IDS = {
    "coffee_leaf_rust", "coffee_berry_disease", "coffee_wilt_disease",
    "bacterial_blight", "brown_eye_spot", "phoma_leaf_blight",
    "fusarium_bark_disease", "armillaria_root_rot", "american_leaf_spot",
    "sooty_mould", "coffee_leaf_miner", "antestia_bug", "coffee_berry_borer",
    "white_stem_borer", "coffee_thrips", "coffee_mealybug",
    "coffee_root_mealybug", "green_scale", "coffee_nematodes",
    "coffee_lace_bug", "coffee_leaf_skeletoniser", "nitrogen_deficiency",
    "magnesium_deficiency", "potassium_deficiency", "waterlogging",
    "drought_stress", "sun_scorch", "overbearing_dieback", "hail_damage",
    FALLBACK_ID,
}

# Serious problems that must always reach the extension officer (PR #35 review guide).
MUST_BE_URGENT = {
    "coffee_berry_disease", "coffee_wilt_disease", "bacterial_blight",
    "fusarium_bark_disease", "armillaria_root_rot", "white_stem_borer",
}

# Spec section 8, guardrail 1: no pesticide/fungicide/fertiliser product,
# active ingredient, dose or mix rate in anything the farmer hears.
BANNED_IN_FARMER_ADVICE = re.compile(
    r"\b(?:copper|bordeaux|fungicides?|insecticides?|herbicides?|pesticides?|"
    r"nematicides?|acaricides?|chlorpyrifos|dursban|glyphosate|mancozeb|"
    r"chlorothalonil|triadimefon|bayleton|cyproconazole|hexaconazole|"
    r"deltamethrin|decis|endosulfan|profenofos|imidacloprid|fenitrothion|"
    r"carbendazim|dimethoate|neem|npk|urea|super\s?phosphate|dose|doses|"
    r"dosage|mix rate|g/l|ml/l|per litre|per liter)\b"
    r"|\b\d+(?:\.\d+)?\s?(?:ml|g|kg|l|cc|litres?|liters?|%)(?=\W|$)",
    re.IGNORECASE,
)

# Spec section 8, guardrail 4 and the #17 wilt decision: the diagnosis comes from
# a phone call, so advice to destroy a tree must put the extension officer first.
DESTROY_TREE = re.compile(r"\b(?:uproot\w*|dig (?:out|up)|cut (?:\w+ )?down|fell)\b", re.IGNORECASE)
OFFICER = re.compile(r"extension officer", re.IGNORECASE)
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def load_rows():
    with DISEASES_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


def load_eval_rows():
    with EVAL_PATH.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        return reader.fieldnames, list(reader)


def ledger_symptoms():
    """The 9 Symptom values of the ledger (server/farm_ledger/enums.py)."""
    tree = ast.parse(LEDGER_ENUMS_PATH.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "Symptom":
            return {
                stmt.value.value
                for stmt in node.body
                if isinstance(stmt, ast.Assign) and isinstance(stmt.value, ast.Constant)
            }
    raise AssertionError("Symptom enum not found in server/farm_ledger/enums.py")


class CoffeeDiseaseSchemaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = load_rows()
        cls.by_id = {row["id"]: row for row in cls.rows}
        cls.problem_rows = [row for row in cls.rows if row["kind"] != "fallback"]

    def test_every_row_has_exactly_the_frozen_keys_in_order(self):
        for row in self.rows:
            with self.subTest(row=row.get("id")):
                self.assertEqual(list(row.keys()), ROW_KEYS)

    def test_ids_are_unique_snake_case_and_the_merged_ids_still_exist(self):
        ids = [row["id"] for row in self.rows]
        self.assertEqual(len(ids), len(set(ids)), "duplicate ids")
        for row_id in ids:
            self.assertRegex(row_id, ID_PATTERN)
        self.assertGreaterEqual(len(self.rows), len(FROZEN_IDS))
        self.assertEqual(FROZEN_IDS - set(ids), set(), "a merged id was removed or renamed")

    def test_enums(self):
        symptoms = ledger_symptoms()
        self.assertEqual(len(symptoms), 9)
        for row in self.rows:
            with self.subTest(row=row["id"]):
                self.assertIn(row["kind"], KINDS)
                self.assertIn(row["urgency"], URGENCIES)
                self.assertLessEqual(set(row["symptom_categories"]), symptoms)
                self.assertLessEqual(set(row["plant_parts"]), PLANT_PARTS)
                self.assertIsInstance(row["in_bracol"], bool)

    def test_not_sure_is_the_only_fallback(self):
        fallbacks = [row["id"] for row in self.rows if row["kind"] == "fallback"]
        self.assertEqual(fallbacks, [FALLBACK_ID])

    def test_every_problem_row_is_cited(self):
        for row in self.problem_rows:
            with self.subTest(row=row["id"]):
                self.assertTrue(row["sources"], "no sources")
                for source in row["sources"]:
                    self.assertEqual(set(source), SOURCE_KEYS)
                    self.assertTrue(source["publisher"].strip())
                    self.assertTrue(source["title"].strip())
                    self.assertRegex(source["url"], r"^https?://\S+$")
                    self.assertTrue(source["year"] is None or isinstance(source["year"], int))

    def test_every_problem_row_can_be_matched_and_told_apart(self):
        for row in self.problem_rows:
            with self.subTest(row=row["id"]):
                self.assertTrue(row["symptom_categories"])
                self.assertTrue(row["plant_parts"])
                self.assertTrue(row["farmer_words"])
                self.assertTrue(row["key_signs"])
                self.assertTrue(row["tell_apart_question"].strip().endswith("?"))

    def test_look_alikes_resolve_to_other_rows(self):
        for row in self.rows:
            with self.subTest(row=row["id"]):
                for look_alike in row["look_alikes"]:
                    self.assertIn(look_alike, self.by_id)
                    self.assertNotEqual(look_alike, row["id"])
                self.assertEqual(len(row["look_alikes"]), len(set(row["look_alikes"])))


class FarmerSafetyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = load_rows()
        cls.by_id = {row["id"]: row for row in cls.rows}

    def test_farmer_advice_names_no_chemical_product_or_dose(self):
        for row in self.rows:
            with self.subTest(row=row["id"]):
                hits = [m.group(0) for m in BANNED_IN_FARMER_ADVICE.finditer(row["farmer_advice_en"])]
                self.assertEqual(hits, [], "chemical/product/dose wording in farmer_advice_en")

    def test_serious_problems_stay_urgent(self):
        for row_id in MUST_BE_URGENT:
            with self.subTest(row=row_id):
                self.assertEqual(self.by_id[row_id]["urgency"], "urgent")

    def test_every_farmer_advice_points_to_the_extension_officer(self):
        for row in self.rows:
            with self.subTest(row=row["id"]):
                self.assertRegex(row["farmer_advice_en"], OFFICER)

    def test_destroying_a_tree_is_gated_on_the_extension_officer(self):
        for row in self.rows:
            for sentence in SENTENCE_SPLIT.split(row["farmer_advice_en"]):
                destroy = DESTROY_TREE.search(sentence)
                if destroy is None:
                    continue
                with self.subTest(row=row["id"], sentence=sentence):
                    officer = OFFICER.search(sentence)
                    self.assertIsNotNone(officer, "uproot/dig-out advice without the extension officer")
                    self.assertLess(
                        officer.start(), destroy.start(),
                        "the extension officer must come before the uproot/dig-out step",
                    )


class EvalPhrasesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ids = {row["id"]: row for row in load_rows()}
        cls.columns, cls.eval_rows = load_eval_rows()

    def test_columns_are_frozen(self):
        self.assertEqual(self.columns, EVAL_COLUMNS)
        self.assertGreaterEqual(len(self.eval_rows), 32)

    def test_every_phrase_is_consistent_with_the_reference(self):
        symptoms = ledger_symptoms()
        phrases = [row["phrase"] for row in self.eval_rows]
        self.assertEqual(len(phrases), len(set(phrases)), "duplicate phrases")
        for row in self.eval_rows:
            with self.subTest(phrase=row["phrase"]):
                self.assertIn(row["expected_id"], self.ids)
                self.assertIn(row["symptom"], symptoms)
                self.assertIn(row["not_sure_ok"], {"true", "false"})
                self.assertEqual(row["is_synthetic"], "true")
                if row["expected_id"] == FALLBACK_ID:
                    self.assertEqual(row["not_sure_ok"], "true")
                else:
                    self.assertIn(row["symptom"], self.ids[row["expected_id"]]["symptom_categories"])


class ReadmeTest(unittest.TestCase):
    def test_readme_does_not_describe_the_closed_matcher(self):
        text = README_PATH.read_text(encoding="utf-8")
        self.assertIsNone(re.search(r"gemma|ollama|#29|matcher", text, re.IGNORECASE))


if __name__ == "__main__":
    unittest.main()

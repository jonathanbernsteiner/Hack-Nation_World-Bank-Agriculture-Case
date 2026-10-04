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


# --- Review cycle 2 -----------------------------------------------------------
# The #46 knowledge file turns these fields into what the agent says on the call
# ("farmer says", "ask to tell apart", "do now / prevent", "call officer when").
# officer_note_en and conditions are not in this list: they are for the officer.
FARMER_FACING_FIELDS = (
    "farmer_advice_en", "tell_apart_question", "escalate_when", "farmer_words", "key_signs",
)
ADVICE_FIELDS = ("farmer_advice_en", "tell_apart_question", "escalate_when")
# escalate_when is itself the "call the officer when" line, so it may say
# "call before uprooting"; the other two must never ask for a tree to be destroyed first.
ACTION_FIELDS = ("farmer_advice_en", "tell_apart_question")

# Guardrail 1, widened with every product, active ingredient and fertiliser that
# officer_note_en names (copper oxychloride, triazoles, strobilurins, Epsom salts, ...)
# plus common East African brands, so an officer measure can't leak into farmer text.
CHEMICAL_TERMS = re.compile(
    r"\b(?:copper|cuprous|oxychloride|bordeaux|fungicides?|insecticides?|herbicides?|"
    r"pesticides?|bio-?pesticides?|nematicides?|acaricides?|chlorpyrifos|dursban|"
    r"glyphosate|roundup|mancozeb|dithane|chlorothalonil|dithianon|captan|triazoles?|"
    r"triadimefon|bayleton|cyproconazole|hexaconazole|propiconazole|tebuconazole|"
    r"strobilurins?|azoxystrobin|metalaxyl|ridomil|kocide|nordox|deltamethrin|decis|"
    r"cypermethrin|lambda-?cyhalothrin|karate|pyrethroids?|pyrethrum|organophosphates?|"
    r"endosulfan|profenofos|imidacloprid|fipronil|regent|fenitrothion|ethion|rhodocide|"
    r"ultracide|supracide|aldrin|dieldrin|carbendazim|dimethoate|aluminium phosphide|"
    r"gastoxin|neem|kaolin|npk|urea|ammonium|sulphate|sulfate|epsom|dolomite|muriate|"
    r"potash|super\s?phosphate|dose|doses|dosage|mix rate|g/l|ml/l|per litre|per liter)\b",
    re.IGNORECASE,
)

# Guardrail 4 also covers burning, removing or pulling out a tree, active or passive.
TREE = r"(?:(?:the|a|an|any|all|every|this|that|these|those|its|your|dead|dying|sick|affected|infected|infested|attacked|badly|old|whole|diseased|wilted|wilting|coffee)\s+){0,4}trees?\b(?!\s+stumps?)"
DESTROY_TREE_OBJECT = re.compile(
    r"\b(?:burn\w*|destroy\w*|remov\w*|pull\w* (?:out|up)|chop\w* (?:\w+ )?down|kill\w*)\s+" + TREE
    + r"|\btrees?\b(?:\s+\S+){0,4}?\s+(?:burnt|burned|destroyed|removed|pulled (?:out|up)|chopped down|felled|killed)\b",
    re.IGNORECASE,
)

# Guardrail 5: never say an urgent (or unsure) problem can wait or skip the officer.
SKIPS_OFFICER = re.compile(
    r"\b(?:can wait|no need to|not urgent|nothing to worry|"
    r"without (?:\w+ ){0,3}(?:the )?(?:extension )?officer|"
    r"instead of (?:calling|asking|waiting for) the (?:extension )?officer|"
    r"(?:do not|don't|never) (?:need to )?(?:call|ask|tell|bother|wait for) the (?:extension )?officer)\b",
    re.IGNORECASE,
)

# The BRACOL paper names no pathogens, so its "brown leaf spot" is not Phoma (#17 decision).
BRACOL_ROWS = {"coffee_leaf_rust", "brown_eye_spot", "coffee_leaf_miner"}


def field_texts(row, fields):
    """(field, text) pairs for the given fields; list fields yield one pair per item."""
    for field in fields:
        value = row[field]
        for text in value if isinstance(value, list) else [value]:
            if text:
                yield field, text


def first_destroy_step(sentence):
    """Earliest uproot/dig-out/burn/remove-a-tree step in the sentence, or None."""
    matches = [m for m in (DESTROY_TREE.search(sentence), DESTROY_TREE_OBJECT.search(sentence)) if m]
    return min(matches, key=lambda m: m.start()) if matches else None


class SafetyPatternSelfTest(unittest.TestCase):
    """The safety regexes must catch known-bad wording, or the data tests prove nothing."""

    def test_patterns_flag_bad_wording(self):
        for text in ("Spray copper oxychloride.", "Use a triazole.", "Add Epsom salts.",
                     "Apply 2 doses.", "Mix 50 ml per litre."):
            self.assertRegex(text, CHEMICAL_TERMS)
        for text in ("Burn the dead trees where they stand.", "Remove the dying coffee trees.",
                     "Pull out the sick tree.", "Badly attacked trees must be burnt.",
                     "Uproot and burn it."):
            self.assertIsNotNone(first_destroy_step(text), text)
        for text in ("This can wait until next season.", "There is no need to call anyone.",
                     "Uproot it without waiting for the extension officer.",
                     "Do not call the extension officer."):
            self.assertRegex(text, SKIPS_OFFICER)

    def test_patterns_leave_safe_wording_alone(self):
        for text in ("Remove old tree stumps and their roots.", "Strip old berries off the trees and burn them.",
                     "Cut off and destroy badly infested branches.", "Keep or plant shade trees.",
                     "Kill the grub inside with a wire."):
            self.assertIsNone(first_destroy_step(text), text)
        self.assertNotRegex("Feed the trees with manure or compost.", CHEMICAL_TERMS)
        self.assertNotRegex("Call the extension officer the same day.", SKIPS_OFFICER)


class FarmerSafetyCycle2Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = load_rows()
        cls.by_id = {row["id"]: row for row in cls.rows}

    def test_no_chemical_product_or_dose_in_any_farmer_facing_field(self):
        for row in self.rows:
            for field, text in field_texts(row, FARMER_FACING_FIELDS):
                with self.subTest(row=row["id"], field=field):
                    self.assertEqual([m.group(0) for m in CHEMICAL_TERMS.finditer(text)], [])

    def test_any_tree_destroying_step_comes_after_the_extension_officer(self):
        for row in self.rows:
            for field, text in field_texts(row, ACTION_FIELDS):
                for sentence in SENTENCE_SPLIT.split(text):
                    destroy = first_destroy_step(sentence)
                    if destroy is None:
                        continue
                    with self.subTest(row=row["id"], field=field, sentence=sentence):
                        officer = OFFICER.search(sentence)
                        self.assertIsNotNone(officer, "tree-destroying step without the extension officer")
                        self.assertLess(officer.start(), destroy.start())

    def test_urgent_and_unsure_problems_never_wait_or_skip_the_officer(self):
        for row in self.rows:
            if row["urgency"] != "urgent" and row["id"] != FALLBACK_ID:
                continue
            for field, text in field_texts(row, ADVICE_FIELDS):
                with self.subTest(row=row["id"], field=field):
                    self.assertIsNone(SKIPS_OFFICER.search(text))

    def test_not_sure_names_no_problem_and_always_escalates(self):
        row = self.by_id[FALLBACK_ID]
        for key in ("symptom_categories", "plant_parts", "farmer_words", "key_signs", "look_alikes"):
            self.assertEqual(row[key], [], key)
        self.assertTrue(row["escalate_when"].startswith("Always"))
        advice = row["farmer_advice_en"].lower()
        for other in self.rows:
            if other["id"] == FALLBACK_ID:
                continue
            with self.subTest(other=other["id"]):
                self.assertNotIn(other["common_name"].lower(), advice)
                self.assertNotIn(FALLBACK_ID, other["look_alikes"])

    def test_only_the_three_bracol_classes_are_flagged(self):
        self.assertEqual({row["id"] for row in self.rows if row["in_bracol"]}, BRACOL_ROWS)


# --- Review cycle 3 -----------------------------------------------------------
# Kiswahili names go straight into the #46 knowledge file ("farmer says (EN | SW)")
# and from there into what the agent says. #17 decided they come only from a
# source, never from our own translation. The cited TaCRI reports are the
# Kiswahili editions ("Taarifa ya Mwaka ..., Kiswahili").
KISWAHILI_SOURCE_TITLE = re.compile(r"kiswahili|swahili|taarifa ya mwaka", re.IGNORECASE)
README_SWAHILI_SECTION = re.compile(r"- \*\*Swahili names:\*\*\n(.*?)\n- \*\*", re.DOTALL)
README_SWAHILI_ITEM = re.compile(r"^\s+- [^:\n]+: \*([^*\n]+)\*\s*$", re.MULTILINE)


def readme_number(test, pattern, text):
    """The integer groups of the one README sentence that states a count."""
    match = re.search(pattern, text)
    test.assertIsNotNone(match, f"README no longer states this count: {pattern}")
    return tuple(int(group) for group in match.groups())


def readme_swahili_names(text):
    section = README_SWAHILI_SECTION.search(text)
    if section is None:
        raise AssertionError("README has no '- **Swahili names:**' section")
    return [name.strip() for name in README_SWAHILI_ITEM.findall(section.group(1))]


class SwahiliProvenanceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = load_rows()
        cls.named = {row["id"]: row for row in cls.rows if row["swahili_name"] is not None}

    def test_every_swahili_name_cites_a_kiswahili_source(self):
        self.assertTrue(self.named, "no row has a Kiswahili name")
        for row_id, row in self.named.items():
            with self.subTest(row=row_id):
                name = row["swahili_name"]
                self.assertIsInstance(name, str)
                self.assertEqual(name, name.strip())
                self.assertTrue(name, "empty Kiswahili name: use null instead")
                titles = [source["title"] for source in row["sources"]]
                self.assertTrue(
                    any(KISWAHILI_SOURCE_TITLE.search(title) for title in titles),
                    f"'{name}' has no Kiswahili-language source among {titles}",
                )

    def test_readme_lists_exactly_the_swahili_names_in_the_data(self):
        text = README_PATH.read_text(encoding="utf-8")
        listed = readme_swahili_names(text)
        self.assertEqual(len(listed), len(set(listed)), "a Kiswahili name is listed twice")
        self.assertEqual(sorted(listed), sorted(row["swahili_name"] for row in self.named.values()))
        (stated,) = readme_number(self, r"Only (\d+) rows have one", text)
        self.assertEqual(stated, len(self.named))


class ReadmeCountsMatchDataTest(unittest.TestCase):
    """#46 and the pitch quote these README numbers; #45 must update them with its rows."""

    @classmethod
    def setUpClass(cls):
        cls.rows = load_rows()
        cls.problem_rows = [row for row in cls.rows if row["kind"] != "fallback"]
        cls.text = README_PATH.read_text(encoding="utf-8")

    def count_kind(self, kind):
        return sum(row["kind"] == kind for row in self.rows)

    def test_files_table_matches_the_rows_and_sources(self):
        stated = readme_number(
            self,
            r"(\d+) rows: (\d+) diseases, (\d+) pests, (\d+) non-disease look-alikes, (\d+) `not_sure` fallback",
            self.text,
        )
        actual = (
            len(self.rows), self.count_kind("disease"), self.count_kind("pest"),
            self.count_kind("disorder"), self.count_kind("fallback"),
        )
        self.assertEqual(stated, actual)
        (sources,) = readme_number(self, r"(\d+) cited sources", self.text)
        self.assertEqual(sources, len({s["url"] for row in self.rows for s in row["sources"]}))

    def test_eval_phrase_count_matches_the_csv(self):
        _, eval_rows = load_eval_rows()
        (stated,) = readme_number(self, r"(\d+) farmer-style phrases", self.text)
        self.assertEqual(stated, len(eval_rows))

    def test_sourcing_sentence_matches_the_rows(self):
        cited, total = readme_number(self, r"Every problem row \((\d+) of (\d+)\)", self.text)
        self.assertEqual((cited, total), (len(self.problem_rows), len(self.rows)))
        self.assertTrue(all(row["sources"] for row in self.problem_rows))
        three_plus, of_problem_rows = readme_number(
            self, r"(\d+) of the (\d+) problem rows cite three or more", self.text,
        )
        self.assertEqual(of_problem_rows, len(self.problem_rows))
        self.assertEqual(three_plus, sum(len(row["sources"]) >= 3 for row in self.problem_rows))

    def test_overlap_and_bracol_counts_match_the_rows(self):
        (leaf_spots,) = readme_number(self, r"(\d+) rows include `leaf_spots`", self.text)
        self.assertEqual(leaf_spots, sum("leaf_spots" in row["symptom_categories"] for row in self.rows))
        (bracol,) = readme_number(self, r"cover only (\d+) of our rows", self.text)
        self.assertEqual(bracol, sum(row["in_bracol"] for row in self.rows))


class ReadmeParsingSelfTest(unittest.TestCase):
    """The README parsers must find a drifted count or name, or the tests above prove nothing."""

    def test_swahili_parser_reads_the_bullet_list(self):
        text = (
            "- **Swahili names:**\n  - Only 2 rows have one:\n"
            "    - leaf rust: *kutu ya majani*\n    - berry borer: *ruhuka*\n"
            "  - None has been checked by a speaker.\n- **The eval phrases are synthetic.**\n"
        )
        self.assertEqual(readme_swahili_names(text), ["kutu ya majani", "ruhuka"])
        self.assertEqual(readme_number(self, r"Only (\d+) rows have one", text), (2,))

    def test_missing_count_sentence_fails_loudly(self):
        with self.assertRaises(AssertionError):
            readme_number(self, r"(\d+) farmer-style phrases", "32 phrases, reworded")


# --- Uganda rows (#45) ---------------------------------------------------------
UGANDA_IDS = {
    "black_coffee_twig_borer": "pest",
    "low_soil_fertility": "disorder",
    "old_unpruned_trees": "disorder",
    "weed_competition": "disorder",
    "poor_harvest_practice": "disorder",
}


class UgandaRowsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = load_rows()
        cls.by_id = {row["id"]: row for row in cls.rows}
        _, cls.eval_rows = load_eval_rows()

    def test_new_ids_exist_with_the_right_kind_and_not_sure_stays_last(self):
        for row_id, kind in UGANDA_IDS.items():
            with self.subTest(row=row_id):
                self.assertEqual(self.by_id[row_id]["kind"], kind)
                self.assertFalse(self.by_id[row_id]["in_bracol"])
        self.assertEqual(self.rows[-1]["id"], FALLBACK_ID)

    def test_twig_borer_signs_urgency_and_look_alikes(self):
        row = self.by_id["black_coffee_twig_borer"]
        self.assertEqual(row["scientific_name"], "Xylosandrus compactus")
        self.assertEqual(row["urgency"], "soon")
        self.assertIn("underside", row["tell_apart_question"])
        self.assertIn("below the hole", row["farmer_advice_en"])
        self.assertTrue({"coffee_wilt_disease", "overbearing_dieback"} <= set(row["look_alikes"]))
        self.assertIn("black_coffee_twig_borer", self.by_id["coffee_wilt_disease"]["look_alikes"])
        self.assertIn("black_coffee_twig_borer", self.by_id["overbearing_dieback"]["look_alikes"])

    def test_back_links_are_reciprocal(self):
        pairs = [
            ("overbearing_dieback", "old_unpruned_trees"),
            ("nitrogen_deficiency", "low_soil_fertility"),
            ("brown_eye_spot", "bacterial_blight"),
            ("coffee_root_mealybug", "armillaria_root_rot"),
        ]
        for a, b in pairs:
            with self.subTest(a=a, b=b):
                self.assertIn(b, self.by_id[a]["look_alikes"])
        for a, b in (("bacterial_blight", "brown_eye_spot"), ("armillaria_root_rot", "coffee_root_mealybug")):
            with self.subTest(a=a, b=b):
                self.assertIn(b, self.by_id[a]["look_alikes"])

    def test_practice_rows_are_routine_and_name_no_swahili_without_a_source(self):
        for row_id in UGANDA_IDS:
            row = self.by_id[row_id]
            with self.subTest(row=row_id):
                self.assertIsNone(row["swahili_name"])
                if row_id != "black_coffee_twig_borer":
                    self.assertEqual(row["urgency"], "routine")

    def test_eval_phrases_cover_every_new_id(self):
        covered = {row["expected_id"] for row in self.eval_rows}
        self.assertTrue(set(UGANDA_IDS) <= covered)
        new_rows = [row for row in self.eval_rows if row["expected_id"] in UGANDA_IDS]
        self.assertGreaterEqual(len(new_rows), 10)
        self.assertTrue(any("wilting" == r["symptom"] and r["not_sure_ok"] == "true" for r in self.eval_rows
                            if r["expected_id"] in UGANDA_IDS or "borer" in r["note"]))


if __name__ == "__main__":
    unittest.main()

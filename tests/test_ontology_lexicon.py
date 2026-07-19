import re
import unittest

from data_eng.ontology_lexicon import (CAPABILITY_CONCEPTS, NEGATION_PATTERN,
                                       load_lexicon, word_boundary_pattern)

try:
    from data_eng.trust_scoring import CAPABILITY_LEXICON
except ImportError:                     # pyspark not installed locally
    CAPABILITY_LEXICON = None


class OntologyLexiconTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lex = load_lexicon()

    def test_ontology_loads_from_repo(self):
        self.assertIsNotNone(self.lex, "ontology/*.yaml not found next to data_eng/")

    @unittest.skipIf(CAPABILITY_LEXICON is None, "pyspark not installed locally")
    def test_capability_keys_match_trust_scoring(self):
        self.assertEqual(set(CAPABILITY_CONCEPTS), set(CAPABILITY_LEXICON))

    def test_every_capability_has_field_vocabulary(self):
        for cap in CAPABILITY_CONCEPTS:
            self.assertTrue(self.lex.procedure_keywords(cap), f"{cap}: no procedure kws")
            self.assertTrue(self.lex.equipment_keywords(cap), f"{cap}: no equipment kws")
            self.assertTrue(self.lex.specialty_ids(cap), f"{cap}: no specialty ids")

    def test_edge_expansion_reaches_cross_field_evidence(self):
        # The point of the ontology: dialysis equipment vocabulary includes the
        # RO water plant — evidence the flat lexicon can never see.
        kws = self.lex.equipment_keywords("dialysis")
        self.assertTrue(any("ro plant" in k or "ro water" in k or "reverse osmosis" in k
                            for k in kws), kws)

    def test_advanced_equipment_tiers(self):
        self.assertTrue(self.lex.advanced_equipment_keywords("cardiac"))  # cath lab et al.


class BottomUpDerivationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from data_eng.ontology_lexicon import derive_capability_concepts
        cls.lex = load_lexicon()
        cls.derived = derive_capability_concepts(cls.lex)

    def test_derivation_covers_every_capability(self):
        self.assertEqual(set(self.derived), set(CAPABILITY_CONCEPTS))
        for cap, kinds in self.derived.items():
            self.assertTrue(kinds["procedures"], f"{cap}: derivation found no procedures")
            self.assertTrue(kinds["equipment"], f"{cap}: derivation found no equipment")

    def test_hub_guard_blocks_operating_theatre_for_emergency(self):
        # operating-theatre is required by 19 procedures; unless a specialty
        # explicitly models it as corroborating, the hop must not pull it in.
        self.assertNotIn("operating-theatre", self.derived["emergency"]["equipment"])

    def test_derivation_recovers_explicit_corroboration_edges(self):
        # nephrology's modeled corroborating_equipment must survive derivation.
        self.assertIn("ro-water-plant", self.derived["dialysis"]["equipment"])


class WordBoundaryTests(unittest.TestCase):
    """The regex is built for Spark (Java) but is Python-compatible — test it here."""

    def _match(self, keywords, text):
        return re.search(word_boundary_pattern(keywords), text.lower()) is not None

    def test_icu_no_longer_matches_curriculum(self):
        self.assertFalse(self._match(["icu"], "our curriculum covers first aid"))
        self.assertTrue(self._match(["icu"], "22-bed Level II ICU with ventilators"))

    def test_multiword_alias_spans_punctuation(self):
        self.assertTrue(self._match(["x ray"], "Portable X-ray machine in Casualty"))

    def test_negation_pattern_flags_referral_and_absence(self):
        for text in ["patients are referred elsewhere for dialysis",
                     "no dialysis available on site",
                     "listed as a referral hospital"]:
            self.assertIsNotNone(re.search(NEGATION_PATTERN, text), text)
        self.assertIsNone(re.search(NEGATION_PATTERN,
                                    "20-bed dialysis unit with 10 machines"))


if __name__ == "__main__":
    unittest.main()

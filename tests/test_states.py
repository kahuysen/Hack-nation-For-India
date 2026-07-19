import unittest

from data_eng.states import CANONICAL_STATE_NAMES, canonical_state_name


class CanonicalStateTests(unittest.TestCase):
    def test_contract_has_36_unique_states_and_union_territories(self):
        self.assertEqual(len(CANONICAL_STATE_NAMES), 36)
        self.assertEqual(len(set(CANONICAL_STATE_NAMES)), 36)
        self.assertEqual(CANONICAL_STATE_NAMES, tuple(sorted(CANONICAL_STATE_NAMES)))

    def test_common_aliases_have_one_display_name(self):
        self.assertEqual(canonical_state_name("DELHI"), "Delhi")
        self.assertEqual(canonical_state_name("NCT of Delhi"), "Delhi")
        self.assertEqual(canonical_state_name("Maharastra"), "Maharashtra")
        self.assertEqual(canonical_state_name("Orissa"), "Odisha")
        self.assertEqual(canonical_state_name("Tamilnadu"), "Tamil Nadu")
        self.assertEqual(
            canonical_state_name("Dadra & Nagar Haveli"),
            "Dadra and Nagar Haveli and Daman and Diu",
        )

    def test_non_state_source_values_are_rejected(self):
        self.assertIsNone(canonical_state_name("Chennai"))
        self.assertIsNone(canonical_state_name("coordinates 77 2 28 5 type point"))


if __name__ == "__main__":
    unittest.main()

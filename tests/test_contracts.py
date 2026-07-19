import unittest

from data_eng.contracts import CAPABILITIES, resolve_capability


class CapabilityContractTests(unittest.TestCase):
    def test_ids_are_unique(self):
        self.assertEqual(len(CAPABILITIES), len({item.id for item in CAPABILITIES}))

    def test_api_labels_resolve_to_pipeline_keys(self):
        self.assertEqual(resolve_capability("Emergency care").pipeline_key, "emergency")
        self.assertEqual(resolve_capability("NICU").pipeline_key, "NICU")
        self.assertEqual(resolve_capability("cardiac").label, "Cardiac care")

    def test_unknown_capability_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unknown capability"):
            resolve_capability("x-ray")


if __name__ == "__main__":
    unittest.main()

import unittest
from unittest.mock import patch

from backend.app.main import app
from backend.app.routes import evidence, locations, planning


REGION = {
    "capability_id": "nicu", "state": "Bihar", "district": "Patna",
    "lat": 25.6, "lon": 85.1, "n_records": 12, "n_candidates": 2,
    "claiming": 2, "corroborated": 1, "trust_weighted_supply": 0.7,
    "coverage": 0.35, "knowledge": 0.75, "mean_source_trust": 0.5,
    "need_score": 62.0, "n_indicators": 2, "data_confidence": "solid",
    "verdict": "medical_desert", "risk_score": 0.3023,
}

FACILITY = {
    "capability_id": "nicu", "capability_key": "NICU", "facility_id": "f-1",
    "name": "Example Hospital", "state": "Bihar", "district": "Patna",
    "pin": "800001", "is_candidate": 1, "claiming": 1, "n_corroborating": 1,
    "tier": "moderate", "trust_weight": 0.5, "knowledge": 0.75,
    "source_trust": 0.5, "data_confidence": "high",
    "evidence_json": '[{"field":"procedure","snippet":"neonatal intensive care"},'
                     '{"field":"equipment","snippet":""}]',
    "description": None, "latitude": 25.6, "longitude": 85.1, "source_urls": "[]",
}


LOCATION = {
    "facility_id": "f-1", "name": "Example Hospital", "facility_type": "hospital",
    "state": "Bihar", "district": "Patna", "latitude": 25.6, "longitude": 85.1,
}


class ApiContractTests(unittest.TestCase):
    def test_region_limit_supports_the_full_materialized_rollup(self):
        parameter = next(
            item
            for item in app.openapi()["paths"]["/api/regions"]["get"]["parameters"]
            if item["name"] == "limit"
        )
        self.assertEqual(parameter["schema"]["maximum"], 2000)

    @patch("backend.app.routes.planning.query_rows", return_value=[REGION])
    def test_region_query_uses_canonical_id(self, query):
        result = planning.rank_regions("NICU", None, None, 50)
        self.assertEqual(result[0]["capability_id"], "nicu")
        self.assertEqual(query.call_args.args[1], ["nicu", 50])

    @patch("backend.app.routes.locations.query_rows", return_value=[LOCATION])
    def test_facility_locations_pass_through(self, _query):
        result = locations.facility_locations()
        self.assertEqual(result, [LOCATION])

    @patch("backend.app.routes.locations.query_rows",
           side_effect=RuntimeError("TABLE_OR_VIEW_NOT_FOUND"))
    def test_missing_locations_table_degrades_to_empty(self, _query):
        self.assertEqual(locations.facility_locations(), [])

    @patch("backend.app.routes.evidence.query_rows", return_value=[FACILITY])
    def test_empty_evidence_is_removed(self, _query):
        result = evidence.facility_evidence("nicu", None, None, True, 100)
        self.assertEqual(result[0]["evidence"], [
            {"field": "procedure", "snippet": "neonatal intensive care"}
        ])
        self.assertNotIn("evidence_json", result[0])


if __name__ == "__main__":
    unittest.main()

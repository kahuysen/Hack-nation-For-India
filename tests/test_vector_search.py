import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np

from backend.app.models import SimilaritySearchRequest
from backend.app.routes import search
from backend.app.services import vector_search
from data_eng.vector_search.contracts import validate_unique_ids
from data_eng.vector_search.prepare_documents import build_document


class VectorPipelineContractTests(unittest.TestCase):
    def test_document_builder_is_stable_and_searchable(self):
        document = build_document({
            "facility_id": "facility-1",
            "name": "Example Hospital",
            "state": "Bihar",
            "district": "Patna",
            "facility_type": "hospital",
            "capability": "NICU",
            "procedure": "neonatal intensive care",
            "description": "Provides round-the-clock neonatal support.",
        })
        self.assertEqual(document["document_id"], "facility-1")
        self.assertIn("Capabilities: NICU", document["document_text"])
        self.assertIn("Procedures: neonatal intensive care", document["document_text"])
        self.assertEqual(len(document["document_hash"]), 64)

    def test_duplicate_document_ids_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "unique"):
            validate_unique_ids(["same", "same"])


class VectorSearchServiceTests(unittest.TestCase):
    def test_query_embedding_is_normalized(self):
        model = Mock()
        model.query_embed.return_value = iter([
            np.ones(vector_search.settings.embedding_dimension, dtype=np.float32)
        ])
        with patch("backend.app.services.vector_search.embedding_model", return_value=model):
            vector = vector_search.embed_query("neonatal intensive care")
        self.assertEqual(len(vector), vector_search.settings.embedding_dimension)
        self.assertAlmostEqual(float(np.linalg.norm(vector)), 1.0, places=5)

    def test_sdk_response_is_mapped_to_public_contract(self):
        response = SimpleNamespace(as_dict=lambda: {
            "manifest": {"columns": [
                {"name": "document_id"}, {"name": "name"}
            ]},
            "result": {"data_array": [["f-1", "Example Hospital", 0.91]]},
        })
        self.assertEqual(vector_search._response_rows(response), [{
            "document_id": "f-1",
            "name": "Example Hospital",
            "similarity_score": 0.91,
        }])

    @patch("backend.app.routes.search.similarity_search")
    def test_search_route_delegates_to_service(self, similarity_search):
        similarity_search.return_value = []
        request = SimilaritySearchRequest(
            query="emergency surgery", state="Bihar", limit=5)
        response = search.search_facilities(request)
        self.assertEqual(response["results"], [])
        similarity_search.assert_called_once_with(
            "emergency surgery", state="Bihar", district=None, limit=5)


if __name__ == "__main__":
    unittest.main()

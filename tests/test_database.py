import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from backend.app import database


class DeployedAuthenticationTests(unittest.TestCase):
    @patch("backend.app.database.sql.connect", return_value="connection")
    @patch("backend.app.database.Config")
    def test_sdk_auth_is_adapted_to_sql_connector_contract(self, config_type, connect):
        header_factory = Mock(return_value={"Authorization": "Bearer test"})
        config_type.return_value.host = "https://workspace.example.com"
        config_type.return_value.authenticate = header_factory

        deployed_settings = SimpleNamespace(local_profile=None, warehouse_id="warehouse")
        with patch("backend.app.database.settings", deployed_settings):
            result = database.connection()

        self.assertEqual(result, "connection")
        provider = connect.call_args.kwargs["credentials_provider"]
        self.assertIs(provider(), header_factory)
        self.assertEqual(provider()(), {"Authorization": "Bearer test"})


if __name__ == "__main__":
    unittest.main()

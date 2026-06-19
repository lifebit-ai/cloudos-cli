"""Pytest for CostViewer utility methods"""
import pytest
from cloudos_cli.cost.cost import CostViewer

APIKEY = 'test_api_key_12345'
CLOUDOS_URL = 'http://cloudos.lifebit.ai'


class TestCostViewer:
    """Test class for CostViewer utility functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.cost_viewer = CostViewer(CLOUDOS_URL, APIKEY)

    def test_calculate_runtime(self):
        """Test runtime calculation between timestamps"""
        start_time = "2025-09-01T15:23:59.246Z"
        end_time = "2025-09-01T15:26:15.291Z"

        runtime = self.cost_viewer._calculate_runtime(start_time, end_time)
        assert runtime == "2m 16s"

        # Test with hours
        start_time_long = "2025-09-01T13:23:59.246Z"
        end_time_long = "2025-09-01T15:26:15.291Z"

        runtime_long = self.cost_viewer._calculate_runtime(start_time_long, end_time_long)
        assert runtime_long == "2h 2m 16s"

        # Test with invalid timestamp
        runtime_invalid = self.cost_viewer._calculate_runtime("invalid", "invalid")
        assert runtime_invalid == "N/A"

    def test_format_storage(self):
        """Test storage formatting"""
        # Test normal storage info
        storage_info = {"usageQuantity": 600, "usageUnit": "Gb"}
        formatted = self.cost_viewer._format_storage(storage_info)
        assert formatted == "600 Gb"

        # Test empty storage info
        formatted_empty = self.cost_viewer._format_storage({})
        assert formatted_empty == "N/A"

        # Test None storage info
        formatted_none = self.cost_viewer._format_storage(None)
        assert formatted_none == "N/A"

    def test_format_price(self):
        """Test price formatting"""
        # Test normal price info
        price_info = {"amount": 0.1, "currencyCode": "USD"}
        formatted = self.cost_viewer._format_price(price_info)
        assert formatted == "$0.1000/hr"

        # Test total price
        formatted_total = self.cost_viewer._format_price(price_info, total=True)
        assert formatted_total == "$0.1000"

        # Test empty price info
        formatted_empty = self.cost_viewer._format_price({})
        assert formatted_empty == "N/A"

        # Test None price info
        formatted_none = self.cost_viewer._format_price(None)
        assert formatted_none == "N/A"

    def test_format_lifecycle_type(self):
        """Test lifecycle type formatting"""
        # Test cost saving (spot)
        formatted_spot = self.cost_viewer._format_lifecycle_type(True)
        assert formatted_spot == "spot"

        # Test on demand
        formatted_on_demand = self.cost_viewer._format_lifecycle_type(False)
        assert formatted_on_demand == "on demand"

    def test_get_job_costs_not_available(self):
        """Test that get_job_costs is no longer available (endpoint removed)."""
        assert not hasattr(self.cost_viewer, 'get_job_costs'), (
            "get_job_costs should have been removed as the API endpoint "
            "GET /api/v1/jobs/{job_id}/costs/compute was removed"
        )

    def test_display_costs_not_available(self):
        """Test that display_costs is no longer available (endpoint removed)."""
        assert not hasattr(self.cost_viewer, 'display_costs'), (
            "display_costs should have been removed as the underlying "
            "GET /api/v1/jobs/{job_id}/costs/compute API endpoint was removed"
        )

"""Tests for the cost endpoint rename from /costs/compute to /costs/computation"""
import mock
import pytest
import requests
import responses
from cloudos_cli.cost.cost import CostViewer
from tests.functions_for_pytest import load_json_file

INPUT = "tests/test_data/get_job_costs.json"
APIKEY = 'test_api_key_12345'
CLOUDOS_URL = 'http://cloudos.lifebit.ai'
JOB_ID = "616ee9681b866a01d69fa1cd"
WORKSPACE_ID = "test_workspace_123"


class TestCostEndpointRename:
    """Test class verifying the cost endpoint uses the renamed /costs/computation path."""

    def setup_method(self):
        """Set up test fixtures"""
        self.cost_viewer = CostViewer(CLOUDOS_URL, APIKEY)

    @mock.patch('cloudos_cli.cost.cost', mock.MagicMock())
    @responses.activate
    def test_cost_endpoint_uses_computation_path(self):
        """
        Verify that get_job_costs hits /api/v1/jobs/{job_id}/costs/computation
        (not the old /costs/compute path).
        """
        create_json = load_json_file(INPUT)
        header = {
            "Content-type": "application/json",
            "apikey": APIKEY
        }
        # Mock the NEW endpoint path
        responses.add(
            responses.GET,
            url=f"{CLOUDOS_URL}/api/v1/jobs/{JOB_ID}/costs/computation",
            body=create_json,
            headers=header,
            status=200
        )

        # Call should succeed with the new endpoint
        response = self.cost_viewer.get_job_costs(JOB_ID, WORKSPACE_ID)

        # Verify the response structure
        assert isinstance(response, dict)
        assert "master" in response
        assert "workers" in response
        assert "paginationMetadata" in response

        # Verify the request was made to the correct URL
        assert len(responses.calls) == 1
        assert "/costs/computation" in responses.calls[0].request.url
        assert "/costs/compute" not in responses.calls[0].request.url

    @mock.patch('cloudos_cli.cost.cost', mock.MagicMock())
    @responses.activate
    def test_old_compute_endpoint_not_called(self):
        """
        Verify that the old /costs/compute path is no longer used.
        Only register the old endpoint — the call should raise a ConnectionError
        because the new /costs/computation path is not registered.
        """
        create_json = load_json_file(INPUT)
        header = {
            "Content-type": "application/json",
            "apikey": APIKEY
        }
        # Only mock the OLD endpoint path
        responses.add(
            responses.GET,
            url=f"{CLOUDOS_URL}/api/v1/jobs/{JOB_ID}/costs/compute",
            body=create_json,
            headers=header,
            status=200
        )

        # The call should fail because the code now uses /costs/computation
        with pytest.raises(requests.exceptions.ConnectionError):
            self.cost_viewer.get_job_costs(JOB_ID, WORKSPACE_ID)

    @mock.patch('cloudos_cli.cost.cost', mock.MagicMock())
    @responses.activate
    def test_cost_endpoint_passes_pagination_params(self):
        """
        Verify that custom pagination parameters are passed correctly
        to the renamed /costs/computation endpoint.
        """
        create_json = load_json_file(INPUT)
        header = {
            "Content-type": "application/json",
            "apikey": APIKEY
        }
        responses.add(
            responses.GET,
            url=f"{CLOUDOS_URL}/api/v1/jobs/{JOB_ID}/costs/computation",
            body=create_json,
            headers=header,
            status=200
        )

        response = self.cost_viewer.get_job_costs(JOB_ID, WORKSPACE_ID, page=2, limit=50)

        assert isinstance(response, dict)
        # Verify pagination params in the request URL
        request_url = responses.calls[0].request.url
        assert "page=2" in request_url
        assert "limit=50" in request_url

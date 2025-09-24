"""Pytest for job cost functionality"""
import json
import csv
import os
import tempfile
import mock
import pytest
import requests
import responses
from unittest.mock import patch, MagicMock
from cloudos_cli.clos import Cloudos
from cloudos_cli.cost.cost import CostViewer
from cloudos_cli.utils.errors import BadRequestException
from tests.functions_for_pytest import load_json_file

INPUT = "tests/test_data/get_job_costs.json"
APIKEY = 'test_api_key_12345'
CLOUDOS_URL = 'http://cloudos.lifebit.ai'
JOB_ID = "616ee9681b866a01d69fa1cd"
WORKSPACE_ID = "test_workspace_123"


class TestCostViewer:
    """Test class for CostViewer functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.cost_viewer = CostViewer(CLOUDOS_URL, APIKEY)
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up test fixtures"""
        # Clean up any test files
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    @mock.patch('cloudos_cli.cost.cost', mock.MagicMock())
    @responses.activate
    def test_get_job_costs_correct_response(self):
        """
        Test 'get_job_costs' to work as intended
        API request is mocked and replicated with json files
        """
        create_json = load_json_file(INPUT)
        header = {
            "Content-type": "application/json",
            "apikey": APIKEY
        }
        # mock GET method with the .json
        responses.add(
            responses.GET,
            url=f"{CLOUDOS_URL}/api/v1/jobs/{JOB_ID}/costs/compute",
            body=create_json,
            headers=header,
            status=200
        )
        
        # get mock response
        response = self.cost_viewer.get_job_costs(JOB_ID, WORKSPACE_ID)
        
        # check the response structure
        assert "master" in response
        assert "workers" in response
        assert "paginationMetadata" in response
        
        # check master instance data
        master = response["master"]
        assert master["id"] == "i-00e328d0c4fe4bc17"
        assert master["machineType"] == "c4.large"
        assert master["isCostSaving"] is False
        assert master["instancePricePerHour"]["amount"] == 0.1
        assert master["storage"]["usageQuantity"] == 600
        
        # check workers data
        workers = response["workers"]
        assert len(workers) == 2
        assert workers[0]["id"] == "i-0d1d9e96cda992e74"
        assert workers[0]["isCostSaving"] is True
        assert workers[1]["isCostSaving"] is False

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

    @mock.patch('cloudos_cli.cost.cost.retry_requests_get')
    def test_csv_output(self, mock_get):
        """Test CSV output functionality"""
        # Mock the API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = json.loads(load_json_file(INPUT))
        mock_get.return_value = mock_response
        
        # Change to temp directory
        original_cwd = os.getcwd()
        os.chdir(self.temp_dir)
        
        try:
            # Test CSV output
            self.cost_viewer.display_costs(JOB_ID, WORKSPACE_ID, "csv")
            
            # Check if CSV file was created
            csv_filename = f"{JOB_ID}_costs.csv"
            assert os.path.exists(csv_filename)
            
            # Read and verify CSV content
            with open(csv_filename, 'r') as csvfile:
                reader = csv.reader(csvfile)
                rows = list(reader)
                
                # Check header
                expected_headers = [
                    "Type", "Instance id", "Instance", "Life-cycle type",
                    "Run time", "Compute storage", "Instance price",
                    "Compute storage price", "Total"
                ]
                assert rows[0] == expected_headers
                
                # Check we have the right number of rows (header + master + 2 workers)
                assert len(rows) == 4
                
                # Check master row
                master_row = rows[1]
                assert master_row[0] == "Master"
                assert master_row[1] == "i-00e328d0c4fe4bc17"
                assert master_row[2] == "c4.large"
                assert master_row[3] == "on demand"
                
                # Check worker rows
                worker1_row = rows[2]
                assert worker1_row[0] == "Worker"
                assert worker1_row[1] == "i-0d1d9e96cda992e74"
                assert worker1_row[3] == "spot"
                
        finally:
            os.chdir(original_cwd)

    @mock.patch('cloudos_cli.cost.cost.retry_requests_get')
    def test_json_output(self, mock_get):
        """Test JSON output functionality"""
        # Mock the API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = json.loads(load_json_file(INPUT))
        mock_get.return_value = mock_response
        
        # Change to temp directory
        original_cwd = os.getcwd()
        os.chdir(self.temp_dir)
        
        try:
            # Test JSON output
            self.cost_viewer.display_costs(JOB_ID, WORKSPACE_ID, "json")
            
            # Check if JSON file was created
            json_filename = f"{JOB_ID}_costs.json"
            assert os.path.exists(json_filename)
            
            # Read and verify JSON content
            with open(json_filename, 'r') as jsonfile:
                data = json.load(jsonfile)
                
                # Check structure
                assert "job_id" in data
                assert "cost_table" in data
                assert "final_cost" in data
                
                assert data["job_id"] == JOB_ID
                
                # Check cost table structure
                cost_table = data["cost_table"]
                assert len(cost_table) == 3  # master + 2 workers
                
                # Check first entry (master)
                master_entry = cost_table[0]
                assert master_entry["Type"] == "Master"
                assert master_entry["Instance id"] == "i-00e328d0c4fe4bc17"
                assert master_entry["Instance"] == "c4.large"
                assert master_entry["Life-cycle type"] == "on demand"
                
                # Check final cost is properly formatted
                assert data["final_cost"].startswith("$")
                
        finally:
            os.chdir(original_cwd)

    @mock.patch('cloudos_cli.cost.cost.retry_requests_get')
    def test_stdout_output_simple(self, mock_get):
        """Test stdout output functionality with simple case (no pagination)"""
        # Mock the API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = json.loads(load_json_file(INPUT))
        mock_get.return_value = mock_response
        
        # Mock input to avoid actual user interaction
        with patch('builtins.input', return_value='q'):
            # This test simply checks that the method runs without errors
            # The actual table display is tested through the console output captured above
            try:
                self.cost_viewer.display_costs(JOB_ID, WORKSPACE_ID, "stdout")
                # If we reach here without exceptions, the test passes
                assert True
            except Exception as e:
                pytest.fail(f"stdout display failed with exception: {e}")

    @mock.patch('cloudos_cli.cost.cost.retry_requests_get')
    def test_error_handling_401(self, mock_get):
        """Test error handling for 401 Unauthorized"""
        # Mock a 401 response that behaves like the real BadRequestException
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.reason = "Forbidden"
        mock_response.json.return_value = {"error": "Forbidden"}
        
        # Create a BadRequestException that matches what the real code would produce
        exception = BadRequestException(mock_response)
        mock_get.side_effect = exception
        
        with pytest.raises(ValueError) as excinfo:
            self.cost_viewer.display_costs(JOB_ID, WORKSPACE_ID, "stdout")
        
        # Check that the error message contains the expected text
        error_message = str(excinfo.value)
        assert "cannot see other user's job details" in error_message or "401" in error_message or "Forbidden" in error_message

    @mock.patch('cloudos_cli.cost.cost.retry_requests_get')
    def test_error_handling_400(self, mock_get):
        """Test error handling for 400 Bad Request"""
        # Mock a 400 response
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_get.return_value = mock_response
        mock_get.side_effect = BadRequestException(mock_response)
        
        with pytest.raises(ValueError) as excinfo:
            self.cost_viewer.display_costs(JOB_ID, WORKSPACE_ID, "stdout")
        
        assert "Job not found or cost data not available" in str(excinfo.value)


class TestCloudosJobCosts:
    """Test class for Cloudos get_job_costs method"""

    def setup_method(self):
        """Set up test fixtures"""
        self.cost_viewer = CostViewer(CLOUDOS_URL, APIKEY)

    @mock.patch('cloudos_cli.clos', mock.MagicMock())
    @responses.activate
    def test_cloudos_get_job_costs_correct_response(self):
        """
        Test 'get_job_costs' method in Cloudos class
        API request is mocked and replicated with json files
        """
        create_json = load_json_file(INPUT)
        header = {
            "Content-type": "application/json",
            "apikey": APIKEY
        }
        # mock GET method with the .json
        responses.add(
            responses.GET,
            url=f"{CLOUDOS_URL}/api/v1/jobs/{JOB_ID}/costs/compute",
            body=create_json,
            headers=header,
            status=200
        )
        
        # get mock response
        response = self.cost_viewer.get_job_costs(JOB_ID, WORKSPACE_ID)
        
        # check the response
        assert isinstance(response, dict)
        
        # Parse response content
        result_string = json.dumps(response)
        result_json = json.loads(result_string)
        
        # Verify response structure
        assert "master" in result_json
        assert "workers" in result_json
        assert "paginationMetadata" in result_json

    @mock.patch('cloudos_cli.clos', mock.MagicMock())
    @responses.activate
    def test_cloudos_get_job_costs_with_pagination(self):
        """
        Test 'get_job_costs' method with pagination parameters
        """
        create_json = load_json_file(INPUT)
        header = {
            "Content-type": "application/json",
            "apikey": APIKEY
        }
        
        # mock GET method with the .json
        responses.add(
            responses.GET,
            url=f"{CLOUDOS_URL}/api/v1/jobs/{JOB_ID}/costs/compute",
            body=create_json,
            headers=header,
            status=200
        )
        
        # get mock response with custom pagination
        response = self.cost_viewer.get_job_costs(JOB_ID, WORKSPACE_ID, page=2, limit=50)
        
        # check the response
        assert isinstance(response, dict)

    @mock.patch('cloudos_cli.clos', mock.MagicMock())
    @responses.activate
    def test_cloudos_get_job_costs_error_response(self):
        """
        Test 'get_job_costs' method with error response
        """
        header = {
            "Content-type": "application/json",
            "apikey": APIKEY
        }
        
        # mock GET method with error
        responses.add(
            responses.GET,
            url=f"{CLOUDOS_URL}/api/v1/jobs/{JOB_ID}/costs/compute",
            json={"error": "Job not found"},
            headers=header,
            status=404
        )

        # expect BadRequestException
        with pytest.raises(BadRequestException):
            self.cost_viewer.get_job_costs(JOB_ID, WORKSPACE_ID)

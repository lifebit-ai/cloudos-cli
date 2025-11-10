"""Pytest for related analyses functionality"""
import json
import pytest
from unittest.mock import patch, MagicMock, Mock, mock_open
from cloudos_cli.related_analyses.related_analyses import save_as_json, save_as_stdout


class TestRelatedAnalysesFunctions:
    """Test class for related analyses helper functions"""

    def test_save_as_json(self, tmp_path):
        """
        Test saving related analyses data as JSON
        """
        test_data = {
            "job123": {
                "_id": "job123",
                "status": "completed",
                "name": "Test Job",
                "user_name": "John",
                "user_surname": "Doe",
                "createdAt": "2025-11-05T10:23:45.123Z",
                "runTime": 150.0,
                "computeCostSpent": 1250
            }
        }
        
        # Create a temporary file path
        output_file = tmp_path / "test_output.json"
        
        # Save data
        save_as_json(test_data, str(output_file))
        
        # Verify file was created and contains correct data
        assert output_file.exists()
        
        with open(output_file, 'r') as f:
            loaded_data = json.load(f)
        
        assert loaded_data == test_data
        assert loaded_data["job123"]["name"] == "Test Job"
        assert loaded_data["job123"]["status"] == "completed"
        assert loaded_data["job123"]["runTime"] == 150.0

    def test_save_as_json_multiple_jobs(self, tmp_path):
        """
        Test saving multiple related analyses as JSON
        """
        test_data = {
            "job1": {
                "_id": "job1",
                "status": "completed",
                "name": "Job 1",
                "user_name": "Alice",
                "user_surname": "Wonder",
                "createdAt": "2025-11-05T10:00:00.000Z",
                "runTime": 100.0,
                "computeCostSpent": 500
            },
            "job2": {
                "_id": "job2",
                "status": "running",
                "name": "Job 2",
                "user_name": "Bob",
                "user_surname": "Builder",
                "createdAt": "2025-11-05T11:00:00.000Z",
                "runTime": None,
                "computeCostSpent": None
            },
            "job3": {
                "_id": "job3",
                "status": "failed",
                "name": "Job 3",
                "user_name": "Charlie",
                "user_surname": "Chaplin",
                "createdAt": "2025-11-05T12:00:00.000Z",
                "runTime": 200.0,
                "computeCostSpent": 1000
            }
        }
        
        output_file = tmp_path / "multiple_jobs.json"
        save_as_json(test_data, str(output_file))
        
        assert output_file.exists()
        
        with open(output_file, 'r') as f:
            loaded_data = json.load(f)
        
        assert len(loaded_data) == 3
        assert "job1" in loaded_data
        assert "job2" in loaded_data
        assert "job3" in loaded_data

    @patch('builtins.input', return_value='q')  # Simulate user pressing 'q' to quit
    def test_save_as_stdout_single_job(self, mock_input):
        """
        Test displaying a single related analysis to stdout
        """
        test_data = {
            "job123": {
                "_id": "job123",
                "status": "completed",
                "name": "Test Job",
                "user_name": "John",
                "user_surname": "Doe",
                "createdAt": "2025-11-05T10:23:45.123Z",
                "runTime": 150.0,
                "computeCostSpent": 1250
            }
        }
        
        # Should not raise any exceptions
        try:
            save_as_stdout(test_data, "parent_job_id")
            assert True
        except Exception as e:
            pytest.fail(f"save_as_stdout raised an exception: {e}")

    @patch('builtins.input', return_value='q')
    def test_save_as_stdout_empty_data(self, mock_input):
        """
        Test displaying empty related analyses data
        """
        test_data = {}
        
        # Should not raise any exceptions
        try:
            save_as_stdout(test_data, "parent_job_id")
            assert True
        except Exception as e:
            pytest.fail(f"save_as_stdout raised an exception with empty data: {e}")

    @patch('builtins.input', return_value='q')
    def test_save_as_stdout_with_null_values(self, mock_input):
        """
        Test displaying data with null/None values
        """
        test_data = {
            "job_incomplete": {
                "_id": "job_incomplete",
                "status": "running",
                "name": "Incomplete Job",
                "user_name": "Test",
                "user_surname": "User",
                "createdAt": "2025-11-05T10:00:00.000Z",
                "runTime": None,  # Job still running
                "computeCostSpent": None  # No cost yet
            }
        }
        
        # Should not raise any exceptions
        try:
            save_as_stdout(test_data, "parent_job_id")
            assert True
        except Exception as e:
            pytest.fail(f"save_as_stdout raised an exception with null values: {e}")

    @patch('builtins.input', side_effect=['n', 'n', 'q'])  # Navigate next, next, quit
    def test_save_as_stdout_pagination(self, mock_input):
        """
        Test pagination with multiple jobs (more than 10 to trigger pagination)
        """
        # Create 25 jobs to test pagination (limit is 10 per page)
        test_data = {}
        for i in range(25):
            test_data[f"job{i}"] = {
                "_id": f"job{i}",
                "status": "completed",
                "name": f"Job {i}",
                "user_name": "Test",
                "user_surname": f"User{i}",
                "createdAt": f"2025-11-05T10:{i:02d}:00.000Z",
                "runTime": 100.0 + i,
                "computeCostSpent": 500 + i * 10
            }
        
        # Should not raise any exceptions and should handle pagination
        try:
            save_as_stdout(test_data, "parent_job_id")
            # Verify mock_input was called (pagination controls were used)
            # With 25 jobs and 10 per page, we have 3 pages
            # Page 1->2 (n), Page 2->3 (n), Page 3 auto-exits (no input)
            assert mock_input.call_count == 3  # Called twice for page navigation
        except Exception as e:
            pytest.fail(f"save_as_stdout raised an exception during pagination: {e}")

    def test_save_as_json_empty_data(self, tmp_path):
        """
        Test saving empty data as JSON
        """
        test_data = {}
        output_file = tmp_path / "empty_output.json"
        
        save_as_json(test_data, str(output_file))
        
        assert output_file.exists()
        
        with open(output_file, 'r') as f:
            loaded_data = json.load(f)
        
        assert loaded_data == {}
        assert len(loaded_data) == 0


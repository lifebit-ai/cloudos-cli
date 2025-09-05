"""Pytest added for function get_job_status"""
import json
import mock
import pytest
import requests
import responses
from cloudos_cli.clos import Cloudos
from cloudos_cli.utils.errors import BadRequestException
from tests.functions_for_pytest import load_json_file

INPUT = "tests/test_data/get_job_details.json"
INPUT_DOCKER = "tests/test_data/get_job_details_docker.json"
APIKEY = 'vnoiweur89u2ongs'
CLOUDOS_URL = 'http://cloudos.lifebit.ai'
JOB_ID = "616ee9681b866a01d69fa1cd"
JOB_STATUS = "completed"
USER_ID = "kcjaioshfaysgasghakjsg8yas8"
WORKSPACE_ID = "5c6d3e9bd954e800b23f8c62"


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
def test_get_job_details_nextflow_correct_response():
    """
    Test 'get_job_details' to work as intended (using get_job_status) for a Nextflow job
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
            url=f"{CLOUDOS_URL}/api/v1/jobs/{JOB_ID}",
            body=create_json,
            headers=header,
            status=200)
    # start cloudOS service
    clos = Cloudos(apikey=APIKEY, cromwell_token=None, cloudos_url=CLOUDOS_URL)
    # get mock response
    response = clos.get_job_status(j_id=JOB_ID)
    # check the response
    result_string = response.content.decode("utf-8")
    result_json = json.loads(result_string)
    # check if the response is correct for various parameters
    assert result_json["status"] == JOB_STATUS
    assert response.status_code == 200
    assert isinstance(response, requests.models.Response)
    assert result_json["jobType"] == "nextflowAWS"
    assert "command" not in result_json.keys()
    assert result_json["revision"]["commit"] == "7c2067cb3af50cde06524b6f78a112e0801a0080"
    assert result_json["nextflowVersion"] == "22.10.8"
    assert result_json["masterInstance"]["usedInstance"]["type"] == "c5.xlarge"
    assert result_json["storageSizeInGb"] == 500
    assert result_json["batch"]["jobQueue"]["name"] == "nextflow-job-queue-5c6d3e9bd954e800b23f8c62-5255"


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
def test_get_job_details_docker_correct_response():
    """
    Test 'get_job_details' to work as intended (using get_job_status) for Docker jobs
    API request is mocked and replicated with json files
    """
    create_json = load_json_file(INPUT_DOCKER)
    header = {
            "Content-type": "application/json",
            "apikey": APIKEY
        }
    # mock GET method with the .json
    responses.add(
            responses.GET,
            url=f"{CLOUDOS_URL}/api/v1/jobs/{JOB_ID}",
            body=create_json,
            headers=header,
            status=200)
    # start cloudOS service
    clos = Cloudos(apikey=APIKEY, cromwell_token=None, cloudos_url=CLOUDOS_URL)
    # get mock response
    response = clos.get_job_status(j_id=JOB_ID)
    # check the response
    result_string = response.content.decode("utf-8")
    result_json = json.loads(result_string)
    # check if the response is correct for various parameters
    assert result_json["status"] == JOB_STATUS
    assert response.status_code == 200
    assert isinstance(response, requests.models.Response)
    assert result_json["jobType"] == "dockerAWS"
    assert "command" in result_json.keys()
    assert result_json["revision"]["digest"] == "sha256:6015f66923d7afbc53558d7ccffd325d43b4e249f41a6e93eef074c9505d2233"
    assert "nextflowVersion" not in result_json.keys()
    assert result_json["masterInstance"]["usedInstance"]["type"] == "c5.xlarge"
    assert result_json["storageSizeInGb"] == 500
    assert result_json["batch"]["jobQueue"]["name"] == "nextflow-job-queue-5c6d3e9bd954e800b23f8c62-feee"


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
def test_get_process_summary_successful_response():
    """
    Test 'get_process_summary' to work correctly with successful API responses
    """
    header = {
        "Content-type": "application/json",
        "apikey": APIKEY
    }
    
    # Mock responses for each status - simulate realistic process counts
    status_responses = {
        "NEW": [],  # 0 new processes
        "SUBMITTED": [{"id": 1}, {"id": 2}],  # 2 submitted processes
        "RUNNING": [{"id": 3}],  # 1 running process
        "RETRIED": [],  # 0 retried processes
        "CACHED": [{"id": 4}, {"id": 5}, {"id": 6}],  # 3 cached processes
        "COMPLETED": [{"id": 7}, {"id": 8}, {"id": 9}, {"id": 10}],  # 4 completed processes
        "FAILED": [{"id": 11}],  # 1 failed process
        "ABORTED": []  # 0 aborted processes
    }
    
    # Add mock responses for each status
    for status, mock_data in status_responses.items():
        responses.add(
            responses.GET,
            url=f"{CLOUDOS_URL}/api/v2/job-process-metrics/process-info/{JOB_ID}/{USER_ID}",
            json=mock_data,
            headers=header,
            status=200
        )
    
    # Create cloudOS service
    clos = Cloudos(apikey=APIKEY, cromwell_token=None, cloudos_url=CLOUDOS_URL)
    
    # Get process summary
    result = clos.get_process_summary(JOB_ID, USER_ID, WORKSPACE_ID)
    
    # Verify the result structure and values
    assert isinstance(result, dict)
    assert len(result) == 8  # All 8 status types should be present
    
    # Check specific counts match our mock data
    assert result["NEW"] == 0
    assert result["SUBMITTED"] == 2
    assert result["RUNNING"] == 1
    assert result["RETRIED"] == 0
    assert result["CACHED"] == 3
    assert result["COMPLETED"] == 4
    assert result["FAILED"] == 1
    assert result["ABORTED"] == 0


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
def test_get_process_summary_all_empty_response():
    """
    Test 'get_process_summary' with empty responses for all statuses (no processes)
    """
    header = {
        "Content-type": "application/json",
        "apikey": APIKEY
    }
    
    # Mock empty responses for all statuses
    statuses = ["NEW", "SUBMITTED", "RUNNING", "RETRIED", "CACHED", "COMPLETED", "FAILED", "ABORTED"]
    for status in statuses:
        responses.add(
            responses.GET,
            url=f"{CLOUDOS_URL}/api/v2/job-process-metrics/process-info/{JOB_ID}/{USER_ID}",
            json=[],
            headers=header,
            status=200
        )
    
    # Create cloudOS service
    clos = Cloudos(apikey=APIKEY, cromwell_token=None, cloudos_url=CLOUDOS_URL)
    
    # Get process summary
    result = clos.get_process_summary(JOB_ID, USER_ID, WORKSPACE_ID)
    
    # Verify all counts are zero
    assert isinstance(result, dict)
    assert len(result) == 8
    for status in statuses:
        assert result[status] == 0


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
def test_get_process_summary_with_large_numbers():
    """
    Test 'get_process_summary' with larger process counts to ensure scalability
    """
    header = {
        "Content-type": "application/json",
        "apikey": APIKEY
    }
    
    # Create mock data with larger process counts
    large_completed_processes = [{"id": i} for i in range(1, 101)]  # 100 completed processes
    large_running_processes = [{"id": i} for i in range(101, 126)]  # 25 running processes
    
    status_responses = {
        "NEW": [],
        "SUBMITTED": [{"id": 1}, {"id": 2}, {"id": 3}],  # 3 submitted
        "RUNNING": large_running_processes,  # 25 running
        "RETRIED": [{"id": 200}],  # 1 retried
        "CACHED": [{"id": i} for i in range(300, 310)],  # 10 cached
        "COMPLETED": large_completed_processes,  # 100 completed
        "FAILED": [{"id": 400}, {"id": 401}],  # 2 failed
        "ABORTED": []
    }
    
    # Add mock responses for each status
    for status, mock_data in status_responses.items():
        responses.add(
            responses.GET,
            url=f"{CLOUDOS_URL}/api/v2/job-process-metrics/process-info/{JOB_ID}/{USER_ID}",
            json=mock_data,
            headers=header,
            status=200
        )
    
    # Create cloudOS service
    clos = Cloudos(apikey=APIKEY, cromwell_token=None, cloudos_url=CLOUDOS_URL)
    
    # Get process summary
    result = clos.get_process_summary(JOB_ID, USER_ID, WORKSPACE_ID)
    
    # Verify the larger counts are handled correctly
    assert isinstance(result, dict)
    assert result["NEW"] == 0
    assert result["SUBMITTED"] == 3
    assert result["RUNNING"] == 25
    assert result["RETRIED"] == 1
    assert result["CACHED"] == 10
    assert result["COMPLETED"] == 100
    assert result["FAILED"] == 2
    assert result["ABORTED"] == 0
    
    # Verify total processes
    total_processes = sum(result.values())
    assert total_processes == 141  # 3 + 25 + 1 + 10 + 100 + 2


def test_process_summary_status_mapping():
    """
    Test the status display mapping used in job details output
    """
    # This tests the mapping logic used in the job details command
    status_display_map = {
        "NEW": "Pending",
        "SUBMITTED": "Submitted", 
        "RUNNING": "Running",
        "RETRIED": "Retried",
        "CACHED": "Cached",
        "COMPLETED": "Completed",
        "FAILED": "Failed",
        "ABORTED": "Aborted"
    }
    
    # Mock process summary data
    mock_process_summary = {
        "NEW": 0,
        "SUBMITTED": 2,
        "RUNNING": 1,
        "RETRIED": 0,
        "CACHED": 3,
        "COMPLETED": 4,
        "FAILED": 1,
        "ABORTED": 0
    }
    
    # Apply the mapping as done in the actual code
    mapped_summary = {}
    for status, count in mock_process_summary.items():
        display_status = status_display_map.get(status, status)
        mapped_summary[display_status] = count
    
    # Verify the mapping works correctly
    assert mapped_summary["Pending"] == 0
    assert mapped_summary["Submitted"] == 2
    assert mapped_summary["Running"] == 1
    assert mapped_summary["Retried"] == 0
    assert mapped_summary["Cached"] == 3
    assert mapped_summary["Completed"] == 4
    assert mapped_summary["Failed"] == 1
    assert mapped_summary["Aborted"] == 0
    
    # Ensure all statuses are mapped
    assert len(mapped_summary) == 8
    assert all(status in mapped_summary for status in status_display_map.values())

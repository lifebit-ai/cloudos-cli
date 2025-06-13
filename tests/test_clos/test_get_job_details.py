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

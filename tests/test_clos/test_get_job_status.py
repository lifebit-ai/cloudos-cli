"""Pytest added for function get_job_status"""
import json
import mock
import pytest
import requests
import responses
from cloudos.clos import Cloudos
from cloudos.utils.errors import BadRequestException
from tests.functions_for_pytest import load_json_file

INPUT = "tests/test_data/get_job_status.json"
APIKEY = 'vnoiweur89u2ongs'
CLOUDOS_URL = 'http://cloudos.lifebit.ai'
JOB_ID = "616ee9681b866a01d69fa1cd"


@mock.patch('cloudos.clos', mock.MagicMock())
@responses.activate
def test_get_job_status_correct_response():
    """
    Test 'get_job_status' to work as intended
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
    print(response.content)
    assert response.status_code == 200
    assert isinstance(response, requests.models.Response)


@mock.patch('cloudos.clos', mock.MagicMock())
@responses.activate
def test_get_job_status_incorrect_response():
    """
    Test 'get_job_status' to fail with '400' response
    """
    # prepare error message
    error_message = {"statusCode": 400, "code": "BadRequest",
                     "message": "Bad Request.", "time": "2022-11-23_17:31:07"}
    error_json = json.dumps(error_message)
    header = {
            "Content-type": "application/json",
            "apikey": APIKEY
        }
    # mock GET method with the .json
    responses.add(
            responses.GET,
            url=f"{CLOUDOS_URL}/api/v1/jobs/{JOB_ID}",
            body=error_json,
            headers=header,
            status=400)
    # raise 400 error
    with pytest.raises(BadRequestException) as error:
        # check if it failed
        clos = Cloudos(apikey=APIKEY, cromwell_token=None, cloudos_url=CLOUDOS_URL)
        clos.get_job_status(JOB_ID)
    assert "Bad Request" in (str(error))

"""Pytest added for function abort_job"""
import json
import mock
import pytest
import requests
import responses
from cloudos_cli.clos import Cloudos
from cloudos_cli.utils.errors import BadRequestException
from tests.functions_for_pytest import load_json_file

APIKEY = 'vnoiweur89u2ongs'
CLOUDOS_URL = 'http://cloudos.lifebit.ai'
WORKSPACE_ID = 'lv89ufc838sdig'
JOB_ID = "616ee9681b866a01d69fa1cd"


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
def test_abort_job_correct_response():
    """
    Test 'abort_job' to work as intended
    API request is mocked and replicated with json files
    """
    header = {
            "Content-type": "application/json",
            "apikey": APIKEY
        }
    # mock GET method with the .json
    responses.add(
            responses.PUT,
            url=f"{CLOUDOS_URL}/api/v2/jobs/{JOB_ID}/abort?forceAbort=false&teamId={WORKSPACE_ID}",
            headers=header,
            status=200)
    # start cloudOS service
    clos = Cloudos(apikey=APIKEY, cromwell_token=None, cloudos_url=CLOUDOS_URL)
    # get mock response
    response = clos.abort_job(JOB_ID, WORKSPACE_ID)
    assert response.status_code == 200
    assert isinstance(response, requests.models.Response)


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
def test_abort_job_incorrect_response():
    """
    Test 'abort_job' to fail with '400' response
    """
    # prepare error message
    error_message = {"statusCode": 400, "code": "BadRequest",
                     "message": "Bad Request.", "time": "2025-04-25_17:31:07"}
    error_json = json.dumps(error_message)
    header = {
            "Content-type": "application/json",
            "apikey": APIKEY
        }
    # mock GET method with the .json
    responses.add(
            responses.PUT,
            url=f"{CLOUDOS_URL}/api/v2/jobs/{JOB_ID}/abort?forceAbort=false&teamId={WORKSPACE_ID}",
            body=error_json,
            headers=header,
            status=400)
    # raise 400 error
    with pytest.raises(BadRequestException) as error:
        # check if it failed
        clos = Cloudos(apikey=APIKEY, cromwell_token=None, cloudos_url=CLOUDOS_URL)
        clos.abort_job(JOB_ID, WORKSPACE_ID)
    assert "Bad Request" in (str(error))


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
def test_abort_job_with_force_correct_response():
    """
    Test 'abort_job' with force=True to work as intended
    API request is mocked and replicated with json files
    """
    header = {
            "Content-type": "application/json",
            "apikey": APIKEY
        }
    # mock PUT method with the .json
    responses.add(
            responses.PUT,
            url=f"{CLOUDOS_URL}/api/v2/jobs/{JOB_ID}/abort?forceAbort=true&teamId={WORKSPACE_ID}",
            headers=header,
            status=200)
    # start cloudOS service
    clos = Cloudos(apikey=APIKEY, cromwell_token=None, cloudos_url=CLOUDOS_URL)
    # get mock response
    response = clos.abort_job(JOB_ID, WORKSPACE_ID, force=True)
    assert response.status_code == 200
    assert isinstance(response, requests.models.Response)


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
def test_abort_job_with_force_incorrect_response():
    """
    Test 'abort_job' with force=True to fail with '400' response
    """
    # prepare error message
    error_message = {"statusCode": 400, "code": "BadRequest",
                     "message": "Job is already completed!", "time": "2025-04-25_17:31:07"}
    error_json = json.dumps(error_message)
    header = {
            "Content-type": "application/json",
            "apikey": APIKEY
        }
    # mock PUT method with the .json
    responses.add(
            responses.PUT,
            url=f"{CLOUDOS_URL}/api/v2/jobs/{JOB_ID}/abort?forceAbort=true&teamId={WORKSPACE_ID}",
            body=error_json,
            headers=header,
            status=400)
    # raise 400 error
    with pytest.raises(BadRequestException) as error:
        # check if it failed
        clos = Cloudos(apikey=APIKEY, cromwell_token=None, cloudos_url=CLOUDOS_URL)
        clos.abort_job(JOB_ID, WORKSPACE_ID, force=True)
    assert "Job is already completed" in (str(error))


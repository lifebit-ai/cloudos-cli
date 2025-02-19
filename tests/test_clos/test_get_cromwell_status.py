"""Pytests for function Cloudos.get_cromwell_status"""
import json
import mock
import pytest
import requests
import responses
from responses import matchers
from cloudos_cli.clos import Cloudos
from cloudos_cli.utils.errors import BadRequestException
from tests.functions_for_pytest import load_json_file

INPUT = "tests/test_data/process_job_list_initial_json.json"
APIKEY = 'vnoiweur89u2ongs'
CLOUDOS_URL = 'http://cloudos.lifebit.ai'
WORKSPACE_ID = 'lv89ufc838sdig'


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
def test_get_cromwell_status_correct_response():
    """
    Test 'get_cromwell_status' to work as intended
    API request is mocked and replicated with json files
    """
    create_json = load_json_file(INPUT)
    params = {"teamId": WORKSPACE_ID}
    header = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json;charset=UTF-8"
    }
    search_str = f"teamId={WORKSPACE_ID}"
    # mock GET method with the .json
    responses.add(
            responses.GET,
            url=f"{CLOUDOS_URL}/api/v1/cromwell?{search_str}",
            body=create_json,
            headers=header,
            match=[matchers.query_param_matcher(params)],
            status=200)
    # start cloudOS service
    clos = Cloudos(apikey=None, cromwell_token=APIKEY, cloudos_url=CLOUDOS_URL)
    # get mock response
    response = clos.get_cromwell_status(WORKSPACE_ID)
    # check the response
    assert response.status_code == 200
    assert isinstance(response, requests.models.Response)


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
def test_get_cromwell_incorrect_response():
    """
    Test 'get_cromwell_status' to fail with '400' response
    """
    # prepare error message
    error_message = {"statusCode": 400, "time": "2022-11-23_17:31:07"}
    error_json = json.dumps(error_message)
    params = {"teamId": WORKSPACE_ID}
    header = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json;charset=UTF-8"
    }
    search_str = f"teamId={WORKSPACE_ID}"
    # mock GET method with the .json
    responses.add(
            responses.GET,
            url=f"{CLOUDOS_URL}/api/v1/cromwell?{search_str}",
            body=error_json,
            headers=header,
            match=[matchers.query_param_matcher(params)],
            status=400)
    # raise 400 error
    with pytest.raises(BadRequestException) as error:
        # check if it failed
        clos = Cloudos(apikey=APIKEY, cromwell_token=None, cloudos_url=CLOUDOS_URL)
        clos.get_cromwell_status(WORKSPACE_ID)
    assert "Server returned status 400." in (str(error))

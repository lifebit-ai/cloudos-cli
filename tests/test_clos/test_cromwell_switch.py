"""Pytests for function Cloudos.cromwell_switch"""
import json
import mock
import pytest
import requests
import responses
from responses import matchers
from cloudos_cli.clos import Cloudos
from cloudos_cli.utils.errors import BadRequestException

APIKEY = 'vnoiweur89u2ongs'
CLOUDOS_URL = 'http://cloudos.lifebit.ai'
WORKSPACE_ID = 'lv89ufc838sdig'
CROMWELL_ACTION = "stop"


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
def test_cromwell_switch():
    """
    Test 'get_cromwell_switch' to work as intended
    API request is mocked and replicated with json files
    """
    create_json = json.dumps({"mock": "response"})
    params = {"teamId": WORKSPACE_ID}
    header = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json;charset=UTF-8"
    }
    search_str = f"{CROMWELL_ACTION}?teamId={WORKSPACE_ID}"
    # mock GET method with the .json
    responses.add(
            responses.PUT,
            url=f"{CLOUDOS_URL}/api/v1/cromwell/{search_str}",
            body=create_json,
            headers=header,
            match=[matchers.query_param_matcher(params)],
            status=200)
    # start cloudOS service
    clos = Cloudos(apikey=None, cromwell_token=APIKEY, cloudos_url=CLOUDOS_URL)
    # get mock response
    response = clos.cromwell_switch(WORKSPACE_ID, CROMWELL_ACTION)
    # check the response
    assert response.status_code == 200
    assert isinstance(response, requests.models.Response)


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
def test_cromwell_switch_incorrect_response():
    """
    Test 'cromwell_switch' to fail with '400' response
    """
    # prepare error message
    error_message = {"statusCode": 400, "code": "BadRequest",
                     "message": "Bad Request.", "time": "2022-11-23_17:31:07"}
    error_json = json.dumps(error_message)
    params = {"teamId": WORKSPACE_ID}
    header = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json;charset=UTF-8"
    }
    search_str = f"{CROMWELL_ACTION}?teamId={WORKSPACE_ID}"
    # mock GET method with the .json
    responses.add(
            responses.PUT,
            url=f"{CLOUDOS_URL}/api/v1/cromwell/{search_str}",
            body=error_json,
            headers=header,
            match=[matchers.query_param_matcher(params)],
            status=400)
    # raise 400 error
    with pytest.raises(BadRequestException) as error:
        # check if it failed
        clos = Cloudos(apikey=None, cromwell_token=APIKEY, cloudos_url=CLOUDOS_URL)
        clos.cromwell_switch(WORKSPACE_ID, CROMWELL_ACTION)
    assert "Bad Request" in (str(error))

import mock
import json
import pytest
import requests
import responses
from responses import matchers
from cloudos_cli.clos import Cloudos
from cloudos_cli.utils.errors import BadRequestException
from tests.functions_for_pytest import load_json_file

INPUT = "tests/test_data/projects.json"
APIKEY = 'vnoiweur89u2ongs'
CLOUDOS_URL = 'http://cloudos.lifebit.ai'
WORKSPACE_ID = 'lv89ufc838sdig'
PAGE_SIZE = 10
PAGE = 1

@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
def test_get_project_list_correct_response():
    """
    Test 'get_project_list' to work as intended
    """
    create_json = load_json_file(INPUT)
    params = {"teamId": WORKSPACE_ID, "pageSize": PAGE_SIZE, "page": PAGE}
    header = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json;charset=UTF-8",
        "apikey": APIKEY
    }
    search_str = f"teamId={WORKSPACE_ID}&pageSize={PAGE_SIZE}&page={PAGE}"
    # mock GET method with the .json
    responses.add(
            responses.GET,
            url=f"{CLOUDOS_URL}/api/v2/projects?{search_str}",
            body=create_json,
            headers=header,
            match=[matchers.query_param_matcher(params)],
            status=200)
    # start cloudOS service
    clos = Cloudos(apikey=APIKEY, cromwell_token=None, cloudos_url=CLOUDOS_URL)
    # get mock response
    response = clos.get_project_list(WORKSPACE_ID, page_size=PAGE_SIZE, page=PAGE)
    # check the response
    assert isinstance(response, list)
    assert len(response) == 1


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
def test_get_project_list_incorrect_response():
    """
    Test 'get_project_list' to fail with '400' response
    """
    # prepare error message
    error_message = {"statusCode": 400, "code": "BadRequest",
                     "message": "Bad Request.", "time": "2022-11-23_17:31:07"}
    error_json = json.dumps(error_message)
    params = {"teamId": WORKSPACE_ID, "pageSize": PAGE_SIZE, "page": PAGE}
    header = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json;charset=UTF-8",
        "apikey": APIKEY
    }
    search_str = f"teamId={WORKSPACE_ID}&pageSize={PAGE_SIZE}&page={PAGE}"
    # mock GET method with the .json
    responses.add(
            responses.GET,
            url=f"{CLOUDOS_URL}/api/v2/projects?{search_str}",
            body=error_json,
            headers=header,
            match=[matchers.query_param_matcher(params)],
            status=400)
    # raise 400 error
    with pytest.raises(BadRequestException) as error:
        # check if it failed
        clos = Cloudos(apikey=APIKEY, cromwell_token=None, cloudos_url=CLOUDOS_URL)
        clos.get_project_list(WORKSPACE_ID)
    assert "Server returned status 400." in (str(error))

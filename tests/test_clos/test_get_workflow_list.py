import mock
import json
import pytest
import responses
from responses import matchers
from cloudos_cli.clos import Cloudos
from cloudos_cli.utils.errors import BadRequestException
from tests.functions_for_pytest import load_json_file

INPUT = "tests/test_data/workflows/workflows.json"
APIKEY = 'vnoiweur89u2ongs'
CLOUDOS_URL = 'http://cloudos.lifebit.ai'
WORKSPACE_ID = 'lv89ufc838sdig'
PAGE_SIZE = 10
PAGE = 1
ARCHIVED_STATUS = "false"


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
def test_get_workflow_list_correct_response():
    """
    Test 'get_workflow_list' to work as intended
    API request is mocked and replicated with json files
    """
    create_json = load_json_file(INPUT)
    params = {"teamId": WORKSPACE_ID,
              "pageSize": PAGE_SIZE,
              "page": PAGE,
              "archived.status": ARCHIVED_STATUS}
    header = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json;charset=UTF-8",
        "apikey": APIKEY
    }
    search_str = f"teamId={WORKSPACE_ID}&pageSize={PAGE_SIZE}&page={PAGE}&archived.status={ARCHIVED_STATUS}"
    # mock GET method with the .json
    responses.add(
            responses.GET,
            url=f"{CLOUDOS_URL}/api/v3/workflows?{search_str}",
            body=create_json,
            headers=header,
            match=[matchers.query_param_matcher(params)],
            status=200)
    # start cloudOS service
    clos = Cloudos(apikey=APIKEY, cromwell_token=None, cloudos_url=CLOUDOS_URL)
    # get mock response
    response = clos.get_workflow_list(WORKSPACE_ID)
    # check the response
    assert isinstance(response, list)
    assert len(response) == 1


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
def test_get_workflow_list_incorrect_response():
    """
    Test 'get_workflow_list' to fail with '400' response
    """
    # prepare error message
    error_message = {"statusCode": 400, "code": "BadRequest",
                     "message": "Bad Request.", "time": "2022-11-23_17:31:07"}
    error_json = json.dumps(error_message)
    params = {"teamId": WORKSPACE_ID,
              "pageSize": PAGE_SIZE,
              "page": PAGE,
              "archived.status": ARCHIVED_STATUS}
    header = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json;charset=UTF-8",
        "apikey": APIKEY
    }
    search_str = f"teamId={WORKSPACE_ID}&pageSize={PAGE_SIZE}&page={PAGE}&archived.status={ARCHIVED_STATUS}"
    # mock GET method with the .json
    responses.add(
            responses.GET,
            url=f"{CLOUDOS_URL}/api/v3/workflows?{search_str}",
            body=error_json,
            headers=header,
            match=[matchers.query_param_matcher(params)],
            status=400)
    # raise 400 error
    with pytest.raises(BadRequestException) as error:
        # check if it failed
        clos = Cloudos(apikey=APIKEY, cromwell_token=None, cloudos_url=CLOUDOS_URL)
        clos.get_workflow_list(WORKSPACE_ID)
    assert "Server returned status 400." in (str(error))

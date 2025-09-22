import mock
import json
import pytest
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
def test_get_job_list_correct_response():
    """
    Test 'get_job_list' to work as intended
    API request is mocked and replicated with json files
    """
    create_json = load_json_file(INPUT)
    params = {"teamId": WORKSPACE_ID, "archived.status": "false", "limit": 1, "page": 1}
    header = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json;charset=UTF-8",
        "apikey": APIKEY
    }
    search_str = f"teamId={WORKSPACE_ID}&archived.status=false&limit=1&page=1"
    # mock GET method with the .json
    responses.add(
            responses.GET,
            url=f"{CLOUDOS_URL}/api/v2/jobs?{search_str}",
            body=create_json,
            headers=header,
            match=[matchers.query_param_matcher(params)],
            status=200)
    # start cloudOS service
    clos = Cloudos(apikey=APIKEY, cromwell_token=None, cloudos_url=CLOUDOS_URL)
    # get mock response
    response = clos.get_job_list(WORKSPACE_ID, last_n_jobs=1, page=1, page_size=10)
    # check the response
    assert isinstance(response, list)


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
def test_get_job_list_incorrect_response():
    """
    Test 'get_job_list' to fail with '400' response
    """
    # prepare error message
    error_message = {"statusCode": 400, "code": "BadRequest",
                     "message": "Bad Request.", "time": "2022-11-23_17:31:07"}
    error_json = json.dumps(error_message)
    params = {"teamId": WORKSPACE_ID, "archived.status": "false", "limit": 10, "page": 1}
    header = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json;charset=UTF-8",
        "apikey": APIKEY
    }
    search_str = f"teamId={WORKSPACE_ID}&archived.status=false&limit=10&page=1"
    # mock GET method with the .json
    responses.add(
            responses.GET,
            url=f"{CLOUDOS_URL}/api/v2/jobs?{search_str}",
            body=error_json,
            headers=header,
            match=[matchers.query_param_matcher(params)],
            status=400)
    # raise 400 error
    with pytest.raises(BadRequestException) as error:
        # check if it failed
        clos = Cloudos(apikey=APIKEY, cromwell_token=None, cloudos_url=CLOUDOS_URL)
        clos.get_job_list(WORKSPACE_ID, page=1, page_size=10)
    assert "Bad Request" in (str(error))

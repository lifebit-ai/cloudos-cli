import mock
import json
import pytest
import responses
from responses import matchers
from cloudos.clos import Cloudos
from cloudos.utils.errors import BadRequestException
from tests.functions_for_pytest import load_json_file

OUTPUT = "tests/test_data/workflows/curated_workflows.json"
APIKEY = 'vnoiweur89u2ongs'
CLOUDOS_URL = 'http://cloudos.lifebit.ai'
WORKSPACE_ID = 'lv89ufc838sdig'
PAGE = 1


@mock.patch('cloudos.clos', mock.MagicMock())
@responses.activate
def test_get_curated_workflow_list_correct_response():
    """
    Test 'get_curated_workflow_list' to work as intended
    API request is mocked and replicated with json files
    """
    create_json = load_json_file(OUTPUT)
    params = {"teamId": WORKSPACE_ID,
              "groups[]": "curated",
              "page": PAGE}
    header = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json;charset=UTF-8",
        "apikey": APIKEY}
    search_str = f"search=&groups[]=curated&page={PAGE}&teamId={WORKSPACE_ID}"
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
    response = clos.get_curated_workflow_list(WORKSPACE_ID)
    # check the response
    assert isinstance(response, list)
    assert len(response) == 1


@mock.patch('cloudos.clos', mock.MagicMock())
@responses.activate
def test_get_curated_workflow_list_incorrect_response():
    """
    Test 'get_curated_workflow_list' to fail with '400' response
    """
    # prepare error message
    error_message = {"statusCode": 400, "code": "BadRequest",
                     "message": "Bad Request.", "time": "2022-11-23_17:31:07"}
    error_json = json.dumps(error_message)
    search_str = f"search=&groups[]=curated&page={PAGE}&teamId={WORKSPACE_ID}"
    # mock GET method with the .json
    responses.add(
            responses.GET,
            url=f"{CLOUDOS_URL}/api/v3/workflows?{search_str}",
            body=error_json,
            status=400)
    # raise 400 error
    with pytest.raises(BadRequestException) as error:
        # check if it failed
        clos = Cloudos(apikey=APIKEY, cromwell_token=None, cloudos_url=CLOUDOS_URL)
        clos.get_curated_workflow_list(WORKSPACE_ID)
    assert "Server returned status 400." in (str(error))

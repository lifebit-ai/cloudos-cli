"""pytest added for function BadRequestException"""
import mock
import responses
import pytest
from responses import matchers
from cloudos.clos import Cloudos
from cloudos.utils.errors import BadRequestException
from tests.functions_for_pytest import load_json_file

INPUT = "tests/test_data/process_job_list_initial_json.json"
APIKEY = 'vnoiweur89u2ongs'
CLOUDOS_URL = 'http://cloudos.lifebit.ai'
WORKSPACE_ID = 'lv89ufc838sdig'
STATUS_CODE = 400


@mock.patch('cloudos.clos', mock.MagicMock())
@responses.activate
def test_bad_request_exception():
    """
    Test 'get_job_list' to work as intended
    API request is mocked and replicated with json files
    """
    create_json = load_json_file(INPUT)
    params = {"teamId": WORKSPACE_ID, "page": 1}
    header = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json;charset=UTF-8",
        "apikey": APIKEY
    }
    search_str = f"teamId={WORKSPACE_ID}&page=1"
    # mock GET method with the .json
    responses.add(
            responses.GET,
            url=f"{CLOUDOS_URL}/api/v1/jobs?{search_str}",
            body=create_json,
            headers=header,
            match=[matchers.query_param_matcher(params)],
            status=STATUS_CODE)
    # start cloudOS service
    with pytest.raises(BadRequestException) as error:
        clos = Cloudos(apikey=APIKEY, cromwell_token=None, cloudos_url=CLOUDOS_URL)
        clos.get_job_list(workspace_id=WORKSPACE_ID)

    assert "Server returned status 400." in (str(error))

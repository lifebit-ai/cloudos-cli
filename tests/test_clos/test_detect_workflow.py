"""Pytest for method Cloudos.detect_workflow"""
import mock
import responses
from responses import matchers
from cloudos_cli.clos import Cloudos
from tests.functions_for_pytest import load_json_file

INPUT = "tests/test_data/process_workflow_list_initial_request.json"
APIKEY = 'vnoiweur89u2ongs'
CLOUDOS_URL = 'http://cloudos.lifebit.ai'
WORKSPACE_ID = 'lv89ufc838sdig'
PAGE_SIZE = 10
PAGE = 1
ARCHIVED_STATUS = "false"


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
def test_detect_workflow():
    """
    Test 'get_workflow_list' to work as intended
    API request is mocked and replicated with json files
    """
    json_data = load_json_file(INPUT)
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
            body=json_data,
            headers=header,
            match=[matchers.query_param_matcher(params)],
            status=200)
    # start cloudOS service
    clos = Cloudos(apikey=APIKEY, cromwell_token=None, cloudos_url=CLOUDOS_URL)
    # get mock response
    response = clos.detect_workflow(workspace_id=WORKSPACE_ID, workflow_name="picard")
    assert response == 'docker'

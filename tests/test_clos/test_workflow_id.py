import mock
import json
import pytest
import requests
import responses
from responses import matchers
from cloudos.clos import Cloudos
from cloudos.utils.errors import BadRequestException
from tests.functions_for_pytest import load_json_file

INPUT = "tests/test_data/process_job_list_initial_json.json"
APIKEY = 'vnoiweur89u2ongs'
CLOUDOS_URL = 'http://cloudos.lifebit.ai'
WORKSPACE_ID = 'lv89ufc838sdig'


@mock.patch('cloudos.clos', mock.MagicMock())
@responses.activate
def test_workflow_id():
    """
    Test 'workflow_id' to work as intended
    API request is mocked and replicated with json files
    """
    create_json = load_json_file(INPUT)
    params = {"teamId": WORKSPACE_ID, "apikey": APIKEY}
    header = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json;charset=UTF-8"
    }
    search_str = f"teamId={WORKSPACE_ID}&apikey={APIKEY}"
    # mock GET method with the .json
    responses.add(
            responses.GET,
            url=f"{CLOUDOS_URL}/api/v1/jobs?{search_str}",
            body=create_json,
            headers=header,
            match=[matchers.query_param_matcher(params)],
            status=200)
    # start cloudOS service
    clos = Cloudos(apikey=APIKEY, cromwell_token=None, cloudos_url=CLOUDOS_URL)
    # get mock response
    response = clos.get_job_list(WORKSPACE_ID)
    workflow_id = response.json()["jobs"][0]["workflow"]["_id"]
    # check the response
    assert response.status_code == 200
    assert isinstance(workflow_id, str) and len(workflow_id) > 0
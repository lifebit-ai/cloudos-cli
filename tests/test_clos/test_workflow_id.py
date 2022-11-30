import mock
import json
import requests
import responses
from responses import matchers
from cloudos.jobs import Job
from tests.functions_for_pytest import load_json_file

INPUT_PROJECT = "tests/test_data/projects.json"
INPUT_WORKFLOW = "tests/test_data/workflows.json"
APIKEY = 'vnoiweur89u2ongs'
CLOUDOS_URL = 'http://cloudos.lifebit.ai'
WORKSPACE_ID = 'lv89ufc838sdig'
PROJECT_NAME = "lifebit-testing"
WORKFLOW_NAME = "nf-core-deepvariant"

@mock.patch('cloudos.clos', mock.MagicMock())
@responses.activate
def test_workflow_id():
    """
    Test 'workflow_id' to work as intended
    API request is mocked and replicated with json files
    """
    create_json_project = load_json_file(INPUT_PROJECT)
    create_json_workflow = load_json_file(INPUT_WORKFLOW)
    params = {"teamId": WORKSPACE_ID, "apikey": APIKEY}
    header = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json;charset=UTF-8"
    }
    search_str = f"teamId={WORKSPACE_ID}&apikey={APIKEY}"
    # mock GET method with the .json
    responses.add(
            responses.GET,
            url=f"{CLOUDOS_URL}/api/v1/projects?{search_str}",
            body=create_json_project,
            headers=header,
            match=[matchers.query_param_matcher(params)],
            status=200)
    responses.add(
            responses.GET,
            url=f"{CLOUDOS_URL}/api/v1/workflows?{search_str}",
            body=create_json_workflow,
            headers=header,
            match=[matchers.query_param_matcher(params)],
            status=201)
    # start cloudOS service
    job = Job(apikey=APIKEY,
        cloudos_url=CLOUDOS_URL,
        workspace_id=WORKSPACE_ID,
        cromwell_token=None,
        project_name=PROJECT_NAME,
        workflow_name=WORKFLOW_NAME)
    # get mock response
    wf_id = job.workflow_id
    # check the response
    assert isinstance(wf_id, str) and len(wf_id) > 0

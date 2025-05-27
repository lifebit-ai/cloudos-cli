"""pytest is added for checking Job.workflow_id"""
from io import StringIO
import sys
import mock
import responses
from responses import matchers
from cloudos_cli.jobs import Job
from tests.functions_for_pytest import load_json_file

INPUT = "tests/test_data/send_job.json"
APIKEY = 'vnoiweur89u2ongs'
CLOUDOS_URL = 'http://cloudos.lifebit.ai'
WORKSPACE_ID = 'lv89ufc838sdig'
PROJECT_NAME = "lifebit-testing"
WORKFLOW_NAME = "nf-core-deepvariant"
INPUT_PROJECT = "tests/test_data/projects.json"
INPUT_WORKFLOW = "tests/test_data/workflows.json"
PAGE_SIZE = 10
PAGE = 1
ARCHIVED_STATUS = "false"

param_dict = {
    "config": "cloudos_cli/examples/rnatoy.config"
    }


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
def test_send_job():
    """
    Test 'send_job' to work as intended
    API request is mocked and replicated with json files
    """
    create_json_project = load_json_file(INPUT_PROJECT)
    create_json_workflow = load_json_file(INPUT_WORKFLOW)
    create_json = load_json_file(INPUT)
    params_job = {"teamId": WORKSPACE_ID}
    params_projects = {"teamId": WORKSPACE_ID, "pageSize": PAGE_SIZE, "page": PAGE}
    params_workflows = {
        "teamId": WORKSPACE_ID,
        "pageSize": PAGE_SIZE,
        "page": PAGE,
        "archived.status": ARCHIVED_STATUS}
    header = {
            "Content-type": "application/json",
            "apikey": APIKEY
        }
    search_str = f"teamId={WORKSPACE_ID}"
    search_str_projects = f"teamId={WORKSPACE_ID}&pageSize={PAGE_SIZE}&page={PAGE}"
    search_str_workflows = f"teamId={WORKSPACE_ID}&pageSize={PAGE_SIZE}&page={PAGE}&archived.status={ARCHIVED_STATUS}"
    # mock GET method with the .json
    responses.add(
            responses.POST,
            url=f"{CLOUDOS_URL}/api/v2/jobs?{search_str}",
            body=create_json,
            headers=header,
            match=[matchers.query_param_matcher(params_job)],
            status=200)
    responses.add(
            responses.GET,
            url=f"{CLOUDOS_URL}/api/v2/projects?{search_str_projects}",
            body=create_json_project,
            headers=header,
            match=[matchers.query_param_matcher(params_projects)],
            status=200)
    responses.add(
            responses.GET,
            url=f"{CLOUDOS_URL}/api/v3/workflows?{search_str_workflows}",
            body=create_json_workflow,
            headers=header,
            match=[matchers.query_param_matcher(params_workflows)],
            status=200)
    # start cloudOS service
    job = Job(apikey=APIKEY,
              cloudos_url=CLOUDOS_URL,
              workspace_id=WORKSPACE_ID,
              cromwell_token=None,
              project_name=PROJECT_NAME,
              workflow_name=WORKFLOW_NAME)
    output = StringIO()
    sys.stdout = output
    job_json = job.send_job(param_dict["config"])
    result_string = output.getvalue().rstrip()

    assert isinstance(job_json, str)
    assert "Job successfully launched to CloudOS, please check the following link:" in result_string

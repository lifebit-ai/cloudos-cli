"""pytest is added for checking Job.workflow_id"""
from io import StringIO
import sys
import mock
import responses
from responses import matchers
from cloudos.jobs import Job
from tests.functions_for_pytest import load_json_file

INPUT = "tests/test_data/send_job.json"
APIKEY = 'vnoiweur89u2ongs'
CLOUDOS_URL = 'http://cloudos.lifebit.ai'
WORKSPACE_ID = 'lv89ufc838sdig'
PROJECT_NAME = "lifebit-testing"
WORKFLOW_NAME = "nf-core-deepvariant"
INPUT_PROJECT = "tests/test_data/projects.json"
INPUT_WORKFLOW = "tests/test_data/workflows.json"

param_dict = {
    "config": "cloudos/examples/rnatoy.config"
    }

@mock.patch('cloudos.clos', mock.MagicMock())
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
    params_pro_wf = {"teamId": WORKSPACE_ID, "apikey": APIKEY}
    header = {
            "Content-type": "application/json",
            "apikey": APIKEY
        }
    search_str = f"teamId={WORKSPACE_ID}"
    search_str_pro_wf = f"teamId={WORKSPACE_ID}&apikey={APIKEY}"
    # mock GET method with the .json
    responses.add(
            responses.POST,
            url=f"{CLOUDOS_URL}/api/v1/jobs?{search_str}",
            body=create_json,
            headers=header,
            match=[matchers.query_param_matcher(params_job)],
            status=200)
    responses.add(
            responses.GET,
            url=f"{CLOUDOS_URL}/api/v1/projects?{search_str_pro_wf}",
            body=create_json_project,
            headers=header,
            match=[matchers.query_param_matcher(params_pro_wf)],
            status=201)
    responses.add(
            responses.GET,
            url=f"{CLOUDOS_URL}/api/v1/workflows?{search_str_pro_wf}",
            body=create_json_workflow,
            headers=header,
            match=[matchers.query_param_matcher(params_pro_wf)],
            status=202)
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
    
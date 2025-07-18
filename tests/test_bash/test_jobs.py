"""pytest is added for checking Job.workflow_id"""
from io import StringIO
import sys
import mock
import responses
from responses import matchers
from cloudos_cli.jobs import Job
from tests.functions_for_pytest import load_json_file

INPUT = "tests/test_data/send_bash_job.json"
APIKEY = 'vnoiweur89u2ongs'
CLOUDOS_URL = 'http://cloudos.lifebit.ai'
WORKSPACE_ID = 'lv89ufc838sdig'
PROJECT_NAME = "lifebit-testing"
WORKFLOW_NAME = "ubuntu"
INPUT_PROJECT = "tests/test_data/projects.json"
INPUT_WORKFLOW = "tests/test_data/workflows_bash.json"
PAGE_SIZE = 10
PAGE = 1
ARCHIVED_STATUS = "false"
param_dict = {
    "resourceRequirements": {
        "cpu": 1,
        "ram": 4
    },
    "masterInstance": {
        "requestedInstance": {
            "type": "c5.xlarge",
            "asSpot": False
        }
    }
}
command = {"command": 'echo "Hello World"'}


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
def test_send_bash_job():
    """
    Test 'send_bash_job' to work as intended
    API request is mocked and replicated with json files
    """
    create_json_project = load_json_file(INPUT_PROJECT)
    create_json_workflow = load_json_file(INPUT_WORKFLOW)
    create_json = load_json_file(INPUT)
    params_job = {"teamId": WORKSPACE_ID}
    params_projects = {"search": PROJECT_NAME, "teamId": WORKSPACE_ID}
    params_workflows = {"search": WORKFLOW_NAME, "teamId": WORKSPACE_ID}
    header = {
            "Content-type": "application/json",
            "apikey": APIKEY
        }
    search_str = f"teamId={WORKSPACE_ID}"
    search_str_projects = f"teamId={WORKSPACE_ID}&search={PROJECT_NAME}"
    search_str_workflows = f"teamId={WORKSPACE_ID}&search={WORKFLOW_NAME}"
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
    job_json = job.send_job(
        job_config=None,
        parameter=('--test=testValue', '-test2=testValue2', 'test3=testValue3'),
        job_name="test_bash_job",
        workflow_type='docker',
        command=command
    )
    result_string = output.getvalue().rstrip()

    assert isinstance(job_json, str)
    assert "Job successfully launched to CloudOS, please check the following link:" in result_string

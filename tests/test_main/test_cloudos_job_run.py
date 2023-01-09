from io import StringIO
import os
import subprocess
import mock
import responses
from responses import matchers
from cloudos.clos import Cloudos
from cloudos.__main__ import run_cloudos_cli, job, run
from tests.functions_for_pytest import load_json_file
from click.testing import CliRunner
import traceback


INPUT_SEND_JOB = "tests/test_data/send_job.json"
INPUT_DETECT_WORKFLOW = "tests/test_data/process_workflow_list_initial_request.json"
INPUT_PROJECT = "tests/test_data/projects.json"
INPUT_WORKFLOW = "tests/test_data/workflows.json"

APIKEY = 'vnoiweur89u2ongs'
CLOUDOS_URL = 'http://cloudos.lifebit.ai'
WORKSPACE_ID = 'lv89ufc838sdig'
PROJECT_NAME = "lifebit-testing"
WORKFLOW_NAME = "nf-core-deepvariant"


@mock.patch('cloudos.clos', mock.MagicMock())
@responses.activate
def test_cloudos_job_run():
    """
    Test 'get_workflow_list' to work as intended
    API request is mocked and replicated with json files
    """
    json_data_detect_workflow = load_json_file(INPUT_DETECT_WORKFLOW)
    json_send_job = load_json_file(INPUT_SEND_JOB)
    create_json_project = load_json_file(INPUT_PROJECT)
    create_json_workflow = load_json_file(INPUT_WORKFLOW)
    params = {"teamId": WORKSPACE_ID, "apikey": APIKEY}
    header = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json;charset=UTF-8"
    }
    header_api = {
            "Content-type": "application/json",
            "apikey": APIKEY
        }
    search_str = f"teamId={WORKSPACE_ID}&apikey={APIKEY}"
    params_job = {"teamId": WORKSPACE_ID}
    send_job_search_str = f"teamId={WORKSPACE_ID}"
    # mock GET method with the .json
    responses.add(
            responses.GET,
            url=f"{CLOUDOS_URL}/api/v1/workflows?{search_str}",
            body=json_data_detect_workflow,
            headers=header,
            match=[matchers.query_param_matcher(params)],
            status=200)
    responses.add(
            responses.GET,
            url=f"{CLOUDOS_URL}/api/v1/projects?{search_str}",
            body=create_json_project,
            headers=header,
            match=[matchers.query_param_matcher(params)],
            status=201)
#     responses.add(
#             responses.GET,
#             url=f"{CLOUDOS_URL}/api/v1/workflows?{search_str}",
#             body=create_json_workflow,
#             headers=header,
#             match=[matchers.query_param_matcher(params)],
#             status=202)
    responses.add(
            responses.POST,
            url=f"{CLOUDOS_URL}/api/v1/jobs?{send_job_search_str}",
            body=json_send_job,
            headers=header_api,
            match=[matchers.query_param_matcher(params_job)],
            status=203)
    runner = CliRunner()
    result = runner.invoke(run, ["--apikey", APIKEY,
                                    "--cloudos-url", CLOUDOS_URL, 
                                    "--workspace-id", WORKSPACE_ID,
                                    "--project-name", PROJECT_NAME,
                                    "--workflow-name", WORKFLOW_NAME,
                                    "--job-config", "cloudos/examples/rnatoy.config"])
    print(result.exc_info)
    print(result.exit_code)
    print(result.exception)
    print(result.stdout)
    
    # f"Hello, \"{name}\""

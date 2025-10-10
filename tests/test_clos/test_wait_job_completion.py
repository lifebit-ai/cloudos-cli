"""Pytest for method Cloudos.wait_job_completion"""
import mock
import responses
from cloudos_cli.clos import Cloudos
from tests.functions_for_pytest import load_json_file

INPUT = "tests/test_data/get_job_status.json"
APIKEY = 'vnoiweur89u2ongs'
CLOUDOS_URL = 'http://cloudos.lifebit.ai'
WORKSPACE_ID = "5f6d3e9bd954e800b23f8c62"
JOB_ID = '63bd590f72c38201551c3824'


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
def test_wait_job_completion():
    """
    Test 'wait_job_completion' to work as intended
    API request is mocked and replicated with json files
    """
    json_data = load_json_file(INPUT)
    header = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json;charset=UTF-8",
        "apikey": APIKEY
    }
    # mock GET method with the .json
    responses.add(
            responses.GET,
            url=f"{CLOUDOS_URL}/api/v1/jobs/{JOB_ID}?teamId={WORKSPACE_ID}",
            body=json_data,
            headers=header,
            status=200)
    # start cloudOS service
    cl = Cloudos(apikey=APIKEY, cromwell_token=None, cloudos_url=CLOUDOS_URL)
    # get mock job status
    status = cl.wait_job_completion(job_id=JOB_ID,
                                    workspace_id=WORKSPACE_ID,
                                    wait_time=0.01,
                                    request_interval=0.01)
    assert isinstance(status, dict)
    assert status['status'] == 'running'

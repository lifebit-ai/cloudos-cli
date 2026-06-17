"""Test that get_job_list uses the v3 API endpoint."""
import mock
import responses
from responses import matchers
from cloudos_cli.clos import Cloudos
from tests.functions_for_pytest import load_json_file

INPUT = "tests/test_data/process_job_list_initial_json.json"
APIKEY = 'vnoiweur89u2ongs'
CLOUDOS_URL = 'http://cloudos.lifebit.ai'
WORKSPACE_ID = 'lv89ufc838sdig'


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
def test_get_job_list_uses_v3_endpoint():
    """
    Test that get_job_list sends the GET request to /api/v3/jobs
    and NOT to /api/v2/jobs.
    """
    create_json = load_json_file(INPUT)
    params = {"teamId": WORKSPACE_ID, "archived.status": "false", "limit": 1, "page": 1}
    header = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json;charset=UTF-8",
        "apikey": APIKEY
    }
    search_str = f"teamId={WORKSPACE_ID}&archived.status=false&limit=1&page=1"
    # Mock v3 GET endpoint
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v3/jobs?{search_str}",
        body=create_json,
        headers=header,
        match=[matchers.query_param_matcher(params)],
        status=200)
    clos = Cloudos(apikey=APIKEY, cromwell_token=None, cloudos_url=CLOUDOS_URL)
    response = clos.get_job_list(WORKSPACE_ID, last_n_jobs=1, page=1, page_size=10)

    assert isinstance(response, dict)
    assert 'jobs' in response
    # Verify the GET was made to the v3 endpoint
    get_calls = [c for c in responses.calls if c.request.method == 'GET']
    assert len(get_calls) == 1
    assert '/api/v3/jobs' in get_calls[0].request.url
    assert '/api/v2/jobs' not in get_calls[0].request.url


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
def test_get_job_list_v3_returns_correct_structure():
    """
    Test that get_job_list returns the expected dict structure
    when using the v3 endpoint.
    """
    create_json = load_json_file(INPUT)
    params = {"teamId": WORKSPACE_ID, "archived.status": "false", "limit": 10, "page": 1}
    header = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json;charset=UTF-8",
        "apikey": APIKEY
    }
    search_str = f"teamId={WORKSPACE_ID}&archived.status=false&limit=10&page=1"
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v3/jobs?{search_str}",
        body=create_json,
        headers=header,
        match=[matchers.query_param_matcher(params)],
        status=200)
    clos = Cloudos(apikey=APIKEY, cromwell_token=None, cloudos_url=CLOUDOS_URL)
    response = clos.get_job_list(WORKSPACE_ID, page=1, page_size=10)

    assert isinstance(response, dict)
    assert 'jobs' in response
    assert 'pagination_metadata' in response
    assert isinstance(response['jobs'], list)

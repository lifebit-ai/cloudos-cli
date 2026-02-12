import mock
import json
import pytest
import responses
from responses import matchers
from cloudos_cli.clos import Cloudos
from cloudos_cli.utils.errors import BadRequestException
from tests.functions_for_pytest import load_json_file

OUTPUT = "tests/test_data/project_create_response.json"
APIKEY = 'vnoiweur89u2ongs'
CLOUDOS_URL = 'http://cloudos.lifebit.ai'
WORKSPACE_ID = 'lv89ufc838sdig'
PROJECT_NAME = 'test-project'


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
def test_create_project_correct_response():
    """
    Test 'create_project' to work as intended
    API request is mocked and replicated with json files
    """
    create_json = load_json_file(OUTPUT)
    search_str = f"teamId={WORKSPACE_ID}"
    expected_data = {"name": PROJECT_NAME}
    header = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json;charset=UTF-8",
        "apikey": APIKEY
    }

    # mock POST method with the .json
    responses.add(
            responses.POST,
            url=f"{CLOUDOS_URL}/api/v1/projects?{search_str}",
            body=create_json,
            headers=header,
            match=[matchers.json_params_matcher(expected_data)],
            status=200)

    # start cloudOS service
    clos = Cloudos(apikey=APIKEY, cromwell_token=None, cloudos_url=CLOUDOS_URL)

    # get mock response
    project_id = clos.create_project(WORKSPACE_ID, PROJECT_NAME)

    # check the response
    assert isinstance(project_id, str)
    assert project_id == '64a7b1c2f8d9e1a2b3c4d5e6'


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
def test_create_project_bad_request():
    """
    Test 'create_project' to fail with '400' response
    """
    # prepare error message
    error_message = {"statusCode": 400, "code": "BadRequest",
                     "message": "Project name already exists.", "time": "2023-07-07T10:30:00.000Z"}
    error_json = json.dumps(error_message)
    search_str = f"teamId={WORKSPACE_ID}"
    expected_data = {"name": PROJECT_NAME}

    # mock POST method with error response
    responses.add(
            responses.POST,
            url=f"{CLOUDOS_URL}/api/v1/projects?{search_str}",
            body=error_json,
            match=[matchers.json_params_matcher(expected_data)],
            status=400)

    # start cloudOS service
    clos = Cloudos(apikey=APIKEY, cromwell_token=None, cloudos_url=CLOUDOS_URL)

    # test that BadRequestException is raised
    with pytest.raises(BadRequestException):
        clos.create_project(WORKSPACE_ID, PROJECT_NAME)


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
def test_create_project_unauthorized():
    """
    Test 'create_project' to fail with '401' response (unauthorized)
    """
    search_str = f"teamId={WORKSPACE_ID}"
    expected_data = {"name": PROJECT_NAME}

    # mock POST method with 401 response
    responses.add(
            responses.POST,
            url=f"{CLOUDOS_URL}/api/v1/projects?{search_str}",
            body="Unauthorized",
            match=[matchers.json_params_matcher(expected_data)],
            status=401)

    # start cloudOS service
    clos = Cloudos(apikey=APIKEY, cromwell_token=None, cloudos_url=CLOUDOS_URL)

    # test that ValueError is raised for unauthorized access
    with pytest.raises(ValueError, match="It seems your API key is not authorised"):
        clos.create_project(WORKSPACE_ID, PROJECT_NAME)


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
def test_create_project_with_ssl_verification():
    """
    Test 'create_project' with SSL verification disabled
    """
    create_json = load_json_file(OUTPUT)
    search_str = f"teamId={WORKSPACE_ID}"
    expected_data = {"name": PROJECT_NAME}

    # mock POST method with the .json
    responses.add(
            responses.POST,
            url=f"{CLOUDOS_URL}/api/v1/projects?{search_str}",
            body=create_json,
            match=[matchers.json_params_matcher(expected_data)],
            status=200)

    # start cloudOS service
    clos = Cloudos(apikey=APIKEY, cromwell_token=None, cloudos_url=CLOUDOS_URL)

    # get mock response with SSL verification disabled
    project_id = clos.create_project(WORKSPACE_ID, PROJECT_NAME, verify=False)

    # check the response
    assert isinstance(project_id, str)
    assert project_id == '64a7b1c2f8d9e1a2b3c4d5e6'

import mock
import json
import pytest
import responses
from responses import matchers
from cloudos_cli.clos import Cloudos
from cloudos_cli.utils.errors import BadRequestException
from tests.functions_for_pytest import load_json_file

OUTPUT = "tests/test_data/project_members_response.json"
APIKEY = 'vnoiweur89u2ongs'
CLOUDOS_URL = 'http://cloudos.lifebit.ai'
PROJECT_ID = '64a7b1c2f8d9e1a2b3c4d5e6'


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
def test_get_project_members_correct_response():
    """
    Test 'get_project_members' to work as intended.
    API request is mocked and replicated with json files.
    """
    members_json = load_json_file(OUTPUT)
    header = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json;charset=UTF-8",
        "apikey": APIKEY
    }

    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/projects/{PROJECT_ID}/members",
        body=members_json,
        headers=header,
        status=200)

    clos = Cloudos(apikey=APIKEY, cromwell_token=None, cloudos_url=CLOUDOS_URL)

    members = clos.get_project_members(PROJECT_ID)

    assert isinstance(members, list)
    assert len(members) == 2
    assert members[0]['email'] == 'test.user@lifebit.ai'
    assert members[0]['role'] == 'owner'


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
def test_get_project_members_bad_request():
    """
    Test 'get_project_members' to fail with '400' response.
    """
    error_message = {"statusCode": 400, "code": "BadRequest",
                     "message": "Project not found.", "time": "2023-07-07T10:30:00.000Z"}
    error_json = json.dumps(error_message)

    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/projects/{PROJECT_ID}/members",
        body=error_json,
        status=400)

    clos = Cloudos(apikey=APIKEY, cromwell_token=None, cloudos_url=CLOUDOS_URL)

    with pytest.raises(BadRequestException):
        clos.get_project_members(PROJECT_ID)


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
def test_get_project_members_unauthorized():
    """
    Test 'get_project_members' to fail with '401' response (unauthorized).
    """
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/projects/{PROJECT_ID}/members",
        body="Unauthorized",
        status=401)

    clos = Cloudos(apikey=APIKEY, cromwell_token=None, cloudos_url=CLOUDOS_URL)

    with pytest.raises(ValueError, match="It seems your API key is not authorised"):
        clos.get_project_members(PROJECT_ID)


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
def test_get_project_members_ssl_disabled():
    """
    Test 'get_project_members' with SSL verification disabled.
    """
    members_json = load_json_file(OUTPUT)

    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/projects/{PROJECT_ID}/members",
        body=members_json,
        status=200)

    clos = Cloudos(apikey=APIKEY, cromwell_token=None, cloudos_url=CLOUDOS_URL)

    members = clos.get_project_members(PROJECT_ID, verify=False)

    assert isinstance(members, list)
    assert len(members) == 2

import mock
import json
import pytest
import responses
from cloudos_cli.clos import Cloudos
from cloudos_cli.utils.errors import BadRequestException
from tests.functions_for_pytest import load_json_file

INPUT = "tests/test_data/project_members.json"
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
    members_json = load_json_file(INPUT)
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/projects/{PROJECT_ID}/members",
        body=members_json,
        status=200)
    clos = Cloudos(apikey=APIKEY, cromwell_token=None, cloudos_url=CLOUDOS_URL)
    response = clos.get_project_members(PROJECT_ID)
    assert isinstance(response, list)
    assert len(response) == 2
    assert response[0]['email'] == 'test.user@lifebit.ai'
    assert response[1]['role'] == 'member'


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
def test_get_project_members_bad_request():
    """
    Test 'get_project_members' to fail with '400' response.
    """
    error_message = {"statusCode": 400, "code": "BadRequest",
                     "message": "Bad Request.", "time": "2024-01-01T00:00:00.000Z"}
    error_json = json.dumps(error_message)
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/projects/{PROJECT_ID}/members",
        body=error_json,
        status=400)
    clos = Cloudos(apikey=APIKEY, cromwell_token=None, cloudos_url=CLOUDOS_URL)
    with pytest.raises(BadRequestException) as error:
        clos.get_project_members(PROJECT_ID)
    assert "Server returned status 400." in str(error)


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
def test_get_project_members_empty_list():
    """
    Test 'get_project_members' to return an empty list when no members exist.
    """
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/projects/{PROJECT_ID}/members",
        body=json.dumps([]),
        status=200)
    clos = Cloudos(apikey=APIKEY, cromwell_token=None, cloudos_url=CLOUDOS_URL)
    response = clos.get_project_members(PROJECT_ID)
    assert isinstance(response, list)
    assert len(response) == 0

import json
import mock
import pytest
import responses
from cloudos_cli.clos import Cloudos
from cloudos_cli.utils.errors import BadRequestException

APIKEY = 'vnoiweur89u2ongs'
CLOUDOS_URL = 'http://cloudos.lifebit.ai'
PROJECT_ID = 'project-123'

PROJECT_MEMBERS = [
    {"id": "member-1", "email": "member1@example.com", "role": "owner"},
    {"id": "member-2", "email": "member2@example.com", "role": "editor"}
]


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
def test_get_project_members_correct_response():
    """Test 'get_project_members' to work as intended."""
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/projects/{PROJECT_ID}/members",
        body=json.dumps(PROJECT_MEMBERS),
        status=200
    )

    clos = Cloudos(apikey=APIKEY, cromwell_token=None, cloudos_url=CLOUDOS_URL)
    response = clos.get_project_members(PROJECT_ID)

    assert isinstance(response, list)
    assert len(response) == 2
    assert response[0]['email'] == 'member1@example.com'


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
def test_get_project_members_incorrect_response():
    """Test 'get_project_members' to fail with '400' response."""
    error_message = {
        "statusCode": 400,
        "code": "BadRequest",
        "message": "Bad Request.",
        "time": "2022-11-23_17:31:07"
    }
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/projects/{PROJECT_ID}/members",
        body=json.dumps(error_message),
        status=400
    )

    with pytest.raises(BadRequestException) as error:
        clos = Cloudos(apikey=APIKEY, cromwell_token=None, cloudos_url=CLOUDOS_URL)
        clos.get_project_members(PROJECT_ID)
    assert "Server returned status 400." in str(error)

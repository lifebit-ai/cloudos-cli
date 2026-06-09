import mock
import json
import pytest
import responses
from cloudos_cli.clos import Cloudos
from cloudos_cli.utils.errors import BadRequestException

APIKEY = 'vnoiweur89u2ongs'
CLOUDOS_URL = 'http://cloudos.lifebit.ai'
PROJECT_ID = '64a7b1c2f8d9e1a2b3c4d5e6'


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
def test_get_project_members_correct_response():
    """
    Test 'get_project_members' to work as intended
    """
    members_payload = [
        {"id": "user-1", "email": "user-1@example.com", "role": "owner"},
        {"id": "user-2", "email": "user-2@example.com", "role": "member"}
    ]
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/projects/{PROJECT_ID}/members",
        body=json.dumps(members_payload),
        status=200
    )

    clos = Cloudos(apikey=APIKEY, cromwell_token=None, cloudos_url=CLOUDOS_URL)
    response = clos.get_project_members(PROJECT_ID)

    assert isinstance(response, list)
    assert len(response) == 2
    assert response[0]['role'] == 'owner'


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
def test_get_project_members_incorrect_response():
    """
    Test 'get_project_members' to fail with '400' response
    """
    error_message = {
        "statusCode": 400,
        "code": "BadRequest",
        "message": "Invalid project id",
        "time": "2026-06-09_17:18:00"
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

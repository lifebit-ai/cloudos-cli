import mock
import json
import pytest
import responses
from cloudos_cli.queue import Queue
from cloudos_cli.utils.errors import BadRequestException
from tests.functions_for_pytest import load_json_file

INPUT = "tests/test_data/queue/queues.json"
SYSTEM_QUEUES_INPUT = "tests/test_data/queue/system_queues.json"
APIKEY = 'vnoiweur89u2ongs'
CLOUDOS_URL = 'http://cloudos.lifebit.ai'
WORKSPACE_ID = 'lv89ufc838sdig'


@mock.patch('cloudos_cli.queue', mock.MagicMock())
@responses.activate
def test_get_job_queues_correct_response():
    """
    Test 'get_job_queues' to work as intended (includes system queues by default)
    API request is mocked and replicated with json files
    """
    create_json = load_json_file(INPUT)
    system_json = load_json_file(SYSTEM_QUEUES_INPUT)
    header = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json;charset=UTF-8",
        "apikey": APIKEY
    }
    # mock GET method for regular queues
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/teams/aws/v2/job-queues?teamId={WORKSPACE_ID}",
        body=create_json,
        headers=header,
        status=200)
    # mock GET method for system queues
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/teams/aws/v2/system-job-queues?teamId={WORKSPACE_ID}",
        body=system_json,
        headers=header,
        status=200)
    # Initialise Queue
    j_queue = Queue(cloudos_url=CLOUDOS_URL, apikey=APIKEY, cromwell_token=None,
                    workspace_id=WORKSPACE_ID)
    # get mock response (should include system queues by default)
    response = j_queue.get_job_queues()
    # check the response
    assert isinstance(response, list)
    assert len(response) == 2  # 1 regular + 1 system queue


@mock.patch('cloudos_cli.queue', mock.MagicMock())
@responses.activate
def test_get_job_queues_incorrect_response():
    """
    Test 'get_job_queues' to fail with '400' response
    """
    # prepare error message
    error_message = {"statusCode": 400, "code": "BadRequest",
                     "message": "Bad Request.", "time": "2022-11-23_17:31:07"}
    error_json = json.dumps(error_message)
    header = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json;charset=UTF-8",
        "apikey": APIKEY
    }
    # mock GET method with the .json
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/teams/aws/v2/job-queues?teamId={WORKSPACE_ID}",
        body=error_json,
        headers=header,
        status=400)
    # raise 400 error
    with pytest.raises(BadRequestException) as error:
        # check if it failed
        j_queue = Queue(cloudos_url=CLOUDOS_URL, apikey=APIKEY, cromwell_token=None,
                        workspace_id=WORKSPACE_ID)
        j_queue.get_job_queues()
    assert "Server returned status 400." in (str(error))


@mock.patch('cloudos_cli.queue', mock.MagicMock())
@responses.activate
def test_get_system_job_queues_correct_response():
    """
    Test 'get_system_job_queues' to work as intended
    API request is mocked and replicated with json files
    """
    create_json = load_json_file(SYSTEM_QUEUES_INPUT)
    header = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json;charset=UTF-8",
        "apikey": APIKEY
    }
    # mock GET method with the .json
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/teams/aws/v2/system-job-queues?teamId={WORKSPACE_ID}",
        body=create_json,
        headers=header,
        status=200)
    # Initialise Queue
    j_queue = Queue(cloudos_url=CLOUDOS_URL, apikey=APIKEY, cromwell_token=None,
                    workspace_id=WORKSPACE_ID)
    # get mock response
    response = j_queue.get_system_job_queues()
    # check the response
    assert isinstance(response, list)
    assert len(response) == 1
    assert response[0]['resourceType'] == 'system'


@mock.patch('cloudos_cli.queue', mock.MagicMock())
@responses.activate
def test_get_job_queues_exclude_system_queues():
    """
    Test 'get_job_queues' with exclude_system_queues=True
    Should return only regular queues (excluding system queues)
    """
    regular_queues_json = load_json_file(INPUT)
    header = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json;charset=UTF-8",
        "apikey": APIKEY
    }
    
    # Mock regular queues endpoint only (system queues should not be called)
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/teams/aws/v2/job-queues?teamId={WORKSPACE_ID}",
        body=regular_queues_json,
        headers=header,
        status=200)
    
    # Initialise Queue
    j_queue = Queue(cloudos_url=CLOUDOS_URL, apikey=APIKEY, cromwell_token=None,
                    workspace_id=WORKSPACE_ID)
    # get mock response without system queues
    response = j_queue.get_job_queues(exclude_system_queues=True)
    # check the response
    assert isinstance(response, list)
    assert len(response) == 1  # Only regular queue
    
    # Verify system queue endpoint was not called
    assert len(responses.calls) == 1
    assert "system-job-queues" not in responses.calls[0].request.url

import mock
import json
import pytest
import responses
from cloudos.queue import Queue
from cloudos.utils.errors import BadRequestException
from tests.functions_for_pytest import load_json_file

INPUT = "tests/test_data/queue/queues.json"
APIKEY = 'vnoiweur89u2ongs'
CLOUDOS_URL = 'http://cloudos.lifebit.ai'
WORKSPACE_ID = 'lv89ufc838sdig'


@mock.patch('cloudos.queue', mock.MagicMock())
@responses.activate
def test_get_job_queues_correct_response():
    """
    Test 'get_job_queues' to work as intended
    API request is mocked and replicated with json files
    """
    create_json = load_json_file(INPUT)
    header = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json;charset=UTF-8",
        "apikey": APIKEY
    }
    # mock GET method with the .json
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/teams/aws/v2/job-queues?teamId={WORKSPACE_ID}",
        body=create_json,
        headers=header,
        status=200)
    # Initialise Queue
    j_queue = Queue(cloudos_url=CLOUDOS_URL, apikey=APIKEY, cromwell_token=None,
                    workspace_id=WORKSPACE_ID)
    # get mock response
    response = j_queue.get_job_queues()
    # check the response
    assert isinstance(response, list)
    assert len(response) == 1


@mock.patch('cloudos.queue', mock.MagicMock())
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

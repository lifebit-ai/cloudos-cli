import mock
import json
import pytest
import responses
from cloudos.queue import Queue
from cloudos.utils.errors import BadRequestException
from tests.functions_for_pytest import load_json_file

INPUT = 'tests/test_data/queue/queues.json'
APIKEY = 'vnoiweur89u2ongs'
CLOUDOS_URL = 'http://cloudos.lifebit.ai'
WORKSPACE_ID = 'lv89ufc838sdig'
WORKFLOW_TYPE = 'nextflow'


def test_fetch_job_queue_id_batch_false():
    """
    Tests fetch_job_queue_id when batch=False.
    """
    # Initialise Queue
    j_queue = Queue(cloudos_url=CLOUDOS_URL, apikey=APIKEY, cromwell_token=None,
                    workspace_id=WORKSPACE_ID)
    # Call with batch=False
    j_queue_id = j_queue.fetch_job_queue_id(WORKFLOW_TYPE, batch=False)
    assert j_queue_id is None


@mock.patch('cloudos.queue', mock.MagicMock())
@responses.activate
def test_fetch_job_queue_id_batch_true_job_queue_none():
    """
    Tests fetch_job_queue_id when batch=True but no job_queue is provided, so it
    should fall back to the default one.
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
def test_fetch_job_queue_id_batch_true_job_queue_correct():
    """
    Tests fetch_job_queue_id when batch=True and a correct job_queue is provided.
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
def test_fetch_job_queue_id_batch_true_job_queue_wrong():
    """
    Tests fetch_job_queue_id when batch=True and a wrong job_queue is provided, so
    it will fall back to the default one.
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
def test_fetch_job_queue_id_batch_true_workflow_type_wrong():
    """
    Tests fetch_job_queue_id when batch=True and  wrong workflow_type is provided.
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



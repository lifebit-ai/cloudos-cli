import pytest
import responses
from responses import matchers
from cloudos_cli.clos import Cloudos
import mock

# Test constants
APIKEY = 'vnoiweur89u2ongs'
CLOUDOS_URL = 'http://cloudos.lifebit.ai'
WORKSPACE_ID = 'lv89ufc838sdig'
USER_ID = '651d2d387b9838932e40cf1b'
PROJECT_ID = '687fbbc73e05673d74addb82'
WORKFLOW_ID = '68835023a55d9ff1cecdff8e'
QUEUE_ID = 'v41_queue_id'

# Mock data
MOCK_JOB_LIST = {
    "jobs": [
        {
            "_id": "job1",
            "name": "test-job-1",
            "status": "completed",
            "user": {"id": USER_ID, "name": "Test User"},
            "project": {"id": PROJECT_ID, "name": "test-project"},
            "workflow": {"id": WORKFLOW_ID, "name": "test-workflow"},
            "batch": {"jobQueue": {"id": QUEUE_ID}}
        },
        {
            "_id": "job2",
            "name": "test-job-2",
            "status": "running",
            "user": {"id": "other_user_id", "name": "Other User"},
            "project": {"id": "other_project_id", "name": "other-project"},
            "workflow": {"id": "other_workflow_id", "name": "other-workflow"},
            "batch": {"jobQueue": {"id": "other_queue_id"}}
        }
    ]
}

MOCK_USER_INFO = {
    "id": USER_ID,
    "name": "Test",
    "surname": "User",
    "email": "test@example.com"
}

MOCK_QUEUE_LIST = [
    {"id": QUEUE_ID, "name": "v41", "label": "v41"},
    {"id": "other_queue_id", "name": "other-queue", "label": "other-queue"}
]

def setup_clos():
    return Cloudos(apikey=APIKEY, cromwell_token=None, cloudos_url=CLOUDOS_URL)

@responses.activate
def test_filter_by_status():
    expected_params = {
        "teamId": WORKSPACE_ID,
        "archived.status": "false",
        "limit": 10,
        "page": 1,
        "status": "completed"
    }
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v2/jobs",
        json=MOCK_JOB_LIST,
        match=[matchers.query_param_matcher(expected_params)],
        status=200
    )
    clos = setup_clos()
    result = clos.get_job_list(WORKSPACE_ID, filter_status="completed")
    assert isinstance(result, list)
    assert len(result) == 2

@responses.activate
def test_filter_by_job_name():
    expected_params = {
        "teamId": WORKSPACE_ID,
        "archived.status": "false",
        "limit": 10,
        "page": 1,
        "name": "test-job-1"
    }
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v2/jobs",
        json=MOCK_JOB_LIST,
        match=[matchers.query_param_matcher(expected_params)],
        status=200
    )
    clos = setup_clos()
    result = clos.get_job_list(WORKSPACE_ID, filter_job_name="test-job-1")
    assert isinstance(result, list)

@responses.activate
def test_filter_by_job_id():
    expected_params = {
        "teamId": WORKSPACE_ID,
        "archived.status": "false",
        "limit": 10,
        "page": 1,
        "id": "job1"
    }
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v2/jobs",
        json=MOCK_JOB_LIST,
        match=[matchers.query_param_matcher(expected_params)],
        status=200
    )
    clos = setup_clos()
    result = clos.get_job_list(WORKSPACE_ID, filter_job_id="job1")
    assert isinstance(result, list)

@responses.activate
def test_filter_only_mine():
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/users/me",
        json=MOCK_USER_INFO,
        status=200
    )
    expected_params = {
        "teamId": WORKSPACE_ID,
        "archived.status": "false",
        "limit": 10,
        "page": 1,
        "user.id": USER_ID
    }
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v2/jobs",
        json=MOCK_JOB_LIST,
        match=[matchers.query_param_matcher(expected_params)],
        status=200
    )
    clos = setup_clos()
    result = clos.get_job_list(WORKSPACE_ID, filter_only_mine=True)
    assert isinstance(result, list)

@responses.activate
@mock.patch('cloudos_cli.queue.queue.Queue.get_job_queues')
def test_filter_by_queue(mock_get_queues):
    mock_get_queues.return_value = MOCK_QUEUE_LIST
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v2/jobs",
        json=MOCK_JOB_LIST,
        status=200
    )
    clos = setup_clos()
    result = clos.get_job_list(WORKSPACE_ID, filter_queue="v41")
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["_id"] == "job1"


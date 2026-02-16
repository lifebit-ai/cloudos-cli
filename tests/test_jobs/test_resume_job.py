"""pytest added for testing Job.clone_or_resume_job() method with mode='resume'

This test file provides comprehensive testing for the job resume functionality in CloudOS CLI.
It covers:
- Basic job resuming 
- Parameter overrides (job name, cost limit, instance type, etc.)
- Job queue override
- Project name override
- Error handling for API failures
- Direct testing of get_field_from_jobs_endpoint method

The tests use mocked API responses to simulate CloudOS server interactions without 
requiring actual server connections. The main difference from clone tests is that
resume calls the additional get_field_from_jobs_endpoint() method which hits the 'api/v1/jobs' endpoint.
"""
import json
import mock
import pytest
import responses
from responses import matchers
from cloudos_cli.jobs import Job
from cloudos_cli.utils.errors import BadRequestException
from tests.functions_for_pytest import load_json_file

# Test constants
APIKEY = 'vnoiweur89u2ongs'
CLOUDOS_URL = 'http://cloudos.lifebit.ai'
WORKSPACE_ID = 'lv89ufc838sdig'
PROJECT_NAME = "lifebit-testing"
WORKFLOW_NAME = "nf-core-deepvariant"
SOURCE_JOB_ID = "616ee9681b866a01d69fa1cd"
RESUMED_JOB_ID = "617ff9681b866a01d69fa2de"
RESUME_WORK_DIR = "6846b0fd7fa0203cbc02f951"

# Test data files
JOB_PAYLOAD_INPUT = "tests/test_data/job_request_payload.json"
CLONE_RESPONSE_INPUT = "tests/test_data/clone_job_response.json"
PROJECTS_INPUT = "tests/test_data/projects.json"
WORKFLOWS_INPUT = "tests/test_data/workflows.json"
QUEUES_INPUT = "tests/test_data/job_queues.json"
JOB_DETAILS_INPUT = "tests/test_data/get_job_details.json"
BRANCHES_INPUT = "tests/test_data/get_branches.json"


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
def test_resume_job_basic():
    """
    Test basic job resume functionality
    """
    # Load test data
    job_payload = load_json_file(JOB_PAYLOAD_INPUT)
    clone_response = load_json_file(CLONE_RESPONSE_INPUT)
    projects_data = load_json_file(PROJECTS_INPUT)
    workflows_data = load_json_file(WORKFLOWS_INPUT)
    job_details = load_json_file(JOB_DETAILS_INPUT)

    # Set up headers
    headers = {
        "Content-type": "application/json",
        "apikey": APIKEY
    }

    # Mock GET request for job payload
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/jobs/{SOURCE_JOB_ID}/request-payload?teamId={WORKSPACE_ID}",
        body=job_payload,
        headers=headers,
        status=200
    )

    # Mock GET request for job details (resume work dir)
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/jobs/{SOURCE_JOB_ID}?teamId={WORKSPACE_ID}",
        body=job_details,
        headers=headers,
        status=200
    )

    # Mock POST request for job creation
    responses.add(
        responses.POST,
        url=f"{CLOUDOS_URL}/api/v2/jobs?teamId={WORKSPACE_ID}",
        body=clone_response,
        headers=headers,
        status=200
    )

    # Mock GET requests for projects and workflows
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v2/projects?teamId={WORKSPACE_ID}&search={PROJECT_NAME}",
        body=projects_data,
        headers=headers,
        status=200
    )
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v3/workflows?teamId={WORKSPACE_ID}&search={WORKFLOW_NAME}",
        body=workflows_data,
        headers=headers,
        status=200
    )
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v3/workflows?teamId={WORKSPACE_ID}&search={WORKFLOW_NAME}&pageSize=10",
        body=workflows_data,
        headers=headers,
        status=200
    )

    # Create Job object
    job = Job(
        apikey=APIKEY,
        cloudos_url=CLOUDOS_URL,
        workspace_id=WORKSPACE_ID,
        cromwell_token=None,
        project_name=PROJECT_NAME,
        workflow_name=WORKFLOW_NAME
    )

    # Test basic resuming with mode="resume"
    result_job_id = job.clone_or_resume_job(source_job_id=SOURCE_JOB_ID, mode="resume")

    assert result_job_id == RESUMED_JOB_ID
    assert isinstance(result_job_id, str)


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
def test_resume_job_with_overrides():
    """
    Test job resume with parameter overrides
    """
    # Load test data
    job_payload = load_json_file(JOB_PAYLOAD_INPUT)
    clone_response = load_json_file(CLONE_RESPONSE_INPUT)
    projects_data = load_json_file(PROJECTS_INPUT)
    workflows_data = load_json_file(WORKFLOWS_INPUT)
    job_details = load_json_file(JOB_DETAILS_INPUT)

    headers = {
        "Content-type": "application/json",
        "apikey": APIKEY
    }

    # Mock GET request for job payload
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/jobs/{SOURCE_JOB_ID}/request-payload?teamId={WORKSPACE_ID}",
        body=job_payload,
        headers=headers,
        status=200
    )

    # Mock GET request for job details (resume work dir and workflow for branch validation)
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/jobs/{SOURCE_JOB_ID}?teamId={WORKSPACE_ID}",
        body=job_details,
        headers=headers,
        status=200
    )

    # Mock GET request for branches (needed for branch validation)
    branches_data = load_json_file(BRANCHES_INPUT)
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/git/github/getBranches",
        body=branches_data,
        headers=headers,
        status=200,
        match=[matchers.query_param_matcher({
            "repositoryIdentifier": "820526317",
            "owner": "lifebit-ai",
            "workflowOwnerId": "5d72291a024bb8943d8f219a",
            "page": "1",
            "limit": "100",
            "teamId": WORKSPACE_ID
        })]
    )

    # Mock POST request for job creation  
    responses.add(
        responses.POST,
        url=f"{CLOUDOS_URL}/api/v2/jobs?teamId={WORKSPACE_ID}",
        body=clone_response,
        headers=headers,
        status=200
    )

    # Mock GET requests for projects and workflows
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v2/projects?teamId={WORKSPACE_ID}&search={PROJECT_NAME}",
        body=projects_data,
        headers=headers,
        status=200
    )
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v3/workflows?teamId={WORKSPACE_ID}&search={WORKFLOW_NAME}",
        body=workflows_data,
        headers=headers,
        status=200
    )
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v3/workflows?teamId={WORKSPACE_ID}&search={WORKFLOW_NAME}&pageSize=10",
        body=workflows_data,
        headers=headers,
        status=200
    )

    # Create Job object
    job = Job(
        apikey=APIKEY,
        cloudos_url=CLOUDOS_URL,
        workspace_id=WORKSPACE_ID,
        cromwell_token=None,
        project_name=PROJECT_NAME,
        workflow_name=WORKFLOW_NAME
    )

    # Test resume with overrides including branch
    result_job_id = job.clone_or_resume_job(
        source_job_id=SOURCE_JOB_ID,
        mode="resume",
        job_name="resumed_job_test",
        cost_limit=50.0,
        master_instance="c5.2xlarge",
        nextflow_version="24.04.4",
        branch="develop",
        repository_platform="github",
        profile="test",
        do_not_save_logs=False,
        use_fusion=True,
        parameters=["--input=s3://new-bucket/new-input.txt", "--threads=8"]
    )

    assert result_job_id == RESUMED_JOB_ID
    assert isinstance(result_job_id, str)


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@mock.patch('cloudos_cli.queue.queue.Queue')
@responses.activate
def test_resume_job_with_queue_override(mock_queue_class):
    """
    Test job resume with job queue override
    """
    # Load test data
    job_payload = load_json_file(JOB_PAYLOAD_INPUT)
    clone_response = load_json_file(CLONE_RESPONSE_INPUT)
    projects_data = load_json_file(PROJECTS_INPUT)
    workflows_data = load_json_file(WORKFLOWS_INPUT)
    queues_data = json.loads(load_json_file(QUEUES_INPUT))
    job_details = load_json_file(JOB_DETAILS_INPUT)

    headers = {
        "Content-type": "application/json", 
        "apikey": APIKEY
    }

    # Mock GET request for job payload
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/jobs/{SOURCE_JOB_ID}/request-payload?teamId={WORKSPACE_ID}",
        body=job_payload,
        headers=headers,
        status=200
    )

    # Mock GET request for job details (resume work dir)
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/jobs/{SOURCE_JOB_ID}?teamId={WORKSPACE_ID}",
        body=job_details,
        headers=headers,
        status=200
    )

    # Mock POST request for job creation
    responses.add(
        responses.POST,
        url=f"{CLOUDOS_URL}/api/v2/jobs?teamId={WORKSPACE_ID}",
        body=clone_response,
        headers=headers,
        status=200
    )

    # Mock GET requests for projects and workflows
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v2/projects?teamId={WORKSPACE_ID}&search={PROJECT_NAME}",
        body=projects_data,
        headers=headers,
        status=200
    )
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v3/workflows?teamId={WORKSPACE_ID}&search={WORKFLOW_NAME}",
        body=workflows_data,
        headers=headers,
        status=200
    )
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v3/workflows?teamId={WORKSPACE_ID}&search={WORKFLOW_NAME}&pageSize=10",
        body=workflows_data,
        headers=headers,
        status=200
    )

    # Mock Queue class
    mock_queue_instance = mock_queue_class.return_value
    mock_queue_instance.get_job_queues.return_value = queues_data

    # Create Job object
    job = Job(
        apikey=APIKEY,
        cloudos_url=CLOUDOS_URL,
        workspace_id=WORKSPACE_ID,
        cromwell_token=None,
        project_name=PROJECT_NAME,
        workflow_name=WORKFLOW_NAME
    )

    # Test resume with queue override
    result_job_id = job.clone_or_resume_job(
        source_job_id=SOURCE_JOB_ID,
        mode="resume",
        queue_name="test-queue"
    )

    assert result_job_id == RESUMED_JOB_ID
    mock_queue_instance.get_job_queues.assert_called_once()


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate 
def test_resume_job_with_project_override():
    """
    Test job resume with project name override
    """
    # Load test data
    job_payload = load_json_file(JOB_PAYLOAD_INPUT)
    clone_response = load_json_file(CLONE_RESPONSE_INPUT) 
    projects_data = load_json_file(PROJECTS_INPUT)
    new_project_data = load_json_file("tests/test_data/new_project.json")
    workflows_data = load_json_file(WORKFLOWS_INPUT)
    job_details = load_json_file(JOB_DETAILS_INPUT)

    headers = {
        "Content-type": "application/json",
        "apikey": APIKEY
    }

    # Mock GET request for job payload
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/jobs/{SOURCE_JOB_ID}/request-payload?teamId={WORKSPACE_ID}",
        body=job_payload,
        headers=headers,
        status=200
    )

    # Mock GET request for job details (resume work dir)
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/jobs/{SOURCE_JOB_ID}?teamId={WORKSPACE_ID}",
        body=job_details,
        headers=headers,
        status=200
    )

    # Mock POST request for job creation
    responses.add(
        responses.POST,
        url=f"{CLOUDOS_URL}/api/v2/jobs?teamId={WORKSPACE_ID}",
        body=clone_response,
        headers=headers,
        status=200
    )

    # Mock GET requests for projects and workflows (multiple calls expected)
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v2/projects?teamId={WORKSPACE_ID}&search={PROJECT_NAME}",
        body=projects_data,
        headers=headers,
        status=200
    )
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v2/projects?teamId={WORKSPACE_ID}&search=new-project-name",
        body=new_project_data,
        headers=headers,
        status=200
    )
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v3/workflows?teamId={WORKSPACE_ID}&search={WORKFLOW_NAME}",
        body=workflows_data,
        headers=headers,
        status=200
    )
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v3/workflows?teamId={WORKSPACE_ID}&search={WORKFLOW_NAME}&pageSize=10",
        body=workflows_data,
        headers=headers,
        status=200
    )

    # Create Job object
    job = Job(
        apikey=APIKEY,
        cloudos_url=CLOUDOS_URL,
        workspace_id=WORKSPACE_ID,
        cromwell_token=None,
        project_name=PROJECT_NAME,
        workflow_name=WORKFLOW_NAME
    )

    # Test resume with project override
    result_job_id = job.clone_or_resume_job(
        source_job_id=SOURCE_JOB_ID,
        mode="resume",
        project_name="new-project-name"
    )

    assert result_job_id == RESUMED_JOB_ID


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
def test_resume_job_get_payload_error():
    """
    Test resume_job when getting job payload fails
    """
    # Load test data for initialization
    projects_data = load_json_file(PROJECTS_INPUT)
    workflows_data = load_json_file(WORKFLOWS_INPUT)

    headers = {
        "Content-type": "application/json",
        "apikey": APIKEY
    }

    # Mock GET requests for Job initialization
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v2/projects?teamId={WORKSPACE_ID}&search={PROJECT_NAME}",
        body=projects_data,
        headers=headers,
        status=200
    )
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v3/workflows?teamId={WORKSPACE_ID}&search={WORKFLOW_NAME}",
        body=workflows_data,
        headers=headers,
        status=200
    )
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v3/workflows?teamId={WORKSPACE_ID}&search={WORKFLOW_NAME}&pageSize=10",
        body=workflows_data,
        headers=headers,
        status=200
    )

    # Mock GET request for job payload - return error
    error_message = {"statusCode": 404, "code": "NotFound",
                     "message": "Job not found", "time": "2025-04-25_17:31:07"}
    error_json = json.dumps(error_message)

    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/jobs/{SOURCE_JOB_ID}/request-payload?teamId={WORKSPACE_ID}",
        body=error_json,
        headers=headers,
        status=404
    )

    # Create Job object
    job = Job(
        apikey=APIKEY,
        cloudos_url=CLOUDOS_URL,
        workspace_id=WORKSPACE_ID,
        cromwell_token=None,
        project_name=PROJECT_NAME,
        workflow_name=WORKFLOW_NAME
    )

    # Test that BadRequestException is raised
    with pytest.raises(BadRequestException):
        job.clone_or_resume_job(source_job_id=SOURCE_JOB_ID, mode="resume")


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
def test_resume_job_create_error():
    """
    Test resume_job when creating resumed job fails
    """
    # Load test data
    job_payload = load_json_file(JOB_PAYLOAD_INPUT)
    projects_data = load_json_file(PROJECTS_INPUT)
    workflows_data = load_json_file(WORKFLOWS_INPUT)
    job_details = load_json_file(JOB_DETAILS_INPUT)

    headers = {
        "Content-type": "application/json",
        "apikey": APIKEY
    }

    # Mock GET request for job payload - success
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/jobs/{SOURCE_JOB_ID}/request-payload?teamId={WORKSPACE_ID}",
        body=job_payload,
        headers=headers,
        status=200
    )

    # Mock GET request for job details (resume work dir) - success
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/jobs/{SOURCE_JOB_ID}?teamId={WORKSPACE_ID}",
        body=job_details,
        headers=headers,
        status=200
    )

    # Mock POST request for job creation - return error
    error_message = {"statusCode": 400, "code": "BadRequest",
                     "message": "Invalid job parameters", "time": "2025-04-25_17:31:07"}
    error_json = json.dumps(error_message)

    responses.add(
        responses.POST,
        url=f"{CLOUDOS_URL}/api/v2/jobs?teamId={WORKSPACE_ID}",
        body=error_json,
        headers=headers,
        status=400
    )

    # Mock GET requests for projects and workflows
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v2/projects?teamId={WORKSPACE_ID}&search={PROJECT_NAME}",
        body=projects_data,
        headers=headers,
        status=200
    )
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v3/workflows?teamId={WORKSPACE_ID}&search={WORKFLOW_NAME}",
        body=workflows_data,
        headers=headers,
        status=200
    )
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v3/workflows?teamId={WORKSPACE_ID}&search={WORKFLOW_NAME}&pageSize=10",
        body=workflows_data,
        headers=headers,
        status=200
    )

    # Create Job object
    job = Job(
        apikey=APIKEY,
        cloudos_url=CLOUDOS_URL,
        workspace_id=WORKSPACE_ID,
        cromwell_token=None,
        project_name=PROJECT_NAME,
        workflow_name=WORKFLOW_NAME
    )

    # Test that BadRequestException is raised
    with pytest.raises(BadRequestException):
        job.clone_or_resume_job(source_job_id=SOURCE_JOB_ID, mode="resume")


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
def test_get_resume_work_dir():
    """
    Test get_field_from_jobs_endpoint method directly
    """
    # Load test data
    job_details = load_json_file(JOB_DETAILS_INPUT)
    projects_data = load_json_file(PROJECTS_INPUT)
    workflows_data = load_json_file(WORKFLOWS_INPUT)

    headers = {
        "Content-type": "application/json",
        "apikey": APIKEY
    }

    # Mock GET request for job details
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/jobs/{SOURCE_JOB_ID}?teamId={WORKSPACE_ID}",
        body=job_details,
        headers=headers,
        status=200
    )

    # Mock GET requests for Job initialization
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v2/projects?teamId={WORKSPACE_ID}&search={PROJECT_NAME}",
        body=projects_data,
        headers=headers,
        status=200
    )
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v3/workflows?teamId={WORKSPACE_ID}&search={WORKFLOW_NAME}",
        body=workflows_data,
        headers=headers,
        status=200
    )
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v3/workflows?teamId={WORKSPACE_ID}&search={WORKFLOW_NAME}&pageSize=10",
        body=workflows_data,
        headers=headers,
        status=200
    )

    # Create Job object
    job = Job(
        apikey=APIKEY,
        cloudos_url=CLOUDOS_URL,
        workspace_id=WORKSPACE_ID,
        cromwell_token=None,
        project_name=PROJECT_NAME,
        workflow_name=WORKFLOW_NAME
    )

    # Test get_field_from_jobs_endpoint method
    resume_work_dir = job.get_field_from_jobs_endpoint(SOURCE_JOB_ID, field="resumeWorkDir")

    assert resume_work_dir == RESUME_WORK_DIR
    assert isinstance(resume_work_dir, str)


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
def test_get_resume_work_dir_error():
    """
    Test get_field_from_jobs_endpoint when API call fails
    """
    # Load test data for initialization
    projects_data = load_json_file(PROJECTS_INPUT)
    workflows_data = load_json_file(WORKFLOWS_INPUT)

    headers = {
        "Content-type": "application/json",
        "apikey": APIKEY
    }

    # Mock GET requests for Job initialization
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v2/projects?teamId={WORKSPACE_ID}&search={PROJECT_NAME}",
        body=projects_data,
        headers=headers,
        status=200
    )
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v3/workflows?teamId={WORKSPACE_ID}&search={WORKFLOW_NAME}",
        body=workflows_data,
        headers=headers,
        status=200
    )
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v3/workflows?teamId={WORKSPACE_ID}&search={WORKFLOW_NAME}&pageSize=10",
        body=workflows_data,
        headers=headers,
        status=200
    )

    # Mock GET request for job details - return error
    error_message = {"statusCode": 404, "code": "NotFound",
                     "message": "Job not found", "time": "2025-04-25_17:31:07"}
    error_json = json.dumps(error_message)

    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/jobs/{SOURCE_JOB_ID}?teamId={WORKSPACE_ID}",
        body=error_json,
        headers=headers,
        status=404
    )

    # Create Job object
    job = Job(
        apikey=APIKEY,
        cloudos_url=CLOUDOS_URL,
        workspace_id=WORKSPACE_ID,
        cromwell_token=None,
        project_name=PROJECT_NAME,
        workflow_name=WORKFLOW_NAME
    )

    # Test that BadRequestException is raised
    with pytest.raises(BadRequestException):
        job.get_field_from_jobs_endpoint(SOURCE_JOB_ID, field="resumeWorkDir")

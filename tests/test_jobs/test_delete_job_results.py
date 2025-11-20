"""pytest for delete_job_results method"""
import pytest
import mock
import responses
from responses import matchers
from cloudos_cli.jobs import Job
from cloudos_cli.utils.errors import BadRequestException

APIKEY = 'test_api_key_12345'
CLOUDOS_URL = 'https://test.cloudos.lifebit.ai'
WORKSPACE_ID = 'test_workspace_123'
FOLDER_ID = 'test_folder_456'


@mock.patch('cloudos_cli.jobs.job.Job.project_id', new_callable=mock.PropertyMock)
@mock.patch('cloudos_cli.jobs.job.Job.workflow_id', new_callable=mock.PropertyMock)
@responses.activate
def test_delete_job_results_success_204(mock_workflow_id, mock_project_id):
    """
    Test successful deletion with 204 NoContent response
    """
    mock_project_id.return_value = "test_project_id"
    mock_workflow_id.return_value = "test_workflow_id"
    
    url = f"{CLOUDOS_URL}/api/v1/folders/{FOLDER_ID}"
    params = {"teamId": WORKSPACE_ID}
    
    responses.add(
        responses.DELETE,
        url=url,
        status=204,
        match=[matchers.query_param_matcher(params)]
    )
    
    job = Job(
        apikey=APIKEY,
        cloudos_url=CLOUDOS_URL,
        workspace_id=WORKSPACE_ID,
        cromwell_token=None,
        project_name="test_project",
        workflow_name="test_workflow"
    )
    
    result = job.delete_job_results(FOLDER_ID)
    
    assert result["message"] == "Results deleted successfully"
    assert result["status"] == "deleted"


@mock.patch('cloudos_cli.jobs.job.Job.project_id', new_callable=mock.PropertyMock)
@mock.patch('cloudos_cli.jobs.job.Job.workflow_id', new_callable=mock.PropertyMock)
@responses.activate
def test_delete_job_results_not_found_404(mock_workflow_id, mock_project_id):
    """
    Test deletion when folder doesn't exist (404)
    """
    mock_project_id.return_value = "test_project_id"
    mock_workflow_id.return_value = "test_workflow_id"
    
    url = f"{CLOUDOS_URL}/api/v1/folders/{FOLDER_ID}"
    params = {"teamId": WORKSPACE_ID}
    
    responses.add(
        responses.DELETE,
        url=url,
        status=404,
        json={"message": "The access to the S3Folder is not allowed"},
        match=[matchers.query_param_matcher(params)]
    )
    
    job = Job(
        apikey=APIKEY,
        cloudos_url=CLOUDOS_URL,
        workspace_id=WORKSPACE_ID,
        cromwell_token=None,
        project_name="test_project",
        workflow_name="test_workflow"
    )
    
    with pytest.raises(ValueError) as exc_info:
        job.delete_job_results(FOLDER_ID)
    
    assert "The access to the S3Folder is not allowed" in str(exc_info.value)


@mock.patch('cloudos_cli.jobs.job.Job.project_id', new_callable=mock.PropertyMock)
@mock.patch('cloudos_cli.jobs.job.Job.workflow_id', new_callable=mock.PropertyMock)
@responses.activate
def test_delete_job_results_unauthorized_401(mock_workflow_id, mock_project_id):
    """
    Test deletion with unauthorized access (401)
    """
    mock_project_id.return_value = "test_project_id"
    mock_workflow_id.return_value = "test_workflow_id"
    
    url = f"{CLOUDOS_URL}/api/v1/folders/{FOLDER_ID}"
    params = {"teamId": WORKSPACE_ID}
    
    responses.add(
        responses.DELETE,
        url=url,
        status=401,
        match=[matchers.query_param_matcher(params)]
    )
    
    job = Job(
        apikey=APIKEY,
        cloudos_url=CLOUDOS_URL,
        workspace_id=WORKSPACE_ID,
        cromwell_token=None,
        project_name="test_project",
        workflow_name="test_workflow"
    )
    
    with pytest.raises(ValueError) as exc_info:
        job.delete_job_results(FOLDER_ID)
    
    assert "Unauthorized" in str(exc_info.value)
    assert "API key" in str(exc_info.value)


@mock.patch('cloudos_cli.jobs.job.Job.project_id', new_callable=mock.PropertyMock)
@mock.patch('cloudos_cli.jobs.job.Job.workflow_id', new_callable=mock.PropertyMock)
@responses.activate
def test_delete_job_results_forbidden_403(mock_workflow_id, mock_project_id):
    """
    Test deletion with forbidden access (403)
    """
    mock_project_id.return_value = "test_project_id"
    mock_workflow_id.return_value = "test_workflow_id"
    
    url = f"{CLOUDOS_URL}/api/v1/folders/{FOLDER_ID}"
    params = {"teamId": WORKSPACE_ID}
    
    responses.add(
        responses.DELETE,
        url=url,
        status=403,
        match=[matchers.query_param_matcher(params)]
    )
    
    job = Job(
        apikey=APIKEY,
        cloudos_url=CLOUDOS_URL,
        workspace_id=WORKSPACE_ID,
        cromwell_token=None,
        project_name="test_project",
        workflow_name="test_workflow"
    )
    
    with pytest.raises(ValueError) as exc_info:
        job.delete_job_results(FOLDER_ID)
    
    assert "Forbidden" in str(exc_info.value)
    assert "permission" in str(exc_info.value)


@mock.patch('cloudos_cli.jobs.job.Job.project_id', new_callable=mock.PropertyMock)
@mock.patch('cloudos_cli.jobs.job.Job.workflow_id', new_callable=mock.PropertyMock)
@responses.activate
def test_delete_job_results_conflict_409(mock_workflow_id, mock_project_id):
    """
    Test deletion with conflict (409)
    """
    mock_project_id.return_value = "test_project_id"
    mock_workflow_id.return_value = "test_workflow_id"
    
    url = f"{CLOUDOS_URL}/api/v1/folders/{FOLDER_ID}"
    params = {"teamId": WORKSPACE_ID}
    
    responses.add(
        responses.DELETE,
        url=url,
        status=409,
        match=[matchers.query_param_matcher(params)]
    )
    
    job = Job(
        apikey=APIKEY,
        cloudos_url=CLOUDOS_URL,
        workspace_id=WORKSPACE_ID,
        cromwell_token=None,
        project_name="test_project",
        workflow_name="test_workflow"
    )
    
    with pytest.raises(ValueError) as exc_info:
        job.delete_job_results(FOLDER_ID)
    
    assert "Conflict" in str(exc_info.value)


@mock.patch('cloudos_cli.jobs.job.Job.project_id', new_callable=mock.PropertyMock)
@mock.patch('cloudos_cli.jobs.job.Job.workflow_id', new_callable=mock.PropertyMock)
@responses.activate
def test_delete_job_results_bad_request_400(mock_workflow_id, mock_project_id):
    """
    Test deletion with bad request (400)
    """
    mock_project_id.return_value = "test_project_id"
    mock_workflow_id.return_value = "test_workflow_id"
    
    url = f"{CLOUDOS_URL}/api/v1/folders/{FOLDER_ID}"
    params = {"teamId": WORKSPACE_ID}
    
    responses.add(
        responses.DELETE,
        url=url,
        status=400,
        match=[matchers.query_param_matcher(params)]
    )
    
    job = Job(
        apikey=APIKEY,
        cloudos_url=CLOUDOS_URL,
        workspace_id=WORKSPACE_ID,
        cromwell_token=None,
        project_name="test_project",
        workflow_name="test_workflow"
    )
    
    with pytest.raises(ValueError) as exc_info:
        job.delete_job_results(FOLDER_ID)
    
    assert "Operation not permitted" in str(exc_info.value)
    assert "Workspace does not allow deleting results folders" in str(exc_info.value)


@mock.patch('cloudos_cli.jobs.job.Job.project_id', new_callable=mock.PropertyMock)
@mock.patch('cloudos_cli.jobs.job.Job.workflow_id', new_callable=mock.PropertyMock)
@responses.activate
def test_delete_job_results_server_error_500(mock_workflow_id, mock_project_id):
    """
    Test deletion with internal server error (500)
    """
    mock_project_id.return_value = "test_project_id"
    mock_workflow_id.return_value = "test_workflow_id"
    
    url = f"{CLOUDOS_URL}/api/v1/folders/{FOLDER_ID}"
    params = {"teamId": WORKSPACE_ID}
    
    responses.add(
        responses.DELETE,
        url=url,
        status=500,
        match=[matchers.query_param_matcher(params)]
    )
    
    job = Job(
        apikey=APIKEY,
        cloudos_url=CLOUDOS_URL,
        workspace_id=WORKSPACE_ID,
        cromwell_token=None,
        project_name="test_project",
        workflow_name="test_workflow"
    )
    
    # The retry mechanism will exhaust retries on 500 errors
    with pytest.raises(Exception) as exc_info:
        job.delete_job_results(FOLDER_ID)
    
    # Should raise either RetryError or the underlying ValueError after retries
    assert "Max retries exceeded" in str(exc_info.value) or "Internal server error" in str(exc_info.value)

"""Pytest added for function get_job_workdir"""
import json
import mock
import pytest
import requests
import responses
from cloudos_cli.clos import Cloudos
from cloudos_cli.utils.errors import BadRequestException, NotAuthorisedException
from tests.functions_for_pytest import load_json_file

APIKEY = 'vnoiweur89u2ongs'
CLOUDOS_URL = 'http://cloudos.lifebit.ai'
JOB_ID = "616ee9681b866a01d69fa1cd"
WORKSPACE_ID = "5c6d3e9bd954e800b23f8c62"
WORKDIR_ID = "workdir123"


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
def test_get_job_workdir_aws_correct_response():
    """
    Test 'get_job_workdir' to work as intended for AWS S3 storage
    API request is mocked and replicated with json files
    """
    # Mock job details response
    job_response = {
        "_id": JOB_ID,
        "team": WORKSPACE_ID,
        "resumeWorkDir": WORKDIR_ID,
        "status": "completed",
        "logs": {
            "s3BucketName": "my-bucket",
            "s3Prefix": "jobs/logs/path"
        }
    }
    
    header = {
        "Content-type": "application/json",
        "apikey": APIKEY
    }
    
    # Mock GET method for job details
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/jobs/{JOB_ID}",
        json=job_response,
        headers=header,
        status=200
    )
    
    # Mock cloud detection requests (for AWS, we don't need the azure endpoint)
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/cloud/azure",
        json=None,
        status=404
    )
    
    # start cloudOS service
    clos = Cloudos(apikey=APIKEY, cromwell_token=None, cloudos_url=CLOUDOS_URL)
    
    # get workdir path
    workdir_path = clos.get_job_workdir(JOB_ID, WORKSPACE_ID)
    
    # check the response (workdir path should replace /logs with /work)
    expected_path = "s3://my-bucket/jobs/work/path"
    assert workdir_path == expected_path


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
def test_get_job_workdir_azure_correct_response():
    """
    Test 'get_job_workdir' to work as intended for Azure Blob storage
    """
    # Mock job details response
    job_response = {
        "_id": JOB_ID,
        "team": WORKSPACE_ID,
        "resumeWorkDir": WORKDIR_ID,
        "status": "completed",
        "logs": {
            "blobStorageAccountName": WORKSPACE_ID,
            "blobContainerName": "my-container",
            "blobPrefix": "jobs/logs/path"
        }
    }
    
    header = {
        "Content-type": "application/json",
        "apikey": APIKEY
    }
    
    # Mock GET method for job details
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/jobs/{JOB_ID}",
        json=job_response,
        headers=header,
        status=200
    )
    
    # Mock Azure cloud detection request
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/cloud/azure",
        json={"storage": {"storageAccount": "testaccount"}},
        status=200
    )
    
    # start cloudOS service
    clos = Cloudos(apikey=APIKEY, cromwell_token=None, cloudos_url=CLOUDOS_URL)
    
    # get workdir path
    workdir_path = clos.get_job_workdir(JOB_ID, WORKSPACE_ID)
    
    # check the response (workdir path should replace /logs with /work)
    expected_path = f"az://testaccount.blob.core.windows.net/my-container/jobs/work/path"
    assert workdir_path == expected_path


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
def test_get_job_workdir_workspace_mismatch():
    """
    Test 'get_job_workdir' to fail when workspace doesn't match
    """
    # Mock job details response with different workspace
    job_response = {
        "_id": JOB_ID,
        "team": "different_workspace_id",
        "resumeWorkDir": WORKDIR_ID,
        "status": "completed"
    }
    
    header = {
        "Content-type": "application/json",
        "apikey": APIKEY
    }
    
    # Mock GET method for job details
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/jobs/{JOB_ID}",
        json=job_response,
        headers=header,
        status=200
    )
    
    # start cloudOS service
    clos = Cloudos(apikey=APIKEY, cromwell_token=None, cloudos_url=CLOUDOS_URL)
    
    # Test that it raises ValueError for workspace mismatch
    with pytest.raises(ValueError) as error:
        clos.get_job_workdir(JOB_ID, WORKSPACE_ID)
    
    assert "Workspace provided or configured is different from workspace where the job was executed" in str(error.value)


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
def test_get_job_workdir_job_not_found():
    """
    Test 'get_job_workdir' to fail with '404' response when job is not found
    """
    # prepare error message
    error_message = {"statusCode": 404, "code": "NotFound",
                     "message": "Job not found.", "time": "2022-11-23_17:31:07"}
    
    header = {
        "Content-type": "application/json",
        "apikey": APIKEY
    }
    
    # mock GET method with error response
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/jobs/{JOB_ID}",
        json=error_message,
        headers=header,
        status=404
    )
    
    # Test that it raises BadRequestException
    with pytest.raises(BadRequestException):
        clos = Cloudos(apikey=APIKEY, cromwell_token=None, cloudos_url=CLOUDOS_URL)
        clos.get_job_workdir(JOB_ID, WORKSPACE_ID)


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
def test_get_job_workdir_unauthorized():
    """
    Test 'get_job_workdir' to fail with '401' response for unauthorized access
    """
    header = {
        "Content-type": "application/json",
        "apikey": APIKEY
    }
    
    # mock GET method with 401 response
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/jobs/{JOB_ID}?teamId={WORKSPACE_ID}",
        json={"message": "Unauthorized"},
        headers=header,
        status=401
    )
    
    # Test that it raises NotAuthorisedException
    with pytest.raises(NotAuthorisedException):
        clos = Cloudos(apikey=APIKEY, cromwell_token=None, cloudos_url=CLOUDOS_URL)
        clos.get_job_workdir(JOB_ID, WORKSPACE_ID)


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
def test_get_job_workdir_unsupported_cloud():
    """
    Test 'get_job_workdir' to fail with unsupported cloud provider
    """
    # Mock job details response without logs (so it falls back to folder approach)
    job_response = {
        "_id": JOB_ID,
        "team": WORKSPACE_ID,
        "resumeWorkDir": WORKDIR_ID,
        "status": "completed"
    }
    
    # Mock folder details response with unsupported folderType
    folder_response = [{
        "folderType": "UnsupportedFolder",
        "someOtherField": "value"
    }]
    
    header = {
        "Content-type": "application/json",
        "apikey": APIKEY
    }
    
    # Mock GET method for job details
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/jobs/{JOB_ID}",
        json=job_response,
        headers=header,
        status=200
    )
    
    # Mock GET method for folder details
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/folders",
        json=folder_response,
        headers=header,
        status=200
    )
    
    # start cloudOS service
    clos = Cloudos(apikey=APIKEY, cromwell_token=None, cloudos_url=CLOUDOS_URL)
    
    # Test that it raises ValueError for unsupported cloud provider
    with pytest.raises(ValueError) as error:
        clos.get_job_workdir(JOB_ID, WORKSPACE_ID)
    
    assert "Unsupported cloud provider" in str(error.value)

"""Pytest for workdir deletion status functionality"""
import json
import mock
import pytest
import responses
from cloudos_cli.clos import Cloudos

APIKEY = 'test_api_key_12345'
CLOUDOS_URL = 'https://cloudos.lifebit.ai'
JOB_ID = "6912036aa6ed001148c96018"
WORKSPACE_ID = "5c6d3e9bd954e800b23f8c62"
WORKDIR_FOLDER_ID = "6912036dbe4f417054dadf34"


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
def test_get_workdir_deletion_status_ready():
    """
    Test get_workdir_deletion_status with ready (available) status
    """
    # Mock job details response with workDirectory field
    job_response = {
        "_id": JOB_ID,
        "name": "test_job",
        "team": WORKSPACE_ID,
        "status": "completed",
        "workDirectory": {
            "folderId": WORKDIR_FOLDER_ID,
        }
    }
    
    # Mock folder details response with ready status
    folder_response = [{
        "_id": WORKDIR_FOLDER_ID,
        "name": f"test_job-{JOB_ID}",
        "status": "ready",
        "folderType": "S3Folder",
        "createdAt": "2024-11-10T15:24:20.528Z",
        "updatedAt": "2024-11-10T15:24:20.528Z",
        "user": {
            "id": "user123",
            "name": "Test",
            "surname": "User",
            "email": "test@example.com"
        }
    }]
    
    header = {
        "Content-type": "application/json",
        "apikey": APIKEY
    }
    
    # Mock GET method for job details
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/jobs/{JOB_ID}?teamId={WORKSPACE_ID}",
        json=job_response,
        headers=header,
        status=200
    )
    
    # Mock GET method for folder details with status filters
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/folders/",
        json=folder_response,
        headers=header,
        status=200
    )
    
    # Create Cloudos instance and call method
    clos = Cloudos(apikey=APIKEY, cromwell_token=None, cloudos_url=CLOUDOS_URL)
    result = clos.get_workdir_deletion_status(JOB_ID, WORKSPACE_ID)
    
    # Assertions
    assert result["job_id"] == JOB_ID
    assert result["job_name"] == "test_job"
    assert result["workdir_folder_id"] == WORKDIR_FOLDER_ID
    assert result["status"] == "ready"
    assert result["items"]["name"] == f"test_job-{JOB_ID}"


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
def test_get_workdir_deletion_status_scheduled_for_deletion():
    """
    Test get_workdir_deletion_status with scheduledForDeletion status
    """
    # Mock job details response with workDirectory and deletedBy
    job_response = {
        "_id": JOB_ID,
        "name": "test_job_scheduled",
        "team": WORKSPACE_ID,
        "status": "aborted",
        "workDirectory": {
            "folderId": WORKDIR_FOLDER_ID,
            "deletedBy": {
                "id": "user123",
                "name": "Test",
                "surname": "User",
                "email": "test@example.com"
            }
        }
    }
    
    # Mock folder details response with scheduledForDeletion status
    folder_response = [{
        "_id": WORKDIR_FOLDER_ID,
        "name": f"test_job_scheduled-{JOB_ID}",
        "status": "scheduledForDeletion",
        "folderType": "S3Folder",
        "createdAt": "2024-11-10T15:24:20.528Z",
        "updatedAt": "2024-11-12T13:13:17.540Z",
        "user": {
            "id": "user123",
            "name": "Test",
            "surname": "User",
            "email": "test@example.com"
        }
    }]
    
    header = {
        "Content-type": "application/json",
        "apikey": APIKEY
    }
    
    # Mock GET method for job details
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/jobs/{JOB_ID}?teamId={WORKSPACE_ID}",
        json=job_response,
        headers=header,
        status=200
    )
    
    # Mock GET method for folder details
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/folders/",
        json=folder_response,
        headers=header,
        status=200
    )
    
    # Create Cloudos instance and call method
    clos = Cloudos(apikey=APIKEY, cromwell_token=None, cloudos_url=CLOUDOS_URL)
    result = clos.get_workdir_deletion_status(JOB_ID, WORKSPACE_ID)
    
    # Assertions
    assert result["job_id"] == JOB_ID
    assert result["job_name"] == "test_job_scheduled"
    assert result["workdir_folder_id"] == WORKDIR_FOLDER_ID
    assert result["status"] == "scheduledForDeletion"
    assert "deletedBy" in result["items"]
    assert result["items"]["deletedBy"]["email"] == "test@example.com"


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
def test_get_workdir_deletion_status_deleting():
    """
    Test get_workdir_deletion_status with deleting status
    """
    # Mock job details response
    job_response = {
        "_id": JOB_ID,
        "name": "test_job_deleting",
        "team": WORKSPACE_ID,
        "status": "completed",
        "workDirectory": {
            "folderId": WORKDIR_FOLDER_ID,
            "deletedBy": {
                "id": "user123",
                "name": "Test",
                "surname": "User",
                "email": "test@example.com"
            }
        }
    }
    
    # Mock folder details response with deleting status
    folder_response = [{
        "_id": WORKDIR_FOLDER_ID,
        "name": f"test_job_deleting-{JOB_ID}",
        "status": "deleting",
        "folderType": "S3Folder",
        "createdAt": "2024-11-10T15:24:20.528Z",
        "updatedAt": "2024-11-12T14:00:00.000Z"
    }]
    
    header = {
        "Content-type": "application/json",
        "apikey": APIKEY
    }
    
    # Mock GET methods
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/jobs/{JOB_ID}?teamId={WORKSPACE_ID}",
        json=job_response,
        headers=header,
        status=200
    )
    
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/folders/",
        json=folder_response,
        headers=header,
        status=200
    )
    
    # Create Cloudos instance and call method
    clos = Cloudos(apikey=APIKEY, cromwell_token=None, cloudos_url=CLOUDOS_URL)
    result = clos.get_workdir_deletion_status(JOB_ID, WORKSPACE_ID)
    
    # Assertions
    assert result["job_id"] == JOB_ID
    assert result["status"] == "deleting"


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
def test_get_workdir_deletion_status_deleted():
    """
    Test get_workdir_deletion_status with deleted status
    """
    # Mock job details response
    job_response = {
        "_id": JOB_ID,
        "name": "test_job_deleted",
        "team": WORKSPACE_ID,
        "status": "completed",
        "workDirectory": {
            "folderId": WORKDIR_FOLDER_ID,
            "deletedBy": {
                "id": "user123",
                "name": "Test",
                "surname": "User",
                "email": "test@example.com"
            }
        }
    }
    
    # Mock folder details response with deleted status
    folder_response = [{
        "_id": WORKDIR_FOLDER_ID,
        "name": f"test_job_deleted-{JOB_ID}",
        "status": "deleted",
        "folderType": "S3Folder",
        "createdAt": "2024-11-10T15:24:20.528Z",
        "updatedAt": "2024-11-12T15:00:00.000Z"
    }]
    
    header = {
        "Content-type": "application/json",
        "apikey": APIKEY
    }
    
    # Mock GET methods
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/jobs/{JOB_ID}?teamId={WORKSPACE_ID}",
        json=job_response,
        headers=header,
        status=200
    )
    
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/folders/",
        json=folder_response,
        headers=header,
        status=200
    )
    
    # Create Cloudos instance and call method
    clos = Cloudos(apikey=APIKEY, cromwell_token=None, cloudos_url=CLOUDOS_URL)
    result = clos.get_workdir_deletion_status(JOB_ID, WORKSPACE_ID)
    
    # Assertions
    assert result["job_id"] == JOB_ID
    assert result["status"] == "deleted"


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
def test_get_workdir_deletion_status_failed_to_delete():
    """
    Test get_workdir_deletion_status with failedToDelete status
    """
    # Mock job details response
    job_response = {
        "_id": JOB_ID,
        "name": "test_job_failed",
        "team": WORKSPACE_ID,
        "status": "completed",
        "workDirectory": {
            "folderId": WORKDIR_FOLDER_ID,
            "deletedBy": {
                "id": "user123",
                "name": "Test",
                "surname": "User",
                "email": "test@example.com"
            }
        }
    }
    
    # Mock folder details response with failedToDelete status
    folder_response = [{
        "_id": WORKDIR_FOLDER_ID,
        "name": f"test_job_failed-{JOB_ID}",
        "status": "failedToDelete",
        "folderType": "S3Folder",
        "createdAt": "2024-11-10T15:24:20.528Z",
        "updatedAt": "2024-11-12T16:00:00.000Z"
    }]
    
    header = {
        "Content-type": "application/json",
        "apikey": APIKEY
    }
    
    # Mock GET methods
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/jobs/{JOB_ID}?teamId={WORKSPACE_ID}",
        json=job_response,
        headers=header,
        status=200
    )
    
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/folders/",
        json=folder_response,
        headers=header,
        status=200
    )
    
    # Create Cloudos instance and call method
    clos = Cloudos(apikey=APIKEY, cromwell_token=None, cloudos_url=CLOUDOS_URL)
    result = clos.get_workdir_deletion_status(JOB_ID, WORKSPACE_ID)
    
    # Assertions
    assert result["job_id"] == JOB_ID
    assert result["status"] == "failedToDelete"


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
def test_get_workdir_deletion_status_legacy_resume_workdir():
    """
    Test get_workdir_deletion_status with legacy resumeWorkDir format (no workDirectory field)
    """
    # Mock job details response with only resumeWorkDir (legacy format)
    job_response = {
        "_id": JOB_ID,
        "name": "test_job_legacy",
        "team": WORKSPACE_ID,
        "status": "completed",
        "resumeWorkDir": WORKDIR_FOLDER_ID
    }
    
    # Mock folder details response
    folder_response = [{
        "_id": WORKDIR_FOLDER_ID,
        "name": f"test_job_legacy-{JOB_ID}",
        "status": "ready",
        "folderType": "S3Folder",
        "createdAt": "2024-11-10T15:24:20.528Z",
        "updatedAt": "2024-11-10T15:24:20.528Z"
    }]
    
    header = {
        "Content-type": "application/json",
        "apikey": APIKEY
    }
    
    # Mock GET methods
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/jobs/{JOB_ID}?teamId={WORKSPACE_ID}",
        json=job_response,
        headers=header,
        status=200
    )
    
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/folders/",
        json=folder_response,
        headers=header,
        status=200
    )
    
    # Create Cloudos instance and call method
    clos = Cloudos(apikey=APIKEY, cromwell_token=None, cloudos_url=CLOUDOS_URL)
    result = clos.get_workdir_deletion_status(JOB_ID, WORKSPACE_ID)
    
    # Assertions
    assert result["job_id"] == JOB_ID
    assert result["job_name"] == "test_job_legacy"
    assert result["workdir_folder_id"] == WORKDIR_FOLDER_ID
    assert result["status"] == "ready"
    # Legacy format doesn't have deletedBy
    assert "deletedBy" not in result["items"]

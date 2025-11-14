"""Pytest for results deletion status functionality"""
import json
import mock
import pytest
import responses
from cloudos_cli.clos import Cloudos

APIKEY = 'test_api_key_12345'
CLOUDOS_URL = 'https://cloudos.lifebit.ai'
JOB_ID = "6912036aa6ed001148c96018"
WORKSPACE_ID = "5c6d3e9bd954e800b23f8c62"
PROJECT_ID = "652d36b0a2b0007139a9617e"
ANALYSIS_RESULTS_FOLDER_ID = "analysis_results_folder_123"
RESULTS_FOLDER_ID = "691203a404045859383117b3"


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
def test_get_results_deletion_status_ready():
    """
    Test get_results_deletion_status with ready (available) status
    """
    # Mock job details response
    job_response = {
        "_id": JOB_ID,
        "name": "test_job_results",
        "team": WORKSPACE_ID,
        "status": "completed",
        "project": {
            "_id": PROJECT_ID,
            "name": "test_project"
        },
        "analysisResults": {
            "folderId": RESULTS_FOLDER_ID
        }
    }
    
    # Mock project content response (list of folders including Analysis Results)
    project_content_response = {
        "folders": [
            {
                "_id": "other_folder_123",
                "name": "Data"
            },
            {
                "_id": ANALYSIS_RESULTS_FOLDER_ID,
                "name": "Analyses Results"
            }
        ],
        "files": []
    }
    
    # Mock datasets API response with job results folder
    datasets_response = {
        "folders": [
            {
                "_id": RESULTS_FOLDER_ID,
                "name": f"test_job_results-{JOB_ID}",
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
            }
        ],
        "files": []
    }
    
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
    
    # Mock GET method for project content
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/datasets/{PROJECT_ID}",
        json=project_content_response,
        headers=header,
        status=200
    )
    
    # Mock GET method for datasets items (Analysis Results folder contents)
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/datasets/{ANALYSIS_RESULTS_FOLDER_ID}/items",
        json=datasets_response,
        headers=header,
        status=200
    )
    
    # Create Cloudos instance and call method
    clos = Cloudos(apikey=APIKEY, cromwell_token=None, cloudos_url=CLOUDOS_URL)
    result = clos.get_results_deletion_status(JOB_ID, WORKSPACE_ID)
    
    # Assertions
    assert result["job_id"] == JOB_ID
    assert result["job_name"] == "test_job_results"
    assert result["results_folder_id"] == RESULTS_FOLDER_ID
    assert result["status"] == "ready"
    assert result["items"]["name"] == f"test_job_results-{JOB_ID}"


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
def test_get_results_deletion_status_scheduled_for_deletion():
    """
    Test get_results_deletion_status with scheduledForDeletion status and deletedBy info
    """
    # Mock job details response with deletedBy in analysisResults
    job_response = {
        "_id": JOB_ID,
        "name": "test_job_scheduled",
        "team": WORKSPACE_ID,
        "status": "aborted",
        "project": {
            "_id": PROJECT_ID,
            "name": "test_project"
        },
        "analysisResults": {
            "folderId": RESULTS_FOLDER_ID,
            "deletedBy": {
                "id": "user123",
                "name": "Test",
                "surname": "User",
                "email": "test@example.com"
            }
        }
    }
    
    # Mock project content response
    project_content_response = {
        "folders": [
            {
                "_id": ANALYSIS_RESULTS_FOLDER_ID,
                "name": "Analyses Results"
            }
        ],
        "files": []
    }
    
    # Mock datasets API response with scheduledForDeletion status
    datasets_response = {
        "folders": [
            {
                "_id": RESULTS_FOLDER_ID,
                "name": f"test_job_scheduled-{JOB_ID}",
                "status": "scheduledForDeletion",
                "folderType": "S3Folder",
                "createdAt": "2024-11-10T15:24:20.528Z",
                "updatedAt": "2024-11-11T14:43:44.416Z",
                "user": {
                    "id": "user123",
                    "name": "Test",
                    "surname": "User",
                    "email": "test@example.com"
                }
            }
        ],
        "files": []
    }
    
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
        url=f"{CLOUDOS_URL}/api/v1/datasets/{PROJECT_ID}",
        json=project_content_response,
        headers=header,
        status=200
    )
    
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/datasets/{ANALYSIS_RESULTS_FOLDER_ID}/items",
        json=datasets_response,
        headers=header,
        status=200
    )
    
    # Create Cloudos instance and call method
    clos = Cloudos(apikey=APIKEY, cromwell_token=None, cloudos_url=CLOUDOS_URL)
    result = clos.get_results_deletion_status(JOB_ID, WORKSPACE_ID)
    
    # Assertions
    assert result["job_id"] == JOB_ID
    assert result["job_name"] == "test_job_scheduled"
    assert result["results_folder_id"] == RESULTS_FOLDER_ID
    assert result["status"] == "scheduledForDeletion"
    assert "deletedBy" in result["items"]
    assert result["items"]["deletedBy"]["email"] == "test@example.com"


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
def test_get_results_deletion_status_deleting():
    """
    Test get_results_deletion_status with deleting status
    """
    # Mock job details response
    job_response = {
        "_id": JOB_ID,
        "name": "test_job_deleting",
        "team": WORKSPACE_ID,
        "status": "completed",
        "project": {
            "_id": PROJECT_ID,
            "name": "test_project"
        },
        "analysisResults": {
            "folderId": RESULTS_FOLDER_ID,
            "deletedBy": {
                "id": "user123",
                "name": "Test",
                "surname": "User",
                "email": "test@example.com"
            }
        }
    }
    
    # Mock project content response
    project_content_response = {
        "folders": [
            {
                "_id": ANALYSIS_RESULTS_FOLDER_ID,
                "name": "Analyses Results"
            }
        ],
        "files": []
    }
    
    # Mock datasets API response with deleting status
    datasets_response = {
        "folders": [
            {
                "_id": RESULTS_FOLDER_ID,
                "name": f"test_job_deleting-{JOB_ID}",
                "status": "deleting",
                "folderType": "S3Folder",
                "createdAt": "2024-11-10T15:24:20.528Z",
                "updatedAt": "2024-11-12T14:00:00.000Z"
            }
        ],
        "files": []
    }
    
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
        url=f"{CLOUDOS_URL}/api/v1/datasets/{PROJECT_ID}",
        json=project_content_response,
        headers=header,
        status=200
    )
    
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/datasets/{ANALYSIS_RESULTS_FOLDER_ID}/items",
        json=datasets_response,
        headers=header,
        status=200
    )
    
    # Create Cloudos instance and call method
    clos = Cloudos(apikey=APIKEY, cromwell_token=None, cloudos_url=CLOUDOS_URL)
    result = clos.get_results_deletion_status(JOB_ID, WORKSPACE_ID)
    
    # Assertions
    assert result["job_id"] == JOB_ID
    assert result["status"] == "deleting"


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
def test_get_results_deletion_status_deleted():
    """
    Test get_results_deletion_status with deleted status
    """
    # Mock job details response
    job_response = {
        "_id": JOB_ID,
        "name": "test_job_deleted",
        "team": WORKSPACE_ID,
        "status": "completed",
        "project": {
            "_id": PROJECT_ID,
            "name": "test_project"
        },
        "analysisResults": {
            "folderId": RESULTS_FOLDER_ID,
            "deletedBy": {
                "id": "user123",
                "name": "Test",
                "surname": "User",
                "email": "test@example.com"
            }
        }
    }
    
    # Mock project content response
    project_content_response = {
        "folders": [
            {
                "_id": ANALYSIS_RESULTS_FOLDER_ID,
                "name": "Analyses Results"
            }
        ],
        "files": []
    }
    
    # Mock datasets API response with deleted status
    datasets_response = {
        "folders": [
            {
                "_id": RESULTS_FOLDER_ID,
                "name": f"test_job_deleted-{JOB_ID}",
                "status": "deleted",
                "folderType": "S3Folder",
                "createdAt": "2024-11-10T15:24:20.528Z",
                "updatedAt": "2024-11-12T15:00:00.000Z"
            }
        ],
        "files": []
    }
    
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
        url=f"{CLOUDOS_URL}/api/v1/datasets/{PROJECT_ID}",
        json=project_content_response,
        headers=header,
        status=200
    )
    
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/datasets/{ANALYSIS_RESULTS_FOLDER_ID}/items",
        json=datasets_response,
        headers=header,
        status=200
    )
    
    # Create Cloudos instance and call method
    clos = Cloudos(apikey=APIKEY, cromwell_token=None, cloudos_url=CLOUDOS_URL)
    result = clos.get_results_deletion_status(JOB_ID, WORKSPACE_ID)
    
    # Assertions
    assert result["job_id"] == JOB_ID
    assert result["status"] == "deleted"


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
def test_get_results_deletion_status_failed_to_delete():
    """
    Test get_results_deletion_status with failedToDelete status
    """
    # Mock job details response
    job_response = {
        "_id": JOB_ID,
        "name": "test_job_failed",
        "team": WORKSPACE_ID,
        "status": "completed",
        "project": {
            "_id": PROJECT_ID,
            "name": "test_project"
        },
        "analysisResults": {
            "folderId": RESULTS_FOLDER_ID,
            "deletedBy": {
                "id": "user123",
                "name": "Test",
                "surname": "User",
                "email": "test@example.com"
            }
        }
    }
    
    # Mock project content response
    project_content_response = {
        "folders": [
            {
                "_id": ANALYSIS_RESULTS_FOLDER_ID,
                "name": "Analyses Results"
            }
        ],
        "files": []
    }
    
    # Mock datasets API response with failedToDelete status
    datasets_response = {
        "folders": [
            {
                "_id": RESULTS_FOLDER_ID,
                "name": f"test_job_failed-{JOB_ID}",
                "status": "failedToDelete",
                "folderType": "S3Folder",
                "createdAt": "2024-11-10T15:24:20.528Z",
                "updatedAt": "2024-11-12T16:00:00.000Z"
            }
        ],
        "files": []
    }
    
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
        url=f"{CLOUDOS_URL}/api/v1/datasets/{PROJECT_ID}",
        json=project_content_response,
        headers=header,
        status=200
    )
    
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/datasets/{ANALYSIS_RESULTS_FOLDER_ID}/items",
        json=datasets_response,
        headers=header,
        status=200
    )
    
    # Create Cloudos instance and call method
    clos = Cloudos(apikey=APIKEY, cromwell_token=None, cloudos_url=CLOUDOS_URL)
    result = clos.get_results_deletion_status(JOB_ID, WORKSPACE_ID)
    
    # Assertions
    assert result["job_id"] == JOB_ID
    assert result["status"] == "failedToDelete"


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
def test_get_results_deletion_status_alternative_folder_name():
    """
    Test get_results_deletion_status with alternative 'AnalysesResults' folder name (no space)
    """
    # Mock job details response
    job_response = {
        "_id": JOB_ID,
        "name": "test_job_alt",
        "team": WORKSPACE_ID,
        "status": "completed",
        "project": {
            "_id": PROJECT_ID,
            "name": "test_project"
        },
        "analysisResults": {
            "folderId": RESULTS_FOLDER_ID
        }
    }
    
    # Mock project content response with alternative folder name
    project_content_response = {
        "folders": [
            {
                "_id": ANALYSIS_RESULTS_FOLDER_ID,
                "name": "AnalysesResults"  # No space
            }
        ],
        "files": []
    }
    
    # Mock datasets API response
    datasets_response = {
        "folders": [
            {
                "_id": RESULTS_FOLDER_ID,
                "name": f"test_job_alt-{JOB_ID}",
                "status": "ready",
                "folderType": "S3Folder",
                "createdAt": "2024-11-10T15:24:20.528Z",
                "updatedAt": "2024-11-10T15:24:20.528Z"
            }
        ],
        "files": []
    }
    
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
        url=f"{CLOUDOS_URL}/api/v1/datasets/{PROJECT_ID}",
        json=project_content_response,
        headers=header,
        status=200
    )
    
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/datasets/{ANALYSIS_RESULTS_FOLDER_ID}/items",
        json=datasets_response,
        headers=header,
        status=200
    )
    
    # Create Cloudos instance and call method
    clos = Cloudos(apikey=APIKEY, cromwell_token=None, cloudos_url=CLOUDOS_URL)
    result = clos.get_results_deletion_status(JOB_ID, WORKSPACE_ID)
    
    # Assertions
    assert result["job_id"] == JOB_ID
    assert result["job_name"] == "test_job_alt"
    assert result["results_folder_id"] == RESULTS_FOLDER_ID
    assert result["status"] == "ready"

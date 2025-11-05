import pytest
from unittest import mock
from cloudos_cli.link.link import Link
from cloudos_cli.utils.requests import retry_requests_post
import responses


"""Unit tests for the Link class - Positive test cases only."""

CLOUDOS_URL = "http://cloudos.lifebit.ai"
APIKEY = "testapikey"
WORKSPACE_ID = "workspace123"
PROJECT_NAME = "test_project"
VERIFY = True


@pytest.fixture
def link_instance():
    """Fixture to create a Link instance."""
    return Link(
        cloudos_url=CLOUDOS_URL,
        apikey=APIKEY,
        workspace_id=WORKSPACE_ID,
        project_name=PROJECT_NAME,
        cromwell_token=None,
        verify=VERIFY,
    )


@pytest.fixture
def link_instance_test_response():
    return Link(
        cloudos_url="https://lifebit.ai",
        apikey="dummy-key",
        workspace_id="team123",
        verify=False,
        project_name=PROJECT_NAME,
        cromwell_token=None,
    )


def test_parse_s3_path_valid(link_instance):
    """Test parse_s3_path with a valid S3 URL."""
    s3_url = "s3://mybucket/myfolder/mysubfolder"
    expected_result = {
        "dataItem": {
            "type": "S3Folder",
            "data": {
                "name": "mysubfolder",
                "s3BucketName": "mybucket",
                "s3Prefix": "myfolder/mysubfolder",
            },
        }
    }
    result = link_instance.parse_s3_path(s3_url)
    assert result == expected_result


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
def test_link_s3_folder_success():
    """Test link_S3_folder with a successful response."""
    s3_folder = "s3://mybucket/myfolder"
    session_id = "session123"
    headers = {
        "Content-type": "application/json",
        "apikey": APIKEY
    }
    url=f"{CLOUDOS_URL}/api/v1/interactive-sessions/{session_id}/fuse-filesystem/mount?teamId={WORKSPACE_ID}"

    expected_payload = {
        "dataItem": {
            "type": "S3Folder",
            "data": {
                "name": "mysubfolder",
                "s3BucketName": "mybucket",
                "s3Prefix": "myfolder/mysubfolder",
            },
        }
    }

    # Register mock response (simulate 204 No Content with empty body)
    responses.add(
        method=responses.POST,
        url=url,
        headers=headers,
        body='',
        match=[responses.json_params_matcher(expected_payload)],
        status=204
    )

    r = retry_requests_post(url, headers=headers, json=expected_payload, verify=True)
    assert r.status_code == 204 # Expecting a 204 No Content response


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
def test_link_file_explorer_folder_success():
    """Test linking File Explorer folder with a successful response."""
    fe_folder = "Data/Downloads"
    session_id = "session123"
    headers = {
        "Content-type": "application/json",
        "apikey": APIKEY
    }
    url=f"{CLOUDOS_URL}/api/v1/interactive-sessions/{session_id}/fuse-filesystem/mount?teamId={WORKSPACE_ID}"

    expected_payload = {
        "dataItem": {
            "kind": "Folder",
            "item": "123r758asfkasf",
            "name": "Downloads"
        }
    }

    # Register mock response (simulate 204 No Content with empty body)
    responses.add(
        method=responses.POST,
        url=url,
        headers=headers,
        body='',
        match=[responses.json_params_matcher(expected_payload)],
        status=204
    )

    r = retry_requests_post(url, headers=headers, json=expected_payload, verify=True)
    assert r.status_code == 204 # Expecting a 204 No Content response


@responses.activate
def test_link_folder_204_s3(capsys, link_instance_test_response, monkeypatch):
    """Test successful S3 folder linking and mounting."""
    url = f"https://lifebit.ai/api/v1/interactive-sessions/sessionABC/fuse-filesystem/mount?teamId=team123"
    responses.add(responses.POST, url, status=204)
    
    # Mock the GET request for checking fuse filesystem status
    status_url = f"https://lifebit.ai/api/v1/interactive-sessions/sessionABC/fuse-filesystems?teamId=team123"
    mock_response = {
        "fuseFileSystems": [
            {
                "_id": "123",
                "resource": "sessionABC",
                "storageProvider": "s3",
                "kind": "source",
                "item": "456",
                "mountPoint": "/opt/lifebit/volumes/file-systems/folder",
                "mountName": "folder",
                "readOnly": True,
                "status": "mounted",
                "errorMessage": None
            }
        ],
        "paginationMetadata": {"Pagination-Count": 1, "Pagination-Page": 1, "Pagination-Limit": 30}
    }
    responses.add(responses.GET, status_url, json=mock_response, status=200)

    # Patch `parse_s3_path` to return a mocked S3 folder structure
    monkeypatch.setattr(link_instance_test_response, "parse_s3_path", lambda x: {
        "dataItem": {
            "type": "S3Folder",
            "data": {
                "name": "folder",
                "s3BucketName": "bucket",
                "s3Prefix": "path/to/folder/"
            }
        }
    })

    link_instance_test_response.link_folder("s3://bucket/path/to/folder", "sessionABC")
    captured = capsys.readouterr()
    assert "Successfully mounted S3 folder: s3://bucket/path/to/folder/" in captured.out


@responses.activate
def test_link_folder_204_file_explorer(capsys, link_instance_test_response, monkeypatch):
    """Test successful File Explorer folder linking and mounting."""
    url = f"https://lifebit.ai/api/v1/interactive-sessions/sessionABC/fuse-filesystem/mount?teamId=team123"
    responses.add(responses.POST, url, status=204)
    
    # Mock the GET request for checking fuse filesystem status
    status_url = f"https://lifebit.ai/api/v1/interactive-sessions/sessionABC/fuse-filesystems?teamId=team123"
    mock_response = {
        "fuseFileSystems": [
            {
                "_id": "123",
                "resource": "sessionABC",
                "storageProvider": "file",
                "kind": "source",
                "item": "456",
                "mountPoint": "/opt/lifebit/volumes/file-systems/data",
                "mountName": "data",
                "readOnly": False,
                "status": "mounted",
                "errorMessage": None
            }
        ],
        "paginationMetadata": {"Pagination-Count": 1, "Pagination-Page": 1, "Pagination-Limit": 30}
    }
    responses.add(responses.GET, status_url, json=mock_response, status=200)

    monkeypatch.setattr(link_instance_test_response, "parse_file_explorer_path", lambda x: {
        "dataItem": {
            "kind": "Folder",
            "item": "456",
            "name": "data"
        }
    })

    link_instance_test_response.link_folder("/home/user/data", "sessionABC")
    captured = capsys.readouterr()
    assert "Successfully mounted File Explorer folder: /home/user/data" in captured.out


@responses.activate 
def test_get_fuse_filesystems_status_success(link_instance_test_response):
    """Test successful retrieval of fuse filesystem status."""
    status_url = f"https://lifebit.ai/api/v1/interactive-sessions/sessionABC/fuse-filesystems?teamId=team123"
    mock_response = {
        "fuseFileSystems": [
            {
                "_id": "123",
                "resource": "sessionABC",
                "storageProvider": "s3",
                "mountName": "test-mount",
                "status": "mounted"
            }
        ]
    }
    responses.add(responses.GET, status_url, json=mock_response, status=200)
    
    result = link_instance_test_response.get_fuse_filesystems_status("sessionABC")
    assert len(result) == 1
    assert result[0]["mountName"] == "test-mount"
    assert result[0]["status"] == "mounted"


@responses.activate
def test_list_mounted_filesystems(capsys, link_instance_test_response):
    """Test listing mounted filesystems."""
    status_url = f"https://lifebit.ai/api/v1/interactive-sessions/sessionABC/fuse-filesystems?teamId=team123"
    mock_response = {
        "fuseFileSystems": [
            {
                "_id": "123",
                "resource": "sessionABC",
                "storageProvider": "s3",
                "mountName": "mounted-folder",
                "mountPoint": "/opt/lifebit/volumes/file-systems/mounted-folder",
                "status": "mounted",
                "readOnly": True,
                "errorMessage": None
            },
            {
                "_id": "456", 
                "resource": "sessionABC",
                "storageProvider": "s3",
                "mountName": "another-mounted-folder",
                "mountPoint": "/opt/lifebit/volumes/file-systems/another-mounted-folder",
                "status": "mounted",
                "readOnly": False,
                "errorMessage": None
            }
        ]
    }
    responses.add(responses.GET, status_url, json=mock_response, status=200)
    
    link_instance_test_response.list_mounted_filesystems("sessionABC")
    captured = capsys.readouterr()
    
    assert "Filesystem status for session sessionABC:" in captured.out
    assert "mounted-folder [s3] - MOUNTED (read-only)" in captured.out
    assert "another-mounted-folder [s3] - MOUNTED" in captured.out
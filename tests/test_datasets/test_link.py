import pytest
from unittest import mock
from cloudos_cli.link.link import Link
from cloudos_cli.utils.requests import retry_requests_post
import responses


"""Unit tests for the Link class."""

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
    # Mock v2 endpoint to return 404 (testing fallback to v1)
    url_v2 = f"https://lifebit.ai/api/v2/interactive-sessions/sessionABC/fuse-filesystem/mount?teamId=team123"
    responses.add(responses.POST, url_v2, status=404, json={"message": "Not Found"})
    
    # Mock v1 endpoint
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
    # Mock v2 endpoint to return 404 (testing fallback to v1)
    url_v2 = f"https://lifebit.ai/api/v2/interactive-sessions/sessionABC/fuse-filesystem/mount?teamId=team123"
    responses.add(responses.POST, url_v2, status=404, json={"message": "Not Found"})
    
    # Mock v1 endpoint
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
def test_link_folder_v2_success_s3(capsys, link_instance_test_response, monkeypatch):
    """Test successful S3 folder linking using API v2."""
    # Mock v2 endpoint
    url_v2 = f"https://lifebit.ai/api/v2/interactive-sessions/sessionABC/fuse-filesystem/mount?teamId=team123"
    responses.add(responses.POST, url_v2, status=204)

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
    # Should not show fallback message
    assert "Using API v1" not in captured.out


@responses.activate
def test_link_folder_v2_fallback_to_v1(capsys, link_instance_test_response, monkeypatch):
    """Test fallback from API v2 to v1 when v2 is not available."""
    # Mock v2 endpoint to return 404 (not found)
    url_v2 = f"https://lifebit.ai/api/v2/interactive-sessions/sessionABC/fuse-filesystem/mount?teamId=team123"
    responses.add(responses.POST, url_v2, status=404, json={"message": "Not Found"})

    # Mock v1 endpoint to succeed
    url_v1 = f"https://lifebit.ai/api/v1/interactive-sessions/sessionABC/fuse-filesystem/mount?teamId=team123"
    responses.add(responses.POST, url_v1, status=204)

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
    # Fallback to v1 happens silently (no message shown to user)


@responses.activate
def test_link_folder_v2_file_explorer(capsys, link_instance_test_response, monkeypatch):
    """Test successful File Explorer folder linking using API v2."""
    # Mock v2 endpoint
    url_v2 = f"https://lifebit.ai/api/v2/interactive-sessions/sessionABC/fuse-filesystem/mount?teamId=team123"
    responses.add(responses.POST, url_v2, status=204)

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
def test_link_folders_batch_multiple_s3(capsys, link_instance_test_response, monkeypatch):
    """Test linking multiple S3 folders in one batch request using v2 API."""
    # Mock v2 endpoint for batch request
    url_v2 = f"https://lifebit.ai/api/v2/interactive-sessions/sessionABC/fuse-filesystem/mount?teamId=team123"
    responses.add(responses.POST, url_v2, status=204)

    # Mock the GET request for checking fuse filesystem status for each folder
    status_url = f"https://lifebit.ai/api/v1/interactive-sessions/sessionABC/fuse-filesystems?teamId=team123"
    
    # First call - returns folder1
    mock_response_1 = {
        "fuseFileSystems": [{
            "_id": "123",
            "mountName": "folder1",
            "status": "mounted"
        }],
        "paginationMetadata": {"Pagination-Count": 1}
    }
    responses.add(responses.GET, status_url, json=mock_response_1, status=200)
    
    # Second call - returns folder2
    mock_response_2 = {
        "fuseFileSystems": [{
            "_id": "124",
            "mountName": "folder2",
            "status": "mounted"
        }],
        "paginationMetadata": {"Pagination-Count": 1}
    }
    responses.add(responses.GET, status_url, json=mock_response_2, status=200)
    
    # Third call - returns folder3
    mock_response_3 = {
        "fuseFileSystems": [{
            "_id": "125",
            "mountName": "folder3",
            "status": "mounted"
        }],
        "paginationMetadata": {"Pagination-Count": 1}
    }
    responses.add(responses.GET, status_url, json=mock_response_3, status=200)

    # Patch parse_s3_path
    def mock_parse_s3_path(url):
        if "folder1" in url:
            return {"dataItem": {"type": "S3Folder", "data": {"name": "folder1", "s3BucketName": "bucket1", "s3Prefix": "path1/folder1/"}}}
        elif "folder2" in url:
            return {"dataItem": {"type": "S3Folder", "data": {"name": "folder2", "s3BucketName": "bucket2", "s3Prefix": "path2/folder2/"}}}
        else:
            return {"dataItem": {"type": "S3Folder", "data": {"name": "folder3", "s3BucketName": "bucket3", "s3Prefix": "path3/folder3/"}}}
    
    monkeypatch.setattr(link_instance_test_response, "parse_s3_path", mock_parse_s3_path)

    # Test batch linking
    folders = [
        "s3://bucket1/path1/folder1/",
        "s3://bucket2/path2/folder2/",
        "s3://bucket3/path3/folder3/"
    ]
    link_instance_test_response.link_folders_batch(folders, "sessionABC")
    
    captured = capsys.readouterr()
    assert "Successfully mounted S3 folder: s3://bucket1/path1/folder1/" in captured.out
    assert "Successfully mounted S3 folder: s3://bucket2/path2/folder2/" in captured.out
    assert "Successfully mounted S3 folder: s3://bucket3/path3/folder3/" in captured.out


@responses.activate
def test_link_folders_batch_v2_fallback_to_v1_multiple(capsys, link_instance_test_response, monkeypatch):
    """Test fallback to v1 API when linking multiple folders."""
    # Mock v2 endpoint to return 404
    url_v2 = f"https://lifebit.ai/api/v2/interactive-sessions/sessionABC/fuse-filesystem/mount?teamId=team123"
    responses.add(responses.POST, url_v2, status=404, json={"message": "Not Found"})

    # Mock v1 endpoint for each folder (3 separate requests in fallback)
    url_v1 = f"https://lifebit.ai/api/v1/interactive-sessions/sessionABC/fuse-filesystem/mount?teamId=team123"
    responses.add(responses.POST, url_v1, status=204)  # folder1
    responses.add(responses.POST, url_v1, status=204)  # folder2
    responses.add(responses.POST, url_v1, status=204)  # folder3

    # Mock status checks
    status_url = f"https://lifebit.ai/api/v1/interactive-sessions/sessionABC/fuse-filesystems?teamId=team123"
    responses.add(responses.GET, status_url, json={"fuseFileSystems": [{"_id": "1", "mountName": "folder1", "status": "mounted"}]}, status=200)
    responses.add(responses.GET, status_url, json={"fuseFileSystems": [{"_id": "2", "mountName": "folder2", "status": "mounted"}]}, status=200)
    responses.add(responses.GET, status_url, json={"fuseFileSystems": [{"_id": "3", "mountName": "folder3", "status": "mounted"}]}, status=200)

    def mock_parse_s3_path(url):
        if "folder1" in url:
            return {"dataItem": {"type": "S3Folder", "data": {"name": "folder1", "s3BucketName": "bucket1", "s3Prefix": "path1/folder1/"}}}
        elif "folder2" in url:
            return {"dataItem": {"type": "S3Folder", "data": {"name": "folder2", "s3BucketName": "bucket2", "s3Prefix": "path2/folder2/"}}}
        else:
            return {"dataItem": {"type": "S3Folder", "data": {"name": "folder3", "s3BucketName": "bucket3", "s3Prefix": "path3/folder3/"}}}
    
    monkeypatch.setattr(link_instance_test_response, "parse_s3_path", mock_parse_s3_path)

    folders = [
        "s3://bucket1/path1/folder1/",
        "s3://bucket2/path2/folder2/",
        "s3://bucket3/path3/folder3/"
    ]
    link_instance_test_response.link_folders_batch(folders, "sessionABC")
    
    captured = capsys.readouterr()
    # All three should succeed via v1 fallback
    assert "Successfully mounted S3 folder: s3://bucket1/path1/folder1/" in captured.out
    assert "Successfully mounted S3 folder: s3://bucket2/path2/folder2/" in captured.out
    assert "Successfully mounted S3 folder: s3://bucket3/path3/folder3/" in captured.out


@responses.activate  
def test_link_folders_batch_partial_failure_v1_fallback(capsys, link_instance_test_response, monkeypatch):
    """Test error handling when one folder fails during v1 fallback."""
    # Mock v2 endpoint to return 404 (forcing v1 fallback)
    url_v2 = f"https://lifebit.ai/api/v2/interactive-sessions/sessionABC/fuse-filesystem/mount?teamId=team123"
    responses.add(responses.POST, url_v2, status=404, json={"message": "Not Found"})

    # Mock v1 endpoint - first succeeds, second fails with 403
    url_v1 = f"https://lifebit.ai/api/v1/interactive-sessions/sessionABC/fuse-filesystem/mount?teamId=team123"
    responses.add(responses.POST, url_v1, status=204)  # folder1 succeeds
    responses.add(responses.POST, url_v1, status=403, json={"message": "Folder already mounted"})  # folder2 fails

    # Mock status check for successful folder1
    status_url = f"https://lifebit.ai/api/v1/interactive-sessions/sessionABC/fuse-filesystems?teamId=team123"
    responses.add(responses.GET, status_url, json={"fuseFileSystems": [{"_id": "1", "mountName": "folder1", "status": "mounted"}]}, status=200)

    def mock_parse_s3_path(url):
        if "folder1" in url:
            return {"dataItem": {"type": "S3Folder", "data": {"name": "folder1", "s3BucketName": "bucket1", "s3Prefix": "path1/folder1/"}}}
        else:
            return {"dataItem": {"type": "S3Folder", "data": {"name": "folder2", "s3BucketName": "bucket2", "s3Prefix": "path2/folder2/"}}}
    
    monkeypatch.setattr(link_instance_test_response, "parse_s3_path", mock_parse_s3_path)

    folders = [
        "s3://bucket1/path1/folder1/",
        "s3://bucket2/path2/folder2/"
    ]
    
    # Should raise ValueError for the second folder
    with pytest.raises(ValueError, match="already exists with 'mounted' status"):
        link_instance_test_response.link_folders_batch(folders, "sessionABC")

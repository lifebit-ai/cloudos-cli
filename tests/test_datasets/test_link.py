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


def test_parse_s3_path_invalid_prefix(link_instance):
    """Test parse_s3_path with an invalid S3 URL prefix."""
    s3_url = "http://mybucket/myfolder/mysubfolder"
    with pytest.raises(ValueError, match="Invalid S3 URL. Link must start with 's3://'"):
        link_instance.parse_s3_path(s3_url)


def test_parse_s3_path_missing_key(link_instance):
    """Test parse_s3_path with an S3 URL missing a key after the bucket."""
    s3_url = "s3://mybucket/"
    with pytest.raises(ValueError, match="S3 URL must include a key after the bucket"):
        link_instance.parse_s3_path(s3_url)


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

    # Register mock response (simulate 200 OK with optional empty JSON body)
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

    # Register mock response (simulate 200 OK with optional empty JSON body)
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

@responses.activate
def test_link_folder_403(link_instance_test_response):
    url = f"https://lifebit.ai/api/v1/interactive-sessions/sessionABC/fuse-filesystem/mount?teamId=team123"
    responses.add(responses.POST, url, status=403)
    
    with pytest.raises(ValueError, match="already exists"):
        link_instance_test_response.link_folder("s3://bucket/path", "sessionABC")


@responses.activate
def test_link_folder_401(link_instance_test_response):
    url = f"https://lifebit.ai/api/v1/interactive-sessions/sessionABC/fuse-filesystem/mount?teamId=team123"
    responses.add(responses.POST, url, status=401)

    with pytest.raises(ValueError, match="Invalid API key"):
        link_instance_test_response.link_folder("s3://bucket/path", "sessionABC")


@responses.activate
def test_link_folder_400_ia_inactive(link_instance_test_response):
    url = f"https://lifebit.ai/api/v1/interactive-sessions/sessionABC/fuse-filesystem/mount?teamId=team123"
    responses.add(responses.POST, url, status=400, json={"message": "Request failed with status code 403"})

    with pytest.raises(ValueError, match="Interactive Analysis session is not active"):
        link_instance_test_response.link_folder("s3://bucket/path", "sessionABC")


@responses.activate
def test_link_folder_400_invalid_dataitem(link_instance_test_response):
    url = f"https://lifebit.ai/api/v1/interactive-sessions/sessionABC/fuse-filesystem/mount?teamId=team123"
    responses.add(responses.POST, url, status=400, json={"message": "Invalid Supported DataItem folderType. Supported values are S3Folder"})

    with pytest.raises(ValueError, match="Invalid Supported DataItem"):
        link_instance_test_response.link_folder("s3://bucket/path", "sessionABC")


@responses.activate
def test_link_folder_400_cannot_link(link_instance_test_response):
    url = f"https://lifebit.ai/api/v1/interactive-sessions/sessionABC/fuse-filesystem/mount?teamId=team123"
    responses.add(responses.POST, url, status=400, json={"message": "Some other error"})

    with pytest.raises(ValueError, match="Cannot link folder"):
        link_instance_test_response.link_folder("s3://bucket/path", "sessionABC")


@responses.activate
def test_link_folder_204_s3(capsys, link_instance_test_response, monkeypatch):
    url = f"https://lifebit.ai/api/v1/interactive-sessions/sessionABC/fuse-filesystem/mount?teamId=team123"
    responses.add(responses.POST, url, status=204)

    # Patch `parse_s3_path` to return a mocked S3 folder structure
    monkeypatch.setattr(link_instance_test_response, "parse_s3_path", lambda x: {
        "dataItem": {
            "type": "S3Folder",
            "data": {
                "s3BucketName": "bucket",
                "s3Prefix": "path/to/folder/"
            }
        }
    })

    link_instance_test_response.link_folder("s3://bucket/path/to/folder", "sessionABC")
    captured = capsys.readouterr()
    assert "Succesfully linked S3 folder: s3://bucket/path/to/folder/" in captured.out


@responses.activate
def test_link_folder_204_file_explorer(capsys, link_instance_test_response, monkeypatch):
    url = f"https://lifebit.ai/api/v1/interactive-sessions/sessionABC/fuse-filesystem/mount?teamId=team123"
    responses.add(responses.POST, url, status=204)

    monkeypatch.setattr(link_instance_test_response, "parse_file_explorer_path", lambda x: {"dummy": "data"})

    link_instance_test_response.link_folder("/home/user/data", "sessionABC")
    captured = capsys.readouterr()
    assert "Succesfully linked File Explorer folder: /home/user/data" in captured.out
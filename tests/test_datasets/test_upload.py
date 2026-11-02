import base64
import json
import os
import re
import stat
from unittest import mock

import pytest
import requests
import responses
from click.testing import CliRunner
from responses import matchers

from cloudos_cli.datasets import Datasets
from cloudos_cli.__main__ import run_cloudos_cli
from cloudos_cli.datasets.s3_multipart_upload import (
    MAX_OBJECT_SIZE,
    S3UploadError,
    SignedS3MultipartUploader,
    TransferError,
    compute_part_size,
    s3_uri_encode,
)
from tests.functions_for_pytest import load_json_file

APIKEY = 'vnoiweur89u2ongs'
CLOUDOS_URL = 'http://cloudos.lifebit.ai'
WORKSPACE_ID = 'lv89ufc838sdig'
PROJECT_NAME = "lifebit-testing"
PROJECT_ID = "1234bc123125"
DATA_ID = "mock-dataset-id-4321"
CLI_AUTH = ['-k', APIKEY, '-c', CLOUDOS_URL, '--workspace-id', WORKSPACE_ID, '--project-name', PROJECT_NAME]

AIRLOCK_URL = f"{CLOUDOS_URL}/api/v2/airlock-api/workspaces/{WORKSPACE_ID}/configuration"
SIGNER_URL = f"{CLOUDOS_URL}/api/v1/s3/signUploadForEvaporate"
S3_URL_RE = re.compile(r"^https://s3\.us-east-1\.amazonaws\.com/.*")
CLOUD_AWS = {"lifebitBucketName": "lifebit-user-data-12345678", "lifebitBucketS3Prefix": "deploit",
             "awsRegion": "us-east-1"}
TMP_CREDENTIALS = {"credentials": "opaque-encrypted-credentials-blob",
                   "sessionToken": base64.b64encode(b"test-session-token").decode(),
                   "key": base64.b64encode(b"ASIATESTKEY").decode()}


def airlock(enabled=True, import_from_computer=True):
    return {"enabled": enabled, "permissions": {"members": {
        "enableImportFromComputer": import_from_computer, "enableViewFile": True}}}


def _client():
    return Datasets(cloudos_url=CLOUDOS_URL, apikey=APIKEY, workspace_id=WORKSPACE_ID,
                    project_name=PROJECT_NAME, verify=True, project_id=PROJECT_ID, cromwell_token=None)


def _mock_s3_upload(status=200, complete_status=200, complete_body="<CompleteMultipartUploadResult/>"):
    """Mock the signer and a successful (or failing) multipart upload plus file registration."""
    responses.add(responses.GET, f"{CLOUDOS_URL}/api/v1/aws/tmp-credentials", json=TMP_CREDENTIALS)
    responses.add(responses.GET, SIGNER_URL, json={"signature": "0" * 64})
    responses.add(responses.POST, S3_URL_RE, content_type="application/xml",
                  body="<InitiateMultipartUploadResult><UploadId>u1</UploadId></InitiateMultipartUploadResult>")
    responses.add(responses.PUT, S3_URL_RE, status=status, headers={"ETag": '"etag-1"'},
                  body="<Error><Message>Signature expired</Message></Error>")
    responses.add(responses.POST, S3_URL_RE, status=complete_status, body=complete_body)
    return (responses.add(responses.DELETE, S3_URL_RE, status=204),
            responses.add(responses.POST, f"{CLOUDOS_URL}/api/v1/files/s3", json={"name": "f"}, status=201))


def _mock_cli_chain(airlock_config=None, cloud_status=200):
    """Mock project lookup, the Airlock policy, the AWS config and listing of 'Data'."""
    responses.add(responses.GET, f"{CLOUDOS_URL}/api/v2/projects",
                  json=json.loads(load_json_file("tests/test_data/projects.json")),
                  match=[matchers.query_param_matcher({"teamId": WORKSPACE_ID, "search": PROJECT_NAME})])
    responses.add(responses.GET, AIRLOCK_URL, json=airlock_config or {}, status=200 if airlock_config else 404)
    responses.add(responses.GET, f"{CLOUDOS_URL}/api/v1/cloud/aws",
                  json=CLOUD_AWS if cloud_status == 200 else None, status=cloud_status)
    responses.add(responses.GET, f"{CLOUDOS_URL}/api/v2/datasets",
                  json=json.loads(load_json_file("tests/test_data/datasets.json")),
                  match=[matchers.query_param_matcher({"projectId": PROJECT_ID, "teamId": WORKSPACE_ID})])
    content = json.loads(load_json_file("tests/test_data/dataset_source_content.json"))
    responses.add(responses.GET, f"{CLOUDOS_URL}/api/v1/datasets/{DATA_ID}/items", json=content)
    return content


# ---------------------------------------------------------------------------
# Airlock precheck (shared by upload and download)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("action, status, config, blocked", [
    ("upload", 200, airlock(import_from_computer=False), True),
    ("upload", 200, airlock(), False),
    ("upload", 200, airlock(enabled=False, import_from_computer=False), False),
    ("upload", 404, {"message": "Not Found"}, False),  # no policy configured
    ("upload", 403, {"message": "Forbidden"}, False),  # can't read the policy; the platform still enforces it
    # A direct upload would skip the import scan and approval.
    ("upload", 200, {**airlock(), "airlockIn": {"enabled": True}}, True),
    ("upload", 200, {**airlock(), "importSettings": {"enabled": True}}, True),
    # The platform rejects every API-key download while Airlock is on, even with enableViewFile.
    ("download", 200, airlock(), True),
    ("download", 200, airlock(enabled=False), False),
])
@responses.activate
def test_airlock_precheck(action, status, config, blocked):
    responses.add(responses.GET, AIRLOCK_URL, json=config, status=status,
                  match=[matchers.query_param_matcher({"teamId": WORKSPACE_ID})])
    message = _client().check_airlock_restriction(action)
    assert (message is not None) == blocked
    if blocked:
        assert "Airlock" in message


# ---------------------------------------------------------------------------
# S3 multipart upload
# ---------------------------------------------------------------------------

def test_compute_part_size():
    assert compute_part_size(501) == 8 * 1024 * 1024
    huge_file = 200 * 1024 ** 3  # would need 25,000 parts at 8 MiB
    part_size = compute_part_size(huge_file)
    assert -(-huge_file // part_size) <= 10000
    assert part_size % (1024 * 1024) == 0


def test_s3_uri_encode_preserves_path_separators():
    assert s3_uri_encode("teams/abc def/dataset/file name.txt") == "teams/abc%20def/dataset/file%20name.txt"


@pytest.mark.parametrize("kind, segment", [("Dataset", "dataset"), ("Folder", "folder")])
@responses.activate
def test_upload_key_layout_matches_web_uploader(tmp_path, kind, segment):
    abort, register = _mock_s3_upload()
    local_file = tmp_path / "f.txt"
    local_file.write_text("hi")

    _client().upload_local_file(local_path=str(local_file), destination_folder_id="fid",
                                destination_parent_kind=kind, cloud_config=CLOUD_AWS, progress=False)

    body = json.loads(register.calls[0].request.body)
    assert body["s3ObjectKey"] == f"deploit/{segment}/fid/f.txt"
    assert body["parent"] == {"kind": kind, "id": "fid"}
    assert body["sizeInBytes"] == 2
    assert abort.call_count == 0


@responses.activate
def test_upload_aborts_multipart_on_part_failure(tmp_path):
    abort, register = _mock_s3_upload(status=403)
    local_file = tmp_path / "big.bin"
    local_file.write_bytes(b"x" * 1000)

    with pytest.raises(S3UploadError, match="Signature expired"):
        _client().upload_local_file(local_path=str(local_file), destination_folder_id="fid",
                                    destination_parent_kind="Folder", cloud_config=CLOUD_AWS, progress=False)
    assert abort.call_count == 1
    assert register.call_count == 0


@pytest.mark.parametrize("complete_status, complete_body, error", [
    # S3 can report a failed completion with a 200 status and an <Error> body.
    (200, "<Error><Code>InternalError</Code><Message>We encountered an internal error</Message></Error>",
     "internal error"),
    # An object already exists at the key, e.g. from a concurrent upload of the same name.
    (412, "<Error><Code>PreconditionFailed</Code><Message>pre-conditions</Message></Error>",
     "is already stored"),
])
@responses.activate
def test_upload_failed_completion_is_aborted_and_not_registered(tmp_path, complete_status, complete_body, error):
    abort, register = _mock_s3_upload(complete_status=complete_status, complete_body=complete_body)
    local_file = tmp_path / "f.txt"
    local_file.write_text("hi")

    with pytest.raises((S3UploadError, ValueError), match=error):
        _client().upload_local_file(local_path=str(local_file), destination_folder_id="fid",
                                    destination_parent_kind="Folder", cloud_config=CLOUD_AWS, progress=False)
    assert abort.call_count == 1
    assert register.call_count == 0
    complete = next(c for c in responses.calls if "uploadId=" in c.request.url and c.request.method == "POST")
    assert complete.request.headers["if-none-match"] == "*"


def test_upload_rejects_files_over_5tib(tmp_path):
    local_file = tmp_path / "tiny.bin"
    local_file.write_bytes(b"x")
    real = os.stat(local_file)
    huge = os.stat_result((stat.S_IFREG | 0o644, real.st_ino, real.st_dev, 1, 0, 0, MAX_OBJECT_SIZE + 1, 0, 0, 0))
    with mock.patch("cloudos_cli.datasets.datasets.os.stat", return_value=huge):
        with pytest.raises(ValueError, match="5 TiB"):
            _client().upload_local_file(local_path=str(local_file), destination_folder_id="fid",
                                        destination_parent_kind="Folder", cloud_config=CLOUD_AWS)


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="needs FIFO support")
def test_upload_rejects_non_regular_file(tmp_path):
    fifo = tmp_path / "pipe"
    os.mkfifo(fifo)
    with pytest.raises(ValueError, match="not a regular file"):
        _client().upload_local_file(local_path=str(fifo), destination_folder_id="fid",
                                    destination_parent_kind="Folder", cloud_config=CLOUD_AWS)


# ---------------------------------------------------------------------------
# Security hardening
# ---------------------------------------------------------------------------

def _uploader(client, region="us-east-1", bucket="lifebit-user-data-12345678", verify=True):
    return SignedS3MultipartUploader(
        datasets_client=client, bucket=bucket, key="deploit/dataset/x/f.txt", region=region,
        content_type="text/plain", access_key_id="ASIATEST", session_token="tok",
        credentials_blob="blob", verify=verify,
    )


@pytest.mark.parametrize("region", ["evil.com/#", "us-east-1.attacker.net", "", "US-EAST-1", "us-east-1\n"])
def test_uploader_rejects_unexpected_region(region):
    with pytest.raises(ValueError, match="region"):
        _uploader(_client(), region=region)


@pytest.mark.parametrize("bucket", ["a", "bad/bucket", "Bucket_With_Caps", "x" * 70])
def test_uploader_rejects_unexpected_bucket(bucket):
    with pytest.raises(ValueError, match="bucket"):
        _uploader(_client(), bucket=bucket)


@pytest.mark.parametrize("body", ["not-a-signature", "", '{"signature": "abc"}', "<html>oops</html>"])
@responses.activate
def test_signer_rejects_unexpected_response(body):
    responses.add(responses.GET, SIGNER_URL, body=body, status=200)
    with pytest.raises(TransferError):
        _client().sign_upload_for_evaporate("s", "20260101T000000Z", "c", "blob")


@pytest.mark.parametrize("body", ['{"signature": "' + "a" * 64 + '"}', '"' + "b" * 64 + '"', "c" * 64])
@responses.activate
def test_signer_accepts_known_response_shapes(body):
    responses.add(responses.GET, SIGNER_URL, body=body, status=200)
    assert len(_client().sign_upload_for_evaporate("s", "20260101T000000Z", "c", "blob")) == 64


def test_s3_requests_honour_ssl_settings():
    client = _client()
    uploader = _uploader(client, verify="/path/to/ca.pem")
    fake = mock.Mock(status_code=200, headers={"ETag": '"e"'})
    with mock.patch.object(client, "sign_upload_for_evaporate", return_value="0" * 64), \
            mock.patch("cloudos_cli.datasets.s3_multipart_upload.retry_requests_put", return_value=fake) as put:
        uploader.upload_part(1, b"data", "upload-id")
    assert put.call_args.kwargs["verify"] == "/path/to/ca.pem"
    assert put.call_args.kwargs["timeout"]


def test_s3_network_errors_do_not_leak_url_or_token():
    client = _client()
    leaky = requests.exceptions.ConnectionError(
        "Max retries exceeded with url: /b/k?partNumber=1&X-Amz-Security-Token=SUPERSECRET")
    with mock.patch.object(client, "sign_upload_for_evaporate", return_value="0" * 64), \
            mock.patch("cloudos_cli.datasets.s3_multipart_upload.retry_requests_put", side_effect=leaky):
        with pytest.raises(TransferError) as exc_info:
            _uploader(client).upload_part(1, b"data", "upload-id")
    assert "SUPERSECRET" not in str(exc_info.value)
    assert exc_info.value.__cause__ is None and exc_info.value.__suppress_context__


@responses.activate
def test_signer_network_errors_do_not_leak_canonical_request():
    responses.add(responses.GET, SIGNER_URL,
                  body=requests.exceptions.ConnectionError("url: ...x-amz-security-token:SUPERSECRET"))
    with pytest.raises(TransferError) as exc_info:
        _client().sign_upload_for_evaporate("s", "20260101T000000Z", "x-amz-security-token:SUPERSECRET", "blob")
    assert "SUPERSECRET" not in str(exc_info.value)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

@responses.activate
def test_cli_upload_prints_virtual_and_storage_path(tmp_path):
    _mock_cli_chain()
    _mock_s3_upload()
    local_file = tmp_path / "new.csv"
    local_file.write_text("a,b\n1,2\n")

    result = CliRunner().invoke(run_cloudos_cli, [
        'datasets', 'upload', str(local_file), 'Data', '--show-storage-path', *CLI_AUTH])

    assert result.exit_code == 0, result.output
    assert f"Virtual path: Projects/{PROJECT_NAME}/Data/new.csv" in result.output
    assert f"Storage path: s3://lifebit-user-data-12345678/deploit/dataset/{DATA_ID}/new.csv" in result.output


@responses.activate
def test_cli_upload_blocked_by_airlock(tmp_path):
    _mock_cli_chain(airlock_config=airlock(import_from_computer=False))
    local_file = tmp_path / "upload_me.txt"
    local_file.write_text("hello")

    result = CliRunner().invoke(run_cloudos_cli, ['datasets', 'upload', str(local_file), 'Data', *CLI_AUTH])

    assert result.exit_code != 0
    assert "Airlock" in result.output and "workspace admin" in result.output


@responses.activate
def test_cli_upload_non_aws_workspace_gives_clear_error(tmp_path):
    _mock_cli_chain(cloud_status=404)
    local_file = tmp_path / "upload_me.txt"
    local_file.write_text("hello")

    result = CliRunner().invoke(run_cloudos_cli, ['datasets', 'upload', str(local_file), 'Data', *CLI_AUTH])

    assert result.exit_code != 0
    assert "only supported in AWS workspaces" in result.output


@responses.activate
def test_cli_upload_refuses_existing_name_before_uploading(tmp_path):
    """An existing file shares the S3 key, so nothing may be sent to S3 for a duplicate."""
    content = _mock_cli_chain()
    creds = responses.add(responses.GET, f"{CLOUDOS_URL}/api/v1/aws/tmp-credentials", json={})
    s3 = responses.add(responses.POST, S3_URL_RE, status=200)
    local_file = tmp_path / content["files"][0]["name"]
    local_file.write_bytes(b"new content that must not reach S3")

    result = CliRunner().invoke(run_cloudos_cli, ['datasets', 'upload', str(local_file), 'Data', *CLI_AUTH])

    assert result.exit_code != 0
    assert "already exists" in result.output
    assert creds.call_count == 0 and s3.call_count == 0


def test_cli_upload_destination_outside_data_suggests_fix(tmp_path):
    local_file = tmp_path / "a.txt"
    local_file.write_text("x")

    result = CliRunner().invoke(run_cloudos_cli, ['datasets', 'upload', str(local_file), 'cli-test', *CLI_AUTH])

    assert result.exit_code != 0
    assert "Did you mean 'Data/cli-test'?" in str(result.exception)

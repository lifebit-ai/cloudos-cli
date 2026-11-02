import base64

import pytest
import requests
import responses
from click.testing import CliRunner
from responses import matchers

from cloudos_cli.__main__ import run_cloudos_cli
from cloudos_cli.datasets.s3_multipart_upload import TransferError
from cloudos_cli.utils.errors import BadRequestException
from tests.test_datasets.test_upload import CLI_AUTH, CLOUDOS_URL, WORKSPACE_ID, _client, _mock_cli_chain, airlock

SIGNED_URL = "https://mock-signed-s3-url.example.com/lifebit-user-data-xxxx/flowchart.png?X-Amz-Signature=abc"
S3_ITEM = {"name": "flowchart.png", "fileType": "S3File", "s3BucketName": "lifebit-user-data-xxxx",
           "s3ObjectKey": "teams/x/dataset/y/flowchart.png"}
AZURE_ITEM = {"name": "results.tsv", "fileType": "AzureBlobFile", "blobContainerName": "my-container",
              "blobStorageAccountName": "mystorageaccount", "blobName": "path/to/results.tsv"}


def _b64(text):
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def _leftovers(directory):
    return [p.name for p in directory.iterdir() if p.name.startswith(".cloudos-download-")]


# ---------------------------------------------------------------------------
# Presigned URL and streaming to disk
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("item, endpoint, params", [
    (S3_ITEM, "s3", {"bucket": "lifebit-user-data-xxxx", "key": _b64(S3_ITEM["s3ObjectKey"])}),
    (AZURE_ITEM, "azure", {"containerName": "my-container", "storageAccountName": "mystorageaccount",
                           "blobKey": _b64(AZURE_ITEM["blobName"])}),
])
@responses.activate
def test_get_signed_download_url(item, endpoint, params):
    responses.add(responses.GET, f"{CLOUDOS_URL}/api/v1/data-access/{endpoint}/signed-object-url",
                  json={"signedUrl": SIGNED_URL},
                  match=[matchers.query_param_matcher({**params, "teamId": WORKSPACE_ID})])
    assert _client().get_signed_download_url(item) == SIGNED_URL


@responses.activate
def test_get_signed_download_url_missing_url_raises():
    responses.add(responses.GET, f"{CLOUDOS_URL}/api/v1/data-access/s3/signed-object-url", json={})
    with pytest.raises(ValueError, match="did not return a signed download URL"):
        _client().get_signed_download_url(S3_ITEM)


@responses.activate
def test_download_raises_on_error_status(tmp_path):
    responses.add(responses.GET, SIGNED_URL, status=403, body="Forbidden")
    with pytest.raises(BadRequestException):
        _client().download_to_file(SIGNED_URL, str(tmp_path / "out.bin"))
    assert _leftovers(tmp_path) == []


@responses.activate
def test_truncated_download_leaves_no_partial_file(tmp_path):
    responses.add(responses.GET, SIGNED_URL, body=b"only-part")
    dest = tmp_path / "out.bin"
    with pytest.raises(TransferError, match="size mismatch"):
        _client().download_to_file(SIGNED_URL, str(dest), expected_size=1000)
    assert not dest.exists()
    assert _leftovers(tmp_path) == []


@responses.activate
def test_oversized_download_is_cut_off(tmp_path):
    responses.add(responses.GET, SIGNED_URL, body=b"x" * 10_000)
    dest = tmp_path / "out.bin"
    with pytest.raises(TransferError, match="size mismatch"):
        _client().download_to_file(SIGNED_URL, str(dest), expected_size=10, chunk_size=100)
    assert not dest.exists()
    assert _leftovers(tmp_path) == []


def test_download_refuses_non_https_url(tmp_path):
    with pytest.raises(TransferError, match="not HTTPS"):
        _client().download_to_file("http://example.com/f?sig=x", str(tmp_path / "out.bin"))
    assert _leftovers(tmp_path) == []


@responses.activate
def test_failed_overwrite_keeps_existing_file(tmp_path):
    responses.add(responses.GET, SIGNED_URL, body=b"short")
    dest = tmp_path / "out.bin"
    dest.write_bytes(b"precious original")
    with pytest.raises(TransferError):
        _client().download_to_file(SIGNED_URL, str(dest), overwrite=True, expected_size=1000)
    assert dest.read_bytes() == b"precious original"


@responses.activate
def test_overwrite_replaces_existing_file(tmp_path):
    responses.add(responses.GET, SIGNED_URL, body=b"new")
    dest = tmp_path / "out.bin"
    dest.write_bytes(b"old")
    _client().download_to_file(SIGNED_URL, str(dest), overwrite=True, expected_size=3)
    assert dest.read_bytes() == b"new"
    assert _leftovers(tmp_path) == []


def test_dangling_symlink_is_not_followed_without_overwrite(tmp_path):
    target = tmp_path / "elsewhere.txt"
    link = tmp_path / "out.bin"
    link.symlink_to(target)
    with pytest.raises(FileExistsError):
        _client().download_to_file(SIGNED_URL, str(link))
    assert not target.exists()


@responses.activate
def test_download_network_error_does_not_leak_presigned_url(tmp_path):
    responses.add(responses.GET, SIGNED_URL,
                  body=requests.exceptions.ConnectionError(f"Max retries exceeded with url: {SIGNED_URL}"))
    with pytest.raises(TransferError) as exc_info:
        _client().download_to_file(SIGNED_URL, str(tmp_path / "out.bin"))
    assert "X-Amz-Signature" not in str(exc_info.value)
    assert _leftovers(tmp_path) == []


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

@responses.activate
def test_cli_download_into_folder_with_storage_path(tmp_path):
    item = _mock_cli_chain()["files"][0]
    responses.add(responses.GET, f"{CLOUDOS_URL}/api/v1/data-access/s3/signed-object-url",
                  json={"signedUrl": SIGNED_URL})
    content = b"x" * item["sizeInBytes"]
    responses.add(responses.GET, SIGNED_URL, body=content)

    result = CliRunner().invoke(run_cloudos_cli, [
        'datasets', 'download', 'Data/flowchart.png', str(tmp_path), '--show-storage-path', *CLI_AUTH])

    assert result.exit_code == 0, result.output
    assert (tmp_path / "flowchart.png").read_bytes() == content
    assert f"Storage path: s3://{item['s3BucketName']}/{item['s3ObjectKey']}" in result.output


@responses.activate
def test_cli_download_blocked_by_airlock(tmp_path):
    _mock_cli_chain(airlock_config=airlock())

    result = CliRunner().invoke(run_cloudos_cli, [
        'datasets', 'download', 'Data/flowchart.png', str(tmp_path / "out.png"), *CLI_AUTH])

    assert result.exit_code != 0
    assert "Airlock" in result.output
    assert not any("signed-object-url" in c.request.url for c in responses.calls)


@responses.activate
def test_cli_download_refuses_overwrite_without_flag(tmp_path):
    _mock_cli_chain()
    existing_file = tmp_path / "flowchart.png"
    existing_file.write_bytes(b"old content")

    result = CliRunner().invoke(run_cloudos_cli, [
        'datasets', 'download', 'Data/flowchart.png', str(existing_file), *CLI_AUTH])

    assert result.exit_code != 0
    assert "already exists" in str(result.exception)
    assert existing_file.read_bytes() == b"old content"


@responses.activate
def test_cli_download_to_missing_folder_with_trailing_slash(tmp_path, monkeypatch):
    _mock_cli_chain()
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(run_cloudos_cli, [
        'datasets', 'download', 'Data/flowchart.png', 'downloads/', *CLI_AUTH])

    assert result.exit_code != 0
    assert "Local folder 'downloads/' does not exist" in str(result.exception)
    # Refused before any download was attempted.
    assert not any("signed-object-url" in c.request.url for c in responses.calls)
    assert list(tmp_path.iterdir()) == []

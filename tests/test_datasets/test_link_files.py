"""Unit tests for file-level linking support in the Link class."""

import pytest
from unittest import mock
from cloudos_cli.link.link import Link
import responses

CLOUDOS_URL = "https://lifebit.ai"
APIKEY = "testapikey"
WORKSPACE_ID = "team123"
PROJECT_NAME = "test_project"


@pytest.fixture
def link_instance():
    return Link(
        cloudos_url=CLOUDOS_URL,
        apikey=APIKEY,
        workspace_id=WORKSPACE_ID,
        project_name=PROJECT_NAME,
        cromwell_token=None,
        verify=False,
    )


# ---------------------------------------------------------------------------
# is_s3_file_path
# ---------------------------------------------------------------------------

class TestIsS3FilePath:

    def test_trailing_slash_is_folder(self, link_instance):
        assert link_instance.is_s3_file_path("s3://bucket/prefix/") is False

    def test_extension_no_trailing_slash_is_file(self, link_instance):
        assert link_instance.is_s3_file_path("s3://bucket/path/data.csv") is True

    def test_no_extension_no_trailing_slash_is_folder(self, link_instance):
        assert link_instance.is_s3_file_path("s3://bucket/path/folder") is False

    def test_multiple_extensions_in_path_only_last_segment_matters(self, link_instance):
        assert link_instance.is_s3_file_path("s3://bucket/path.v2/folder") is False

    def test_txt_file_is_file(self, link_instance):
        assert link_instance.is_s3_file_path("s3://bucket/data/file.txt") is True

    def test_vcf_gz_file_is_file(self, link_instance):
        assert link_instance.is_s3_file_path("s3://bucket/data/sample.vcf.gz") is True


# ---------------------------------------------------------------------------
# parse_s3_file_path
# ---------------------------------------------------------------------------

class TestParseS3FilePath:

    def test_valid_s3_file(self, link_instance):
        result = link_instance.parse_s3_file_path("s3://mybucket/path/data.csv")
        assert result == {
            "dataItem": {
                "type": "S3File",
                "data": {
                    "name": "data.csv",
                    "s3BucketName": "mybucket",
                    "s3ObjectKey": "path/data.csv",
                },
            }
        }

    def test_nested_path(self, link_instance):
        result = link_instance.parse_s3_file_path("s3://bucket/a/b/c/file.txt")
        assert result["dataItem"]["data"]["name"] == "file.txt"
        assert result["dataItem"]["data"]["s3ObjectKey"] == "a/b/c/file.txt"
        assert result["dataItem"]["type"] == "S3File"

    def test_invalid_url_raises(self, link_instance):
        with pytest.raises(ValueError, match="must start with 's3://'"):
            link_instance.parse_s3_file_path("https://bucket/file.csv")

    def test_no_key_raises(self, link_instance):
        with pytest.raises(ValueError):
            link_instance.parse_s3_file_path("s3://bucket")


# ---------------------------------------------------------------------------
# _parse_file_explorer_item (auto-detect)
# ---------------------------------------------------------------------------

class TestParseFileExplorerItem:

    def _make_ds_mock(self, folders=None, files=None):
        ds = mock.MagicMock()
        ds.list_folder_content.return_value = {
            "folders": folders or [],
            "files": files or [],
        }
        return ds

    def test_detects_folder(self, link_instance, monkeypatch):
        ds = self._make_ds_mock(
            folders=[{"name": "results", "_id": "folder_id_1", "folderType": "S3Folder"}]
        )
        monkeypatch.setattr(
            "cloudos_cli.link.link.generate_datasets_for_project",
            lambda *a, **kw: ds
        )
        result = link_instance._parse_file_explorer_item("Data/results")
        assert result["dataItem"]["kind"] == "Folder"
        assert result["dataItem"]["item"] == "folder_id_1"
        assert result["dataItem"]["name"] == "results"

    def test_detects_file(self, link_instance, monkeypatch):
        ds = self._make_ds_mock(
            files=[{"name": "data.csv", "_id": "file_id_99"}]
        )
        monkeypatch.setattr(
            "cloudos_cli.link.link.generate_datasets_for_project",
            lambda *a, **kw: ds
        )
        result = link_instance._parse_file_explorer_item("Data/data.csv")
        assert result["dataItem"]["kind"] == "File"
        assert result["dataItem"]["item"] == "file_id_99"
        assert result["dataItem"]["name"] == "data.csv"

    def test_virtual_folder_raises(self, link_instance, monkeypatch):
        ds = self._make_ds_mock(
            folders=[{"name": "vfolder", "_id": "vf_id", "folderType": "VirtualFolder"}]
        )
        monkeypatch.setattr(
            "cloudos_cli.link.link.generate_datasets_for_project",
            lambda *a, **kw: ds
        )
        with pytest.raises(ValueError, match="Virtual folders cannot be linked"):
            link_instance._parse_file_explorer_item("Data/vfolder")

    def test_not_found_raises(self, link_instance, monkeypatch):
        ds = self._make_ds_mock()
        monkeypatch.setattr(
            "cloudos_cli.link.link.generate_datasets_for_project",
            lambda *a, **kw: ds
        )
        with pytest.raises(ValueError, match="not found"):
            link_instance._parse_file_explorer_item("Data/missing_item")


# ---------------------------------------------------------------------------
# 100-item limit check
# ---------------------------------------------------------------------------

class TestLinkItemsLimit:

    @responses.activate
    def test_exceeds_100_item_limit_raises(self, link_instance, monkeypatch):
        status_url = f"{CLOUDOS_URL}/api/v1/interactive-sessions/session1/fuse-filesystems?teamId={WORKSPACE_ID}"
        existing = [{"mountName": f"item{i}", "status": "mounted"} for i in range(99)]
        responses.add(responses.GET, status_url, json={"fuseFileSystems": existing}, status=200)

        monkeypatch.setattr(link_instance, "parse_s3_path", lambda x: {
            "dataItem": {"type": "S3Folder", "data": {"name": "new_folder", "s3BucketName": "b", "s3Prefix": "p/"}}
        })
        monkeypatch.setattr(link_instance, "is_s3_file_path", lambda x: False)

        # 99 existing + 2 new = 101 → should fail
        with pytest.raises(ValueError, match="Cannot link more than 100 items"):
            link_instance.link_folders_batch(
                ["s3://bucket/folder1/", "s3://bucket/folder2/"],
                "session1"
            )

    @responses.activate
    def test_exactly_100_items_succeeds(self, link_instance, monkeypatch):
        status_url = f"{CLOUDOS_URL}/api/v1/interactive-sessions/sessionABC/fuse-filesystems?teamId={WORKSPACE_ID}"
        existing = [{"mountName": f"item{i}", "status": "mounted"} for i in range(99)]
        responses.add(responses.GET, status_url, json={"fuseFileSystems": existing}, status=200)

        url_v2 = f"{CLOUDOS_URL}/api/v2/interactive-sessions/sessionABC/fuse-filesystem/mount?teamId={WORKSPACE_ID}"
        responses.add(responses.POST, url_v2, status=204)

        responses.add(
            responses.GET, status_url,
            json={"fuseFileSystems": [{"_id": "x", "mountName": "newfile", "status": "mounted"}]},
            status=200
        )

        monkeypatch.setattr(link_instance, "is_s3_file_path", lambda x: True)
        monkeypatch.setattr(link_instance, "parse_s3_file_path", lambda x: {
            "dataItem": {"type": "S3File", "data": {"name": "newfile", "s3BucketName": "b", "s3ObjectKey": "path/newfile.csv"}}
        })

        # 99 existing + 1 new = 100 → should succeed
        link_instance.link_folders_batch(["s3://b/path/newfile.csv"], "sessionABC")


# ---------------------------------------------------------------------------
# Duplicate name check against existing session items
# ---------------------------------------------------------------------------

class TestDuplicateNameCheck:

    @responses.activate
    def test_duplicate_against_existing_session_item_raises(self, link_instance, monkeypatch):
        status_url = f"{CLOUDOS_URL}/api/v1/interactive-sessions/sessionABC/fuse-filesystems?teamId={WORKSPACE_ID}"
        existing = [{"mountName": "data.csv", "status": "mounted"}]
        responses.add(responses.GET, status_url, json={"fuseFileSystems": existing}, status=200)

        monkeypatch.setattr(link_instance, "is_s3_file_path", lambda x: True)
        monkeypatch.setattr(link_instance, "parse_s3_file_path", lambda x: {
            "dataItem": {"type": "S3File", "data": {"name": "data.csv", "s3BucketName": "b", "s3ObjectKey": "p/data.csv"}}
        })

        with pytest.raises(ValueError, match="already mounted in session"):
            link_instance.link_folders_batch(["s3://b/p/data.csv"], "sessionABC")


# ---------------------------------------------------------------------------
# S3 file linking end-to-end (v2)
# ---------------------------------------------------------------------------

class TestLinkS3FileV2:

    @responses.activate
    def test_s3_file_linked_via_v2(self, link_instance, capsys, monkeypatch):
        status_url = f"{CLOUDOS_URL}/api/v1/interactive-sessions/sessionABC/fuse-filesystems?teamId={WORKSPACE_ID}"
        responses.add(responses.GET, status_url, json={"fuseFileSystems": []}, status=200)

        url_v2 = f"{CLOUDOS_URL}/api/v2/interactive-sessions/sessionABC/fuse-filesystem/mount?teamId={WORKSPACE_ID}"
        responses.add(responses.POST, url_v2, status=204)

        responses.add(
            responses.GET, status_url,
            json={"fuseFileSystems": [{"_id": "1", "mountName": "file.csv", "status": "mounted"}]},
            status=200
        )

        monkeypatch.setattr(link_instance, "is_s3_file_path", lambda x: True)
        monkeypatch.setattr(link_instance, "parse_s3_file_path", lambda x: {
            "dataItem": {"type": "S3File", "data": {"name": "file.csv", "s3BucketName": "bucket", "s3ObjectKey": "path/file.csv"}}
        })

        link_instance.link_folders_batch(["s3://bucket/path/file.csv"], "sessionABC")
        captured = capsys.readouterr()
        assert "Successfully mounted S3 file: s3://bucket/path/file.csv" in captured.out


# ---------------------------------------------------------------------------
# File Explorer file linking end-to-end (v2)
# ---------------------------------------------------------------------------

class TestLinkFileExplorerFileV2:

    @responses.activate
    def test_fe_file_linked_via_v2(self, link_instance, capsys, monkeypatch):
        status_url = f"{CLOUDOS_URL}/api/v1/interactive-sessions/sessionABC/fuse-filesystems?teamId={WORKSPACE_ID}"
        responses.add(responses.GET, status_url, json={"fuseFileSystems": []}, status=200)

        url_v2 = f"{CLOUDOS_URL}/api/v2/interactive-sessions/sessionABC/fuse-filesystem/mount?teamId={WORKSPACE_ID}"
        responses.add(responses.POST, url_v2, status=204)

        responses.add(
            responses.GET, status_url,
            json={"fuseFileSystems": [{"_id": "2", "mountName": "observations.csv", "status": "mounted"}]},
            status=200
        )

        monkeypatch.setattr(link_instance, "_parse_file_explorer_item", lambda x: {
            "dataItem": {"kind": "File", "item": "file_abc", "name": "observations.csv"}
        })

        link_instance.link_folders_batch(["Data/observations.csv"], "sessionABC")
        captured = capsys.readouterr()
        assert "Successfully mounted File Explorer file: Data/observations.csv" in captured.out


# ---------------------------------------------------------------------------
# Mixed file and folder batch linking
# ---------------------------------------------------------------------------

class TestMixedBatchLinking:

    @responses.activate
    def test_mixed_s3_files_and_folders(self, link_instance, capsys, monkeypatch):
        status_url = f"{CLOUDOS_URL}/api/v1/interactive-sessions/sessionABC/fuse-filesystems?teamId={WORKSPACE_ID}"
        responses.add(responses.GET, status_url, json={"fuseFileSystems": []}, status=200)

        url_v2 = f"{CLOUDOS_URL}/api/v2/interactive-sessions/sessionABC/fuse-filesystem/mount?teamId={WORKSPACE_ID}"
        responses.add(responses.POST, url_v2, status=204)

        responses.add(responses.GET, status_url, json={"fuseFileSystems": [{"_id": "1", "mountName": "file.csv", "status": "mounted"}]}, status=200)
        responses.add(responses.GET, status_url, json={"fuseFileSystems": [{"_id": "2", "mountName": "folder", "status": "mounted"}]}, status=200)

        def mock_is_file(url):
            return url.endswith(".csv")

        def mock_parse_file(url):
            return {"dataItem": {"type": "S3File", "data": {"name": "file.csv", "s3BucketName": "b", "s3ObjectKey": "data/file.csv"}}}

        def mock_parse_folder(url):
            return {"dataItem": {"type": "S3Folder", "data": {"name": "folder", "s3BucketName": "b", "s3Prefix": "data/folder/"}}}

        monkeypatch.setattr(link_instance, "is_s3_file_path", mock_is_file)
        monkeypatch.setattr(link_instance, "parse_s3_file_path", mock_parse_file)
        monkeypatch.setattr(link_instance, "parse_s3_path", mock_parse_folder)

        link_instance.link_folders_batch(
            ["s3://b/data/file.csv", "s3://b/data/folder/"],
            "sessionABC"
        )
        captured = capsys.readouterr()
        assert "Successfully mounted S3 file" in captured.out
        assert "Successfully mounted S3 folder" in captured.out


# ---------------------------------------------------------------------------
# Backward compatibility: existing folder tests still work via link_folders_batch
# ---------------------------------------------------------------------------

class TestBackwardCompatibility:

    @responses.activate
    def test_folder_linking_unchanged(self, link_instance, capsys, monkeypatch):
        status_url = f"{CLOUDOS_URL}/api/v1/interactive-sessions/sessionABC/fuse-filesystems?teamId={WORKSPACE_ID}"
        responses.add(responses.GET, status_url, json={"fuseFileSystems": []}, status=200)

        url_v2 = f"{CLOUDOS_URL}/api/v2/interactive-sessions/sessionABC/fuse-filesystem/mount?teamId={WORKSPACE_ID}"
        responses.add(responses.POST, url_v2, status=204)

        responses.add(
            responses.GET, status_url,
            json={"fuseFileSystems": [{"_id": "1", "mountName": "myfolder", "status": "mounted"}]},
            status=200
        )

        monkeypatch.setattr(link_instance, "is_s3_file_path", lambda x: False)
        monkeypatch.setattr(link_instance, "parse_s3_path", lambda x: {
            "dataItem": {"type": "S3Folder", "data": {"name": "myfolder", "s3BucketName": "b", "s3Prefix": "path/myfolder/"}}
        })

        link_instance.link_folder("s3://b/path/myfolder/", "sessionABC")
        captured = capsys.readouterr()
        assert "Successfully mounted S3 folder: s3://b/path/myfolder/" in captured.out

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

    def test_empty_bucket_raises(self, link_instance):
        with pytest.raises(ValueError, match="bucket name is empty"):
            link_instance.parse_s3_file_path("s3:///some/key.csv")

    def test_trailing_slash_key_raises(self, link_instance):
        with pytest.raises(ValueError, match="folder-like"):
            link_instance.parse_s3_file_path("s3://bucket/folder/")


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
            "cloudos_cli.link.link.Datasets",
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
            "cloudos_cli.link.link.Datasets",
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
            "cloudos_cli.link.link.Datasets",
            lambda *a, **kw: ds
        )
        with pytest.raises(ValueError, match="Virtual folders cannot be linked"):
            link_instance._parse_file_explorer_item("Data/vfolder")

    def test_not_found_raises(self, link_instance, monkeypatch):
        ds = self._make_ds_mock()
        monkeypatch.setattr(
            "cloudos_cli.link.link.Datasets",
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
        status_url = f"{CLOUDOS_URL}/api/v1/interactive-sessions/session1/fuse-filesystems?teamId={WORKSPACE_ID}&limit=100&page=1"
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
        status_url = f"{CLOUDOS_URL}/api/v1/interactive-sessions/sessionABC/fuse-filesystems?teamId={WORKSPACE_ID}&limit=100&page=1"
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
        status_url = f"{CLOUDOS_URL}/api/v1/interactive-sessions/sessionABC/fuse-filesystems?teamId={WORKSPACE_ID}&limit=100&page=1"
        existing = [{"mountName": "data.csv", "status": "mounted"}]
        responses.add(responses.GET, status_url, json={"fuseFileSystems": existing}, status=200)

        monkeypatch.setattr(link_instance, "is_s3_file_path", lambda x: True)
        monkeypatch.setattr(link_instance, "parse_s3_file_path", lambda x: {
            "dataItem": {"type": "S3File", "data": {"name": "data.csv", "s3BucketName": "b", "s3ObjectKey": "p/data.csv"}}
        })

        with pytest.raises(ValueError, match="already mounted in the session"):
            link_instance.link_folders_batch(["s3://b/p/data.csv"], "sessionABC")


# ---------------------------------------------------------------------------
# S3 file linking end-to-end (v2)
# ---------------------------------------------------------------------------

class TestLinkS3FileV2:

    @responses.activate
    def test_s3_file_linked_via_v2(self, link_instance, capsys, monkeypatch):
        status_url = f"{CLOUDOS_URL}/api/v1/interactive-sessions/sessionABC/fuse-filesystems?teamId={WORKSPACE_ID}&limit=100&page=1"
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
        status_url = f"{CLOUDOS_URL}/api/v1/interactive-sessions/sessionABC/fuse-filesystems?teamId={WORKSPACE_ID}&limit=100&page=1"
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
        status_url = f"{CLOUDOS_URL}/api/v1/interactive-sessions/sessionABC/fuse-filesystems?teamId={WORKSPACE_ID}&limit=100&page=1"
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
        status_url = f"{CLOUDOS_URL}/api/v1/interactive-sessions/sessionABC/fuse-filesystems?teamId={WORKSPACE_ID}&limit=100&page=1"
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


# ---------------------------------------------------------------------------
# _parse_file_explorer_item guards (new in 2.91.0)
# ---------------------------------------------------------------------------

class TestParseFileExplorerItemGuards:
    """Validate the two defensive checks added at the top of _parse_file_explorer_item."""

    def test_missing_project_name_raises_clear_error(self):
        link = Link(
            cloudos_url=CLOUDOS_URL, apikey=APIKEY, workspace_id=WORKSPACE_ID,
            project_name=None, cromwell_token=None, verify=False,
        )
        with pytest.raises(ValueError, match="without a project"):
            link._parse_file_explorer_item("Data/file.csv")

    def test_path_starting_with_project_name_is_rejected(self, link_instance):
        # link_instance.project_name == 'test_project'
        with pytest.raises(ValueError, match="must NOT include the project name"):
            link_instance._parse_file_explorer_item("test_project/Data/file.csv")

    def test_rejection_message_quotes_the_correct_relative_form(self, link_instance):
        try:
            link_instance._parse_file_explorer_item("test_project/Data/file.csv")
        except ValueError as e:
            assert "Use 'Data/file.csv' instead." in str(e)

    def test_public_wrapper_matches_private(self, link_instance, monkeypatch):
        # parse_file_explorer_item should be a thin alias for _parse_file_explorer_item
        ds = mock.MagicMock()
        ds.list_folder_content.return_value = {
            "folders": [{"name": "results", "_id": "rid", "folderType": "S3Folder"}],
            "files": [],
        }
        monkeypatch.setattr(
            "cloudos_cli.link.link.Datasets",
            lambda *a, **kw: ds
        )
        public = link_instance.parse_file_explorer_item("Data/results")
        private = link_instance._parse_file_explorer_item("Data/results")
        assert public == private


# ---------------------------------------------------------------------------
# _translate_mount_error
# ---------------------------------------------------------------------------

class TestTranslateMountError:

    def test_prefix_does_not_exist_appends_guidance(self, link_instance):
        raw = "S3 prefix does not exist"
        out = link_instance._translate_mount_error(raw)
        assert raw in out
        assert "workspace's cloud account has read access" in out

    def test_key_does_not_exist_appends_guidance(self, link_instance):
        raw = "object key does not exist"
        out = link_instance._translate_mount_error(raw)
        assert raw in out
        assert "Verify the path is correct" in out

    def test_access_denied_appends_guidance(self, link_instance):
        raw = "S3 returned: access denied for bucket"
        out = link_instance._translate_mount_error(raw)
        assert raw in out
        assert "does not have permission" in out

    def test_forbidden_appends_guidance(self, link_instance):
        raw = "403 Forbidden"
        out = link_instance._translate_mount_error(raw)
        assert raw in out
        assert "does not have permission" in out

    def test_unknown_error_passes_through_unchanged(self, link_instance):
        raw = "Some unrelated mount failure"
        assert link_instance._translate_mount_error(raw) == raw


# ---------------------------------------------------------------------------
# v1 fallback rejects file items
# ---------------------------------------------------------------------------

class TestV1FallbackRejectsFiles:

    @responses.activate
    def test_v1_fallback_rejects_s3_file(self, link_instance, monkeypatch):
        status_url = f"{CLOUDOS_URL}/api/v1/interactive-sessions/sessionABC/fuse-filesystems?teamId={WORKSPACE_ID}&limit=100&page=1"
        responses.add(responses.GET, status_url, json={"fuseFileSystems": []}, status=200)

        # v2 returns 404 to trigger v1 fallback
        url_v2 = f"{CLOUDOS_URL}/api/v2/interactive-sessions/sessionABC/fuse-filesystem/mount?teamId={WORKSPACE_ID}"
        responses.add(responses.POST, url_v2, status=404, json={"message": "Not Found"})

        monkeypatch.setattr(link_instance, "is_s3_file_path", lambda x: True)
        monkeypatch.setattr(link_instance, "parse_s3_file_path", lambda x: {
            "dataItem": {
                "type": "S3File",
                "data": {"name": "file.csv", "s3BucketName": "b", "s3ObjectKey": "p/file.csv"},
            }
        })

        with pytest.raises(ValueError, match="File linking requires API v2"):
            link_instance.link_folders_batch(["s3://b/p/file.csv"], "sessionABC")

    @responses.activate
    def test_v1_fallback_rejects_fe_file(self, link_instance, monkeypatch):
        status_url = f"{CLOUDOS_URL}/api/v1/interactive-sessions/sessionABC/fuse-filesystems?teamId={WORKSPACE_ID}&limit=100&page=1"
        responses.add(responses.GET, status_url, json={"fuseFileSystems": []}, status=200)

        url_v2 = f"{CLOUDOS_URL}/api/v2/interactive-sessions/sessionABC/fuse-filesystem/mount?teamId={WORKSPACE_ID}"
        responses.add(responses.POST, url_v2, status=404, json={"message": "Not Found"})

        # Bypass _parse_file_explorer_item so we land directly in the v1-fallback file check
        monkeypatch.setattr(link_instance, "parse_file_explorer_item", lambda path: {
            "dataItem": {"kind": "File", "item": "id1", "name": "data.csv"}
        })

        with pytest.raises(ValueError, match="File linking requires API v2"):
            link_instance.link_folders_batch(["Data/data.csv"], "sessionABC")


# ---------------------------------------------------------------------------
# Direct Datasets construction (no more sys.exit via helper)
# ---------------------------------------------------------------------------

class TestDatasetsConstructionErrors:
    """The Datasets() call inside _parse_file_explorer_item must surface as a
    plain ValueError — never as sys.exit(1) — so callers can handle it."""

    def test_project_not_found_raises_clean_value_error(self, link_instance, monkeypatch):
        def boom(*args, **kwargs):
            raise ValueError("Project 'no-such-project' was not found in workspace 'ws'")

        monkeypatch.setattr("cloudos_cli.link.link.Datasets", boom)
        with pytest.raises(ValueError, match="Cannot resolve project 'test_project'"):
            link_instance._parse_file_explorer_item("Data/file.csv")

    def test_forbidden_raises_clean_value_error(self, link_instance, monkeypatch):
        from cloudos_cli.utils.errors import BadRequestException

        class _FakeResp:
            status_code = 403
            content = b'Forbidden'

            def json(self):
                return {"message": "Forbidden"}

        def boom(*args, **kwargs):
            raise BadRequestException(_FakeResp())

        monkeypatch.setattr("cloudos_cli.link.link.Datasets", boom)
        with pytest.raises(ValueError, match="Forbidden when accessing the project"):
            link_instance._parse_file_explorer_item("Data/file.csv")


# ---------------------------------------------------------------------------
# Duplicate-mount message names both colliding paths
# ---------------------------------------------------------------------------

class TestDuplicateMountMessage:
    """The error must name BOTH colliding paths in a batch-vs-batch collision."""

    def test_batch_collision_mentions_both_paths(self, link_instance):
        seen = {}
        # First registration succeeds (returns None)
        link_instance._raise_if_duplicate_mount("foo", "/first/path", seen)
        seen["foo"] = "/first/path"
        # Second one with the same mount name should mention BOTH paths
        with pytest.raises(ValueError) as excinfo:
            link_instance._raise_if_duplicate_mount("foo", "/second/path", seen)
        msg = str(excinfo.value)
        assert "/first/path" in msg
        assert "/second/path" in msg

    def test_session_collision_mentions_path_and_session(self, link_instance):
        # Pre-existing session item → value is None
        seen = {"foo": None}
        with pytest.raises(ValueError, match="already mounted in the session"):
            link_instance._raise_if_duplicate_mount("foo", "/new/path", seen)


# ---------------------------------------------------------------------------
# list_folder_content errors are wrapped as ValueError, not raw BadRequestException
# ---------------------------------------------------------------------------

class TestListFolderContentErrors:

    def test_forbidden_list_call_becomes_value_error(self, link_instance, monkeypatch):
        from cloudos_cli.utils.errors import BadRequestException

        class _Resp:
            status_code = 403
            content = b'Forbidden'

            def json(self):
                return {"message": "Forbidden"}

        ds = mock.MagicMock()
        ds.list_folder_content.side_effect = BadRequestException(_Resp())
        monkeypatch.setattr("cloudos_cli.link.link.Datasets", lambda *a, **kw: ds)

        with pytest.raises(ValueError, match="Not authorised to list"):
            link_instance._parse_file_explorer_item("Data/file.csv")


# ---------------------------------------------------------------------------
# get_fuse_filesystems_status paginates correctly
# ---------------------------------------------------------------------------

class TestFuseFilesystemsPagination:

    @responses.activate
    def test_single_page_no_pagination_metadata(self, link_instance):
        url_p1 = f"{CLOUDOS_URL}/api/v1/interactive-sessions/sX/fuse-filesystems?teamId={WORKSPACE_ID}&limit=100&page=1"
        responses.add(
            responses.GET, url_p1,
            json={"fuseFileSystems": [{"_id": "a", "mountName": "a", "status": "mounted"}]},
            status=200,
        )
        items = link_instance.get_fuse_filesystems_status("sX")
        assert len(items) == 1
        assert items[0]["mountName"] == "a"

    @responses.activate
    def test_multi_page_pagination_collects_all_items(self, link_instance):
        # Page 1: 2 items, total 3 → fetch page 2
        url_p1 = f"{CLOUDOS_URL}/api/v1/interactive-sessions/sY/fuse-filesystems?teamId={WORKSPACE_ID}&limit=100&page=1"
        url_p2 = f"{CLOUDOS_URL}/api/v1/interactive-sessions/sY/fuse-filesystems?teamId={WORKSPACE_ID}&limit=100&page=2"
        responses.add(
            responses.GET, url_p1,
            json={
                "fuseFileSystems": [
                    {"_id": "1", "mountName": "a", "status": "mounted"},
                    {"_id": "2", "mountName": "b", "status": "mounted"},
                ],
                "paginationMetadata": {
                    "Pagination-Count": 3, "Pagination-Page": 1, "Pagination-Limit": 2
                },
            },
            status=200,
        )
        responses.add(
            responses.GET, url_p2,
            json={
                "fuseFileSystems": [
                    {"_id": "3", "mountName": "c", "status": "mounted"},
                ],
                "paginationMetadata": {
                    "Pagination-Count": 3, "Pagination-Page": 2, "Pagination-Limit": 2
                },
            },
            status=200,
        )
        items = link_instance.get_fuse_filesystems_status("sY")
        assert [i["mountName"] for i in items] == ["a", "b", "c"]

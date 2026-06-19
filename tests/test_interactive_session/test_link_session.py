"""Tests for the interactive-session link CLI command and path-normalisation helpers."""

import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

from cloudos_cli.__main__ import run_cloudos_cli
from cloudos_cli.interactive_session.cli import _normalize_file_explorer_path, _check_duplicate_mount_name


# ---------------------------------------------------------------------------
# _normalize_file_explorer_path
# ---------------------------------------------------------------------------

class TestNormalizeFileExplorerPath:

    def test_s3_path_returned_unchanged(self):
        path, project = _normalize_file_explorer_path("s3://bucket/prefix/", "my-project")
        assert path == "s3://bucket/prefix/"
        assert project is None

    def test_azure_path_returned_unchanged(self):
        path, project = _normalize_file_explorer_path("az://container/blob", "my-project")
        assert path == "az://container/blob"
        assert project is None

    def test_known_root_folder_data_uses_profile_project(self):
        path, project = _normalize_file_explorer_path("Data/results", "profile-project")
        assert path == "Data/results"
        assert project == "profile-project"

    def test_known_root_folder_case_insensitive(self):
        path, project = _normalize_file_explorer_path("analysesresults/report.html", "p")
        assert project == "p"

    def test_cohorts_root_folder(self):
        path, project = _normalize_file_explorer_path("Cohorts/my-cohort", "workspace-project")
        assert path == "Cohorts/my-cohort"
        assert project == "workspace-project"

    def test_project_inferred_from_first_segment(self):
        path, project = _normalize_file_explorer_path("my-project/Data/folder", None)
        assert path == "Data/folder"
        assert project == "my-project"

    def test_project_inferred_overrides_supplied_project(self):
        # The first segment wins over the profile project when it is not a known root folder
        path, project = _normalize_file_explorer_path("other-project/Data/file.csv", "profile-project")
        assert path == "Data/file.csv"
        assert project == "other-project"

    def test_bare_path_no_slash_uses_profile_project(self):
        # A path with no slash is treated as a top-level item on the profile project
        path, project = _normalize_file_explorer_path("Data", "my-project")
        assert path == "Data"
        assert project == "my-project"

    def test_bare_path_no_slash_no_project_returns_none(self):
        path, project = _normalize_file_explorer_path("Data", None)
        assert path == "Data"
        assert project is None


# ---------------------------------------------------------------------------
# _check_duplicate_mount_name
# ---------------------------------------------------------------------------

class TestCheckDuplicateMountName:

    def test_new_name_is_registered(self):
        seen = {}
        _check_duplicate_mount_name("folder", "Data/folder", seen)
        assert seen["folder"] == "Data/folder"

    def test_duplicate_raises_value_error(self):
        seen = {"folder": "Data/folder"}
        with pytest.raises(ValueError):
            _check_duplicate_mount_name("folder", "OtherProject/Data/folder", seen)


# ---------------------------------------------------------------------------
# link_session CLI command — structural checks
# ---------------------------------------------------------------------------

class TestLinkSessionCommand:

    def test_command_exists(self):
        runner = CliRunner()
        result = runner.invoke(run_cloudos_cli, ["interactive-session", "link", "--help"])
        assert result.exit_code == 0
        assert "--session-id" in result.output
        assert "--job-id" in result.output

    def test_requires_session_id(self):
        runner = CliRunner()
        result = runner.invoke(run_cloudos_cli, [
            "interactive-session", "link",
            "s3://bucket/folder/",
            "--apikey", "key",
            "--cloudos-url", "http://test.com",
            "--workspace-id", "ws",
        ])
        assert result.exit_code != 0

    def test_path_and_job_id_are_mutually_exclusive(self):
        runner = CliRunner()
        result = runner.invoke(run_cloudos_cli, [
            "interactive-session", "link",
            "s3://bucket/folder/",
            "--apikey", "key",
            "--cloudos-url", "http://test.com",
            "--workspace-id", "ws",
            "--session-id", "sess123",
            "--job-id", "job456",
        ])
        assert result.exit_code != 0
        assert "Cannot use both" in result.output

    def test_results_flag_requires_job_id(self):
        runner = CliRunner()
        result = runner.invoke(run_cloudos_cli, [
            "interactive-session", "link",
            "s3://bucket/folder/",
            "--apikey", "key",
            "--cloudos-url", "http://test.com",
            "--workspace-id", "ws",
            "--session-id", "sess123",
            "--results",
        ])
        assert result.exit_code != 0
        assert "--results" in result.output or "job-id" in result.output.lower()

    def test_neither_path_nor_job_id_is_error(self):
        runner = CliRunner()
        result = runner.invoke(run_cloudos_cli, [
            "interactive-session", "link",
            "--apikey", "key",
            "--cloudos-url", "http://test.com",
            "--workspace-id", "ws",
            "--session-id", "sess123",
        ])
        assert result.exit_code != 0

    @patch("cloudos_cli.__main__.get_shared_config", return_value={})
    @patch("cloudos_cli.configure.configure.ConfigurationProfile.load_profile_and_validate_data")
    def test_top_level_folder_path_without_project_name_is_error(self, mock_config, _mock_shared):
        mock_config.return_value = {
            "apikey": "key",
            "cloudos_url": "http://test.com",
            "workspace_id": "ws",
            "project_name": None,
        }
        runner = CliRunner()
        result = runner.invoke(run_cloudos_cli, [
            "interactive-session", "link",
            "Data/my-folder",
            "--apikey", "key",
            "--cloudos-url", "http://test.com",
            "--workspace-id", "ws",
            "--session-id", "sess123",
        ])
        assert result.exit_code != 0
        assert "--project-name" in result.output

    @patch("cloudos_cli.interactive_session.cli._make_link_client")
    @patch("cloudos_cli.configure.configure.ConfigurationProfile.load_profile_and_validate_data")
    def test_s3_path_calls_link_folders_batch(self, mock_config, mock_make_client):
        mock_config.return_value = {
            "apikey": "key",
            "cloudos_url": "http://test.com",
            "workspace_id": "ws",
            "project_name": "proj",
        }
        mock_client = MagicMock()
        mock_client.link_folders_batch.return_value = True
        mock_make_client.return_value = mock_client

        runner = CliRunner()
        result = runner.invoke(run_cloudos_cli, [
            "interactive-session", "link",
            "s3://bucket/folder/",
            "--apikey", "key",
            "--cloudos-url", "http://test.com",
            "--workspace-id", "ws",
            "--session-id", "sess123",
        ])

        mock_client.link_folders_batch.assert_called_once()
        call_args = mock_client.link_folders_batch.call_args
        assert call_args[0][0] == ["s3://bucket/folder/"]
        assert call_args[0][1] == "sess123"

    @patch("cloudos_cli.interactive_session.cli._make_link_client")
    @patch("cloudos_cli.configure.configure.ConfigurationProfile.load_profile_and_validate_data")
    def test_file_explorer_path_infers_project(self, mock_config, mock_make_client):
        mock_config.return_value = {
            "apikey": "key",
            "cloudos_url": "http://test.com",
            "workspace_id": "ws",
            "project_name": None,
        }
        mock_client = MagicMock()
        mock_client.link_folders_batch.return_value = True
        mock_make_client.return_value = mock_client

        runner = CliRunner()
        result = runner.invoke(run_cloudos_cli, [
            "interactive-session", "link",
            "my-project/Data/folder",
            "--apikey", "key",
            "--cloudos-url", "http://test.com",
            "--workspace-id", "ws",
            "--session-id", "sess123",
        ])

        mock_make_client.assert_called_once()
        call_args = mock_make_client.call_args[0]
        assert call_args[:4] == ("http://test.com", "key", "ws", "my-project")
        call_args = mock_client.link_folders_batch.call_args
        assert call_args[0][0] == ["Data/folder"]

    @patch("cloudos_cli.interactive_session.cli._make_link_client")
    @patch("cloudos_cli.configure.configure.ConfigurationProfile.load_profile_and_validate_data")
    def test_multi_project_paths_grouped_correctly(self, mock_config, mock_make_client):
        mock_config.return_value = {
            "apikey": "key",
            "cloudos_url": "http://test.com",
            "workspace_id": "ws",
            "project_name": None,
        }
        mock_client = MagicMock()
        mock_client.link_folders_batch.return_value = True
        mock_make_client.return_value = mock_client

        runner = CliRunner()
        result = runner.invoke(run_cloudos_cli, [
            "interactive-session", "link",
            "proj-a/Data/folder1,proj-b/Data/folder2",
            "--apikey", "key",
            "--cloudos-url", "http://test.com",
            "--workspace-id", "ws",
            "--session-id", "sess123",
        ])

        # Two separate project groups → two client instantiations
        assert mock_make_client.call_count == 2
        projects_called = {call[0][3] for call in mock_make_client.call_args_list}
        assert projects_called == {"proj-a", "proj-b"}

    @patch("cloudos_cli.interactive_session.cli._make_link_client")
    @patch("cloudos_cli.configure.configure.ConfigurationProfile.load_profile_and_validate_data")
    def test_committed_count_accumulates_across_groups(self, mock_config, mock_make_client):
        """committed_count passed to second group reflects paths already submitted."""
        mock_config.return_value = {
            "apikey": "key",
            "cloudos_url": "http://test.com",
            "workspace_id": "ws",
            "project_name": None,
        }
        mock_client = MagicMock()
        mock_client.link_folders_batch.return_value = True
        mock_make_client.return_value = mock_client

        runner = CliRunner()
        runner.invoke(run_cloudos_cli, [
            "interactive-session", "link",
            "proj-a/Data/f1,proj-a/Data/f2,proj-b/Data/f3",
            "--apikey", "key",
            "--cloudos-url", "http://test.com",
            "--workspace-id", "ws",
            "--session-id", "sess123",
        ])

        calls = mock_client.link_folders_batch.call_args_list
        # First group (proj-a, 2 paths): committed_count=0
        # Second group (proj-b, 1 path): committed_count=2
        committed_counts = [c[1].get("committed_count", c[0][2] if len(c[0]) > 2 else 0)
                            for c in calls]
        assert 0 in committed_counts
        assert 2 in committed_counts

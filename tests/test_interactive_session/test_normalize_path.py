"""Unit tests for _normalize_file_explorer_path helper."""

import pytest
from cloudos_cli.interactive_session.cli import _normalize_file_explorer_path


class TestNormalizeFileExplorerPath:
    """Tests for _normalize_file_explorer_path."""

    # --- S3 / Azure paths are returned unchanged ---

    def test_s3_path_returned_unchanged(self):
        path, project = _normalize_file_explorer_path("s3://bucket/prefix/", "my-project")
        assert path == "s3://bucket/prefix/"
        assert project is None

    def test_s3_file_path_returned_unchanged(self):
        path, project = _normalize_file_explorer_path("s3://bucket/data/file.csv", "my-project")
        assert path == "s3://bucket/data/file.csv"
        assert project is None

    def test_s3_path_no_project_name_returns_none(self):
        path, project = _normalize_file_explorer_path("s3://bucket/prefix/", None)
        assert path == "s3://bucket/prefix/"
        assert project is None

    def test_azure_path_returned_unchanged(self):
        path, project = _normalize_file_explorer_path("az://container/blob/", "my-project")
        assert path == "az://container/blob/"
        assert project is None

    # --- Paths with no slash are treated as relative to project_name ---

    def test_single_segment_uses_project_name(self):
        path, project = _normalize_file_explorer_path("Results", "my-project")
        assert path == "Results"
        assert project == "my-project"

    def test_single_segment_no_project_name(self):
        path, project = _normalize_file_explorer_path("Results", None)
        assert path == "Results"
        assert project is None

    # --- Known root folders are treated as relative to project_name ---

    def test_data_folder_uses_project_name(self):
        path, project = _normalize_file_explorer_path("Data/Downloads", "my-project")
        assert path == "Data/Downloads"
        assert project == "my-project"

    def test_data_folder_case_insensitive(self):
        path, project = _normalize_file_explorer_path("data/Downloads", "my-project")
        assert path == "data/Downloads"
        assert project == "my-project"

    def test_analysesresults_folder_uses_project_name(self):
        path, project = _normalize_file_explorer_path("AnalysesResults/run-1", "my-project")
        assert path == "AnalysesResults/run-1"
        assert project == "my-project"

    def test_analyses_results_underscore_uses_project_name(self):
        path, project = _normalize_file_explorer_path("Analyses_Results/run-1", "my-project")
        assert path == "Analyses_Results/run-1"
        assert project == "my-project"

    def test_analyses_results_hyphen_uses_project_name(self):
        path, project = _normalize_file_explorer_path("Analyses-Results/run-1", "my-project")
        assert path == "Analyses-Results/run-1"
        assert project == "my-project"

    def test_cohorts_folder_uses_project_name(self):
        path, project = _normalize_file_explorer_path("Cohorts/cohort-a", "my-project")
        assert path == "Cohorts/cohort-a"
        assert project == "my-project"

    def test_known_root_deep_path_uses_project_name(self):
        path, project = _normalize_file_explorer_path("Data/folder/subfolder/file.csv", "my-project")
        assert path == "Data/folder/subfolder/file.csv"
        assert project == "my-project"

    # --- Paths whose first segment is the project name ---

    def test_explicit_project_name_extracted(self):
        path, project = _normalize_file_explorer_path("my-project/Data/file.csv", "other-project")
        assert path == "Data/file.csv"
        assert project == "my-project"

    def test_explicit_project_name_no_profile_project(self):
        path, project = _normalize_file_explorer_path("my-project/Data/file.csv", None)
        assert path == "Data/file.csv"
        assert project == "my-project"

    def test_explicit_project_with_deep_path(self):
        path, project = _normalize_file_explorer_path("proj/AnalysesResults/run-1/output.csv", None)
        assert path == "AnalysesResults/run-1/output.csv"
        assert project == "proj"

    def test_unknown_root_segment_treated_as_project(self):
        """A first segment that is not a known root folder is inferred as project name."""
        path, project = _normalize_file_explorer_path("custom-folder/subfolder", "profile-project")
        assert path == "subfolder"
        assert project == "custom-folder"

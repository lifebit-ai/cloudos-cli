"""Unit tests for _handle_mount_error, _translate_mount_error, and link_job_* methods."""

import pytest
from unittest import mock
from cloudos_cli.interactive_session.link import Link
from cloudos_cli.utils.errors import JoBNotCompletedException

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
# _translate_mount_error
# ---------------------------------------------------------------------------

class TestTranslateMountError:
    def test_prefix_does_not_exist(self, link_instance):
        result = link_instance._translate_mount_error("prefix does not exist in bucket")
        assert "prefix does not exist in bucket" in result
        assert "workspace may not have permission" in result

    def test_key_does_not_exist(self, link_instance):
        result = link_instance._translate_mount_error("key does not exist")
        assert "key does not exist" in result
        assert "Verify the path is correct" in result

    def test_access_denied(self, link_instance):
        result = link_instance._translate_mount_error("Access Denied")
        assert "Access Denied" in result
        assert "workspace does not have permission" in result

    def test_forbidden(self, link_instance):
        result = link_instance._translate_mount_error("Forbidden response from S3")
        assert "workspace does not have permission" in result

    def test_unknown_error_returned_unchanged(self, link_instance):
        result = link_instance._translate_mount_error("some unexpected error")
        assert result == "some unexpected error"


# ---------------------------------------------------------------------------
# _handle_mount_error
# ---------------------------------------------------------------------------

class TestHandleMountError:
    def test_403_already_mounted(self, link_instance):
        with pytest.raises(ValueError, match="already exists with 'mounted' status"):
            link_instance._handle_mount_error(Exception("403 already mounted item"), "S3")

    def test_403_not_active(self, link_instance):
        with pytest.raises(ValueError, match="not active or access denied"):
            link_instance._handle_mount_error(Exception("403 Forbidden access"), "S3")

    def test_401_unauthorized(self, link_instance):
        with pytest.raises(ValueError, match="Invalid API key"):
            link_instance._handle_mount_error(Exception("401 unauthorized"), "S3")

    def test_400_virtual_folder(self, link_instance):
        with pytest.raises(ValueError, match="Virtual folders cannot be linked"):
            link_instance._handle_mount_error(
                Exception("400 Invalid Supported DataItem folderType"), "S3"
            )

    def test_400_generic(self, link_instance):
        with pytest.raises(ValueError, match="Cannot link item"):
            link_instance._handle_mount_error(Exception("400 bad request"), "S3")

    def test_404_not_found(self, link_instance):
        with pytest.raises(ValueError, match="Session not found"):
            link_instance._handle_mount_error(Exception("404 not found"), "S3")

    def test_unknown_error(self, link_instance):
        with pytest.raises(ValueError, match="Failed to mount S3 item"):
            link_instance._handle_mount_error(Exception("connection timeout"), "S3")

    def test_type_folder_appears_in_message(self, link_instance):
        with pytest.raises(ValueError, match="File Explorer"):
            link_instance._handle_mount_error(Exception("connection reset"), "File Explorer")


# ---------------------------------------------------------------------------
# link_job_results
# ---------------------------------------------------------------------------

class TestLinkJobResults:
    def test_links_successfully(self, link_instance, capsys):
        link_instance.get_job_results = mock.Mock(return_value="s3://bucket/results/")
        link_instance.link_folder = mock.Mock(return_value=True)

        link_instance.link_job_results("job1", "ws1", "sess1", True)

        link_instance.link_folder.assert_called_once_with("s3://bucket/results/", "sess1")
        out = capsys.readouterr().out
        assert "Linking results" in out

    def test_no_results_path(self, link_instance, capsys):
        link_instance.get_job_results = mock.Mock(return_value=None)
        link_instance.link_job_results("job1", "ws1", "sess1", True)
        err = capsys.readouterr()
        assert "No results found" in err.out + err.err

    def test_mount_returns_false(self, link_instance, capsys):
        link_instance.get_job_results = mock.Mock(return_value="s3://bucket/results/")
        link_instance.link_folder = mock.Mock(return_value=False)
        link_instance.link_job_results("job1", "ws1", "sess1", True)
        # Should not raise; message printed
        link_instance.link_folder.assert_called_once()

    def test_job_not_completed_exception(self, link_instance, capsys):
        link_instance.get_job_results = mock.Mock(
            side_effect=JoBNotCompletedException("job1", "running")
        )
        link_instance.link_job_results("job1", "ws1", "sess1", True)
        err = capsys.readouterr()
        assert "Cannot link results" in err.out + err.err

    def test_results_not_available_exception(self, link_instance, capsys):
        link_instance.get_job_results = mock.Mock(
            side_effect=Exception("Results are not available")
        )
        link_instance.link_job_results("job1", "ws1", "sess1", True)
        err = capsys.readouterr()
        assert "Cannot link results" in err.out + err.err

    def test_generic_exception(self, link_instance, capsys):
        link_instance.get_job_results = mock.Mock(side_effect=Exception("network error"))
        link_instance.link_job_results("job1", "ws1", "sess1", True)
        err = capsys.readouterr()
        assert "Failed to link results" in err.out + err.err

    def test_verbose_prints_path(self, link_instance, capsys):
        link_instance.get_job_results = mock.Mock(return_value="s3://bucket/results/")
        link_instance.link_folder = mock.Mock(return_value=True)
        link_instance.link_job_results("job1", "ws1", "sess1", True, verbose=True)
        out = capsys.readouterr().out
        assert "s3://bucket/results/" in out


# ---------------------------------------------------------------------------
# link_job_workdir
# ---------------------------------------------------------------------------

class TestLinkJobWorkdir:
    def test_links_successfully(self, link_instance, capsys):
        link_instance.get_job_workdir = mock.Mock(return_value="s3://bucket/workdir/")
        link_instance.link_folder = mock.Mock(return_value=True)

        link_instance.link_job_workdir("job1", "ws1", "sess1", True)

        link_instance.link_folder.assert_called_once_with("s3://bucket/workdir/", "sess1")
        out = capsys.readouterr().out
        assert "Linking working directory" in out

    def test_no_workdir(self, link_instance, capsys):
        link_instance.get_job_workdir = mock.Mock(return_value=None)
        link_instance.link_job_workdir("job1", "ws1", "sess1", True)
        err = capsys.readouterr()
        assert "No working directory found" in err.out + err.err

    def test_mount_returns_false(self, link_instance, capsys):
        link_instance.get_job_workdir = mock.Mock(return_value="s3://bucket/workdir/")
        link_instance.link_folder = mock.Mock(return_value=False)
        link_instance.link_job_workdir("job1", "ws1", "sess1", True)
        link_instance.link_folder.assert_called_once()

    def test_not_available_exception(self, link_instance, capsys):
        link_instance.get_job_workdir = mock.Mock(
            side_effect=Exception("workdir not yet available")
        )
        link_instance.link_job_workdir("job1", "ws1", "sess1", True)
        err = capsys.readouterr()
        assert "Cannot link workdir" in err.out + err.err

    def test_generic_exception(self, link_instance, capsys):
        link_instance.get_job_workdir = mock.Mock(side_effect=Exception("network error"))
        link_instance.link_job_workdir("job1", "ws1", "sess1", True)
        err = capsys.readouterr()
        assert "Failed to link workdir" in err.out + err.err

    def test_workdir_stripped_of_whitespace(self, link_instance, capsys):
        link_instance.get_job_workdir = mock.Mock(return_value="  s3://bucket/workdir/  ")
        link_instance.link_folder = mock.Mock(return_value=True)
        link_instance.link_job_workdir("job1", "ws1", "sess1", True)
        link_instance.link_folder.assert_called_once_with("s3://bucket/workdir/", "sess1")


# ---------------------------------------------------------------------------
# link_job_logs
# ---------------------------------------------------------------------------

class TestLinkJobLogs:
    def test_links_successfully(self, link_instance, capsys):
        logs_dict = {"stdout": "s3://bucket/logs/stdout.txt"}
        link_instance.get_job_logs = mock.Mock(return_value=logs_dict)
        link_instance.link_folder = mock.Mock(return_value=True)

        link_instance.link_job_logs("job1", "ws1", "sess1", True)

        link_instance.link_folder.assert_called_once_with("s3://bucket/logs", "sess1")
        out = capsys.readouterr().out
        assert "Linking logs directory" in out

    def test_no_logs(self, link_instance, capsys):
        link_instance.get_job_logs = mock.Mock(return_value=None)
        link_instance.link_job_logs("job1", "ws1", "sess1", True)
        err = capsys.readouterr()
        assert "No logs found" in err.out + err.err

    def test_empty_logs_dict(self, link_instance, capsys):
        link_instance.get_job_logs = mock.Mock(return_value={})
        link_instance.link_job_logs("job1", "ws1", "sess1", True)
        err = capsys.readouterr()
        assert "No logs found" in err.out + err.err

    def test_mount_returns_false(self, link_instance, capsys):
        link_instance.get_job_logs = mock.Mock(
            return_value={"stdout": "s3://bucket/logs/stdout.txt"}
        )
        link_instance.link_folder = mock.Mock(return_value=False)
        link_instance.link_job_logs("job1", "ws1", "sess1", True)
        link_instance.link_folder.assert_called_once()

    def test_not_available_exception(self, link_instance, capsys):
        link_instance.get_job_logs = mock.Mock(
            side_effect=Exception("logs not yet available")
        )
        link_instance.link_job_logs("job1", "ws1", "sess1", True)
        err = capsys.readouterr()
        assert "Cannot link logs" in err.out + err.err

    def test_generic_exception(self, link_instance, capsys):
        link_instance.get_job_logs = mock.Mock(side_effect=Exception("connection reset"))
        link_instance.link_job_logs("job1", "ws1", "sess1", True)
        err = capsys.readouterr()
        assert "Failed to link logs" in err.out + err.err

    def test_verbose_prints_logs_dir(self, link_instance, capsys):
        link_instance.get_job_logs = mock.Mock(
            return_value={"stdout": "s3://bucket/logs/stdout.txt"}
        )
        link_instance.link_folder = mock.Mock(return_value=True)
        link_instance.link_job_logs("job1", "ws1", "sess1", True, verbose=True)
        out = capsys.readouterr().out
        assert "s3://bucket/logs" in out

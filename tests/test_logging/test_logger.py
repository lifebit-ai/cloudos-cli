"""Pytest tests for cloudos_cli.logging.logger module"""
import json
import logging
import os
import sys
import tempfile
import datetime as dt
from unittest.mock import Mock, patch
from pathlib import Path
import pytest

from cloudos_cli.logging.logger import (
    LogFormatter,
    CommandContextFilter,
    PrivateFileHandler,
    mask_secret_values,
    redact_argv,
    redact_params,
    secure_log_dir,
    _cmd_filter_factory,
    setup_logging,
    update_command_context_from_click,
    LOG_CONFIG
)


class TestLogFormatter:
    """Test cases for LogFormatter class"""

    def test_log_formatter_init_default(self):
        """Test LogFormatter initialization with default fmt_keys"""
        formatter = LogFormatter()
        assert formatter.fmt_keys == {}

    def test_log_formatter_init_with_fmt_keys(self):
        """Test LogFormatter initialization with custom fmt_keys"""
        fmt_keys = {"level": "levelname", "msg": "message"}
        formatter = LogFormatter(fmt_keys=fmt_keys)
        assert formatter.fmt_keys == fmt_keys

    def test_format_basic_log_record(self):
        """Test formatting a basic log record"""
        formatter = LogFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )

        result = formatter.format(record)
        parsed_result = json.loads(result)

        assert "message" in parsed_result
        assert "timestamp" in parsed_result
        assert parsed_result["message"] == "Test message"

        # Verify timestamp format (ISO format with timezone)
        timestamp = parsed_result["timestamp"]
        assert timestamp.endswith("+00:00")  # UTC timezone

    def test_format_with_custom_fmt_keys(self):
        """Test formatting with custom fmt_keys"""
        fmt_keys = {"level": "levelname", "logger_name": "name"}
        formatter = LogFormatter(fmt_keys=fmt_keys)
        record = logging.LogRecord(
            name="test_logger",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Error message",
            args=(),
            exc_info=None
        )

        result = formatter.format(record)
        parsed_result = json.loads(result)

        assert parsed_result["level"] == "ERROR"
        assert parsed_result["logger_name"] == "test_logger"
        assert "message" in parsed_result
        assert "timestamp" in parsed_result

    def test_format_with_exception_info(self):
        """Test formatting log record with exception info"""
        formatter = LogFormatter()

        try:
            raise ValueError("Test exception")
        except ValueError:
            exc_info = sys.exc_info()
            record = logging.LogRecord(
                name="test_logger",
                level=logging.ERROR,
                pathname="test.py",
                lineno=1,
                msg="Error occurred",
                args=(),
                exc_info=exc_info
            )

        result = formatter.format(record)
        parsed_result = json.loads(result)

        assert "exc_info" in parsed_result
        assert "ValueError: Test exception" in parsed_result["exc_info"]

    def test_prepare_log_dict(self):
        """Test _prepare_log_dict method"""
        fmt_keys = {"level": "levelname", "module": "module"}
        formatter = LogFormatter(fmt_keys=fmt_keys)
        record = logging.LogRecord(
            name="test_logger",
            level=logging.WARNING,
            pathname="test.py",
            lineno=1,
            msg="Warning message",
            args=(),
            exc_info=None
        )
        record.module = "test_module"

        result = formatter._prepare_log_dict(record)

        assert result["level"] == "WARNING"
        assert result["module"] == "test_module"
        assert result["message"] == "Warning message"
        assert "timestamp" in result


class TestCommandContextFilter:
    """Test cases for CommandContextFilter class"""

    def test_init_default(self):
        """Test CommandContextFilter initialization with defaults"""
        filter_obj = CommandContextFilter()
        assert filter_obj.command is None
        assert filter_obj.params is None

    def test_init_with_values(self):
        """Test CommandContextFilter initialization with values"""
        filter_obj = CommandContextFilter(command="test command", params={"key": "value"})
        assert filter_obj.command == "test command"
        assert filter_obj.params == {"key": "value"}

    @patch('sys.argv', ['cloudos-cli', 'jobs', 'run', '--debug'])
    def test_set_seed_from_argv(self):
        """Test setting command from sys.argv"""
        filter_obj = CommandContextFilter()
        filter_obj.set_seed_from_argv()

        assert filter_obj.command == "cloudos-cli jobs run --debug"
        assert filter_obj.params is None

    def test_set_from_click_ctx(self):
        """Test setting command and params from Click context"""
        # Mock Click context
        ctx = Mock()
        ctx.command_path = "cloudos-cli jobs run"
        ctx.params = {"debug": True, "project_id": "123"}

        filter_obj = CommandContextFilter()
        filter_obj.set_from_click_ctx(ctx)

        assert filter_obj.command == "cloudos-cli jobs run"
        assert filter_obj.params == {"debug": True, "project_id": "123"}

    def test_set_from_click_ctx_none_params(self):
        """Test setting command from Click context with None params"""
        ctx = Mock()
        ctx.command_path = "cloudos-cli version"
        ctx.params = None

        filter_obj = CommandContextFilter()
        filter_obj.set_from_click_ctx(ctx)

        assert filter_obj.command == "cloudos-cli version"
        assert filter_obj.params is None

    def test_set_from_click_ctx_none(self):
        """Test setting from None Click context"""
        filter_obj = CommandContextFilter()

        # The current implementation will raise AttributeError when ctx is None
        # because it tries to access ctx.command_path before checking if ctx is None
        with pytest.raises(AttributeError):
            filter_obj.set_from_click_ctx(None)

    def test_filter_adds_missing_attributes(self):
        """Test filter method adds missing command and params attributes"""
        filter_obj = CommandContextFilter(command="test command", params={"test": True})
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )

        result = filter_obj.filter(record)

        assert result is True
        assert record.command == "test command"
        assert record.params == {"test": True}

    def test_filter_preserves_existing_attributes(self):
        """Test filter method preserves existing command and params attributes"""
        filter_obj = CommandContextFilter(command="default command", params={"default": True})
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.command = "existing command"
        record.params = {"existing": True}

        result = filter_obj.filter(record)

        assert result is True
        assert record.command == "existing command"
        assert record.params == {"existing": True}


class TestRedactParams:
    """Test cases for redacting secret-bearing params"""

    def test_redact_params_masks_secrets(self):
        """Test that apikey, tokens, secrets, passwords and keys are masked"""
        params = {
            "apikey": "my-secret-apikey-1234",
            "cromwell_token": "cromwell-secret",
            "Github_Token": "gh-secret",
            "client_secret": "client-secret",
            "db_password": "pw-secret",
            "ssh_key": "key-secret",
            "project_name": "my-project",
            "debug": True,
        }

        result = redact_params(params)

        for name in ["apikey", "cromwell_token", "Github_Token", "client_secret", "db_password", "ssh_key"]:
            assert result[name] == "***"
        assert result["project_name"] == "my-project"
        assert result["debug"] is True
        # the original dict is left untouched
        assert params["apikey"] == "my-secret-apikey-1234"

    def test_redact_params_keeps_unset_secrets(self):
        """Test that unset (None) secret params stay None"""
        assert redact_params({"apikey": None}) == {"apikey": None}

    def test_redact_params_non_dict(self):
        """Test that non-dict params are returned unchanged"""
        assert redact_params(None) is None

    def test_redact_argv_masks_secret_option_values(self):
        """Test that secret option values are masked in every argv form"""
        argv = ["cloudos", "job", "run", "--apikey", "secret1", "-k", "secret2", "-ksecret3",
                "--apikey=secret4", "--cromwell-token", "secret5", "--workspace-id", "ws123", "--debug"]

        result = redact_argv(argv)

        assert result == ["cloudos", "job", "run", "--apikey", "***", "-k", "***", "-k***",
                          "--apikey=***", "--cromwell-token", "***", "--workspace-id", "ws123", "--debug"]

    def test_redact_argv_masks_cromwell_token_short_flag(self):
        """Test that -t (--cromwell-token) values are masked"""
        assert redact_argv(["cloudos", "cromwell", "status", "-t", "secret1", "-tsecret2"]) == \
            ["cloudos", "cromwell", "status", "-t", "***", "-t***"]

    def test_redact_argv_masks_secret_assignments(self):
        """Test that secret name=value assignments inside free-form args are masked"""
        argv = ["cloudos", "bash", "job", "--parameter", "password=secret1", "--parameter", "reads=s3://bucket/r.fq",
                "--parameter=db_token=secret2", "--command", "export API_KEY='secret 3' && echo GENOME=hg38"]

        result = redact_argv(argv)

        assert result == ["cloudos", "bash", "job", "--parameter", "password=***", "--parameter", "reads=s3://bucket/r.fq",
                          "--parameter=db_token=***", "--command", "export API_KEY=*** && echo GENOME=hg38"]

    def test_redact_assignments_masks_whole_secret_values(self):
        """Test that secrets with spaces or escaped quotes are fully masked"""
        params = {
            "parameter": ("password=two words", "--db_token=a b c", "reads=s3://bucket/r f.fq"),
            "command": 'export API_KEY="a\\"b-secret" && echo done',
        }

        result = redact_params(params)

        assert result["parameter"] == ("password=***", "--db_token=***", "reads=s3://bucket/r f.fq")
        assert result["command"] == "export API_KEY=*** && echo done"
        assert redact_argv(["cloudos", "--parameter", "password=two words", "--parameter=password=two words"]) == \
            ["cloudos", "--parameter", "password=***", "--parameter=password=***"]

    def test_redact_params_masks_secret_assignments(self):
        """Test that secret name=value assignments inside parameter and command values are masked"""
        params = {
            "parameter": ("password=secret1", "reads=s3://bucket/r.fq", "-db_token=secret2"),
            "command": 'export TOKEN="secret 3"; run --genome=hg38',
            "workspace_id": "ws123",
        }

        result = redact_params(params)

        assert result["parameter"] == ("password=***", "reads=s3://bucket/r.fq", "-db_token=***")
        assert result["command"] == "export TOKEN=***; run --genome=hg38"
        assert result["workspace_id"] == "ws123"

    @patch('sys.argv', ['cloudos', 'job', 'run', '--apikey', 'my-secret-apikey-1234', '--workspace-id', 'ws123'])
    def test_set_seed_from_argv_redacts_apikey(self):
        """Test that the argv seed, used before Click has parsed, does not keep the apikey"""
        filter_obj = CommandContextFilter()
        filter_obj.set_seed_from_argv()

        assert filter_obj.command == "cloudos job run --apikey *** --workspace-id ws123"

    def test_filter_redacts_apikey_from_click_ctx(self):
        """Test that the apikey value never reaches an emitted record's params"""
        ctx = Mock()
        ctx.command_path = "cloudos-cli job run"
        ctx.params = {"apikey": "my-secret-apikey-1234", "cromwell_token": "cromwell-secret",
                      "workspace_id": "ws123"}
        filter_obj = CommandContextFilter()
        filter_obj.set_from_click_ctx(ctx)
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )

        filter_obj.filter(record)

        assert record.params["apikey"] == "***"
        assert record.params["cromwell_token"] == "***"
        assert record.params["workspace_id"] == "ws123"
        formatted = LogFormatter(fmt_keys={"params": "params"}).format(record)
        assert "my-secret-apikey-1234" not in formatted
        assert "cromwell-secret" not in formatted

    def test_filter_redacts_existing_record_params(self):
        """Test that params passed on the record itself are redacted too"""
        filter_obj = CommandContextFilter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.params = {"apikey": "my-secret-apikey-1234"}

        filter_obj.filter(record)

        assert record.params == {"apikey": "***"}

    def test_redact_long_assignment_chain_does_not_raise(self):
        """Test that a long name=value chain in one value is handled without recursion"""
        value = "sample_map=" + ",".join(f"S{i}=s3://b/S{i}.fq" for i in range(2000))

        assert redact_argv(["cloudos", "--parameter", value]) == ["cloudos", "--parameter", value]
        assert redact_params({"parameter": (value,)}) == {"parameter": (value,)}
        assert redact_params({"parameter": (value + ",password=secret1",)}) == \
            {"parameter": (value + ",password=***",)}
        with patch('sys.argv', ['cloudos', 'job', 'run', '--parameter', value]):
            CommandContextFilter().set_seed_from_argv()

    def test_redact_free_form_secret_forms(self):
        """Test that secret options, auth headers and URL credentials inside free-form values are masked"""
        cases = {
            "cloudos job list --apikey S3CRET-1 --workspace-id ws": "cloudos job list --apikey *** --workspace-id ws",
            "cloudos job list -k a1b2c3d4e5f6a7b8c9d0e1f2 --workspace-id ws": "cloudos job list -k *** --workspace-id ws",
            "cloudos cromwell status -t 'a1b2c3d4 e5f6a7b8c9d0'": "cloudos cromwell status -t ***",
            "curl -H 'Authorization: Bearer a1b2c3d4e5f6a7b8c9d0e1f2'": "curl -H 'Authorization: Bearer ***'",
            "curl -H 'Authorization: Basic YWRtaW46cGFzc3dvcmQxMjM='": "curl -H 'Authorization: Basic ***'",
            "psql postgres://admin:S3CRET-5@db:5432/x": "psql postgres://admin:***@db:5432/x",
            "run --workspace-id ws123 https://host/path user@host": "run --workspace-id ws123 https://host/path user@host",
            # ordinary -k/-t flags and words after Bearer/Basic are not credentials
            "sort -k 2 in.txt | cut -t , -f 1": "sort -k 2 in.txt | cut -t , -f 1",
            "Basic variant calling": "Basic variant calling",
        }
        for command, expected in cases.items():
            assert redact_params({"command": command}) == {"command": expected}
            assert redact_argv(["cloudos", "bash", "job", "--command", command]) == \
                ["cloudos", "bash", "job", "--command", expected]
        assert redact_params({"parameter": ("db_url=postgres://admin:S3CRET-6@db:5432/x",)}) == \
            {"parameter": ("db_url=postgres://admin:***@db:5432/x",)}
        params = {"job_name": "Basic variant calling", "parameter": ("mode=Basic alignment",)}
        assert redact_params(params) == params
        assert redact_argv(["cloudos", "bash", "job", "--job-name", "Basic variant calling"]) == \
            ["cloudos", "bash", "job", "--job-name", "Basic variant calling"]


class TestSecretValuesInMessages:
    """Test cases for masking raw secret values in log messages and tracebacks"""

    @staticmethod
    def _record(msg, exc_info=None):
        return logging.LogRecord(
            name="test_logger",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg=msg,
            args=(),
            exc_info=exc_info
        )

    def test_mask_secret_values(self):
        """Test that raw and stripped secret values are masked and short values are ignored"""
        text = "header value: ' my-secret' and my-secret and abc"
        assert mask_secret_values(text, {" my-secret", "abc"}) == "header value: ' ***' and *** and abc"

    def test_filter_masks_secret_in_message(self):
        """Test that an exception message carrying the apikey is masked"""
        filter_obj = CommandContextFilter(params={"apikey": " my-secret", "workspace_id": "ws1"})
        record = self._record(ValueError("Invalid header value: ' my-secret'"))

        filter_obj.filter(record)

        assert record.getMessage() == "Invalid header value: ' ***'"
        assert record.params["apikey"] == "***"

    def test_filter_masks_secret_in_exc_info(self):
        """Test that a traceback carrying the apikey is masked in the formatted record"""
        try:
            raise ValueError("Invalid header value: ' my-secret'")
        except ValueError:
            record = self._record("Error occurred", exc_info=sys.exc_info())
        filter_obj = CommandContextFilter(params={"apikey": " my-secret"})

        filter_obj.filter(record)
        formatted = LogFormatter(fmt_keys={"exc_info": "exc_info"}).format(record)

        assert "my-secret" not in formatted
        assert "Invalid header value: ' ***'" in json.loads(formatted)["exc_info"]

    @patch('sys.argv', ['cloudos', 'job', 'list', '-k', 'argv-secret-1234', '--workspace-id', 'ws1'])
    def test_filter_masks_argv_secret_before_click(self):
        """Test that a secret only seen in argv (before Click parsed) is masked in messages"""
        filter_obj = CommandContextFilter()
        filter_obj.set_seed_from_argv()
        record = self._record("failed with key argv-secret-1234")

        filter_obj.filter(record)

        assert record.getMessage() == "failed with key ***"

    @patch('sys.argv', ['cloudos', 'job', 'list'])
    def test_setup_logging_masks_secret_in_log_file(self, tmp_path):
        """Test end to end that an exception carrying the apikey is masked in the log file"""
        import cloudos_cli.logging.logger as logger_module
        logger_module._cmd_filter_instance = None
        try:
            with patch.object(Path, "home", return_value=tmp_path):
                setup_logging(debug=True)
                ctx = Mock()
                ctx.command_path = "cloudos job list"
                ctx.params = {"apikey": " MY-SECRET-KEY-123", "workspace_id": "ws1"}
                update_command_context_from_click(ctx)
                try:
                    raise ValueError("header value: ' MY-SECRET-KEY-123'")
                except ValueError as exc:
                    logging.getLogger("CloudOS").error(exc, exc_info=exc)

            log_file = next((tmp_path / ".cloudos" / "logs").glob("cloudos-*.jsonl"))
            log_content = log_file.read_text()
            assert "MY-SECRET-KEY-123" not in log_content
            assert "header value: ' ***'" in log_content
        finally:
            root = logging.getLogger()
            for handler in root.handlers:
                handler.close()
            root.handlers.clear()
            logger_module._cmd_filter_instance = None


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX file modes only")
class TestLogFilePermissions:
    """Test cases for log file and directory permissions"""

    def teardown_method(self):
        """Close and clear handlers so the temporary log file is released"""
        root = logging.getLogger()
        for handler in root.handlers:
            handler.close()
        root.handlers.clear()

    def test_private_file_handler_creates_file_0600(self, tmp_path):
        """Test that PrivateFileHandler creates its file with mode 0600"""
        log_file = tmp_path / "test.jsonl"
        handler = PrivateFileHandler(str(log_file))
        handler.close()

        assert log_file.stat().st_mode & 0o777 == 0o600

    def test_private_file_handler_tightens_existing_file(self, tmp_path):
        """Test that an existing world-readable log file is reset to 0600"""
        log_file = tmp_path / "test.jsonl"
        log_file.write_text("")
        log_file.chmod(0o644)

        handler = PrivateFileHandler(str(log_file))
        handler.close()

        assert log_file.stat().st_mode & 0o777 == 0o600

    @patch('sys.argv', ['cloudos-cli', 'job', 'run'])
    def test_setup_logging_private_dir_and_file(self, tmp_path):
        """Test that setup_logging creates a 0700 log dir and a 0600 log file without the apikey"""
        import cloudos_cli.logging.logger as logger_module
        logger_module._cmd_filter_instance = None

        with patch.object(Path, "home", return_value=tmp_path):
            setup_logging(debug=True)
            ctx = Mock()
            ctx.command_path = "cloudos-cli job run"
            ctx.params = {"apikey": "my-secret-apikey-1234", "workspace_id": "ws123"}
            update_command_context_from_click(ctx)
            logging.getLogger("test_logger").info("Test info message")

        log_dir = tmp_path / ".cloudos" / "logs"
        log_files = list(log_dir.glob("cloudos-*.jsonl"))
        assert len(log_files) == 1
        assert log_dir.stat().st_mode & 0o777 == 0o700
        assert log_files[0].stat().st_mode & 0o777 == 0o600

        log_content = log_files[0].read_text()
        assert "Test info message" in log_content
        assert "my-secret-apikey-1234" not in log_content
        assert json.loads(log_content.strip().splitlines()[-1])["params"]["apikey"] == "***"

        logger_module._cmd_filter_instance = None

    def test_setup_logging_tightens_existing_dir(self, tmp_path):
        """Test that an existing world-readable log dir is reset to 0700"""
        log_dir = tmp_path / ".cloudos" / "logs"
        log_dir.mkdir(parents=True)
        log_dir.chmod(0o755)

        with patch.object(Path, "home", return_value=tmp_path):
            setup_logging(debug=False)

        assert log_dir.stat().st_mode & 0o777 == 0o700

    def test_secure_log_dir_tightens_existing_dir_and_files(self, tmp_path):
        """Test that a 0755 log dir and 0644 log files from earlier versions become 0700 and 0600"""
        log_dir = tmp_path / ".cloudos" / "logs"
        log_dir.mkdir(parents=True)
        log_dir.chmod(0o755)
        old_file = log_dir / "cloudos-20260101-000000.jsonl"
        old_file.write_text("{}\n")
        old_file.chmod(0o644)

        with patch.object(Path, "home", return_value=tmp_path):
            assert secure_log_dir() == str(log_dir)

        assert log_dir.stat().st_mode & 0o777 == 0o700
        assert old_file.stat().st_mode & 0o777 == 0o600
        assert old_file.read_text() == "{}\n"

    def test_secure_log_dir_does_not_raise(self, tmp_path):
        """Test that a log dir that can't be changed does not break the CLI"""
        with patch.object(Path, "home", return_value=tmp_path), \
                patch("cloudos_cli.logging.logger.os.chmod", side_effect=PermissionError("denied")):
            secure_log_dir()

    def test_cli_start_up_secures_log_dir(self, tmp_path, monkeypatch):
        """Test that a normal (non-crashing) CLI run tightens the log dir and old log files"""
        from click.testing import CliRunner
        from cloudos_cli.__main__ import run_cloudos_cli

        monkeypatch.setenv("HOME", str(tmp_path))
        log_dir = tmp_path / ".cloudos" / "logs"
        log_dir.mkdir(parents=True)
        log_dir.chmod(0o755)
        old_file = log_dir / "cloudos-20260101-000000.jsonl"
        old_file.write_text("{}\n")
        old_file.chmod(0o644)

        with patch.object(Path, "home", return_value=tmp_path):
            result = CliRunner().invoke(run_cloudos_cli, ["job", "--help"])

        assert result.exit_code == 0
        assert log_dir.stat().st_mode & 0o777 == 0o700
        assert old_file.stat().st_mode & 0o777 == 0o600


class TestCmdFilterFactory:
    """Test cases for _cmd_filter_factory function"""

    @patch('sys.argv', ['cloudos-cli', 'test'])
    def test_cmd_filter_factory_creates_singleton(self):
        """Test that _cmd_filter_factory creates and returns the same instance"""
        # Reset global instance
        import cloudos_cli.logging.logger as logger_module
        logger_module._cmd_filter_instance = None

        filter1 = _cmd_filter_factory()
        filter2 = _cmd_filter_factory()

        assert filter1 is filter2
        assert isinstance(filter1, CommandContextFilter)
        assert filter1.command == "cloudos-cli test"

    @patch('sys.argv', ['cloudos-cli', 'jobs', 'list'])
    def test_cmd_filter_factory_sets_command_from_argv(self):
        """Test that factory sets command from sys.argv"""
        # Reset global instance
        import cloudos_cli.logging.logger as logger_module
        logger_module._cmd_filter_instance = None

        filter_obj = _cmd_filter_factory()

        assert filter_obj.command == "cloudos-cli jobs list"
        assert filter_obj.params is None


class TestSetupLogging:
    """Test cases for setup_logging function"""

    def setup_method(self):
        """Setup for each test method"""
        # Clear any existing handlers
        logging.getLogger().handlers.clear()

        # Create temporary directory for log files
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)

        # Track log files for cleanup
        self.log_dir = os.path.join(Path.home(), ".cloudos/logs")
        self.log_files_before = set()
        if os.path.exists(self.log_dir):
            self.log_files_before = set(Path(self.log_dir).glob("cloudos-*.jsonl"))

    def teardown_method(self):
        """Cleanup after each test method"""
        # Restore original directory
        os.chdir(self.original_cwd)

        # Clean up temporary directory
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

        # Clean up log files created during test
        if os.path.exists(self.log_dir):
            log_files_after = set(Path(self.log_dir).glob("cloudos-*.jsonl"))
            new_log_files = log_files_after - self.log_files_before
            for log_file in new_log_files:
                try:
                    log_file.unlink()
                except FileNotFoundError:
                    pass  # File already removed

        # Clear handlers
        logging.getLogger().handlers.clear()

    @patch('cloudos_cli.logging.logger._cmd_filter_factory')
    def test_setup_logging_debug_true(self, mock_filter_factory):
        """Test setup_logging with debug=True"""
        mock_filter = Mock()
        mock_filter_factory.return_value = mock_filter

        setup_logging(debug=True)

        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG
        assert len(root_logger.handlers) > 0

        # Check that log directory was created
        log_dir = os.path.join(Path.home(), ".cloudos/logs")
        assert os.path.exists(log_dir)

        # Check that log file was created
        log_files = list(Path(log_dir).glob("cloudos-*.jsonl"))
        assert len(log_files) > 0

    @patch('cloudos_cli.logging.logger._cmd_filter_factory')
    def test_setup_logging_debug_false(self, mock_filter_factory):
        """Test setup_logging with debug=False"""
        mock_filter = Mock()
        mock_filter_factory.return_value = mock_filter

        setup_logging(debug=False)

        root_logger = logging.getLogger()
        assert root_logger.level == logging.WARNING
        assert len(root_logger.handlers) > 0

        # Check that log directory was created
        log_dir = os.path.join(Path.home(), ".cloudos/logs")
        assert os.path.exists(log_dir)

    @patch('cloudos_cli.logging.logger._cmd_filter_factory')
    def test_setup_logging_creates_timestamped_filename(self, mock_filter_factory):
        """Test that setup_logging creates timestamped log filename"""
        mock_filter = Mock()
        mock_filter_factory.return_value = mock_filter

        with patch('cloudos_cli.logging.logger.dt.datetime') as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "20240901-120000"
            mock_datetime.fromtimestamp.return_value = dt.datetime.now()

            setup_logging(debug=True)

            expected_filename = os.path.join(Path.home(), ".cloudos/logs/cloudos-20240901-120000.jsonl")
            assert os.path.exists(expected_filename)

    @patch('cloudos_cli.logging.logger._cmd_filter_factory')
    def test_setup_logging_formatter_configuration(self, mock_filter_factory):
        """Test that setup_logging configures formatters correctly"""
        mock_filter = Mock()
        mock_filter_factory.return_value = mock_filter

        setup_logging(debug=True)

        root_logger = logging.getLogger()

        # Test that handlers have LogFormatter instances
        for handler in root_logger.handlers:
            assert isinstance(handler.formatter, LogFormatter)


class TestUpdateCommandContextFromClick:
    """Test cases for update_command_context_from_click function"""

    @patch('cloudos_cli.logging.logger._cmd_filter_factory')
    def test_update_command_context_from_click(self, mock_filter_factory):
        """Test updating command context from Click context"""
        mock_filter = Mock()
        mock_filter_factory.return_value = mock_filter

        ctx = Mock()
        ctx.command_path = "cloudos-cli jobs submit"
        ctx.params = {"workflow_id": "wf123", "debug": False}

        update_command_context_from_click(ctx)

        mock_filter.set_from_click_ctx.assert_called_once_with(ctx)


class TestLogConfig:
    """Test cases for LOG_CONFIG dictionary"""

    def test_log_config_structure(self):
        """Test that LOG_CONFIG has expected structure"""
        assert "version" in LOG_CONFIG
        assert LOG_CONFIG["version"] == 1

        assert "disable_existing_loggers" in LOG_CONFIG
        assert LOG_CONFIG["disable_existing_loggers"] is False

        assert "formatters" in LOG_CONFIG
        assert "json" in LOG_CONFIG["formatters"]
        assert "simple" in LOG_CONFIG["formatters"]

        assert "filters" in LOG_CONFIG
        assert "cmdctx" in LOG_CONFIG["filters"]

        assert "handlers" in LOG_CONFIG
        assert "file" in LOG_CONFIG["handlers"]
        assert "stderr" in LOG_CONFIG["handlers"]

        assert "root" in LOG_CONFIG

    def test_log_config_handlers_configuration(self):
        """Test handlers configuration in LOG_CONFIG"""
        file_handler = LOG_CONFIG["handlers"]["file"]
        assert file_handler["class"] == "cloudos_cli.logging.logger.PrivateFileHandler"
        assert file_handler["level"] == "DEBUG"
        assert file_handler["formatter"] == "json"
        assert "cmdctx" in file_handler["filters"]

        stderr_handler = LOG_CONFIG["handlers"]["stderr"]
        assert stderr_handler["class"] == "logging.StreamHandler"
        assert stderr_handler["level"] == "ERROR"
        assert stderr_handler["formatter"] == "simple"
        assert "cmdctx" in stderr_handler["filters"]

    def test_log_config_root_configuration(self):
        """Test root logger configuration in LOG_CONFIG"""
        root_config = LOG_CONFIG["root"]
        assert root_config["level"] == "DEBUG"
        assert "file" in root_config["handlers"]


class TestIntegration:
    """Integration tests for the logging system"""

    def setup_method(self):
        """Setup for each test method"""
        # Clear any existing handlers
        logging.getLogger().handlers.clear()

        # Create temporary directory for log files
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)

        # Track log files for cleanup
        self.log_dir = os.path.join(Path.home(), ".cloudos/logs")
        self.log_files_before = set()
        if os.path.exists(self.log_dir):
            self.log_files_before = set(Path(self.log_dir).glob("cloudos-*.jsonl"))

    def teardown_method(self):
        """Cleanup after each test method"""
        # Restore original directory
        os.chdir(self.original_cwd)

        # Clean up temporary directory
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

        # Clean up log files created during test
        if os.path.exists(self.log_dir):
            log_files_after = set(Path(self.log_dir).glob("cloudos-*.jsonl"))
            new_log_files = log_files_after - self.log_files_before
            for log_file in new_log_files:
                try:
                    log_file.unlink()
                except FileNotFoundError:
                    pass  # File already removed

        # Clear handlers
        logging.getLogger().handlers.clear()

    @patch('sys.argv', ['cloudos-cli', 'jobs', 'run'])
    @patch('cloudos_cli.logging.logger._cmd_filter_factory')
    def test_end_to_end_logging_workflow(self, mock_filter_factory):
        """Test complete logging workflow from setup to log output"""
        # Reset global instance
        import cloudos_cli.logging.logger as logger_module
        logger_module._cmd_filter_instance = None

        # Create real filter for integration test
        mock_filter_factory.side_effect = lambda: CommandContextFilter()

        # Setup logging
        setup_logging(debug=True)

        # Create a Click context and update command context
        ctx = Mock()
        ctx.command_path = "cloudos-cli jobs run"
        ctx.params = {"project_id": "proj123", "debug": True}
        update_command_context_from_click(ctx)

        # Log some messages
        logger = logging.getLogger("test_logger")
        logger.info("Test info message")
        logger.warning("Test warning message")
        logger.error("Test error message")

        # Verify log file was created and contains expected content
        log_dir = os.path.join(Path.home(), ".cloudos/logs")
        log_files = list(Path(log_dir).glob("cloudos-*.jsonl"))
        assert len(log_files) >= 1

        # Get the most recent log file (the one just created)
        log_file = max(log_files, key=lambda f: f.stat().st_mtime)
        with open(log_file, 'r') as f:
            log_content = f.read()

        # Verify log contains expected messages
        assert "Test info message" in log_content
        assert "Test warning message" in log_content
        assert "Test error message" in log_content

        # Verify JSON structure
        log_lines = log_content.strip().split('\n')
        for line in log_lines:
            if line:  # Skip empty lines
                log_entry = json.loads(line)
                assert "message" in log_entry
                assert "timestamp" in log_entry
                assert "level" in log_entry
                assert "command" in log_entry
                assert "params" in log_entry

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
        assert file_handler["class"] == "logging.FileHandler"
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

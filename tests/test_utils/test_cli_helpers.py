"""Pytest tests for cloudos_cli.utils.cli_helpers output sanitising"""
from unittest.mock import patch

import pytest

from cloudos_cli.utils.cli_helpers import custom_exception_handler, strip_control_chars


@pytest.fixture(autouse=True)
def no_log_file():
    """Keep custom_exception_handler from writing to ~/.cloudos/logs and from showing tracebacks."""
    with patch('cloudos_cli.utils.cli_helpers.setup_logging'), \
            patch('cloudos_cli.utils.cli_helpers.get_debug_mode', return_value=False):
        yield


class TestStripControlChars:
    def test_strips_c0_del_and_c1(self):
        """Test that ESC, CR, BEL, DEL and C1 characters are removed"""
        assert strip_control_chars("a\x1b[31mb\x07c\rd\x7fe\x9b2Jf\x00") == "a[31mbcde2Jf"

    def test_keeps_tab_newline_and_unicode(self):
        """Test that tabs, newlines and printable unicode are kept"""
        assert strip_control_chars("name\twith\nlines é 文件") == "name\twith\nlines é 文件"

    def test_converts_non_strings(self):
        """Test that non-string values are converted to text"""
        assert strip_control_chars(1024) == "1024"


class TestCustomExceptionHandlerOutput:
    @pytest.mark.parametrize("message", [
        "File '[link=https://evil.example]report.pdf[/link]' not found",
        "Rename failed. 400 - unexpected [/oops] tag",
        "[bold]not bold[/bold]",
    ])
    def test_markup_in_error_is_printed_literally(self, capsys, message):
        """Test that rich markup in an error message is printed as text instead of being interpreted"""
        custom_exception_handler(ValueError, ValueError(message), None)

        assert f"Error: {message}" in capsys.readouterr().err

    def test_control_chars_in_error_are_stripped(self, capsys):
        """Test that terminal escape sequences in an error message are not printed"""
        custom_exception_handler(ValueError, ValueError("bad name \x1b]8;;https://evil.example\x07x\x1b[2J"), None)

        err = capsys.readouterr().err
        assert "\x1b" not in err and "\x07" not in err
        assert "Error: bad name ]8;;https://evil.example" in err

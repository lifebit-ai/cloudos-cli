"""CLI helper utilities for debug mode and exception handling."""

import rich_click as click
import sys
import logging
import re
from rich.console import Console
from rich.markup import escape
from cloudos_cli.logging.logger import setup_logging

# Global debug state
_global_debug = False

# C0 (except tab and newline), DEL and C1 control characters, e.g. ESC sequences that drive the terminal
CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")


def strip_control_chars(text):
    """Remove control characters from remote-provided text before it is printed to a terminal."""
    return CONTROL_CHARS_RE.sub("", str(text))


def custom_exception_handler(exc_type, exc_value, exc_traceback):
    """Custom exception handler that respects debug mode"""
    console = Console(stderr=True)
    # Initialise logger
    debug_mode = '--debug' in sys.argv
    setup_logging(debug_mode)
    logger = logging.getLogger("CloudOS")
    if get_debug_mode():
        logger.error(exc_value, exc_info=exc_value)
        console.print("[yellow]Debug mode: showing full traceback[/yellow]")
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
    else:
        # Extract a clean error message
        if hasattr(exc_value, 'message'):
            error_msg = exc_value.message
        elif str(exc_value):
            error_msg = str(exc_value)
        else:
            error_msg = f"{exc_type.__name__}"
        logger.error(exc_value)
        # error_msg can hold server- or file-name-derived text, which must not be read as rich markup
        console.print(f"[bold red]Error: {escape(strip_control_chars(error_msg))}[/bold red]")

        # For network errors, give helpful context
        if 'HTTPSConnectionPool' in str(exc_value) or 'Max retries exceeded' in str(exc_value):
            console.print("[yellow]Tip: This appears to be a network connectivity issue. Please check your internet connection and try again.[/yellow]")


def pass_debug_to_subcommands(group_cls=click.RichGroup):
    """Custom Group class that passes --debug option to all subcommands"""

    class DebugGroup(group_cls):
        def add_command(self, cmd, name=None):
            # Add debug option to the command if it doesn't already have it
            if isinstance(cmd, (click.Command, click.Group)):
                has_debug = any(param.name == 'debug' for param in cmd.params)
                if not has_debug:
                    debug_option = click.Option(
                        ['--debug'], 
                        is_flag=True, 
                        help='Show detailed error information and tracebacks',
                        is_eager=True,
                        expose_value=False,
                        callback=self._debug_callback
                    )
                    cmd.params.insert(-1, debug_option)  # Insert at the end for precedence

            super().add_command(cmd, name)

        def _debug_callback(self, ctx, param, value):
            """Callback to handle debug flag"""
            global _global_debug
            if value:
                _global_debug = True
                ctx.meta['debug'] = True
            else:
                ctx.meta['debug'] = False
            return value

    return DebugGroup


def get_debug_mode():
    """Get current debug mode state"""
    return _global_debug


def setup_debug(ctx, param, value):
    """Setup debug mode globally and in context"""
    global _global_debug
    _global_debug = value
    if value:
        ctx.meta['debug'] = True
    else:
        ctx.meta['debug'] = False
    return value

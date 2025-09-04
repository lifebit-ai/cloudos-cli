import sys
import os
import json
import datetime as dt
import logging
import logging.config
import copy
from pathlib import Path
from cloudos_cli._version import __version__


_cmd_filter_instance = None


class LogFormatter(logging.Formatter):
    def __init__(self, *, fmt_keys=None):
        super().__init__()
        self.fmt_keys = fmt_keys or {}

    def format(self, record: logging.LogRecord) -> str:
        message = self._prepare_log_dict(record)
        return json.dumps(message, default=str)

    def _prepare_log_dict(self, record: logging.LogRecord):
        always = {
            "version": __version__,
            "message": record.getMessage(),
            "timestamp": dt.datetime.fromtimestamp(record.created, tz=dt.timezone.utc).isoformat(),
        }
        if record.exc_info:
            always["exc_info"] = self.formatException(record.exc_info)

        out = {}
        for key, attr in self.fmt_keys.items():
            if attr in always:
                out[key] = always.pop(attr)
            else:
                out[key] = getattr(record, attr, None)
        out.update(always)
        return out


class CommandContextFilter(logging.Filter):
    """Injects record.command and record.params everywhere."""
    def __init__(self, command=None, params=None):
        super().__init__()
        self.command = command
        self.params = params

    def set_seed_from_argv(self):
        self.command = " ".join(sys.argv)
        self.params = None

    def set_from_click_ctx(self, ctx):
        # Runs after Click has parsed
        self.command = ctx.command_path
        self.params = dict(ctx.params) if ctx and ctx.params is not None else None

    def filter(self, record):
        if not hasattr(record, "command"):
            record.command = self.command
        if not hasattr(record, "params"):
            record.params = self.params
        return True


def _cmd_filter_factory():
    """Factory used by dictConfig so we can get the SAME instance later."""
    global _cmd_filter_instance
    if _cmd_filter_instance is None:
        _cmd_filter_instance = CommandContextFilter()
        _cmd_filter_instance.set_seed_from_argv()
    return _cmd_filter_instance


LOG_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": LogFormatter,
        },
        "simple": {"format": "%(levelname)s: %(message)s"},
    },
    "filters": {
        "cmdctx": {"()": _cmd_filter_factory}
    },
    "handlers": {
        "file": {
            "class": "logging.FileHandler",
            "level": "DEBUG",
            "formatter": "json",
            "filters": ["cmdctx"],
            "filename": None,
        },
        "stderr": {
            "class": "logging.StreamHandler",
            "level": "ERROR",
            "formatter": "simple",
            "filters": ["cmdctx"],
            "stream": "ext://sys.stderr",
        },
    },
    "root": {"level": "DEBUG", "handlers": ["file"]},
}


def setup_logging(debug):
    debug_fields = {
            "version": "version",
            "level": "levelname",
            "timestamp": "timestamp",
            "message": "message",
            "logger": "name",
            "command": "command",
            "params": "params",
            "exc_info": "exc_info"
    }
    non_debug_fields = {
            "version": "version",
            "level": "levelname",
            "timestamp": "timestamp",
            "message": "message",
            "logger": "name",
            "command": "command",
            "params": "params",
    }
    config = copy.deepcopy(LOG_CONFIG)

    # build a timestamped log filename
    ts = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    log_dir = os.path.join(Path.home(), ".cloudos/logs")
    os.makedirs(log_dir, exist_ok=True)
    config["handlers"]["file"]["filename"] = os.path.join(log_dir, f"cloudos-{ts}.jsonl")

    # adjust log level if requested
    config["root"]["level"] = "DEBUG" if debug else "WARNING"

    logging.config.dictConfig(config)
    root = logging.getLogger()
    if debug:
        formatter = debug_fields
    else:
        formatter = non_debug_fields
    for handle in root.handlers:
        log_formatter = LogFormatter(fmt_keys=formatter)
        handle.setFormatter(log_formatter)


def update_command_context_from_click(ctx):
    """Call this AFTER Click parsed args."""
    _cmd_filter_factory().set_from_click_ctx(ctx)

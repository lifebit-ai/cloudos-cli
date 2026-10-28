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

# Click params whose values must never be written to a log
SECRET_PARAM_NAMES = {"apikey", "cromwell_token"}
SECRET_PARAM_MARKERS = ("token", "secret", "password", "key")
SECRET_SHORT_FLAGS = {"-k"}  # -k is --apikey on every command
REDACTED = "***"


def _is_secret_param(name):
    name = str(name).lower()
    return name in SECRET_PARAM_NAMES or any(marker in name for marker in SECRET_PARAM_MARKERS)


def redact_params(params):
    """Return a copy of params with secret-bearing values masked."""
    if not isinstance(params, dict):
        return params
    return {
        name: REDACTED if value is not None and _is_secret_param(name) else value
        for name, value in params.items()
    }


def redact_argv(argv):
    """Return a copy of argv with the values of secret options masked."""
    out = []
    mask_next = False
    for arg in argv:
        if mask_next:
            out.append(REDACTED)
            mask_next = False
            continue
        if arg in SECRET_SHORT_FLAGS:
            mask_next = True
        elif arg.startswith("--"):
            name, sep, _ = arg[2:].partition("=")
            if _is_secret_param(name.replace("-", "_")):
                if sep:
                    arg = f"--{name}={REDACTED}"
                else:
                    mask_next = True
        elif arg[:2] in SECRET_SHORT_FLAGS:
            # attached value, e.g. -kVALUE
            arg = arg[:2] + REDACTED
        out.append(arg)
    return out


class PrivateFileHandler(logging.FileHandler):
    """FileHandler whose log file is only readable by its owner (0600).

    On Windows, chmod only toggles the read-only flag, so access there is
    governed by the ACL inherited from the user's profile directory.
    """
    def _open(self):
        fd = os.open(self.baseFilename, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        os.close(fd)
        # also tighten a file that already existed with looser permissions
        os.chmod(self.baseFilename, 0o600)
        return super()._open()


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
    """Injects record.command and record.params (with secrets redacted) everywhere."""
    def __init__(self, command=None, params=None):
        super().__init__()
        self.command = command
        self.params = params

    def set_seed_from_argv(self):
        self.command = " ".join(redact_argv(sys.argv))
        self.params = None

    def set_from_click_ctx(self, ctx):
        # Runs after Click has parsed
        self.command = ctx.command_path
        self.params = dict(ctx.params) if ctx and ctx.params is not None else None

    def filter(self, record):
        if not hasattr(record, "command"):
            record.command = self.command
        record.params = redact_params(getattr(record, "params", self.params))
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
            "class": "cloudos_cli.logging.logger.PrivateFileHandler",
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
    os.makedirs(log_dir, mode=0o700, exist_ok=True)
    # makedirs leaves an existing directory's mode untouched
    os.chmod(log_dir, 0o700)
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

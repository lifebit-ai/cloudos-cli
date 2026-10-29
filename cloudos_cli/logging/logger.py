import sys
import os
import re
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
SECRET_SHORT_FLAGS = {"-k", "-t"}  # -k is --apikey and -t is --cromwell-token on every command
REDACTED = "***"
# raw secret values shorter than this are not searched for in messages, to avoid masking common words
MIN_SECRET_VALUE_LENGTH = 4

# Patterns for secrets inside free-form values such as --parameter or --command
_MARKERS = "|".join(SECRET_PARAM_MARKERS)
_VALUE = r"""("(?:[^"\\]|\\.)*"|'[^']*'|\S+)"""
# NAME=value with a secret-looking name, e.g. password=X, --apikey=X, --parameter=db_token=X, ?api_key=X
SECRET_ASSIGNMENT_RE = re.compile(
    rf"(?<![A-Za-z0-9_.-])([A-Za-z0-9_.-]*(?:{_MARKERS})[A-Za-z0-9_.-]*)={_VALUE}", re.IGNORECASE)
# values shorter than this after -k/-t or Bearer/Basic are ordinary arguments, not credentials
MIN_CREDENTIAL_LENGTH = 16
_CREDENTIAL_AHEAD = (rf"""(?=\s+(?:"[^"]{{{MIN_CREDENTIAL_LENGTH},}}"|'[^']{{{MIN_CREDENTIAL_LENGTH},}}'"""
                     rf"""|\S{{{MIN_CREDENTIAL_LENGTH},}}))""")
# secret option followed by its value, e.g. "cloudos job list -k X" or "--cromwell-token X";
# -k/-t only with a credential-length value, so "sort -k 2" and "cut -t ," are kept
SECRET_OPTION_RE = re.compile(
    rf"(?<!\S)(-[kt]{_CREDENTIAL_AHEAD}|--[A-Za-z0-9_-]*(?:{_MARKERS})[A-Za-z0-9_-]*)(\s+){_VALUE}",
    re.IGNORECASE)
# HTTP credentials, e.g. "Authorization: Bearer X"; credential-length only, so "Basic variant calling" is kept
AUTH_SCHEME_RE = re.compile(
    rf"\b(Bearer|Basic)(\s+)(?=[^\s'\"]{{{MIN_CREDENTIAL_LENGTH},}})[^\s'\"]+", re.IGNORECASE)
# password in a URL, e.g. postgres://user:X@host
URL_CREDENTIALS_RE = re.compile(r"(://[^/\s:@]+:)[^/\s@]+(@)")
ASSIGNMENT_NAME_RE = re.compile(r"[A-Za-z0-9_.-]+")


def _is_secret_param(name):
    name = str(name).lower()
    return name in SECRET_PARAM_NAMES or any(marker in name for marker in SECRET_PARAM_MARKERS)


def _redact_text(value):
    """Mask secrets inside a free-form string."""
    # When the value starts with a chain of assignments (e.g. --parameter "password=two words" or
    # --parameter=password=X), mask everything after the first secret-named one, spaces included.
    parts = value.split("=")
    for i, name in enumerate(parts[:-1]):
        if not ASSIGNMENT_NAME_RE.fullmatch(name):
            break
        if _is_secret_param(name):
            return "=".join(parts[:i + 1]) + "=" + REDACTED
    value = SECRET_ASSIGNMENT_RE.sub(rf"\1={REDACTED}", value)
    value = SECRET_OPTION_RE.sub(rf"\1\2{REDACTED}", value)
    value = AUTH_SCHEME_RE.sub(rf"\1\2{REDACTED}", value)
    return URL_CREDENTIALS_RE.sub(rf"\1{REDACTED}\2", value)


def _redact_assignments(value):
    """Mask secrets inside a string, or each string of a list or tuple."""
    if isinstance(value, str):
        return _redact_text(value)
    if isinstance(value, (list, tuple)):
        return type(value)(_redact_text(item) if isinstance(item, str) else item for item in value)
    return value


def redact_params(params):
    """Return a copy of params with secret-bearing values masked."""
    if not isinstance(params, dict):
        return params
    return {
        name: REDACTED if value is not None and _is_secret_param(name) else _redact_assignments(value)
        for name, value in params.items()
    }


def secret_param_values(params):
    """Return the raw values of the secret params, to mask wherever they appear."""
    if not isinstance(params, dict):
        return set()
    return {str(value) for name, value in params.items() if value and _is_secret_param(name)}


def redact_argv(argv, secrets=None):
    """Return a copy of argv with the values of secret options masked.

    If secrets is a set, the raw values that were masked are added to it.
    """
    out = []
    mask_next = False
    found = set()
    for arg in argv:
        if mask_next:
            found.add(arg)
            out.append(REDACTED)
            mask_next = False
            continue
        if arg in SECRET_SHORT_FLAGS:
            mask_next = True
        elif arg.startswith("--"):
            name, sep, value = arg[2:].partition("=")
            if _is_secret_param(name.replace("-", "_")):
                if sep:
                    found.add(value)
                    arg = f"--{name}={REDACTED}"
                else:
                    mask_next = True
            else:
                arg = _redact_text(arg)
        elif arg[:2] in SECRET_SHORT_FLAGS:
            # attached value, e.g. -kVALUE
            found.add(arg[2:])
            arg = arg[:2] + REDACTED
        else:
            arg = _redact_text(arg)
        out.append(arg)
    if secrets is not None:
        secrets.update(value for value in found if value)
    return out


def mask_secret_values(text, secrets):
    """Replace each raw secret value found in text.

    The stripped value is what's searched for, so " KEY" is masked as " ***" and "KEY" as "***".
    """
    candidates = {secret.strip() for secret in secrets if len(secret.strip()) >= MIN_SECRET_VALUE_LENGTH}
    # longest first, so a secret that contains another is masked whole
    for secret in sorted(candidates, key=len, reverse=True):
        text = text.replace(secret, REDACTED)
    return text


def secure_log_dir():
    """Create ~/.cloudos/logs if needed and restrict it, and existing log files, to the owner.

    Never raises, so a directory we can't change does not break the CLI.
    """
    log_dir = os.path.join(Path.home(), ".cloudos/logs")
    try:
        os.makedirs(log_dir, mode=0o700, exist_ok=True)
        # makedirs leaves an existing directory's mode untouched
        os.chmod(log_dir, 0o700)
        # files written by earlier versions were 0644
        for path in Path(log_dir).glob("cloudos-*.jsonl"):
            path.chmod(0o600)
    except OSError as exc:
        logging.getLogger(__name__).debug("Could not restrict %s: %s", log_dir, exc)
    return log_dir


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
            # CommandContextFilter stores a traceback with secret values masked in exc_text
            always["exc_info"] = record.exc_text or self.formatException(record.exc_info)

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
        # raw secret values, masked wherever they appear in a message or traceback
        self.secret_values = set()

    def set_seed_from_argv(self):
        self.command = " ".join(redact_argv(sys.argv, self.secret_values))
        self.params = None

    def set_from_click_ctx(self, ctx):
        # Runs after Click has parsed
        self.command = ctx.command_path
        self.params = dict(ctx.params) if ctx and ctx.params is not None else None
        self.secret_values |= secret_param_values(self.params)

    def filter(self, record):
        if not hasattr(record, "command"):
            record.command = self.command
        params = getattr(record, "params", self.params)
        record.params = redact_params(params)
        # exceptions can carry a secret, e.g. requests puts a malformed API key header in its message
        secrets = self.secret_values | secret_param_values(params) | secret_param_values(self.params)
        if secrets:
            record.msg = mask_secret_values(record.getMessage(), secrets)
            record.args = None
            if record.exc_info:
                record.exc_text = mask_secret_values(logging.Formatter().formatException(record.exc_info), secrets)
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
    log_dir = secure_log_dir()
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

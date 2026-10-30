"""Shared fixtures for the tests of .github/scripts.

The scripts run on GitHub Actions against Docker, Trivy and AWS Bedrock. Here
those are stand-ins: a `docker` that only fails on a marker, a scan that
reports a finding for each known package environment.yml doesn't yet require
at its fixed version, and a fake `boto3` that plays back scripted replies.
"""
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / ".github" / "scripts"

# What the fake scan knows about: package -> (finding id, fixed version).
KNOWN_FINDINGS = {
    "urllib3": ("CVE-2026-97687", "2.8.0"),
    "brotli": ("GHSA-9v8h-qqgm-4m35", "1.2.1"),
}

ENVIRONMENT_YML = """\
name: cloudos
channels:
  - conda-forge
dependencies:
  - python=3.11
  - pip:
    - requests>=2.31.0
"""

# Fails the build when environment.yml asks for something that can't install.
FAKE_DOCKER = """\
#!/bin/sh
if grep -q BREAKS-THE-BUILD environment.yml; then
  echo "conda: package not found" >&2
  exit 1
fi
exit 0
"""

FAKE_SCAN = """\
import json
import sys
from pathlib import Path

known = json.loads({known!r})
env = Path("environment.yml").read_text()
vulns = [
    {{"VulnerabilityID": vid, "PkgName": pkg, "InstalledVersion": "0.1",
      "FixedVersion": fixed, "Severity": "HIGH", "Title": "test finding"}}
    for pkg, (vid, fixed) in known.items()
    if f"{{pkg}}>={{fixed}}" not in env
]
report = {{"Results": [{{"Target": "python", "Type": "python-pkg", "Vulnerabilities": vulns}}]}}
Path(sys.argv[2]).write_text(json.dumps(report))
"""

# Each converse() call takes the next scripted reply: {"text": ...} is
# returned as the model's answer, {"raise": ...} raises like a throttled call.
FAKE_BOTO3 = """\
import json
import os
from pathlib import Path


class _Client:
    def converse(self, **kwargs):
        counter = Path(os.environ["FAKE_BEDROCK_COUNTER"])
        calls = int(counter.read_text()) if counter.exists() else 0
        counter.write_text(str(calls + 1))
        reply = json.loads(Path(os.environ["FAKE_BEDROCK_REPLIES"]).read_text())[calls]
        if "raise" in reply:
            raise RuntimeError(reply["raise"])
        return {"output": {"message": {"content": [{"text": reply["text"]}]}}}


def client(*args, **kwargs):
    return _Client()
"""

FAKE_BOTOCORE_CONFIG = """\
class Config:
    def __init__(self, *args, **kwargs):
        pass
"""


def load_autofix():
    """Import .github/scripts/autofix.py as a module."""
    spec = importlib.util.spec_from_file_location("autofix", SCRIPTS / "autofix.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def edit_reply(*edits):
    """A model reply, as text, proposing the given (find, replace) edits."""
    return {"text": json.dumps({
        "edits": [{"path": "environment.yml", "find": find, "replace": replace}
                  for find, replace in edits],
        "findings": [],
    })}


def add_dependency(line):
    """An edit that adds a dependency line under `pip:` in ENVIRONMENT_YML."""
    return ("    - requests>=2.31.0\n", f"    - requests>=2.31.0\n    - {line}\n")


def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True,
                          text=True).stdout


def git_env(home):
    """An environment where git ignores the user's config and can commit."""
    env = dict(os.environ)
    env.update({
        "HOME": str(home),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "test@example.com",
        "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "test@example.com",
    })
    return env


class LoopSandbox:
    """A throwaway git repo laid out like this one, to run autofix_loop.sh in."""

    def __init__(self, tmp_path, replies=()):
        self.tmp = tmp_path
        self.repo = tmp_path / "repo"
        self.autofix_dir = tmp_path / "autofix"
        self.output = tmp_path / "github_output"
        bin_dir = tmp_path / "bin"
        fake_modules = tmp_path / "fake_modules"

        scripts = self.repo / ".github" / "scripts"
        scan_dir = self.repo / ".github" / "actions" / "trivy-scan"
        for directory in (scripts, scan_dir, bin_dir, fake_modules / "boto3",
                          fake_modules / "botocore"):
            directory.mkdir(parents=True)
        for name in ("autofix_loop.sh", "autofix.py"):
            (scripts / name).write_text((SCRIPTS / name).read_text())
        (self.repo / "environment.yml").write_text(ENVIRONMENT_YML)
        (self.repo / "Dockerfile").write_text("FROM condaforge/miniforge3\n")

        # The loop runs `python` and `"$scan"`: point both at this interpreter.
        (bin_dir / "python").symlink_to(sys.executable)
        (scan_dir / "fake_scan.py").write_text(FAKE_SCAN.format(known=json.dumps(KNOWN_FINDINGS)))
        (scan_dir / "scan.sh").write_text(
            '#!/bin/sh\nexec python "$(dirname "$0")/fake_scan.py" "$@"\n')
        (bin_dir / "docker").write_text(FAKE_DOCKER)
        for executable in (scan_dir / "scan.sh", bin_dir / "docker"):
            executable.chmod(0o755)

        (fake_modules / "boto3" / "__init__.py").write_text(FAKE_BOTO3)
        (fake_modules / "botocore" / "__init__.py").write_text("")
        (fake_modules / "botocore" / "config.py").write_text(FAKE_BOTOCORE_CONFIG)
        self.replies_file = tmp_path / "replies.json"
        self.replies_file.write_text(json.dumps(list(replies)))
        self.counter = tmp_path / "model_calls"

        self.env = git_env(tmp_path)
        self.env.update({
            "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
            "PYTHONPATH": str(fake_modules),
            "FAKE_BEDROCK_REPLIES": str(self.replies_file),
            "FAKE_BEDROCK_COUNTER": str(self.counter),
            "IMAGE": "cloudos-cli:test",
            "BEDROCK_MODEL_ID": "test-model",
            "AUTOFIX_DIR": str(self.autofix_dir),
            "GITHUB_OUTPUT": str(self.output),
        })
        self.env.pop("AWS_BEARER_TOKEN_BEDROCK", None)

        git(self.repo, "init", "-q")
        subprocess.run(["git", "add", "-A"], cwd=self.repo, env=self.env, check=True)
        subprocess.run(["git", "commit", "-qm", "init"], cwd=self.repo, env=self.env, check=True)
        self.start_sha = git(self.repo, "rev-parse", "HEAD").strip()

    def run(self, max_rounds="3"):
        self.output.write_text("")
        env = dict(self.env, MAX_ROUNDS=max_rounds)
        return subprocess.run(["bash", ".github/scripts/autofix_loop.sh"], cwd=self.repo,
                              env=env, capture_output=True, text=True)

    def outputs(self):
        lines = self.output.read_text().splitlines()
        return dict(line.split("=", 1) for line in lines if "=" in line)

    def model_calls(self):
        return int(self.counter.read_text()) if self.counter.exists() else 0

    def history(self):
        return json.loads((self.autofix_dir / "history.json").read_text())

    def commits_since_start(self):
        log = git(self.repo, "log", "--format=%s", f"{self.start_sha}..HEAD")
        return log.splitlines()

    def environment_yml(self):
        return (self.repo / "environment.yml").read_text()

    def worktree_clean(self):
        return git(self.repo, "status", "--porcelain") == ""

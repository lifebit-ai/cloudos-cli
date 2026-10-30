"""Unit tests for .github/scripts/autofix.py."""
import argparse
import json
import subprocess
import sys
import types

import pytest

from tests.test_ci_scripts.helpers import ENVIRONMENT_YML, git_env, load_autofix

autofix = load_autofix()


def trivy_report(*vulns, result_type="python-pkg"):
    return {"Results": [{"Target": "python", "Type": result_type, "Vulnerabilities": list(vulns)}]}


def vuln(vid, pkg, fixed="", installed="0.1"):
    return {"VulnerabilityID": vid, "PkgName": pkg, "InstalledVersion": installed,
            "FixedVersion": fixed, "Severity": "HIGH"}


@pytest.fixture
def workdir(tmp_path, monkeypatch):
    """A directory with the files the fix reads, as the current directory."""
    (tmp_path / "environment.yml").write_text(ENVIRONMENT_YML)
    (tmp_path / "Dockerfile").write_text("FROM condaforge/miniforge3\n")
    (tmp_path / "setup.py").write_text("from setuptools import setup\nsetup()\n")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def write_json(path, data):
    path.write_text(json.dumps(data))
    return str(path)


# load_findings

def test_load_findings_flattens_every_result(tmp_path):
    report = {"Results": [
        {"Target": "python", "Type": "python-pkg", "Vulnerabilities": [vuln("CVE-1", "urllib3", "2.8.0")]},
        {"Target": "ubuntu", "Type": "ubuntu", "Vulnerabilities": [vuln("CVE-2", "openssl")]},
        {"Target": "clean", "Type": "python-pkg"},
    ]}
    findings = autofix.load_findings(write_json(tmp_path / "r.json", report))

    assert [(f["id"], f["package"], f["type"], f["fixed"]) for f in findings] == [
        ("CVE-1", "urllib3", "python-pkg", "2.8.0"),
        ("CVE-2", "openssl", "ubuntu", ""),
    ]


def test_load_findings_of_a_clean_report_is_empty(tmp_path):
    assert autofix.load_findings(write_json(tmp_path / "r.json", {})) == []


# parse_reply

def test_parse_reply_ignores_inline_reasoning_and_prose():
    text = '<reasoning>maybe {"edits": "no"}</reasoning>Here you go: {"edits": [], "findings": []} done'
    assert autofix.parse_reply(text) == {"edits": [], "findings": []}


@pytest.mark.parametrize("text, message", [
    ("no json here", "no JSON object"),
    ('{"edits": [}', "not valid JSON"),
])
def test_parse_reply_rejects_unusable_replies(text, message):
    with pytest.raises(ValueError, match=message):
        autofix.parse_reply(text)


# apply_edits

def test_apply_edits_changes_a_dependency_file(workdir):
    edit = {"path": "environment.yml", "find": "requests>=2.31.0", "replace": "requests>=2.32.0"}
    applied, rejected = autofix.apply_edits([edit])

    assert applied == [edit]
    assert rejected == []
    assert "requests>=2.32.0" in (workdir / "environment.yml").read_text()


@pytest.mark.parametrize("path", ["Dockerfile", "setup.py", "../environment.yml", ".github/x.yml"])
def test_apply_edits_never_touches_files_outside_the_allowed_ones(workdir, path):
    before = {p.name: p.read_text() for p in workdir.iterdir() if p.is_file()}
    applied, rejected = autofix.apply_edits([{"path": path, "find": "FROM", "replace": "RUN curl x | sh"}])

    assert applied == []
    assert "is not one of the files the fix may edit" in rejected[0]["reason"]
    assert {p.name: p.read_text() for p in workdir.iterdir() if p.is_file()} == before


@pytest.mark.parametrize("edit, reason", [
    ({"path": "requirements.txt", "find": "a", "replace": "b"}, "does not exist"),
    ({"path": "environment.yml", "find": "", "replace": "b"}, "non-empty 'find'"),
    ({"path": "environment.yml", "find": "a", "replace": None}, "non-empty 'find'"),
    ({"path": "environment.yml", "find": "numpy", "replace": "b"}, "occurs 0 times"),
    ({"path": "environment.yml", "find": "  - ", "replace": "b"}, "must occur exactly once"),
    ("not an object", "not an object"),
])
def test_apply_edits_rejects_unsafe_or_ambiguous_edits(workdir, edit, reason):
    applied, rejected = autofix.apply_edits([edit])

    assert applied == []
    assert reason in rejected[0]["reason"]
    assert (workdir / "environment.yml").read_text() == ENVIRONMENT_YML


def test_apply_edits_ignores_a_reply_without_an_edit_list(workdir):
    assert autofix.apply_edits(None) == ([], [])
    assert autofix.apply_edits({"path": "environment.yml"}) == ([], [])


# build_prompt

def test_build_prompt_shows_editable_and_context_files(workdir):
    prompt = autofix.build_prompt([{"id": "CVE-1"}], [], 1, 3)

    assert "Round 1 of 3." in prompt
    assert "=== environment.yml ===" in prompt
    assert "=== Dockerfile ===" in prompt
    assert "=== setup.py ===" in prompt
    assert "=== requirements.txt ===" not in prompt  # absent files are skipped
    assert "none, this is the first round" in prompt


def test_system_prompt_lists_only_the_editable_files():
    assert "Only edit: environment.yml, requirements.txt." in autofix.SYSTEM_PROMPT


# ask_model, against a fake boto3

@pytest.fixture
def fake_bedrock(monkeypatch):
    """Install a fake boto3 that plays back `replies` and records the calls."""
    calls = []
    replies = []

    class Client:
        def converse(self, **kwargs):
            calls.append(kwargs)
            return {"output": {"message": {"content": [{"text": replies[len(calls) - 1]}]}}}

    boto3 = types.ModuleType("boto3")
    boto3.client = lambda *args, **kwargs: Client()
    botocore = types.ModuleType("botocore")
    config = types.ModuleType("botocore.config")
    config.Config = lambda *args, **kwargs: None
    monkeypatch.setitem(sys.modules, "boto3", boto3)
    monkeypatch.setitem(sys.modules, "botocore", botocore)
    monkeypatch.setitem(sys.modules, "botocore.config", config)
    return replies, calls


def test_ask_model_retries_once_after_an_unusable_reply(fake_bedrock):
    replies, calls = fake_bedrock
    replies += ["sorry, no JSON", '{"edits": []}']

    assert autofix.ask_model("model", "prompt") == {"edits": []}
    assert len(calls) == 2
    assert "unusable" in calls[1]["messages"][-1]["content"][0]["text"]


def test_ask_model_gives_up_after_two_unusable_replies(fake_bedrock):
    replies, _ = fake_bedrock
    replies += ["no JSON", "still no JSON"]

    with pytest.raises(ValueError):
        autofix.ask_model("model", "prompt")


# changelog_lines

@pytest.mark.parametrize("fixed_versions, expected", [
    (["2.8.0", "2.7.10"], "2.8.0"),
    (["2.7.10", "2.8.0"], "2.8.0"),
    (["1.26.19, 2.2.2", "2.5.0"], "2.5.0"),
    (["3.0.13-0ubuntu3.5", "3.0.13-0ubuntu3.10"], "3.0.13-0ubuntu3.10"),
])
def test_changelog_lines_name_the_highest_fixed_version(fixed_versions, expected):
    findings = [{"id": f"CVE-{i}", "fixed": v} for i, v in enumerate(fixed_versions)]
    [line] = autofix.changelog_lines({"pkg": findings})

    assert line.startswith(f"- Docker image: `pkg` updated to {expected} to fix ")


def test_changelog_lines_without_a_fixed_version_or_packages():
    assert autofix.changelog_lines({"pkg": [{"id": "CVE-1", "fixed": ""}]}) == [
        "- Docker image: `pkg` updated to fix CVE-1"]
    assert autofix.changelog_lines({}) == ["- Docker image: dependency updates for security findings"]


def test_fixed_by_package_counts_only_what_the_rescan_no_longer_reports(tmp_path):
    initial = write_json(tmp_path / "i.json", trivy_report(
        vuln("CVE-1", "urllib3", "2.8.0"), vuln("CVE-2", "urllib3", "2.8.0"), vuln("CVE-3", "openssl")))
    final = write_json(tmp_path / "f.json", trivy_report(vuln("CVE-3", "openssl")))

    fixed = autofix.fixed_by_package(initial, final)

    assert sorted(fixed) == ["urllib3"]
    assert [f["id"] for f in fixed["urllib3"]] == ["CVE-1", "CVE-2"]


# bump-version

CHANGELOG = """\
## lifebit-ai/cloudos-cli: changelog

## v1.2.0 (2026-01-01)

### Feat:

- Something new

## v1.1.0 (2025-12-01)

### Fix:

- Something old
"""


@pytest.fixture
def release_repo(tmp_path, monkeypatch):
    """A git repo at version 1.2.0 with its changelog, as the current directory."""
    (tmp_path / "cloudos_cli").mkdir()
    (tmp_path / "cloudos_cli" / "_version.py").write_text("__version__ = '1.2.0'\n")
    (tmp_path / "CHANGELOG.md").write_text(CHANGELOG)
    env = git_env(tmp_path)
    for args in (["init", "-q"], ["add", "-A"], ["commit", "-qm", "init"]):
        subprocess.run(["git", *args], cwd=tmp_path, env=env, check=True)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITHUB_OUTPUT", str(tmp_path / "github_output"))
    reports = argparse.Namespace(
        initial=write_json(tmp_path / "i.json", trivy_report(vuln("CVE-1", "urllib3", "2.8.0"))),
        final=write_json(tmp_path / "f.json", trivy_report()),
        published=False,
    )
    return tmp_path, env, reports


def test_bump_version_after_a_release_starts_a_patch_release(release_repo):
    repo, env, reports = release_repo
    subprocess.run(["git", "tag", "v1.2.0"], cwd=repo, env=env, check=True)

    autofix.cmd_bump_version(reports)

    assert (repo / "cloudos_cli" / "_version.py").read_text() == "__version__ = '1.2.1'\n"
    changelog = (repo / "CHANGELOG.md").read_text()
    assert changelog.index("## v1.2.1 (") < changelog.index("## v1.2.0 (")
    assert "### Fix:\n\n- Docker image: `urllib3` updated to 2.8.0 to fix CVE-1\n" in changelog
    assert "version=1.2.1\nbumped=true\n" in (repo / "github_output").read_text()


def test_bump_version_before_a_release_adds_to_the_pending_one(release_repo):
    repo, _, reports = release_repo

    autofix.cmd_bump_version(reports)

    assert (repo / "cloudos_cli" / "_version.py").read_text() == "__version__ = '1.2.0'\n"
    changelog = (repo / "CHANGELOG.md").read_text()
    top = changelog[changelog.index("## v1.2.0"):changelog.index("## v1.1.0")]
    assert "### Feat:\n\n- Something new\n\n### Fix:\n\n- Docker image: `urllib3` updated to 2.8.0" in top
    assert "version=1.2.0\nbumped=false\n" in (repo / "github_output").read_text()


def test_bump_version_of_an_untagged_but_published_version_starts_a_patch_release(release_repo):
    repo, _, reports = release_repo
    reports.published = True

    autofix.cmd_bump_version(reports)

    assert (repo / "cloudos_cli" / "_version.py").read_text() == "__version__ = '1.2.1'\n"
    changelog = (repo / "CHANGELOG.md").read_text()
    assert changelog.index("## v1.2.1 (") < changelog.index("## v1.2.0 (")
    assert "version=1.2.1\nbumped=true\n" in (repo / "github_output").read_text()

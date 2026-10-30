"""Run .github/scripts/autofix_loop.sh end to end, with Docker, Trivy and
Bedrock replaced by the stand-ins in helpers.py."""
import shutil

import pytest

from tests.test_ci_scripts.helpers import LoopSandbox, add_dependency, edit_reply

pytestmark = pytest.mark.skipif(
    shutil.which("bash") is None or shutil.which("jq") is None or shutil.which("git") is None,
    reason="autofix_loop.sh needs bash, jq and git",
)

FIX_URLLIB3 = edit_reply(add_dependency("urllib3>=2.8.0"))
FIX_BROTLI = edit_reply(add_dependency("brotli>=1.2.1"))
FIX_BOTH = edit_reply(add_dependency("urllib3>=2.8.0\n    - brotli>=1.2.1"))


def test_clean_image_never_calls_the_model(tmp_path):
    sandbox = LoopSandbox(tmp_path)
    (sandbox.repo / "environment.yml").write_text(
        sandbox.environment_yml() + "    - urllib3>=2.8.0\n    - brotli>=1.2.1\n")
    result = sandbox.run()

    assert result.returncode == 0, result.stderr
    assert sandbox.outputs() == {"changed": "false", "initial": "0", "remaining": "0", "rounds": "0"}
    assert sandbox.model_calls() == 0


def test_max_rounds_zero_is_a_plain_scan(tmp_path):
    sandbox = LoopSandbox(tmp_path)
    result = sandbox.run(max_rounds="0")

    assert result.returncode == 0, result.stderr
    assert sandbox.outputs() == {"changed": "false", "initial": "2", "remaining": "2", "rounds": "0"}
    assert sandbox.model_calls() == 0


def test_fix_in_one_round_is_committed(tmp_path):
    sandbox = LoopSandbox(tmp_path, replies=[FIX_BOTH])
    result = sandbox.run()

    assert result.returncode == 0, result.stderr
    assert sandbox.outputs() == {"changed": "true", "initial": "2", "remaining": "0", "rounds": "1"}
    assert sandbox.commits_since_start() == ["Security autofix: round 1"]
    assert "urllib3>=2.8.0" in sandbox.environment_yml()
    assert sandbox.history()[0]["build"] == "ok"
    assert sandbox.history()[0]["still_failing"] == []


def test_each_round_that_helps_is_committed(tmp_path):
    sandbox = LoopSandbox(tmp_path, replies=[FIX_URLLIB3, FIX_BROTLI])
    result = sandbox.run()

    assert result.returncode == 0, result.stderr
    assert sandbox.outputs() == {"changed": "true", "initial": "2", "remaining": "0", "rounds": "2"}
    assert sandbox.commits_since_start() == ["Security autofix: round 2", "Security autofix: round 1"]


def test_failed_model_call_keeps_earlier_rounds(tmp_path):
    sandbox = LoopSandbox(tmp_path, replies=[FIX_URLLIB3, {"raise": "ThrottlingException"}])
    result = sandbox.run()

    assert result.returncode == 0, result.stderr
    assert "the model call failed; keeping the earlier rounds" in result.stdout
    assert sandbox.outputs() == {"changed": "true", "initial": "2", "remaining": "1", "rounds": "2"}
    assert sandbox.commits_since_start() == ["Security autofix: round 1"]


def test_rejected_edits_get_another_round(tmp_path):
    bad_find = edit_reply(("    - requests>=9.9.9\n", "    - urllib3>=2.8.0\n"))
    sandbox = LoopSandbox(tmp_path, replies=[bad_find, FIX_BOTH])
    result = sandbox.run()

    assert result.returncode == 0, result.stderr
    assert "retrying with the rejections as feedback" in result.stdout
    assert sandbox.outputs() == {"changed": "true", "initial": "2", "remaining": "0", "rounds": "2"}
    assert "occurs 0 times" in sandbox.history()[0]["rejected"][0]["reason"]


def test_no_proposed_edits_stops_the_loop(tmp_path):
    sandbox = LoopSandbox(tmp_path, replies=[edit_reply(), FIX_BOTH])
    result = sandbox.run()

    assert result.returncode == 0, result.stderr
    assert "The model proposed no edits; stopping." in result.stdout
    assert sandbox.outputs() == {"changed": "false", "initial": "2", "remaining": "2", "rounds": "1"}
    assert sandbox.model_calls() == 1


def test_round_that_fixes_nothing_is_rolled_back(tmp_path):
    useless = edit_reply(add_dependency("numpy>=1.26.4"))
    sandbox = LoopSandbox(tmp_path, replies=[useless, FIX_BOTH])
    result = sandbox.run()

    assert result.returncode == 0, result.stderr
    assert sandbox.outputs() == {"changed": "true", "initial": "2", "remaining": "0", "rounds": "2"}
    assert "numpy" not in sandbox.environment_yml()
    assert sandbox.commits_since_start() == ["Security autofix: round 2"]
    assert "no fewer than before" in sandbox.history()[0]["rolled_back"]


def test_round_that_breaks_the_build_is_rolled_back(tmp_path):
    breaks = edit_reply(add_dependency("BREAKS-THE-BUILD"))
    sandbox = LoopSandbox(tmp_path, replies=[breaks, FIX_BOTH])
    result = sandbox.run()

    assert result.returncode == 0, result.stderr
    assert sandbox.outputs() == {"changed": "true", "initial": "2", "remaining": "0", "rounds": "2"}
    assert "BREAKS-THE-BUILD" not in sandbox.environment_yml()
    assert sandbox.history()[0]["build"] == "failed"
    assert "package not found" in sandbox.history()[0]["build_log_tail"]


def test_gives_up_after_max_rounds(tmp_path):
    useless = edit_reply(add_dependency("numpy>=1.26.4"))
    sandbox = LoopSandbox(tmp_path, replies=[useless, useless])
    result = sandbox.run(max_rounds="2")

    assert result.returncode == 0, result.stderr
    assert sandbox.outputs() == {"changed": "false", "initial": "2", "remaining": "2", "rounds": "2"}
    assert sandbox.model_calls() == 2
    assert sandbox.worktree_clean()


def test_image_that_does_not_build_fails(tmp_path):
    sandbox = LoopSandbox(tmp_path)
    (sandbox.repo / "environment.yml").write_text(sandbox.environment_yml() + "    - BREAKS-THE-BUILD\n")
    result = sandbox.run()

    assert result.returncode == 1
    assert "does not build from this commit" in result.stdout
    assert sandbox.model_calls() == 0

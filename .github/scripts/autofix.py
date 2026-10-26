#!/usr/bin/env python3
"""Model-assisted fixes for Trivy findings in the cloudos-cli Docker image.

Called by .github/scripts/autofix_loop.sh and the security-autofix workflow:

  fix           ask a Bedrock model for edits to the dependency files and apply them
  record        note how a round went: did it build, what still fails
  bump-version  make the fix releasable: bump the patch version if the current one shipped
  count-fixed   how many findings the rescan no longer reports
  pr-body       write the pull request description

The model only proposes edits. It never builds, scans, commits or pushes, and
its edits are applied only to the files in ALLOWED_FILES, as exact
find-and-replace pairs, so a confused reply cannot rewrite or truncate a file.
What counts as fixed is decided by the rescan, not by what the model says.
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ALLOWED_FILES = ("environment.yml", "requirements.txt")
# Shown to the model for context only; never edited.
CONTEXT_FILES = ("Dockerfile", "setup.py")
VERSION_FILE = Path("cloudos_cli/_version.py")
CHANGELOG = Path("CHANGELOG.md")

SYSTEM_PROMPT = """\
You fix vulnerabilities in the Docker image of lifebit-ai/cloudos-cli, a Python CLI.
The image is condaforge/miniforge3 (Ubuntu 24.04). `conda env update` installs
environment.yml into /opt/conda, then `pip install -e /` installs the CLI from
setup.py. The Dockerfile already runs `apt-get upgrade` as its last layer.

You get the Trivy findings that still fail, the current dependency files, and what
earlier rounds tried. For each finding:
- Python or conda library (type python-pkg, conda-pkg, pip): require at least the
  lowest fixed version. If environment.yml already lists the package, raise its
  lower bound there. If it does not (a transitive dependency), add a line
  `- <package>>=<fixed version>` to the dependencies in environment.yml, next to
  the other entries and with the same indentation. Never change other packages.
- OS package (type ubuntu, debian): the apt-get upgrade layer picks up fixes the
  archive already has, so if one still fails, leave it and say why.
- No fixed version, or a package the image does not install through these files:
  leave it and say why.

Rules:
- Only edit: environment.yml, requirements.txt.
- Do not change the version or the changelog; the workflow does that.
- Do not repeat an edit an earlier round made that did not fix the finding or
  broke the build. Those edits were rolled back and are not in the current files.
- Every edit is an exact find-and-replace: `find` must be copied character for
  character from the current file and must occur exactly once in it.

Reply with ONLY this JSON object, no prose and no code fence:
{"edits": [{"path": "environment.yml", "find": "<exact existing text>", "replace": "<new text>"}],
 "findings": [{"id": "CVE-...", "package": "...", "status": "fixed" or "left",
               "change": "<what you changed, or empty>", "reason": "<one line>"}]}
"""


def load_findings(report_path):
    """Flatten a Trivy JSON report into one dict per finding."""
    report = json.loads(Path(report_path).read_text())
    findings = []
    for result in report.get("Results") or []:
        for vuln in result.get("Vulnerabilities") or []:
            findings.append({
                "id": vuln["VulnerabilityID"],
                "package": vuln["PkgName"],
                "installed": vuln.get("InstalledVersion", ""),
                "fixed": vuln.get("FixedVersion", ""),
                "severity": vuln.get("Severity", ""),
                "title": vuln.get("Title", ""),
                "type": result.get("Type", ""),
                "target": result.get("Target", ""),
                "path": vuln.get("PkgPath", ""),
                "url": vuln.get("PrimaryURL", ""),
            })
    return findings


def finding_key(finding):
    return (finding["id"], finding["package"])


def load_history(path):
    path = Path(path)
    return json.loads(path.read_text()) if path.exists() else []


def save_history(path, history):
    Path(path).write_text(json.dumps(history, indent=2))


def build_prompt(findings, history, round_no, max_rounds):
    files = "\n\n".join(
        f"=== {name} ===\n{Path(name).read_text()}"
        for name in ALLOWED_FILES + CONTEXT_FILES if Path(name).exists()
    )
    earlier = json.dumps(history, indent=2) if history else "none, this is the first round"
    return (
        f"Round {round_no} of {max_rounds}.\n\n"
        f"Findings that still fail:\n{json.dumps(findings, indent=2)}\n\n"
        f"Earlier rounds:\n{earlier}\n\n"
        f"Current files:\n\n{files}\n"
    )


def parse_reply(text):
    # Some open models put their reasoning inline instead of in a separate
    # content block; only the JSON object after it matters.
    text = re.sub(r"<reasoning>.*?</reasoning>", "", text, flags=re.S)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end < start:
        raise ValueError("no JSON object in the reply")
    try:
        data = json.loads(text[start:end + 1])
    except json.JSONDecodeError as err:
        raise ValueError(f"the reply is not valid JSON: {err}") from err
    if not isinstance(data, dict):
        raise ValueError("the reply is not a JSON object")
    return data


def ask_model(model_id, prompt):
    """One Bedrock Converse call, with one retry if the reply isn't valid JSON.

    Converse gives the same request shape for every model on Bedrock, so
    switching model is only a change of BEDROCK_MODEL_ID. Credentials come
    from the environment: AWS_BEARER_TOKEN_BEDROCK (a Bedrock API key) or the
    role the workflow assumed through OIDC. The region comes from AWS_REGION.
    """
    import boto3
    from botocore.config import Config

    client = boto3.client(
        "bedrock-runtime",
        config=Config(read_timeout=300, retries={"max_attempts": 4, "mode": "adaptive"}),
    )
    messages = [{"role": "user", "content": [{"text": prompt}]}]
    for attempt in range(2):
        response = client.converse(
            modelId=model_id,
            system=[{"text": SYSTEM_PROMPT}],
            messages=messages,
            inferenceConfig={"maxTokens": 8000, "temperature": 0},
        )
        content = response["output"]["message"]["content"]
        text = "".join(block["text"] for block in content if "text" in block)
        try:
            return parse_reply(text)
        except ValueError as err:
            if attempt == 1:
                raise
            print(f"Retrying: {err}", file=sys.stderr)
            messages += [
                {"role": "assistant", "content": [{"text": text or "(empty reply)"}]},
                {"role": "user", "content": [{"text": f"That reply was unusable ({err}). "
                                                      "Reply with only the JSON object."}]},
            ]


def apply_edits(edits):
    applied, rejected = [], []
    for edit in edits if isinstance(edits, list) else []:
        if not isinstance(edit, dict):
            rejected.append({"edit": edit, "reason": "not an object"})
            continue
        path, find, replace = edit.get("path"), edit.get("find"), edit.get("replace")
        reason = None
        if path not in ALLOWED_FILES:
            reason = f"{path!r} is not one of the files the fix may edit"
        elif not Path(path).exists():
            reason = f"{path} does not exist"
        elif not isinstance(find, str) or not find or not isinstance(replace, str):
            reason = "an edit needs a non-empty 'find' and a 'replace' string"
        else:
            content = Path(path).read_text()
            matches = content.count(find)
            if matches != 1:
                reason = f"'find' occurs {matches} times in {path}, it must occur exactly once"
        if reason:
            rejected.append({"path": path, "find": find, "replace": replace, "reason": reason})
            continue
        Path(path).write_text(content.replace(find, replace, 1))
        applied.append({"path": path, "find": find, "replace": replace})
    return applied, rejected


def cmd_fix(args):
    findings = load_findings(args.report)
    history = load_history(args.history)
    reply = ask_model(args.model, build_prompt(findings, history, args.round, args.max_rounds))
    applied, rejected = apply_edits(reply.get("edits"))
    history.append({
        "round": args.round,
        "model_findings": reply.get("findings", []),
        "applied": applied,
        "rejected": rejected,
    })
    save_history(args.history, history)
    print(f"Round {args.round}: applied {len(applied)} edit(s), rejected {len(rejected)}")
    for edit in rejected:
        print(f"  rejected: {edit['reason']}")


def cmd_record(args):
    history = load_history(args.history)
    entry = history[-1]
    entry["build"] = args.build
    if args.build_log:
        entry["build_log_tail"] = "\n".join(Path(args.build_log).read_text().splitlines()[-60:])
    if args.report:
        entry["still_failing"] = [
            f"{f['id']} {f['package']} {f['installed']} (fixed in {f['fixed'] or 'none'})"
            for f in load_findings(args.report)
        ]
    if args.rolled_back:
        # Tells the next round this edit was undone and didn't help.
        entry["rolled_back"] = args.rolled_back
    save_history(args.history, history)


def fixed_by_package(initial_report, final_report):
    """Findings the rescan no longer reports, grouped by package."""
    remaining = {finding_key(f) for f in load_findings(final_report)}
    packages = {}
    for finding in load_findings(initial_report):
        if finding_key(finding) not in remaining:
            packages.setdefault(finding["package"], []).append(finding)
    return packages


def changelog_lines(packages):
    if not packages:
        return ["- Docker image: dependency updates for security findings"]
    lines = []
    for package, findings in sorted(packages.items()):
        # Trivy may list several fixed versions ("1.26.19, 2.2.2"); name the highest.
        versions = [v.strip() for f in findings for v in f["fixed"].split(",") if v.strip()]
        fixed = max(versions, key=lambda v: [int(n) for n in re.findall(r"\d+", v)], default="")
        ids = ", ".join(sorted({f["id"] for f in findings}))
        target = f" to {fixed}" if fixed else ""
        lines.append(f"- Docker image: `{package}` updated{target} to fix {ids}")
    return lines


def git_tag_exists(tag):
    return subprocess.run(
        ["git", "rev-parse", "-q", "--verify", f"refs/tags/{tag}"], capture_output=True
    ).returncode == 0


def cmd_bump_version(args):
    text = VERSION_FILE.read_text()
    match = re.search(r"""__version__\s*=\s*['"]v?(\d+)\.(\d+)\.(\d+)['"]""", text)
    if not match:
        sys.exit(f"Could not parse a plain X.Y.Z __version__ in {VERSION_FILE}")
    major, minor, patch = match.groups()
    current = f"{major}.{minor}.{patch}"
    lines = "\n".join(changelog_lines(fixed_by_package(args.initial, args.final)))
    changelog = CHANGELOG.read_text()
    sections = [m.start() for m in re.finditer(r"^## v", changelog, flags=re.M)]

    # A released version is immutable on Quay and PyPI, so the fix has to ship
    # as a new patch release. An unreleased one (a release blocked by this very
    # scan) just takes the fix with it.
    if git_tag_exists(f"v{current}"):
        version = f"{major}.{minor}.{int(patch) + 1}"
        VERSION_FILE.write_text(text.replace(match.group(0), f"__version__ = '{version}'"))
        today = datetime.date.today().isoformat()
        section = f"## v{version} ({today})\n\n### Fix:\n\n{lines}\n\n"
        at = sections[0] if sections else len(changelog)
        changelog = changelog[:at] + section + changelog[at:]
        bumped = True
    else:
        version = current
        top_end = sections[1] if len(sections) > 1 else len(changelog)
        top = changelog[sections[0]:top_end] if sections else ""
        if "### Fix:\n\n" in top:
            at = changelog.index("### Fix:\n\n", sections[0]) + len("### Fix:\n\n")
            changelog = changelog[:at] + lines + "\n" + changelog[at:]
        else:
            changelog = (changelog[:top_end].rstrip("\n") + f"\n\n### Fix:\n\n{lines}\n\n"
                         + changelog[top_end:])
        bumped = False
    CHANGELOG.write_text(changelog)

    with open(os.environ.get("GITHUB_OUTPUT", os.devnull), "a") as out:
        out.write(f"version={version}\nbumped={str(bumped).lower()}\n")
    print(f"v{current} {'is released; bumped to' if bumped else 'is unreleased; fix ships in'} v{version}")


def cmd_count_fixed(args):
    print(sum(len(f) for f in fixed_by_package(args.initial, args.final).values()))


def cell(text):
    return str(text).replace("|", "\\|").replace("\n", " ")


def cmd_pr_body(args):
    initial = load_findings(args.initial)
    remaining = {finding_key(f) for f in load_findings(args.final)}
    history = load_history(args.history)
    notes = {(n.get("id"), n.get("package")): n
             for entry in history for n in entry.get("model_findings", []) if isinstance(n, dict)}

    if args.mode == "rebuild":
        intro = (
            f"The newest release, `v{args.release}`, has **{len(initial)}** CRITICAL/HIGH "
            f"finding(s) that a fresh build of `{args.base}` no longer has, usually OS packages "
            "patched since it was built, which the build's `apt-get upgrade` picks up. Released "
            "images are never rebuilt in place, so this PR only bumps the version: merging it "
            "makes the release workflow publish a new, clean versioned image (and PyPI package)."
        )
        after = "Fresh build"
    elif args.mode == "pr":
        intro = (
            f"The image built from `{args.base}` had **{len(initial)}** CRITICAL/HIGH "
            f"finding(s). `{args.model}` proposed fixes over {len(history)} round(s), each one "
            f"rebuilt and rescanned; **{len(remaining)}** remain. Rounds that reduced the findings were pushed "
            "to this branch as `Security autofix` commits."
        )
        after = "After rescan"
    else:
        intro = (
            f"The scheduled Trivy scan of the image built from `{args.base}` found "
            f"**{len(initial)}** CRITICAL/HIGH finding(s). `{args.model}` proposed fixes over "
            f"{len(history)} round(s); after rebuilding and rescanning, **{len(remaining)}** remain."
        )
        after = "After rescan"
    out = [
        intro,
        "",
        f"| CVE | Severity | Package | Installed | Fixed in | {after} | Model's note |",
        "|---|---|---|---|---|---|---|",
    ]
    for f in initial:
        status = "still failing" if finding_key(f) in remaining else "fixed"
        note = notes.get(finding_key(f), {})
        out.append(" | ".join([
            f"| [{f['id']}]({f['url']})" if f["url"] else f"| {f['id']}",
            f["severity"], f"`{f['package']}`", f["installed"], f["fixed"] or "none",
            status, cell(note.get("change") or note.get("reason") or "") + " |",
        ]))

    if history:
        out += ["", "### Rounds", ""]
    for entry in history:
        applied = ", ".join(f"`{e['path']}`" for e in entry.get("applied", [])) or "no edits"
        line = f"- Round {entry['round']}: {applied}; build {entry.get('build', 'not run')}"
        if entry.get("rejected"):
            line += f"; {len(entry['rejected'])} edit(s) rejected"
        if "still_failing" in entry:
            line += f"; {len(entry['still_failing'])} still failing after it"
        if entry.get("rolled_back"):
            line += "; rolled back, it fixed nothing"
        out.append(line)

    if args.version:
        out += [
            "", "### Release", "",
            f"Version bumped to `v{args.version}` because the previous version is already released."
            if args.bumped == "true" else
            f"`v{args.version}` is not released yet, so the fix ships with it; no version bump.",
        ]
    out += [
        "", "### Review", "",
        "- [ ] Only dependency files, the version and the changelog changed",
        "- [ ] The rescan in the workflow run is clean, or what remains is explained above",
        "- [ ] No major version bump that needs a wider test run",
        "",
        f"From the [workflow run]({args.run_url}). Nothing here is merged automatically.",
    ]
    Path(args.output).write_text("\n".join(out) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    fix = sub.add_parser("fix")
    fix.add_argument("--report", required=True)
    fix.add_argument("--history", required=True)
    fix.add_argument("--round", type=int, required=True)
    fix.add_argument("--max-rounds", type=int, required=True)
    fix.add_argument("--model", required=True)
    fix.set_defaults(func=cmd_fix)

    record = sub.add_parser("record")
    record.add_argument("--history", required=True)
    record.add_argument("--build", choices=["ok", "failed"], required=True)
    record.add_argument("--build-log")
    record.add_argument("--report")
    record.add_argument("--rolled-back", help="why the round's edits were undone")
    record.set_defaults(func=cmd_record)

    bump = sub.add_parser("bump-version")
    bump.add_argument("--initial", required=True)
    bump.add_argument("--final", required=True)
    bump.set_defaults(func=cmd_bump_version)

    count = sub.add_parser("count-fixed")
    count.add_argument("--initial", required=True)
    count.add_argument("--final", required=True)
    count.set_defaults(func=cmd_count_fixed)

    body = sub.add_parser("pr-body")
    body.add_argument("--mode", choices=["fix", "rebuild", "pr"], default="fix")
    body.add_argument("--release")
    body.add_argument("--initial", required=True)
    body.add_argument("--final", required=True)
    body.add_argument("--history", required=True)
    body.add_argument("--base", required=True)
    body.add_argument("--model", required=True)
    body.add_argument("--version")
    body.add_argument("--bumped")
    body.add_argument("--run-url", required=True)
    body.add_argument("--output", required=True)
    body.set_defaults(func=cmd_pr_body)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

#!/usr/bin/env bash
# Build the image, scan it, and let the model fix what fails: up to MAX_ROUNDS
# rounds of fix -> rebuild -> rescan, stopping as soon as the scan is clean.
#
# Each round that builds is committed locally, so a round that breaks the
# build is rolled back without losing the rounds before it. Nothing is pushed
# here; the workflow decides what to do with the commits.
#
# Needs: IMAGE, MAX_ROUNDS, BEDROCK_MODEL_ID, AUTOFIX_DIR, and Bedrock
# credentials in the environment. Writes changed, initial, remaining and
# rounds to $GITHUB_OUTPUT, and the reports and history to $AUTOFIX_DIR.
set -euo pipefail

: "${IMAGE:?}" "${MAX_ROUNDS:?}" "${BEDROCK_MODEL_ID:?}" "${AUTOFIX_DIR:?}"
scan=.github/actions/trivy-scan/scan.sh
autofix=.github/scripts/autofix.py
history="$AUTOFIX_DIR/history.json"
mkdir -p "$AUTOFIX_DIR"

count() { jq '[.Results[]?.Vulnerabilities[]?] | length' "$1"; }

# Same build as the release, so the scan sees what the release would ship.
build() {
  docker build -f Dockerfile --build-arg SECURITY_REFRESH="$(date +%s)" -t "$IMAGE" . >"$1" 2>&1
}

start_sha=$(git rev-parse HEAD)

if ! build "$AUTOFIX_DIR/build-0.log"; then
  tail -50 "$AUTOFIX_DIR/build-0.log"
  echo "::error::The image does not build from this commit, so there is nothing to scan."
  exit 1
fi
"$scan" "$IMAGE" "$AUTOFIX_DIR/initial.json"
last="$AUTOFIX_DIR/initial.json"
initial=$(count "$last")
remaining=$initial
rounds=0
echo "Initial scan: $initial CRITICAL/HIGH finding(s)"

round=1
while [ "$remaining" -gt 0 ] && [ "$round" -le "$MAX_ROUNDS" ]; do
  echo "::group::Round $round of $MAX_ROUNDS"
  rounds=$round
  python "$autofix" fix --report "$last" --history "$history" \
    --round "$round" --max-rounds "$MAX_ROUNDS" --model "$BEDROCK_MODEL_ID"

  if git diff --quiet; then
    echo "The model proposed no edits that apply; stopping."
    echo "::endgroup::"
    break
  fi
  git --no-pager diff

  if build "$AUTOFIX_DIR/build-$round.log"; then
    "$scan" "$IMAGE" "$AUTOFIX_DIR/round-$round.json"
    python "$autofix" record --history "$history" --build ok --report "$AUTOFIX_DIR/round-$round.json"
    git commit -qam "Security autofix: round $round"
    last="$AUTOFIX_DIR/round-$round.json"
    remaining=$(count "$last")
    echo "After round $round: $remaining finding(s) left"
  else
    tail -30 "$AUTOFIX_DIR/build-$round.log"
    python "$autofix" record --history "$history" --build failed --build-log "$AUTOFIX_DIR/build-$round.log"
    git checkout -- .
    echo "The build failed, so round $round's edits were rolled back."
  fi
  echo "::endgroup::"
  round=$((round + 1))
done

cp "$last" "$AUTOFIX_DIR/final.json"
changed=false
git diff --quiet "$start_sha" HEAD || changed=true
{
  echo "changed=$changed"
  echo "initial=$initial"
  echo "remaining=$remaining"
  echo "rounds=$rounds"
} >> "$GITHUB_OUTPUT"

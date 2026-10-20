#!/usr/bin/env bash
# Scan an image with Trivy and write its CRITICAL/HIGH findings to a JSON
# report, printing the usual table to the log as well.
#
# Usage: scan.sh IMAGE REPORT [IMAGE_SRC]
#   IMAGE_SRC is passed to --image-src: "docker" (default) for an image built
#   on this runner, "remote" for one that is only on the registry.
#
# Exits non-zero only when Trivy itself fails (it exits 2 on errors, and
# --exit-code is deliberately not set): callers count the findings and decide
# what they mean, because the release gate fails on them and the weekly scan
# does not. Unfixed CVEs are counted (no --ignore-unfixed), which mirrors the
# Harbor gate. CVEs accepted in .trivyignore.yaml at the repo root are skipped.
set -euo pipefail

image=$1
report=$2
image_src=${3:-docker}
trivy_version=${TRIVY_VERSION:-0.74.0}
severity=${SEVERITY:-CRITICAL,HIGH}

mkdir -p "$(dirname "$report")" "$HOME/.cache/trivy"
report_dir=$(cd "$(dirname "$report")" && pwd)
report_name=$(basename "$report")

ignore=()
if [ -f .trivyignore.yaml ]; then
  ignore=(--ignorefile /src/.trivyignore.yaml)
fi

# Local runs only: behind a TLS-inspecting VPN, Trivy can't verify the DB or
# registry downloads. TRIVY_CA_BUNDLE points at a PEM bundle of the public
# roots plus the VPN's CA; it replaces the container's trust store. CI leaves
# it unset.
ca=()
if [ -n "${TRIVY_CA_BUNDLE:-}" ]; then
  ca=(-v "$TRIVY_CA_BUNDLE:/etc/trivy-ca.pem:ro" -e SSL_CERT_FILE=/etc/trivy-ca.pem)
fi

# Trivy runs as a pinned container, so there is nothing to install. The cache
# mount means the vulnerability DB is downloaded once per runner, not once per
# scan, which matters for the fix loop's repeated rescans.
trivy() {
  docker run --rm \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v "$HOME/.cache/trivy:/root/.cache/trivy" \
    -v "$PWD:/src:ro" \
    -v "$report_dir:/out" \
    ${ca[@]+"${ca[@]}"} \
    "aquasec/trivy:$trivy_version" "$@"
}

trivy image \
  --image-src "$image_src" \
  --scanners vuln \
  --severity "$severity" \
  --format json \
  --output "/out/$report_name" \
  ${ignore[@]+"${ignore[@]}"} \
  "$image"

trivy convert --format table "/out/$report_name"

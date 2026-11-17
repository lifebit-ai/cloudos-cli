# cloudos-cli image: FIPS build

From v2.101.0, the image (`Dockerfile`, published as `quay.io/lifebitaiorg/cloudos-cli:v<version>` and `:latest`) is built for FIPS: Red Hat UBI 10.3 with the CLI in a conda environment, so that every HTTPS call the CLI makes goes through Red Hat's OpenSSL FIPS provider when the host is in FIPS mode (see FIPS module for its certificate status on UBI 10). On a host that isn't in FIPS mode it behaves like any other image (all algorithms allowed). It follows the "FIPS hardening POC" (Confluence, IO Squad space) and `containers/report_etl/2.0.0-fips` in `lifebit-ai/ADAPT-docker-containers`.

```bash
docker build -t quay.io/lifebitaiorg/cloudos-cli:<version> .
docker run --rm --entrypoint sh quay.io/lifebitaiorg/cloudos-cli:<version> /docker/fips/smoketest.sh
```

## FIPS module
All crypto goes through **Red Hat Enterprise Linux 9 - OpenSSL FIPS Provider** (the name on the certificate; the image is UBI 10.3), module version `3.0.7-cda111b5812c30d4`, package `openssl-fips-provider-3.0.7-11.el10_2`. That's the module on [CMVP certificate #5573](https://csrc.nist.gov/projects/cryptographic-module-validation-program/certificate/5573) (FIPS 140-3, active, validated 2026-11-09), which replaced #4857 (now historical). The certificate's tested operational environments are RHEL 9 only. The [Red Hat FIPS page](https://access.redhat.com/compliance/fips) marks the older RHEL 10.0 provider (module `3.0.7-395c1a240fbfffd8`) as "Pending Operational Environment update" and lists RHEL 10.2, where this package comes from, as TBD. So whether this module is validated on RHEL 10 / UBI 10 is unconfirmed: it's the validated module binary, not a validated configuration. Check that with your compliance team before relying on it. The base is **UBI 10.3, pinned by digest**, which ships that provider; `dnf upgrade` excludes `openssl-fips-provider*`, so the certified build stays when the UBI repositories move to a newer one, and the build fails if the provider isn't `3.0.7-11.el10_2`. Move to a newer UBI once Red Hat's certificate covers its provider.

## How it follows FIPS mode
- **System OpenSSL with a FIPS provider**: UBI 10.3 instead of `condaforge/miniforge3` (Ubuntu, no FIPS provider).
- **conda-forge's own OpenSSL**: `fips-harden-conda-env` (copied from `lifebit-ai/vscode` `fips-builds/base/bin`, commit `1d7f3fa1804b`) runs last on `/opt/conda` and, if the image is built with `--build-arg ENV_NAME=<name>`, on the environment the CLI is installed in. It replaces the environment's `libssl`/`libcrypto` with symlinks to `/usr/lib64`, removes CPython's built-in hash modules (including `_blake2`) and `_crypt` where present (Python 3.13 has none), patches `hashlib`, and fails the build if Python still loads a non-system `libcrypto`. It only works if conda's `openssl` matches the system major.minor: `OPENSSL_PIN=3.5`, also added to conda's `pinned_packages`. **Bump it together with the UBI version.**
- **micromamba** (static, with its own crypto) is removed from the Miniforge install.

## Why Python 3.13
`fips-harden-conda-env` was written for Python 3.11/3.12. Tested on the FIPS host (2026-11-16) in a conda env on UBI 10.1, after the script:

| | 3.12 | 3.13 | 3.14 | 3.15 |
|---|---|---|---|---|
| script | OK | OK | runs | fails (`hashlib.py` changed) |
| `hashlib.md5()`, `pbkdf2_hmac("md5")`, `hmac.new(k, m, "md5")`, `hmac.digest(k, m, "md5")` | refused | refused | `hmac.new` **allowed** (built-in `_hmac`, new in 3.14) | – |
| `hashlib.new("md5")` | refused | refused | **allowed**: 3.14's `_hashlib` fetches MD5 from OpenSSL's non-FIPS default provider | – |
| `hashlib.md5(..., usedforsecurity=False)` | allowed | allowed | refused | – |

So 3.13 is the newest Python that keeps every hash and HMAC path inside the FIPS module, and behaves exactly like 3.12. Python 3.14+ would need a change in CPython's `_hashlib` itself, not just the script. (BLAKE2 isn't FIPS-approved. `hashlib.blake2b`/`blake2s` and `hashlib.new("blake2b")` come from CPython's own `_blake2`, which `fips-harden-conda-env` removes, so they're refused. The OpenSSL names `hashlib.new("blake2b512")` and `"blake2s256"` go through `_hashlib` instead, and in FIPS mode they're refused too. Only `usedforsecurity=False` lets them through, through OpenSSL's non-FIPS default provider, the same opt-out that already allows MD5 and SHA-1 for non-security uses (tested on the FIPS host, 2026-11-17). `fips-scan` doesn't test BLAKE2; `smoketest.sh` does.)

## Differences from the Ubuntu image (up to v2.99.3)
The CLI, `environment.yml`, `pip install -e /`, `PATH`, `LANG`/`LC_ALL=C.UTF-8`, `CONDA_DIR`, `CMD ["/bin/bash"]`, `ENTRYPOINT []` and `procps` (for Nextflow) are the same. What changed:
- **Base**: Red Hat UBI 10.3 instead of `condaforge/miniforge3` (Ubuntu 24.04). Ubuntu tools are gone (`apt-get`, `dpkg`, `perl`, `cmp`…); install extra OS packages with `dnf` from the UBI repositories in images built on top of this one.
- **Python 3.13** instead of 3.14 (`python_requires` is `>=3.11`): the newest version that can be hardened (see Why Python 3.13).
- conda's OpenSSL 3.5 instead of 3.6, replaced at runtime by the system library.
- Miniforge is installed from its GitHub release with a pinned version and SHA-256, instead of coming with the base image; micromamba and conda's package cache are removed.
- `TZ=Etc/UTC` (UBI has no `/etc/localtime`; Ubuntu defaults to UTC).
- About 1 GB instead of 790 MB.

## CI and releases
- `release.yml` builds `Dockerfile` (with `SECURITY_REFRESH`, which re-runs the final `dnf upgrade`), runs `docker/fips/smoketest.sh`, applies the Trivy gate, and publishes `v<version>` and `:latest` as before.
- `image-scan.yml` (every PR) and `security-autofix.yml` build the same `Dockerfile`; the PR scan runs the smoke test too. Autofix only edits `environment.yml`/`requirements.txt`, and is told never to change the `openssl` and `python` pins, which the hardening depends on.
- GitHub's runners aren't in FIPS mode, so `smoketest.sh` sets `OPENSSL_FORCE_FIPS_MODE=1`, which RHEL's `libcrypto` treats like a FIPS kernel. It checks that the CLI starts, that Python loads only the system `libcrypto`, that the certified provider is installed (`3.0.7-11.el10_2`, module `3.0.7-cda111b5812c30d4` in `fips.so`) and loads (SHA-256 and HMAC-SHA-256 work), and that MD5, `hashlib.new("md5")`, HMAC-MD5 and BLAKE2 (including `hashlib.new("blake2b512")` and `"blake2s256"`) are refused. It doesn't replace a run on a real FIPS host: use `scripts/fips/fips-scan` from `lifebit-ai/ADAPT-docker-containers` when the base, `OPENSSL_PIN` or the Python version changes.

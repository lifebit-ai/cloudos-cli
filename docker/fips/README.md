# cloudos-cli FIPS image (`Dockerfile.fips`)

`Dockerfile.fips` builds the same image as `Dockerfile` (the CLI, its conda environment, `procps`, `CMD ["/bin/bash"]`, `ENTRYPOINT []`, `LANG`/`LC_ALL=C.UTF-8`, `CONDA_DIR`, `PATH`), but on Red Hat UBI 10, so that every HTTPS call the CLI makes goes through a FIPS 140-3 validated OpenSSL module when the host is in FIPS mode. It follows the "FIPS hardening POC" (Confluence, IO Squad space) and `containers/report_etl/2.0.0-fips` in `lifebit-ai/ADAPT-docker-containers`.

```bash
docker build -f Dockerfile.fips -t quay.io/lifebitaiorg/cloudos-cli:<version>-fips .
docker run --rm --entrypoint sh quay.io/lifebitaiorg/cloudos-cli:<version>-fips /docker/fips/smoketest.sh
```

## FIPS module
All crypto goes through **Red Hat Enterprise Linux 9 - OpenSSL FIPS Provider** (the name on the certificate; the image is UBI 10.1), module version `3.0.7-395c1a240fbfffd8`, package `openssl-fips-provider-3.0.7-8.el10`, covered by [CMVP certificate #4857](https://csrc.nist.gov/projects/cryptographic-module-validation-program/certificate/4857) (FIPS 140-3). The base is **UBI 10.1, pinned by digest**, because newer UBI 10 releases ship a provider build that isn't on a certificate yet; `dnf upgrade` excludes `openssl-fips-provider*`, and the build fails if the provider isn't `3.0.7-8.el10`. Move to the latest UBI once Red Hat's certificate covers its provider.

## How it follows FIPS mode
- **System OpenSSL with a FIPS provider**: UBI 10.1 instead of `condaforge/miniforge3` (Ubuntu, no FIPS provider).
- **conda-forge's own OpenSSL**: `fips-harden-conda-env` (copied from `lifebit-ai/vscode` `fips-builds/base/bin`, commit `1d7f3fa1804b`) runs on `/opt/conda` last. It replaces the environment's `libssl`/`libcrypto` with symlinks to `/usr/lib64`, removes CPython's built-in hash modules, patches `hashlib`, and fails the build if Python still loads a non-system `libcrypto`. It only works if conda's `openssl` matches the system major.minor: `OPENSSL_PIN=3.5`, also added to conda's `pinned_packages`. **Bump it together with the UBI version.**
- **micromamba** (static, with its own crypto) is removed from the Miniforge install.

## Why Python 3.13
`fips-harden-conda-env` was written for Python 3.11/3.12. Tested on the FIPS host (2026-11-16) in a conda env on UBI 10.1, after the script:

| | 3.12 | 3.13 | 3.14 | 3.15 |
|---|---|---|---|---|
| script | OK | OK | runs | fails (`hashlib.py` changed) |
| `hashlib.md5()`, `pbkdf2_hmac("md5")`, `hmac.new(k, m, "md5")`, `hmac.digest(k, m, "md5")` | refused | refused | `hmac.new` **allowed** (built-in `_hmac`, new in 3.14) | – |
| `hashlib.new("md5")` | refused | refused | **allowed**: 3.14's `_hashlib` fetches MD5 from OpenSSL's non-FIPS default provider | – |
| `hashlib.md5(..., usedforsecurity=False)` | allowed | allowed | refused | – |

So 3.13 is the newest Python that keeps every hash and HMAC path inside the FIPS module, and behaves exactly like 3.12. Python 3.14+ would need a change in CPython's `_hashlib` itself, not just the script. (BLAKE2 stays available through CPython's own `_blake2` in every version, as in report_etl: `fips-harden-conda-env` doesn't remove it, and `fips-scan` doesn't test it.)

## Differences from `Dockerfile`
- **Python 3.13** instead of 3.14 (`python_requires` is `>=3.11`): the newest version that can be hardened (see Why Python 3.13).
- conda's OpenSSL 3.5 instead of 3.6, replaced at runtime by the system library.
- Miniforge is installed from its GitHub release with a pinned version and SHA-256, instead of coming with the base image.
- `TZ=Etc/UTC` (UBI has no `/etc/localtime`; Ubuntu defaults to UTC).
- No `SECURITY_REFRESH` layer yet: build with `--no-cache` (or add the same final `dnf upgrade --exclude='openssl-fips-provider*'` layer) so cached builds still pick up OS security fixes.

## Publishing
`release.yml` and `image-scan.yml` only build `Dockerfile`. To publish `<version>-fips` tags, add a build of `Dockerfile.fips` to them (same scan gate), once the image has passed a functional run on a FIPS host.

## Validation
See the PR that added this file for the FIPS scan (`scripts/fips/fips-scan` from `ADAPT-docker-containers`, on a FIPS-enabled host), Trivy and network results.

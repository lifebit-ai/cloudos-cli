# The cloudos-cli image, built for FIPS: Red Hat UBI 10 with the CLI in a conda environment.
# Up to v2.99.3 the image was condaforge/miniforge3 (Ubuntu 24.04); the CLI, environment.yml, PATH, LANG/LC_ALL, CMD
# and ENTRYPOINT are the same. See docker/fips/README.md for what changed.
#
# Containers inherit FIPS mode from the host kernel. On a FIPS-enabled host, UBI's OpenSSL (a FIPS-validated module)
# only allows approved algorithms. conda-forge ships its own OpenSSL without a FIPS provider, so fips-harden-conda-env
# points the conda environment to the system OpenSSL: every HTTPS call the CLI makes (requests/urllib3) then goes
# through the FIPS module. See docker/fips/README.md.
#
# The base is UBI 10.3, pinned by digest, because its OpenSSL FIPS provider (openssl-fips-provider-3.0.7-11.el10_2) is
# module version 3.0.7-cda111b5812c30d4, the one on CMVP certificate #5573 (FIPS 140-3, active; it replaced #4857).
# The certificate's tested operational environments are RHEL 9 only. Red Hat's FIPS page marks the older RHEL 10.0
# provider as "Pending Operational Environment update" and lists RHEL 10.2 as TBD, so validation on UBI 10 is
# unconfirmed: this is the validated module binary, not a validated configuration. The UBI
# repositories only carry the newest provider build, which may not be on a certificate yet, so every other package is
# upgraded (security fixes) but the FIPS provider is kept. Move to a newer base once Red Hat's certificate covers its
# provider.
FROM registry.access.redhat.com/ubi10/ubi:10.3@sha256:73ea54bfbfb586075bd3d45df6483a7f68875233c8cc7cebcf9b2bb42306c308

LABEL name="quay.io/lifebitaiorg/cloudos-cli" \
      description="The cloudos-cli docker container" \
      maintainer="David Pineyro <davidp@lifebit.ai>"

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Check the latest release on https://github.com/conda-forge/miniforge/releases (and its .sha256 file).
ARG MINIFORGE_VERSION=26.7.2-0
ARG MINIFORGE_SHA256=281b0ac7d550802efc81af633225a5e6116d29ae72f3ab4eae7168c3931a4c05

# The conda environment must use the system OpenSSL major.minor, because fips-harden-conda-env points its
# libssl/libcrypto to the system ones (3.5 after the upgrade below). Bump it together with the UBI version.
ENV OPENSSL_PIN=3.5

# Same settings as the Ubuntu image (CONDA_DIR, LANG and LC_ALL came from its condaforge/miniforge3 base).
ENV CONDA_DIR=/opt/conda \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    TZ=Etc/UTC
ENV PATH="${CONDA_DIR}/bin:${PATH}"

# procps-ng is required by Nextflow for `ps` task tracing.
# Pinned to the version only: the UBI repositories keep only the newest release of each package, so a release pin
# (e.g. -13.el10) breaks the rebuild at the next errata. The FIPS provider is the exception: openssl-fips-provider is
# excluded so that dnf keeps the certified build, and `rpm -q` checks its exact release.
RUN dnf upgrade -y --exclude='openssl-fips-provider*' \
    && dnf install -y --setopt=install_weak_deps=0 --exclude='openssl-fips-provider*' \
      procps-ng-4.0.4 \
    && rpm -q openssl-fips-provider-3.0.7-11.el10_2 openssl-fips-provider-so-3.0.7-11.el10_2 \
    && dnf clean all \
    && rm -rf /var/cache/dnf

RUN curl -fsSL -o /tmp/miniforge.sh \
      "https://github.com/conda-forge/miniforge/releases/download/${MINIFORGE_VERSION}/Miniforge3-${MINIFORGE_VERSION}-Linux-x86_64.sh" \
    && echo "${MINIFORGE_SHA256}  /tmp/miniforge.sh" | sha256sum -c - \
    && bash /tmp/miniforge.sh -b -p "${CONDA_DIR}" \
    && rm /tmp/miniforge.sh \
    # Python 3.13 (the Ubuntu image had 3.14; the package needs >= 3.11): the newest version fips-harden-conda-env fully
    # hardens. On a FIPS host, 3.14's _hashlib still computes MD5 through OpenSSL's non-FIPS provider and its built-in
    # _hmac allows HMAC-MD5 (see docker/fips/README.md). conda is pinned to OPENSSL_PIN and this Python.
    && conda install -y -n base python=3.13 "openssl=${OPENSSL_PIN}" \
    && conda config --system --add pinned_packages "openssl=${OPENSSL_PIN}" \
    && conda config --system --add pinned_packages "python=3.13" \
    # micromamba is a static binary with its own crypto, and nothing here needs it.
    && rm -f "${CONDA_DIR}/micromamba" "${CONDA_DIR}/bin/micromamba" \
    # The package cache keeps unhardened copies of python and openssl (and their own libcrypto) in the image.
    && conda clean --all --yes \
    && find "${CONDA_DIR}/pkgs" -mindepth 1 -maxdepth 1 -exec rm -rf {} +

# conda environment and the CLI, as in the Ubuntu image.
ARG ENV_NAME="base"
COPY environment.yml /
RUN conda env update --quiet --name ${ENV_NAME} --file /environment.yml \
    && conda clean -a -y \
    && find "${CONDA_DIR}/pkgs" -mindepth 1 -maxdepth 1 -exec rm -rf {} +

ENV PATH=/opt/conda/envs/${ENV_NAME}/bin:$PATH

COPY . /
ENV PATH=/cloudos_cli:$PATH
RUN pip install --no-cache-dir -e / \
    && chmod ugo+x /cloudos_cli/*py /cloudos_cli/jobs/*py /cloudos_cli/utils/*py \
    && cloudos --help >/dev/null \
    && python -c "import cloudos_cli"

# Two clean-ups, as in the Ubuntu image:
# 1. pip vendors its own dependency manifests (pip/_vendor/vendor.txt and bom.cdx.json), which Trivy reads as
#    installed packages. Metadata only; pip doesn't read them at runtime.
# 2. py-rattler, conda's Rust resolver, links crates with HIGH advisories (pyo3, quinn-proto). Nothing solves
#    dependencies at runtime, so the resolver (its modules, the conda_rattler_solver plugin and both conda-meta
#    entries) is removed; the default solver, libmamba, stays.
RUN find /opt/conda \( -path "*/pip/_vendor/vendor.txt" \
                    -o -path "*/pip/_vendor/bom.cdx.json" \) -delete \
    && rm -rf /opt/conda/lib/python*/site-packages/py_rattler* \
              /opt/conda/lib/python*/site-packages/rattler* \
              /opt/conda/lib/python*/site-packages/conda_rattler_solver* \
              /opt/conda/conda-meta/py-rattler-*.json \
              /opt/conda/conda-meta/conda-rattler-solver-*.json

# Make the environments use the system (FIPS-capable) OpenSSL, and trust the system CA bundle. Last, because any later
# conda install would restore conda's OpenSSL. Both base and, with --build-arg ENV_NAME=<name>, the environment the CLI
# is installed in (first on PATH). Copied from lifebit-ai/ADAPT-docker-containers containers/etl_ingest/4.0.0-fips
# (lifebit-ai/vscode fips-builds/base/bin 1d7f3fa1804b, via report_etl, plus the removal of _blake2 and _crypt).
COPY docker/fips/fips-harden-conda-env /usr/local/bin/fips-harden-conda-env
RUN chmod 755 /usr/local/bin/fips-harden-conda-env \
    && envs="${CONDA_DIR}" \
    && if [ "${ENV_NAME}" != base ]; then envs="${envs} ${CONDA_DIR}/envs/${ENV_NAME}"; fi \
    && for env in ${envs}; do \
         fips-harden-conda-env "${env}" \
         && mkdir -p "${env}/ssl" \
         && ln -sf /etc/pki/tls/certs/ca-bundle.crt "${env}/ssl/cacert.pem" || exit 1; \
       done

# Keep the security update last and in its own layer: earlier layers get cached across rebuilds and a cached update
# silently stops picking up new patches. The release, PR scan and Security autofix force it with
# --build-arg SECURITY_REFRESH=$(date +%s). The FIPS provider stays excluded, and the build fails if it changed.
ARG SECURITY_REFRESH=1
RUN dnf upgrade -y --exclude='openssl-fips-provider*' \
    && rpm -q openssl-fips-provider-3.0.7-11.el10_2 openssl-fips-provider-so-3.0.7-11.el10_2 \
    && dnf clean all \
    && rm -rf /var/cache/dnf

CMD ["/bin/bash"]
ENTRYPOINT []

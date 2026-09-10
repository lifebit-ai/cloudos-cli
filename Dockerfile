# Base: condaforge/miniforge3:26.7.2-0 — the official conda-forge image
# (Ubuntu 24.04 LTS, versioned tags). Replaces continuumio/miniconda3, which is
# Debian: perl-base is an essential package there, cannot be removed, and has
# no fix for CVE-2026-13221 / CVE-2026-42496 / CVE-2026-8376 — a floor of 3
# unfixable CRITICALs at every miniconda tag. miniforge3 also keeps the
# environment at /opt/conda, so nothing that hardcodes a conda path changes.
FROM condaforge/miniforge3:26.7.2-0

LABEL name="quay.io/lifebitaiorg/cloudos-cli" \
      description="The cloudos-cli docker container" \
      maintainer="David Pineyro <davidp@lifebit.ai>"

# `apt-get upgrade` matters: the base image lags the security archive, so
# without it you inherit whatever was current when the base was cut.
# procps is required by Nextflow for `ps` task tracing.
RUN apt-get update -y \
    && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends procps \
    && rm -rf /var/lib/apt/lists/*

# mamba ships in this base, so the old `conda install mamba` step is gone.
ARG ENV_NAME="base"
COPY environment.yml /
RUN conda env update --quiet --name ${ENV_NAME} --file /environment.yml \
    && conda clean -a -y

ENV PATH=/opt/conda/envs/${ENV_NAME}/bin:$PATH

COPY . /
ENV PATH=/cloudos_cli:$PATH
RUN pip install --no-cache-dir -e / \
    && chmod ugo+x /cloudos_cli/*py /cloudos_cli/jobs/*py /cloudos_cli/utils/*py \
    && cloudos --help >/dev/null \
    && python -c "import cloudos_cli"

# Two cleanups are what take a miniforge3 image to zero. Both remove the
# vulnerable code itself — neither hides it from the scanner while leaving it
# installed, which would only make the release gate lie.
#
# 1. pip. It vendors private copies of its own dependencies under
#    pip/_vendor (msgpack, pkg_resources/setuptools, requests, urllib3, ...),
#    and those copies carry HIGH advisories: CVE-2025-47273 (vendored
#    setuptools 70.3.0) and GHSA-6v7p-g79w-8964 (vendored msgpack 1.1.2). The
#    real packages in site-packages are already patched (setuptools 84.0.0,
#    msgpack 1.2.2); only pip's private copies are old and they cannot be
#    upgraded independently of pip, which is already at its latest release.
#    pip is build-time only here — the CLI is installed in the layer above and
#    nothing at runtime shells out to it — so the package is removed outright,
#    vendored code included. (Deleting just pip/_vendor/vendor.txt and
#    bom.cdx.json, as an earlier revision did, dropped Trivy's inventory while
#    leaving the vulnerable code in the image.)
#
# 2. py-rattler is conda's Rust-based resolver. It ships a CycloneDX SBOM
#    declaring the Rust crates linked into its binary, two of which carry HIGH
#    advisories (pyo3, quinn-proto). These are NOT false positives — the code
#    really is in the .so. The environment is fully built by this point and
#    nothing solves dependencies at runtime, so removing the resolver removes
#    real attack surface rather than silencing the scanner.
RUN conda remove --force-remove --yes pip \
    && rm -rf /opt/conda/lib/python*/site-packages/pip \
              /opt/conda/lib/python*/site-packages/pip-*.dist-info \
              /opt/conda/lib/python*/site-packages/py_rattler* \
              /opt/conda/lib/python*/site-packages/rattler* \
    && ! command -v pip

# Keep the security update last and in its own layer: earlier layers get cached
# across rebuilds and a cached update silently stops picking up new patches.
# The release workflow forces it with --build-arg SECURITY_REFRESH=$(date +%s).
ARG SECURITY_REFRESH=1
RUN apt-get update -y && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*

CMD ["/bin/bash"]
ENTRYPOINT []

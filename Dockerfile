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

# Two cleanups are what take a miniforge3 image to zero.
#
# 1. pip vendors its own dependency manifests (pip/_vendor/vendor.txt and
#    bom.cdx.json). Trivy reads them as installed inventory and reports the
#    versions listed there. Metadata only; pip does not read them at runtime.
#
# 2. py-rattler is conda's Rust-based resolver. It ships a CycloneDX SBOM
#    declaring the Rust crates linked into its binary, two of which carry HIGH
#    advisories (pyo3, quinn-proto). These are NOT false positives — the code
#    really is in the .so. The environment is fully built by this point and
#    nothing solves dependencies at runtime, so removing the resolver removes
#    real attack surface rather than silencing the scanner.
#
#    The resolver is four things, not one: the py_rattler/rattler modules, the
#    conda_rattler_solver plugin that dispatches to them, and the conda-meta
#    entries for both. Removing only the modules leaves Trivy's conda-meta
#    analyzer still reporting py-rattler as installed (so a future advisory
#    would fail the gate on code that is no longer here) and leaves the plugin
#    registered against a module that is gone, which turns
#    `conda --solver rattler` into an ImportError. The default solver is
#    libmamba, so nothing routine depends on it.
#
# && rather than ;: with ; the layer's exit status is rm's, which is always 0,
# so a find that errored (a missing /opt/conda, an unreadable tree) was
# discarded and the build carried on with an image that was never cleaned.
# Note find still exits 0 when a pattern simply matches nothing, so this
# guards against a broken tree, not against a base that renames these paths.
RUN find /opt/conda \( -path "*/pip/_vendor/vendor.txt" \
                    -o -path "*/pip/_vendor/bom.cdx.json" \) -delete \
    && rm -rf /opt/conda/lib/python*/site-packages/py_rattler* \
              /opt/conda/lib/python*/site-packages/rattler* \
              /opt/conda/lib/python*/site-packages/conda_rattler_solver* \
              /opt/conda/conda-meta/py-rattler-*.json \
              /opt/conda/conda-meta/conda-rattler-solver-*.json

# Keep the security update last and in its own layer: earlier layers get cached
# across rebuilds and a cached update silently stops picking up new patches.
# The release workflow forces it with --build-arg SECURITY_REFRESH=$(date +%s).
ARG SECURITY_REFRESH=1
RUN apt-get update -y && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*

CMD ["/bin/bash"]
ENTRYPOINT []

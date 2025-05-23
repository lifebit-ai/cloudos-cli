# Full contents of Dockerfile

FROM continuumio/miniconda3:24.7.1-0
LABEL name="quay.io/lifebitaiorg/cloudos-cli" \
      description="The cloudos-cli docker container" \
      maintainer="David Pineyro <davidp@lifebit.ai>"

# Use the base conda env to not be reliant on conda activate when using pip
ARG ENV_NAME="base"

# Install mamba for faster installation in the subsequent step
RUN conda install -c conda-forge mamba -y

# Install the conda environment
COPY environment.yml /
RUN mamba env update --quiet --name ${ENV_NAME} --file /environment.yml && conda clean -a

# Add conda installation dir to PATH (instead of doing 'conda activate')
ENV PATH /opt/conda/envs/${ENV_NAME}/bin:$PATH

# Dump the details of the installed packages to a file for posterity
RUN mamba env export --name ${ENV_NAME} > ${ENV_NAME}_exported.yml

# Copy local package files to be able to install
COPY . /
# Add the created folder to PATH so that tools are accessible
ENV PATH  /cloudos:$PATH
# Install from local files, -e / points to where the setup.py file is located
RUN pip install -e /
# Make the python files executable from anyone (user, group, owner)
RUN chmod ugo+x /cloudos_cli/*py
RUN chmod ugo+x /cloudos_cli/jobs/*py
RUN chmod ugo+x /cloudos_cli/utils/*py

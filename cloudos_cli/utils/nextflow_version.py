"""Nextflow version resolution and validation utilities."""

import rich_click as click
from cloudos_cli.constants import (
    AWS_NEXTFLOW_VERSIONS,
    AZURE_NEXTFLOW_VERSIONS,
    HPC_NEXTFLOW_VERSIONS,
    AWS_NEXTFLOW_LATEST,
    AZURE_NEXTFLOW_LATEST,
    HPC_NEXTFLOW_LATEST
)


def resolve_nextflow_version(
    nextflow_version,
    execution_platform,
    is_module,
    workflow_name=None,
    verbose=False
):
    """
    Resolve and validate the Nextflow version for a job submission.
    
    This function handles:
    - Dynamic defaults based on execution platform and workflow type
    - 'latest' version resolution
    - Platform workflow version forcing
    - Platform-specific version validation with appropriate warnings/errors
    
    Args:
        nextflow_version (str or None): The requested Nextflow version, or None for default
        execution_platform (str): The execution platform ('aws', 'azure', or 'hpc')
        is_module (bool): Whether the workflow is a Platform workflow (module)
        workflow_name (str, optional): The workflow name for informative messages
        verbose (bool, optional): Whether to print verbose messages
    
    Returns:
        str: The resolved and validated Nextflow version
    
    Raises:
        click.BadParameter: If an unsupported version is specified for AWS or HPC platforms
    """
    
    # Step 1: Set dynamic default if no version specified
    if nextflow_version is None:
        if execution_platform == 'azure':
            nextflow_version = '22.11.1-edge'  # Azure has fixed Nextflow version
            if verbose:
                print('\t...Using default Nextflow version 22.11.1-edge for Azure')
        elif execution_platform == 'hpc':
            nextflow_version = '22.10.8'  # HPC has fixed Nextflow version
            if verbose:
                print('\t...Using default Nextflow version 22.10.8 for HPC')
        elif is_module:
            nextflow_version = '22.10.8'  # Lifebit Platform workflows (AWS)
            if verbose:
                print('\t...Using default Nextflow version 22.10.8 for Platform Workflow')
        else:
            nextflow_version = '24.04.4'  # User-imported workflows (AWS only)
            if verbose:
                print('\t...Using default Nextflow version 24.04.4 for user-imported workflow')
    
    # Step 2: Resolve 'latest' to actual version
    if nextflow_version == 'latest':
        if execution_platform == 'aws':
            nextflow_version = AWS_NEXTFLOW_LATEST
        elif execution_platform == 'azure':
            nextflow_version = AZURE_NEXTFLOW_LATEST
        else:
            nextflow_version = HPC_NEXTFLOW_LATEST
        print('You have specified Nextflow version \'latest\' for execution platform ' +
              f'\'{execution_platform}\'. The workflow will use the ' +
              f'latest version available on CloudOS: {nextflow_version}.')
    
    # Step 3: Force correct version for Platform workflows
    if is_module:
        if execution_platform == 'azure':
            if nextflow_version != '22.11.1-edge':
                workflow_msg = f' \'{workflow_name}\'' if workflow_name else ''
                print(f'The selected workflow{workflow_msg} ' +
                      'is a CloudOS Platform Workflow on Azure. Platform Workflows on Azure only work with ' +
                      'Nextflow version 22.11.1-edge. Switching to use 22.11.1-edge')
            nextflow_version = '22.11.1-edge'
        else:
            if nextflow_version != '22.10.8':
                workflow_msg = f' \'{workflow_name}\'' if workflow_name else ''
                print(f'The selected workflow{workflow_msg} ' +
                      'is a CloudOS Platform Workflow. Platform Workflows only work with ' +
                      'Nextflow version 22.10.8. Switching to use 22.10.8')
            nextflow_version = '22.10.8'
    
    # Step 4: Validate version for execution platform
    if execution_platform == 'aws':
        if nextflow_version not in AWS_NEXTFLOW_VERSIONS:
            available_versions = ', '.join(AWS_NEXTFLOW_VERSIONS)
            raise click.BadParameter(
                f'Unsupported Nextflow version \'{nextflow_version}\' for AWS execution platform. '
                f'Supported versions are: {available_versions}.'
            )
    elif execution_platform == 'azure':
        if nextflow_version not in AZURE_NEXTFLOW_VERSIONS:
            available_versions = ', '.join(AZURE_NEXTFLOW_VERSIONS)
            click.secho(
                f'Warning: Nextflow version \'{nextflow_version}\' is not supported for Azure execution platform. '
                f'Azure only supports: {available_versions}. Switching to use {AZURE_NEXTFLOW_LATEST}.',
                fg='yellow', bold=True
            )
            nextflow_version = AZURE_NEXTFLOW_LATEST
    elif execution_platform == 'hpc':
        if nextflow_version not in HPC_NEXTFLOW_VERSIONS:
            available_versions = ', '.join(HPC_NEXTFLOW_VERSIONS)
            raise click.BadParameter(
                f'Unsupported Nextflow version \'{nextflow_version}\' for HPC execution platform. '
                f'HPC only supports: {available_versions}.'
            )
    
    # Step 5: Warn about DSL2 requirement for newer versions
    if nextflow_version not in ['22.10.8', '22.11.1-edge']:
        click.secho(
            f'The Nextflow version being used is: {nextflow_version}. This version requires the pipeline ' +
            'to be written in DSL2 and does not support DSL1.',
            fg='yellow', bold=True
        )
    
    return nextflow_version

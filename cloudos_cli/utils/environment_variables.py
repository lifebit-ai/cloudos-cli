"""Parsing and validation of Nextflow runtime environment variables (e.g. NXF_SYNTAX_PARSER)."""

import re
from cloudos_cli.constants import (
    NEXTFLOW_ENVIRONMENT_VARIABLES,
    MAX_NEXTFLOW_ENVIRONMENT_VARIABLES,
    AWS_NEXTFLOW_VERSIONS,
    AZURE_NEXTFLOW_VERSIONS,
    HPC_NEXTFLOW_VERSIONS,
    AWS_NEXTFLOW_LATEST,
    AZURE_NEXTFLOW_LATEST,
    HPC_NEXTFLOW_LATEST
)

PLATFORM_NEXTFLOW_VERSIONS = {
    'aws': (AWS_NEXTFLOW_VERSIONS, AWS_NEXTFLOW_LATEST),
    'azure': (AZURE_NEXTFLOW_VERSIONS, AZURE_NEXTFLOW_LATEST),
    'hpc': (HPC_NEXTFLOW_VERSIONS, HPC_NEXTFLOW_LATEST)
}


def _version_tuple(version):
    """Return (major, minor, patch) for a Nextflow version string, or None if it can't be parsed.

    Suffixes such as '-edge' are ignored, so '22.11.1-edge' is (22, 11, 1).
    """
    match = re.match(r'^(\d+)\.(\d+)\.(\d+)', str(version))
    if match is None:
        return None
    return tuple(int(part) for part in match.groups())


def _is_version_at_least(version, min_version):
    parsed = _version_tuple(version)
    return parsed is not None and parsed >= _version_tuple(min_version)


def parse_environment_variables(environment_variable):
    """Parse 'NAME=VALUE' strings into the job payload format.

    Parameters
    ----------
    environment_variable : tuple, list or str
        Environment variables in the form ('NXF_SYNTAX_PARSER=v2', ...). A single
        string is accepted as one variable.

    Returns
    -------
    list
        A list of {'name': NAME, 'value': VALUE} dicts, in the given order.

    Raises
    ------
    ValueError
        If a variable is not in the form NAME=VALUE, a name is repeated or there
        are more than MAX_NEXTFLOW_ENVIRONMENT_VARIABLES variables.
    """
    if not environment_variable:
        return []
    if isinstance(environment_variable, str):
        environment_variable = (environment_variable,)
    parsed = []
    names = set()
    for env_var in environment_variable:
        name, sep, value = str(env_var).partition('=')
        name = name.strip()
        value = value.strip()
        if not sep or not name or not value:
            raise ValueError(f"Invalid environment variable '{env_var}'. Use the form NAME=VALUE, "
                             "e.g. NXF_SYNTAX_PARSER=v2.")
        if name in names:
            raise ValueError(f"Environment variable '{name}' was provided more than once.")
        names.add(name)
        parsed.append({'name': name, 'value': value})
    if len(parsed) > MAX_NEXTFLOW_ENVIRONMENT_VARIABLES:
        raise ValueError(f'Too many environment variables ({len(parsed)}). The maximum is '
                         f'{MAX_NEXTFLOW_ENVIRONMENT_VARIABLES}.')
    return parsed


def merge_environment_variables(original, overrides):
    """Merge environment variable overrides into the ones of an existing job.

    A variable in `overrides` replaces the one with the same name in `original`;
    new names are added at the end. Both arguments are lists of {'name', 'value'} dicts.
    """
    merged = [{'name': env_var['name'], 'value': env_var['value']} for env_var in (original or [])]
    for override in overrides or []:
        for env_var in merged:
            if env_var['name'] == override['name']:
                env_var['value'] = override['value']
                break
        else:
            merged.append({'name': override['name'], 'value': override['value']})
    return merged


def validate_environment_variables(environment_variables, nextflow_version,
                                   workflow_type='nextflow', execution_platform='aws',
                                   version_note=None):
    """Check environment variables against the supported allowlist before submitting a job.

    Mirrors the api-server validation: only Nextflow jobs, only allowlisted names,
    only allowed values and only on Nextflow versions that support the variable.

    Parameters
    ----------
    environment_variables : list
        A list of {'name': NAME, 'value': VALUE} dicts, as returned by parse_environment_variables.
    nextflow_version : str
        The Nextflow version of the job. 'latest' is resolved for the execution platform.
    workflow_type : str
        The workflow type: 'nextflow', 'wdl' or 'docker'.
    execution_platform : str
        The execution platform: 'aws', 'azure' or 'hpc'.
    version_note : str, optional
        Extra sentence added to the error when the Nextflow version is too old,
        e.g. to explain that the version is a default.

    Raises
    ------
    ValueError
        With a message explaining what is wrong and how to fix it.
    """
    if not environment_variables:
        return
    if workflow_type != 'nextflow':
        raise ValueError('Environment variables are only supported for Nextflow workflows. '
                         f'This workflow is of type \'{workflow_type}\'.')
    platform_versions, platform_latest = PLATFORM_NEXTFLOW_VERSIONS.get(
        execution_platform, PLATFORM_NEXTFLOW_VERSIONS['aws'])
    if nextflow_version == 'latest':
        nextflow_version = platform_latest
    supported_names = ', '.join(NEXTFLOW_ENVIRONMENT_VARIABLES)
    for env_var in environment_variables:
        name = env_var['name']
        value = env_var['value']
        definition = NEXTFLOW_ENVIRONMENT_VARIABLES.get(name)
        if definition is None:
            raise ValueError(f"Environment variable '{name}' is not supported. "
                             f"Supported environment variables: {supported_names}.")
        allowed_values = definition['allowed_values']
        if value not in allowed_values:
            raise ValueError(f"Invalid value '{value}' for environment variable '{name}'. "
                             f"Allowed values: {', '.join(allowed_values)}.")
        min_version = definition['min_nextflow_version']
        if not _is_version_at_least(nextflow_version, min_version):
            compatible = [v for v in platform_versions if _is_version_at_least(v, min_version)]
            if compatible:
                hint = f"Use one of these Nextflow versions: {', '.join(compatible)}."
            else:
                hint = (f"The {execution_platform} execution platform only supports Nextflow "
                        f"{', '.join(platform_versions)}, so '{name}' can't be used there.")
            note = f'{version_note} ' if version_note else ''
            raise ValueError(f"Environment variable '{name}' requires Nextflow {min_version} or later, "
                             f"but the job uses Nextflow {nextflow_version}. {note}{hint}")

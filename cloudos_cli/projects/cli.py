"""CLI commands for CloudOS project management."""

import rich_click as click
import json
import sys
from cloudos_cli.clos import Cloudos
from cloudos_cli.utils.resources import ssl_selector
from cloudos_cli.configure.configure import with_profile_config, CLOUDOS_URL
from cloudos_cli.utils.cli_helpers import pass_debug_to_subcommands


@click.group(cls=pass_debug_to_subcommands())
def project():
    """CloudOS project functionality."""
    print(project.__doc__ + '\n')


@project.command('list')
@click.option('-k',
              '--apikey',
              help='Your CloudOS API key',
              required=True)
@click.option('-c',
              '--cloudos-url',
              help=(f'The CloudOS url you are trying to access to. Default={CLOUDOS_URL}.'),
              default=CLOUDOS_URL,
              required=True)
@click.option('--workspace-id',
              help='The specific CloudOS workspace id.',
              required=True)
@click.option('--output-basename',
              help=('Output file base name to save project list. ' +
                    'Default=project_list'),
              default='project_list',
              required=False)
@click.option('--output-format',
              help='The desired file format (file extension) for the output. Default=csv.',
              type=click.Choice(['csv', 'json'], case_sensitive=False),
              default='csv')
@click.option('--all-fields',
              help=('Whether to collect all available fields from projects or ' +
                    'just the preconfigured selected fields. Only applicable ' +
                    'when --output-format=csv'),
              is_flag=True)
@click.option('--page',
              help=('Response page to retrieve. Default=1.'),
              type=int,
              default=1)
@click.option('--verbose',
              help='Whether to print information messages or not.',
              is_flag=True)
@click.option('--disable-ssl-verification',
              help=('Disable SSL certificate verification. Please, remember that this option is ' +
                    'not generally recommended for security reasons.'),
              is_flag=True)
@click.option('--ssl-cert',
              help='Path to your SSL certificate file.')
@click.option('--profile', help='Profile to use from the config file', default=None)
@click.pass_context
@with_profile_config(required_params=['apikey', 'workspace_id'])
def list_projects(ctx,
                  apikey,
                  cloudos_url,
                  workspace_id,
                  output_basename,
                  output_format,
                  all_fields,
                  page,
                  verbose,
                  disable_ssl_verification,
                  ssl_cert,
                  profile):
    """Collect all projects from a CloudOS workspace in CSV format."""
    # apikey, cloudos_url, and workspace_id are now automatically resolved by the decorator

    verify_ssl = ssl_selector(disable_ssl_verification, ssl_cert)
    outfile = output_basename + '.' + output_format
    print('Executing list...')
    if verbose:
        print('\t...Preparing objects')
    cl = Cloudos(cloudos_url, apikey, None)
    if verbose:
        print('\tThe following Cloudos object was created:')
        print('\t' + str(cl) + '\n')
        print('\tSearching for projects in the following workspace: ' +
              f'{workspace_id}')
    # Check if the user provided the --page option
    ctx = click.get_current_context()
    if ctx.get_parameter_source('page') == click.core.ParameterSource.DEFAULT:
        get_all = True
    else:
        get_all = False
        if not isinstance(page, int) or page < 1:
            raise ValueError('Please, use a positive integer (>= 1) for the --page parameter')
    my_projects_r = cl.get_project_list(workspace_id, verify_ssl, page=page, get_all=get_all)
    if len(my_projects_r) == 0:
        if ctx.get_parameter_source('page') == click.core.ParameterSource.DEFAULT:
            print('A total of 0 projects collected. This is likely because your workspace ' +
                  'has no projects created yet.')
        else:
            print('A total of 0 projects collected. This is likely because the --page you ' +
                  'requested does not exist. Please, try a smaller number for --page or collect all the ' +
                  'projects by not using --page parameter.')
    elif output_format == 'csv':
        my_projects = cl.process_project_list(my_projects_r, all_fields)
        my_projects.to_csv(outfile, index=False)
        print(f'\tProject list collected with a total of {my_projects.shape[0]} projects.')
    elif output_format == 'json':
        with open(outfile, 'w') as o:
            o.write(json.dumps(my_projects_r))
        print(f'\tProject list collected with a total of {len(my_projects_r)} projects.')
    else:
        raise ValueError('Unrecognised output format. Please use one of [csv|json]')
    print(f'\tProject list saved to {outfile}')


@project.command('create')
@click.option('-k',
              '--apikey',
              help='Your CloudOS API key',
              required=True)
@click.option('-c',
              '--cloudos-url',
              help=(f'The CloudOS url you are trying to access to. Default={CLOUDOS_URL}.'),
              default=CLOUDOS_URL,
              required=True)
@click.option('--workspace-id',
              help='The specific CloudOS workspace id.',
              required=True)
@click.option('--new-project',
              help='The name for the new project.',
              required=True)
@click.option('--verbose',
              help='Whether to print information messages or not.',
              is_flag=True)
@click.option('--disable-ssl-verification',
              help=('Disable SSL certificate verification. Please, remember that this option is ' +
                    'not generally recommended for security reasons.'),
              is_flag=True)
@click.option('--ssl-cert',
              help='Path to your SSL certificate file.')
@click.option('--profile', help='Profile to use from the config file', default=None)
@click.pass_context
@with_profile_config(required_params=['apikey', 'workspace_id'])
def create_project(ctx,
                   apikey,
                   cloudos_url,
                   workspace_id,
                   new_project,
                   verbose,
                   disable_ssl_verification,
                   ssl_cert,
                   profile):
    """Create a new project in CloudOS."""
    # apikey, cloudos_url, and workspace_id are now automatically resolved by the decorator

    # verify ssl configuration
    verify_ssl = ssl_selector(disable_ssl_verification, ssl_cert)

    # Print basic output
    if verbose:
        print(f'\tUsing CloudOS URL: {cloudos_url}')
        print(f'\tUsing workspace: {workspace_id}')
        print(f'\tProject name: {new_project}')

    cl = Cloudos(cloudos_url=cloudos_url, apikey=apikey, cromwell_token=None)

    try:
        project_id = cl.create_project(workspace_id, new_project, verify_ssl)
        print(f'\tProject "{new_project}" created successfully with ID: {project_id}')
        if verbose:
            print(f'\tProject URL: {cloudos_url}/app/projects/{project_id}')
    except Exception as e:
        print(f'\tError creating project: {str(e)}')
        sys.exit(1)

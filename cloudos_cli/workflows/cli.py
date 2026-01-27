"""CLI commands for CloudOS workflow management."""

import rich_click as click
import json
from cloudos_cli.clos import Cloudos
from cloudos_cli.import_wf.import_wf import ImportWorflow
from cloudos_cli.utils.resources import ssl_selector
from cloudos_cli.configure.configure import with_profile_config, CLOUDOS_URL


# Create the workflow group
@click.group()
def workflow():
    """CloudOS workflow functionality: list and import workflows."""
    print(workflow.__doc__ + '\n')


@workflow.command('list')
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
              help=('Output file base name to save workflow list. ' +
                    'Default=workflow_list'),
              default='workflow_list',
              required=False)
@click.option('--output-format',
              help='The desired file format (file extension) for the output. Default=csv.',
              type=click.Choice(['csv', 'json'], case_sensitive=False),
              default='csv')
@click.option('--all-fields',
              help=('Whether to collect all available fields from workflows or ' +
                    'just the preconfigured selected fields. Only applicable ' +
                    'when --output-format=csv'),
              is_flag=True)
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
def list_workflows(ctx,
                   apikey,
                   cloudos_url,
                   workspace_id,
                   output_basename,
                   output_format,
                   all_fields,
                   verbose,
                   disable_ssl_verification,
                   ssl_cert,
                   profile):
    """Collect all workflows from a CloudOS workspace in CSV format."""
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
        print('\tSearching for workflows in the following workspace: ' +
              f'{workspace_id}')
    my_workflows_r = cl.get_workflow_list(workspace_id, verify=verify_ssl)
    if output_format == 'csv':
        my_workflows = cl.process_workflow_list(my_workflows_r, all_fields)
        my_workflows.to_csv(outfile, index=False)
        print(f'\tWorkflow list collected with a total of {my_workflows.shape[0]} workflows.')
    elif output_format == 'json':
        with open(outfile, 'w') as o:
            o.write(json.dumps(my_workflows_r))
        print(f'\tWorkflow list collected with a total of {len(my_workflows_r)} workflows.')
    else:
        raise ValueError('Unrecognised output format. Please use one of [csv|json]')
    print(f'\tWorkflow list saved to {outfile}')


@workflow.command('import')
@click.option('-k',
              '--apikey',
              help='Your CloudOS API key',
              required=True)
@click.option('-c',
              '--cloudos-url',
              help=('The CloudOS url you are trying to access to. ' +
                    f'Default={CLOUDOS_URL}.'),
              default=CLOUDOS_URL,
              required=True)
@click.option('--workspace-id',
              help='The specific CloudOS workspace id.',
              required=True)
@click.option('--repository-platform', type=click.Choice(["github", "gitlab", "bitbucketServer"]),
              help='Name of the repository platform of the workflow. Default=github.',
              default='github')
@click.option("--workflow-name", help="The name that the workflow will have in CloudOS.", required=True)
@click.option("-w", "--workflow-url", help="URL of the workflow repository.", required=True)
@click.option("-d", "--workflow-docs-link", help="URL to the documentation of the workflow.", default='')
@click.option("--cost-limit", help="Cost limit for the workflow. Default: $30 USD.", default=30)
@click.option("--workflow-description", help="Workflow description", default="")
@click.option('--disable-ssl-verification',
              help=('Disable SSL certificate verification. Please, remember that this option is ' +
                    'not generally recommended for security reasons.'),
              is_flag=True)
@click.option('--ssl-cert',
              help='Path to your SSL certificate file.')
@click.option('--profile', help='Profile to use from the config file', default=None)
@click.pass_context
@with_profile_config(required_params=['apikey', 'workspace_id', 'workflow_name'])
def import_wf(ctx,
              apikey,
              cloudos_url,
              workspace_id,
              workflow_name,
              workflow_url,
              workflow_docs_link,
              cost_limit,
              workflow_description,
              repository_platform,
              disable_ssl_verification,
              ssl_cert,
              profile):
    """
    Import workflows from supported repository providers.
    """
    # apikey, cloudos_url, and workspace_id are now automatically resolved by the decorator

    verify_ssl = ssl_selector(disable_ssl_verification, ssl_cert)
    repo_import = ImportWorflow(
        cloudos_url=cloudos_url, cloudos_apikey=apikey, workspace_id=workspace_id, platform=repository_platform,
        workflow_name=workflow_name, workflow_url=workflow_url, workflow_docs_link=workflow_docs_link,
        cost_limit=cost_limit, workflow_description=workflow_description, verify=verify_ssl
    )
    workflow_id = repo_import.import_workflow()
    print(f'\tWorkflow {workflow_name} was imported successfully with the ' +
          f'following ID: {workflow_id}')

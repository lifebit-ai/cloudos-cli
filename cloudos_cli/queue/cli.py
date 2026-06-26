"""CLI commands for Lifebit Platform job queue management."""

import sys
import rich_click as click
import json
from rich.console import Console
from cloudos_cli.queue.queue import (
    Queue,
    QUEUE_PRESETS,
    MAX_WORKSPACE_COMPUTE_ENVS,
    WORKSPACE_CE_LIMIT_REACHED_MESSAGE,
)
from cloudos_cli.utils.resources import ssl_selector
from cloudos_cli.configure.configure import with_profile_config, CLOUDOS_URL
from cloudos_cli.utils.cli_helpers import pass_debug_to_subcommands
from cloudos_cli.utils.details import create_queue_list_table


# Workflow executors supported for job queues.
_EXECUTORS = ["nextflow", "cromwell"]


def _check_workspace_ce_limit(console, j_queue, queues=None):
    """Exit with a warning if the workspace has reached its CE limit.

    Parameters
    ----------
    console : rich.console.Console
        The console used for rich output.
    j_queue : Queue
        The queue client used to count compute environments.
    queues : list or None, optional
        A pre-fetched list of job queue dicts. If ``None``, the queues are
        fetched.
    """
    count = j_queue.count_workspace_compute_environments(queues=queues)
    if count >= MAX_WORKSPACE_COMPUTE_ENVS:
        console.print(
            f"[yellow]Warning:[/yellow] {WORKSPACE_CE_LIMIT_REACHED_MESSAGE}"
        )
        sys.exit(0)




# Create the queue group
@click.group(cls=pass_debug_to_subcommands())
def queue():
    """Lifebit Platform job queue functionality."""
    print(queue.__doc__ + '\n')


@queue.command('list')
@click.option('-k',
              '--apikey',
              help='Your Lifebit Platform API key',
              required=True)
@click.option('-c',
              '--cloudos-url',
              help=(f'The Lifebit Platform url you are trying to access to. Default={CLOUDOS_URL}.'),
              default=CLOUDOS_URL,
              required=True)
@click.option('--workspace-id',
              help='The specific Lifebit Platform workspace id.',
              required=True)
@click.option('--output-basename',
              help=('Output file base name to save job queue list. ' +
                    'Default=job_queue_list'),
              default='job_queue_list',
              required=False)
@click.option('--output-format',
              help=('Output format for queue list. Options: '
                    'stdout (display as interactive table in terminal), '
                    'csv (save as comma-separated values file), '
                    'json (save as JSON file with full API response). '
                    'Default=stdout.'),
              type=click.Choice(['stdout', 'csv', 'json'], case_sensitive=False),
              default='stdout')
@click.option('--all-fields',
              help=('Whether to collect all available fields from queues or ' +
                    'just the preconfigured selected fields. Only applicable ' +
                    'when --output-format=csv'),
              is_flag=True)
@click.option('--exclude-system-queues',
              help='Exclude system job queues from the list.',
              is_flag=True)
@click.option('--execution-platform',
              help='Name of the execution platform implemented in your Lifebit Platform. Default=aws.',
              type=click.Choice(['aws', 'azure', 'hpc']),
              default='aws')
@click.option('--disable-ssl-verification',
              help=('Disable SSL certificate verification. Please, remember that this option is ' +
                    'not generally recommended for security reasons.'),
              is_flag=True)
@click.option('--ssl-cert',
              help='Path to your SSL certificate file.')
@click.option('--profile', help='Profile to use from the config file', default=None)
@click.pass_context
@with_profile_config(required_params=['apikey', 'workspace_id'])
def list_queues(ctx,
                apikey,
                cloudos_url,
                workspace_id,
                output_basename,
                output_format,
                all_fields,
                exclude_system_queues,
                execution_platform,
                disable_ssl_verification,
                ssl_cert,
                profile):
    """Collect and display all available job queues from a Lifebit Platform workspace."""
    # apikey, cloudos_url, and workspace_id are now automatically resolved by the decorator

    verify_ssl = ssl_selector(disable_ssl_verification, ssl_cert)

    # Batch job queues are an AWS-only feature; they are not available in
    # Azure or HPC workspaces.
    if execution_platform in ('azure', 'hpc'):
        Console().print(
            '[yellow]Warning:[/yellow] Batch job queues are not available in '
            f'{execution_platform.upper()} workspaces.'
        )
        sys.exit(0)

    print('Executing list...')
    j_queue = Queue(cloudos_url, apikey, None, workspace_id, verify=verify_ssl)
    my_queues = j_queue.get_job_queues(exclude_system_queues=exclude_system_queues)
    if len(my_queues) == 0:
        raise ValueError('No AWS batch queues found. Please, make sure that your Lifebit Platform supports AWS batch queues')
    if output_format == 'stdout':
        create_queue_list_table(my_queues, cloudos_url)
    elif output_format == 'csv':
        outfile = output_basename + '.' + output_format
        queues_processed = j_queue.process_queue_list(my_queues, all_fields)
        queues_processed.to_csv(outfile, index=False)
        print(f'\tJob queue list collected with a total of {queues_processed.shape[0]} queues.')
        print(f'\tJob queue list saved to {outfile}')
    elif output_format == 'json':
        outfile = output_basename + '.' + output_format
        with open(outfile, 'w') as o:
            o.write(json.dumps(my_queues))
        print(f'\tJob queue list collected with a total of {len(my_queues)} queues.')
        print(f'\tJob queue list saved to {outfile}')


@queue.command('create')
@click.option('-k',
              '--apikey',
              help='Your Lifebit Platform API key',
              required=True)
@click.option('-c',
              '--cloudos-url',
              help=(f'The Lifebit Platform url you are trying to access to. Default={CLOUDOS_URL}.'),
              default=CLOUDOS_URL,
              required=True)
@click.option('--workspace-id',
              help='The specific Lifebit Platform workspace id.',
              required=True)
@click.option('--label',
              help='Name (label) for the new job queue.',
              required=False,
              default=None)
@click.option('--description',
              help='Short description of the new job queue.',
              default='',
              required=False)
@click.option('--preset',
              help=(
                  'Preset template to use. Choices: '
                  + ', '.join(QUEUE_PRESETS.keys())
                  + '. Default=standard-stable.'
              ),
              type=click.Choice(list(QUEUE_PRESETS.keys()), case_sensitive=False),
              default='standard-stable',
              show_default=True,
              required=False)
@click.option('--executor',
              help='Workflow executor for the queue. Default=nextflow.',
              type=click.Choice(_EXECUTORS, case_sensitive=False),
              default='nextflow',
              show_default=True,
              required=False)
@click.option('-y',
              '--yes',
              'skip_confirmation',
              help='Skip the confirmation prompt and proceed immediately.',
              is_flag=True)
@click.option('--set-default',
              help='Set the new job queue as the workspace default. Default=False.',
              is_flag=True)
@click.option('--execution-platform',
              help='Name of the execution platform implemented in your Lifebit Platform. Default=aws.',
              type=click.Choice(['aws', 'azure', 'hpc']),
              default='aws')
@click.option('--disable-ssl-verification',
              help=('Disable SSL certificate verification. Please, remember that this option is '
                    'not generally recommended for security reasons.'),
              is_flag=True)
@click.option('--ssl-cert',
              help='Path to your SSL certificate file.')
@click.option('--profile', help='Profile to use from the config file', default=None)
@click.pass_context
@with_profile_config(required_params=['apikey', 'workspace_id'])
def create_queue(ctx,
                 apikey,
                 cloudos_url,
                 workspace_id,
                 label,
                 description,
                 preset,
                 executor,
                 skip_confirmation,
                 set_default,
                 execution_platform,
                 disable_ssl_verification,
                 ssl_cert,
                 profile):
    """Create a new job queue in a Lifebit Platform workspace.

    A preset template is used to create the queue.
    """

    verify_ssl = ssl_selector(disable_ssl_verification, ssl_cert)

    # Batch job queues are an AWS-only feature; they are not available in
    # Azure or HPC workspaces.
    if execution_platform in ('azure', 'hpc'):
        Console().print(
            '[yellow]Warning:[/yellow] Batch job queues are not available in '
            f'{execution_platform.upper()} workspaces.'
        )
        sys.exit(0)

    # --description is required when creating a queue.
    if not description:
        raise click.UsageError('Missing option --description.')

    if label is None:
        raise click.UsageError('Missing option --label.')

    # Resolve the preset to show the user what will be created
    preset_info = QUEUE_PRESETS[preset]
    ce_name = preset_info['computeEnvironmentName']
    cr = preset_info['computeResources']
    resource_type = cr.get('type', 'EC2')
    max_vcpus_preset = cr.get('maxvCpus', 'N/A')
    instance_count = len(cr.get('instanceTypes', []))
    template_name = preset_info['templateName']

    j_queue = Queue(cloudos_url, apikey, None, workspace_id, verify=verify_ssl)

    # Creating a queue creates a compute environment; enforce the workspace limit.
    _check_workspace_ce_limit(Console(), j_queue)

    if not skip_confirmation:
        click.echo('\nYou are about to create the following job queue:')
        click.echo(f'  Label              : {label}')
        click.echo(f'  Description        : {description or "(none)"}')
        click.echo(f'  Preset             : {template_name}')
        click.echo(f'  Compute env name   : {ce_name}')
        click.echo(f'  Resource type      : {resource_type}')
        click.echo(f'  Max vCPUs          : {max_vcpus_preset}')
        click.echo(f'  Instance types     : {instance_count} types')
        click.echo(f'  Executor           : {executor}')
        click.echo(f'  Set as default     : {set_default}')
        click.echo(f'  Workspace          : {workspace_id}')
        click.echo('')
        if not click.confirm('Proceed with queue creation?'):
            click.echo('Aborted.')
            sys.exit(0)

    console = Console()
    print('Executing queue create...')

    try:
        queue_id = j_queue.create_job_queue(
            label=label,
            description=description,
            preset_name=preset,
            executor=executor,
            is_default=set_default,
        )
        console.print(f'\t[green]Queue "{label}" created successfully.[/green]')
        print(f'\tQueue ID : {queue_id}')
        print(f'\tView at  : {cloudos_url}/app/job-queues/{queue_id}')
    except Exception as e:
        console.print(f'\t[red]Error creating queue:[/red] {str(e)}')
        sys.exit(1)


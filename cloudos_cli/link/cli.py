import rich_click as click
from cloudos_cli.link.link import Link
from cloudos_cli.utils.resources import ssl_selector
from cloudos_cli.configure.configure import with_profile_config, CLOUDOS_URL
from cloudos_cli.utils.errors import BadRequestException
from cloudos_cli.utils.cli_helpers import pass_debug_to_subcommands


@click.command()
@click.argument('path', required=False)
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
@click.option('--session-id',
              help='The specific CloudOS interactive session id.',
              required=True)
@click.option('--job-id',
              help='The job id in CloudOS. When provided, links results, workdir and logs by default.',
              required=False)
@click.option('--project-name',
              help='The name of a CloudOS project. Required for File Explorer paths.',
              required=False)
@click.option('--results',
              help='Link only results folder (only works with --job-id).',
              is_flag=True)
@click.option('--workdir',
              help='Link only working directory (only works with --job-id).',
              is_flag=True)
@click.option('--logs',
              help='Link only logs folder (only works with --job-id).',
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
@with_profile_config(required_params=['apikey', 'workspace_id', 'session_id'])
def link(ctx,
                 path,
                 apikey,
                 cloudos_url,
                 workspace_id,
                 session_id,
                 job_id,
                 project_name,
                 results,
                 workdir,
                 logs,
                 verbose,
                 disable_ssl_verification,
                 ssl_cert,
                 profile):
    """
    Link folders to an interactive analysis session.

    This command is used to link folders
    to an active interactive analysis session for direct access to data.

    PATH: Optional path to link (S3). 
          Required if --job-id is not provided.

    Two modes of operation:

    1. Job-based linking (--job-id): Links job-related folders.
       By default, links results, workdir, and logs folders.
       Use --results, --workdir, or --logs flags to link only specific folders.

    2. Direct path linking (PATH argument): Links a specific S3 path.

    Examples:

        # Link all job folders (results, workdir, logs)
        cloudos link --job-id 12345 --session-id abc123
        
        # Link only results from a job
        cloudos link --job-id 12345 --session-id abc123 --results
        
        # Link a specific S3 path
        cloudos link s3://bucket/folder --session-id abc123
        
    """
    print('CloudOS link functionality: link s3 folders to interactive analysis sessions.\n')

    verify_ssl = ssl_selector(disable_ssl_verification, ssl_cert)

    # Validate input parameters
    if not job_id and not path:
        raise click.UsageError("Either --job-id or PATH argument must be provided.")

    if job_id and path:
        raise click.UsageError("Cannot use both --job-id and PATH argument. Please provide only one.")

    # Validate folder-specific flags only work with --job-id
    if (results or workdir or logs) and not job_id:
        raise click.UsageError("--results, --workdir, and --logs flags can only be used with --job-id.")

    # If no specific folders are selected with job-id, link all by default
    if job_id and not (results or workdir or logs):
        results = True
        workdir = True
        logs = True

    if verbose:
        print('Using the following parameters:')
        print(f'\tCloudOS url: {cloudos_url}')
        print(f'\tWorkspace ID: {workspace_id}')
        print(f'\tSession ID: {session_id}')
        if job_id:
            print(f'\tJob ID: {job_id}')
            print(f'\tLink results: {results}')
            print(f'\tLink workdir: {workdir}')
            print(f'\tLink logs: {logs}')
        else:
            print(f'\tPath: {path}')

    # Initialize Link client
    link_client = Link(
        cloudos_url=cloudos_url,
        apikey=apikey,
        cromwell_token=None,
        workspace_id=workspace_id,
        project_name=project_name,
        verify=verify_ssl
    )

    try:
        if job_id:
            # Job-based linking
            print(f'Linking folders from job {job_id} to interactive session {session_id}...\n')
            
            # Link results
            if results:
                link_client.link_job_results(job_id, workspace_id, session_id, verify_ssl, verbose)
            
            # Link workdir
            if workdir:
                link_client.link_job_workdir(job_id, workspace_id, session_id, verify_ssl, verbose)
            
            # Link logs
            if logs:
                link_client.link_job_logs(job_id, workspace_id, session_id, verify_ssl, verbose)
            
            
        else:
            # Direct path linking
            print(f'Linking path to interactive session {session_id}...\n')
            
            # Link path with validation
            link_client.link_path_with_validation(path, session_id, verify_ssl, project_name, verbose)
            
            print('\nLinking operation completed.')
            
    except BadRequestException as e:
        raise ValueError(f"Request failed: {str(e)}")
    except Exception as e:
        raise ValueError(f"Failed to link folder(s): {str(e)}")

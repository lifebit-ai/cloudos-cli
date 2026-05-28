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
@click.option('--session-id',
              help='The specific Lifebit Platform interactive session id.',
              required=True)
@click.option('--job-id',
              help='The job id in Lifebit Platform. When provided, links results, workdir and logs by default.',
              required=False)
@click.option('--project-name',
              help='The name of a Lifebit Platform project. Required for File Explorer paths.',
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
    Link files or folders to an interactive analysis session.

    This command links S3 or File Explorer items (files and folders) to an active
    interactive analysis session for direct read access.

    PATH: Optional path(s) to link (S3 or File Explorer).
          Required if --job-id is not provided.
          Supports comma-separated list for multiple paths.
          File Explorer paths must include project name (project-name/folder/path).

    Two modes of operation:

    1. Job-based linking (--job-id): Links job-related folders.
       By default, links results, workdir, and logs folders.
       Use --results, --workdir, or --logs flags to link only specific folders.

    2. Direct path linking (PATH argument): Links specific path(s).
       Supports S3 files/folders and Lifebit Platform File Explorer files/folders.
       Both S3 and File Explorer paths can be combined.
       S3 paths ending with '/' or without a file extension are treated as folders.
       S3 paths whose last segment contains a '.' are treated as files.

    Examples:

        # Link all job folders (results, workdir, logs)
        cloudos link --job-id 12345 --session-id abc123

        # Link a single S3 folder
        cloudos link s3://bucket/folder/ --session-id abc123

        # Link a single S3 file
        cloudos link s3://bucket/data/file.csv --session-id abc123

        # Link multiple S3 paths (comma-separated, files and folders mixed)
        cloudos link s3://bucket1/folder1/,s3://bucket2/data/file.csv --session-id abc123

        # Link a File Explorer folder
        cloudos link my-project/Data/folder --session-id abc123 --project-name my-project

        # Link a File Explorer file
        cloudos link my-project/Data/file.csv --session-id abc123 --project-name my-project

        # Combine S3 and File Explorer paths
        cloudos link s3://bucket/data/file.csv,my-project/Data/results --session-id abc123 --project-name my-project

    """
    print('Lifebit Platform link functionality: link s3 folders to interactive analysis sessions.\n')

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
        print(f'\tLifebit Platform url: {cloudos_url}')
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
            # Direct path linking (supports comma-separated multiple paths)
            # Split paths by comma and strip whitespace
            paths = [p.strip() for p in path.split(',') if p.strip()]
            
            if len(paths) == 0:
                raise click.UsageError("No valid paths provided.")
            
            if len(paths) == 1:
                print(f'Linking path to interactive session {session_id}...\n')
            else:
                print(f'Linking {len(paths)} paths to interactive session {session_id}...\n')

            # Link all paths in one batch (v2 API will send them together)
            try:
                all_succeeded = link_client.link_folders_batch(paths, session_id)
                if all_succeeded:
                    print('\nLinking operation completed successfully!')
                else:
                    click.secho('\nLinking operation completed with errors. See details above.', fg='red', err=True)
                    raise SystemExit(1)
            except SystemExit:
                raise
            except Exception as e:
                click.secho(f'\n✗ Failed: {str(e)}', fg='red', err=True)
                raise SystemExit(1)

    except BadRequestException as e:
        raise ValueError(f"Request failed: {str(e)}")
    except Exception as e:
        raise ValueError(f"Failed to link folder(s): {str(e)}")

"""CLI commands for CloudOS interactive session management."""

import rich_click as click
import json
from cloudos_cli.clos import Cloudos
from cloudos_cli.datasets import Datasets
from cloudos_cli.utils.errors import BadRequestException
from cloudos_cli.utils.resources import ssl_selector
from cloudos_cli.interactive_session.interactive_session import (
    create_interactive_session_list_table,
    process_interactive_session_list,
    save_interactive_session_list_to_csv,
    parse_shutdown_duration,
    parse_data_file,
    parse_link_path,
    parse_s3_mount,
    build_session_payload,
    format_session_creation_table,
    resolve_data_file_id
)
from cloudos_cli.configure.configure import with_profile_config, CLOUDOS_URL
from cloudos_cli.utils.cli_helpers import pass_debug_to_subcommands
from cloudos_cli.utils.requests import retry_requests_get


# Create the interactive_session group
@click.group(cls=pass_debug_to_subcommands())
def interactive_session():
    """CloudOS interactive session functionality: list and manage interactive sessions."""
    print(interactive_session.__doc__ + '\n')


@interactive_session.command('list')
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
@click.option('--filter-status',
              multiple=True,
              type=click.Choice(['setup', 'initialising', 'running', 'scheduled', 'stopped'], case_sensitive=False),
              help='Filter sessions by status. Can be specified multiple times to filter by multiple statuses.')
@click.option('--limit',
              type=int,
              default=10,
              help='Number of results per page. Default=10, max=100.')
@click.option('--page',
              type=int,
              default=1,
              help='Page number to retrieve. Default=1.')
@click.option('--filter-owner-only',
              is_flag=True,
              help='Show only the current user\'s sessions.')
@click.option('--archived',
              is_flag=True,
              help='When this flag is used, only archived sessions list is collected.')
@click.option('--output-format',
              help='Output format for session list.',
              type=click.Choice(['stdout', 'csv', 'json'], case_sensitive=False),
              default='stdout')
@click.option('--output-basename',
              help=('Output file base name to save sessions list. ' +
                    'Default=interactive_sessions_list'),
              default='interactive_sessions_list',
              required=False)
@click.option('--table-columns',
              help=('Comma-separated list of columns to display in the table. Only applicable when --output-format=stdout. ' +
                    'Available columns: id,name,status,type,instance,cost,owner. ' +
                    'Default: responsive (auto-selects columns based on terminal width)'),
              default=None)
@click.option('--all-fields',
              help=('Whether to collect all available fields from sessions or ' +
                    'just the preconfigured selected fields. Only applicable ' +
                    'when --output-format=csv.'),
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
def list_sessions(ctx,
                  apikey,
                  cloudos_url,
                  workspace_id,
                  filter_status,
                  limit,
                  page,
                  filter_owner_only,
                  archived,
                  output_format,
                  output_basename,
                  table_columns,
                  all_fields,
                  verbose,
                  disable_ssl_verification,
                  ssl_cert,
                  profile):
    """List interactive sessions for a CloudOS team."""
    # apikey, cloudos_url, and team_id are now automatically resolved by the decorator
    
    verify_ssl = ssl_selector(disable_ssl_verification, ssl_cert)
    
    # Validate limit parameter
    if not isinstance(limit, int) or limit < 1:
        raise ValueError('Please use a positive integer (>= 1) for the --limit parameter')
    
    if limit > 100:
        click.secho('Error: Limit cannot exceed 100. Please use --limit with a value <= 100', fg='red', err=True)
        raise SystemExit(1)
    
    # Validate page parameter
    if not isinstance(page, int) or page < 1:
        raise ValueError('Please use a positive integer (>= 1) for the --page parameter')
    
    # Prepare output file if needed
    selected_columns = table_columns
    if output_format != 'stdout':
        outfile = output_basename + '.' + output_format
    
    if verbose:
        print('Executing list...')
        print('\t...Preparing objects')
    
    cl = Cloudos(cloudos_url, apikey, None)
    
    if verbose:
        print('\tThe following Cloudos object was created:')
        print('\t' + str(cl) + '\n')
        print('\tSearching for interactive sessions in the following workspace: ' + f'{workspace_id}')
    
    try:
        # Call the API method to get interactive sessions
        result = cl.get_interactive_session_list(
            workspace_id,
            page=page,
            limit=limit,
            status=list(filter_status) if filter_status else None,
            owner_only=filter_owner_only,
            include_archived=archived,
            verify=verify_ssl
        )
        
        sessions = result.get('sessions', [])
        pagination_metadata = result.get('pagination_metadata', None)
        
        # Define callback function for fetching additional pages
        def fetch_page(page_num):
            """Fetch a specific page of interactive sessions."""
            return cl.get_interactive_session_list(
                workspace_id,
                page=page_num,
                limit=limit,
                status=list(filter_status) if filter_status else None,
                owner_only=filter_owner_only,
                include_archived=archived,
                verify=verify_ssl
            )
        
        # Handle empty results
        if len(sessions) == 0:
            if filter_status:
                # Show helpful message when filtering returns no results
                status_flow = 'scheduled → initialising → setup → running → stopped'
                click.secho(f'No interactive sessions found in the requested status.', fg='yellow', err=True)
                click.secho(f'Session status flow: {status_flow}', fg='cyan', err=True)
            elif output_format == 'stdout':
                create_interactive_session_list_table([], pagination_metadata, selected_columns, page_size=limit, fetch_page_callback=fetch_page)
            else:
                print('A total of 0 interactive sessions collected.')
        
        # Display results based on output format
        elif output_format == 'stdout':
            create_interactive_session_list_table(sessions, pagination_metadata, selected_columns, page_size=limit, fetch_page_callback=fetch_page)
        
        elif output_format == 'csv':
            sessions_df = process_interactive_session_list(sessions, all_fields)
            save_interactive_session_list_to_csv(sessions_df, outfile)
        
        elif output_format == 'json':
            with open(outfile, 'w') as o:
                o.write(json.dumps(sessions, indent=2))
            print(f'\tInteractive session list collected with a total of {len(sessions)} sessions.')
            print(f'\tInteractive session list saved to {outfile}')
        
        else:
            raise ValueError('Unrecognised output format. Please use one of [stdout|csv|json]')
    
    except BadRequestException as e:
        error_str = str(e)
        # Check if the error is related to authentication
        if '401' in error_str or 'Unauthorized' in error_str:
            click.secho(f'Error: Failed to retrieve interactive sessions. Please check your credentials (API key and CloudOS URL).', fg='red', err=True)
            raise SystemExit(1)
        # Check if the error is related to status filtering
        elif filter_status and ('400' in error_str or 'Invalid' in error_str):
            status_flow = 'scheduled → initialising → setup → running → stopped'
            click.secho(f'No interactive sessions found in the requested status.', fg='yellow', err=True)
            click.secho(f'Session status flow: {status_flow}', fg='cyan', err=True)
            raise SystemExit(1)
        else:
            click.secho(f'Error: Failed to retrieve interactive sessions: {e}', fg='red', err=True)
            raise SystemExit(1)
    except Exception as e:
        error_str = str(e)
        # Check for DNS/connection errors
        if 'Failed to resolve' in error_str or 'Name or service not known' in error_str or 'nodename nor servname provided' in error_str:
            click.secho(f'Error: Unable to connect to CloudOS URL. Please verify the CloudOS URL is correct.', fg='red', err=True)
        # Check for 401 Unauthorized
        elif '401' in error_str or 'Unauthorized' in error_str:
            click.secho(f'Error: Failed to retrieve interactive sessions. Please check your credentials (API key and CloudOS URL).', fg='red', err=True)
        else:
            click.secho(f'Error: {str(e)}', fg='red', err=True)
        raise SystemExit(1)


@interactive_session.command('create')
@click.option('-k',
              '--apikey',
              help='Your CloudOS API key',
              required=False)
@click.option('-c',
              '--cloudos-url',
              help=(f'The CloudOS url you are trying to access to. Default={CLOUDOS_URL}.'),
              default=CLOUDOS_URL,
              required=False)
@click.option('--workspace-id',
              help='The specific CloudOS workspace id.',
              required=False)
@click.option('--project-name',
              help='The project name. Will be resolved to project ID automatically.',
              required=True)
@click.option('--name',
              help='Name for the interactive session (1-100 characters).',
              required=True)
@click.option('--session-type',
              type=click.Choice(['jupyter', 'vscode', 'spark', 'rstudio'], case_sensitive=False),
              help='Type of interactive session.',
              required=True)
@click.option('--instance',
              help='Instance type (e.g., c5.xlarge for AWS, Standard_F1s for Azure). Default depends on execution platform.',
              default=None)
@click.option('--storage',
              type=int,
              help='Storage in GB (100-5000). Default=500.',
              default=500)
@click.option('--spot',
              is_flag=True,
              help='Use spot instances.')
@click.option('--shared',
              is_flag=True,
              help='Make session shared (accessible to workspace).')
@click.option('--cost-limit',
              type=float,
              help='Cost limit in USD. Default=-1 (unlimited).',
              default=-1)
@click.option('--shutdown-in',
              help='Auto-shutdown duration (e.g., 8h, 2d).')
@click.option('--mount',
              multiple=True,
              help='Mount a data file into the session. Supports both CloudOS datasets and S3 files. Format: project_name/dataset_path (e.g., leila-test/Data/file.csv) or s3://bucket/path/to/file (e.g., s3://my-bucket/data/file.csv). Can be used multiple times.')
@click.option('--link',
              multiple=True,
              help='Link a folder into the session for read/write access. Supports S3 folders and CloudOS folders. Format: s3://bucket/prefix (e.g., s3://my-bucket/data/) or project_name/folder_path (e.g., leila-test/Data). Legacy format: mountName:bucketName:s3Prefix. Can be used multiple times.')
@click.option('--r-version',
              type=click.Choice(['4.5.2', '4.4.2'], case_sensitive=False),
              help='R version for RStudio. Options: 4.5.2 (default), 4.4.2.',
              default='4.5.2')
@click.option('--spark-master',
              help='Master instance type for Spark. Default=c5.2xlarge.',
              default='c5.2xlarge')
@click.option('--spark-core',
              help='Core instance type for Spark. Default=c5.xlarge.',
              default='c5.xlarge')
@click.option('--spark-workers',
              type=int,
              help='Initial worker count for Spark. Default=1.',
              default=1)
@click.option('--execution-platform',
              type=click.Choice(['aws', 'azure'], case_sensitive=False),
              help='Cloud execution platform (aws or azure). Default is obtained from profile.',
              default=None)
@click.option('--disable-ssl-verification',
              help=('Disable SSL certificate verification. Please, remember that this option is ' +
                    'not generally recommended for security reasons.'),
              is_flag=True)
@click.option('--ssl-cert',
              help='Path to your SSL certificate file.')
@click.option('--profile', help='Profile to use from the config file', default=None)
@click.option('--verbose',
              help='Whether to print information messages or not.',
              is_flag=True)
@click.pass_context
@with_profile_config(required_params=['apikey', 'workspace_id', 'project_name'])
def create_session(ctx,
                   apikey,
                   cloudos_url,
                   workspace_id,
                   project_name,
                   name,
                   session_type,
                   instance,
                   storage,
                   spot,
                   shared,
                   cost_limit,
                   shutdown_in,
                   mount,
                   link,
                   r_version,
                   spark_master,
                   spark_core,
                   spark_workers,
                   execution_platform,
                   disable_ssl_verification,
                   ssl_cert,
                   profile,
                   verbose):
    """Create a new interactive session."""
    
    verify_ssl = ssl_selector(disable_ssl_verification, ssl_cert)
    
    # Default execution_platform to 'aws' if not specified by user or profile
    if execution_platform is None:
        execution_platform = 'aws'
    else:
        # Normalize to lowercase
        execution_platform = execution_platform.lower()
    
    # Set instance default based on execution_platform if not specified
    if instance is None:
        instance = 'c5.xlarge' if execution_platform == 'aws' else 'Standard_F1s'
    
    if verbose:
        print('Executing create interactive session...')
        print('\t...Preparing objects')
    
    cl = Cloudos(cloudos_url, apikey, None)
    
    if verbose:
        print('\tThe following Cloudos object was created:')
        print('\t' + str(cl) + '\n')
        print(f'\tCreating interactive session in workspace: {workspace_id}')
    
    try:
        # Resolve project name to project ID
        project_id = cl.get_project_id_from_name(workspace_id, project_name, verify=verify_ssl)
        if verbose:
            print(f'\tResolved project name "{project_name}" to ID: {project_id}')
        
        # Parse session type to lowercase
        session_type_lower = session_type.lower()
        
        # Map session type to backend name
        backend_type_mapping = {
            'jupyter': 'regular',
            'vscode': 'vscode',
            'spark': 'spark',
            'rstudio': 'rstudio'
        }
        backend_type = backend_type_mapping.get(session_type_lower)
        
        if not backend_type:
            click.secho(f'Error: Invalid session type: {session_type}', fg='red', err=True)
            raise SystemExit(1)
        
        # Parse shutdown duration
        shutdown_at_parsed = None
        if shutdown_in:
            try:
                shutdown_at_parsed = parse_shutdown_duration(shutdown_in)
            except ValueError as e:
                click.secho(f'Error: Invalid shutdown duration: {str(e)}', fg='red', err=True)
                raise SystemExit(1)
        
        # Parse and resolve mounted data files (both CloudOS and S3)
        parsed_data_files = []
        parsed_s3_mounts = []  # S3 folders go into FUSE mounts
        if mount:
            try:
                for df in mount:
                    parsed = parse_data_file(df)
                    
                    if parsed['type'] == 's3':
                        # S3 files are only supported on AWS
                        if execution_platform != 'aws':
                            click.secho(f'Error: S3 mounts are only supported on AWS. Use CloudOS file explorer paths for Azure.', fg='red', err=True)
                            raise SystemExit(1)
                        
                        # S3 file: add to dataItems as S3File type
                        if verbose:
                            print(f'\tMounting S3 file: s3://{parsed["s3_bucket"]}/{parsed["s3_prefix"]}')
                        
                        # Use the full path as the name
                        s3_file_item = {
                            "type": "S3File",
                            "data": {
                                "name": parsed["s3_prefix"],
                                "s3BucketName": parsed["s3_bucket"],
                                "s3ObjectKey": parsed["s3_prefix"]
                            }
                        }
                        parsed_data_files.append(s3_file_item)
                        
                        if verbose:
                            print(f'\t  ✓ Added S3 file to mount')
                    
                    else:  # type == 'cloudos'
                        # CloudOS dataset file: resolve via Datasets API
                        data_project = parsed['project_name']
                        dataset_path = parsed['dataset_path']
                        
                        if verbose:
                            print(f'\tResolving dataset: {data_project}/{dataset_path}')
                        
                        # Create a Datasets API instance for this specific project
                        datasets_api = Datasets(
                            cloudos_url=cloudos_url,
                            apikey=apikey,
                            workspace_id=workspace_id,
                            project_name=data_project,
                            verify=verify_ssl,
                            cromwell_token=None
                        )
                        
                        resolved = resolve_data_file_id(datasets_api, dataset_path)
                        parsed_data_files.append(resolved)
                        
                        if verbose:
                            print(f'\t  ✓ Resolved to file ID: {resolved["item"]}')
            except Exception as e:
                click.secho(f'Error: Failed to resolve dataset files: {str(e)}', fg='red', err=True)
                raise SystemExit(1)
        
        # Parse and add linked folders from --link (S3 or CloudOS)
        for link_path in link:
            try:
                # Block all linking on Azure platforms
                if execution_platform == 'azure':
                    click.secho(f'Error: Linking folders is not supported on Azure. Please use `cloudos interactive-session create --mount` to load your data in the session.', fg='red', err=True)
                    raise SystemExit(1)
                
                parsed = parse_link_path(link_path)
                
                if parsed['type'] == 's3':
                    # S3 folders are only supported on AWS (additional safeguard)
                    if execution_platform != 'aws':
                        click.secho(f'Error: S3 links are only supported on AWS execution platform.', fg='red', err=True)
                        raise SystemExit(1)
                    
                    # S3 folder: create S3Folder FUSE mount
                    if verbose:
                        print(f'\tLinking S3: s3://{parsed["s3_bucket"]}/{parsed["s3_prefix"]}')
                    
                    # Use bucket name or mount_name if provided (legacy format)
                    mount_name = parsed.get('mount_name', f"{parsed['s3_bucket']}-mount")
                    s3_mount_item = {
                        "type": "S3Folder",
                        "data": {
                            "name": mount_name,
                            "s3BucketName": parsed["s3_bucket"],
                            "s3Prefix": parsed["s3_prefix"]
                        }
                    }
                    parsed_s3_mounts.append(s3_mount_item)
                    
                    if verbose:
                        print(f'\t  ✓ Linked S3: {mount_name}')
                
                else:  # type == 'cloudos'
                    # CloudOS folder: resolve via Datasets API
                    folder_project = parsed['project_name']
                    folder_path = parsed['folder_path']
                    
                    if verbose:
                        print(f'\tLinking CloudOS folder: {folder_project}/{folder_path}')
                    
                    # Create Datasets API instance for this project
                    datasets_api = Datasets(
                        cloudos_url=cloudos_url,
                        apikey=apikey,
                        workspace_id=workspace_id,
                        project_name=folder_project,
                        verify=verify_ssl,
                        cromwell_token=None
                    )
                    
                    # Get folder contents to verify it exists
                    folder_content = datasets_api.list_folder_content(folder_path)
                    
                    # For CloudOS folders, we create a mount item
                    mount_name = folder_path.split('/')[-1] if folder_path else folder_project
                    cloudos_mount_item = {
                        "type": "S3Folder",
                        "data": {
                            "name": mount_name,
                            "s3BucketName": folder_project,
                            "s3Prefix": folder_path + ("/" if folder_path and not folder_path.endswith('/') else "")
                        }
                    }
                    parsed_s3_mounts.append(cloudos_mount_item)
                    
                    if verbose:
                        print(f'\t  ✓ Linked CloudOS folder: {mount_name}')
            
            except Exception as e:
                click.secho(f'Error: Failed to link folder: {str(e)}', fg='red', err=True)
                raise SystemExit(1)
        
        # Build the session payload
        payload = build_session_payload(
            name=name,
            backend=backend_type,
            execution_platform=execution_platform,
            instance_type=instance,
            storage_size=storage,
            is_spot=spot,
            is_shared=shared,
            cost_limit=cost_limit,
            shutdown_at=shutdown_at_parsed,
            project_id=project_id,
            data_files=parsed_data_files,
            s3_mounts=parsed_s3_mounts if execution_platform == 'aws' else [],
            r_version=r_version,
            spark_master_type=spark_master,
            spark_core_type=spark_core,
            spark_workers=spark_workers
        )
        
        if verbose:
            print('\tPayload constructed:')
            print(json.dumps(payload, indent=2))
        
        # Create the session via API
        response = cl.create_interactive_session(workspace_id, payload, verify=verify_ssl)
        
        session_id = response.get('_id')
        
        if verbose:
            print(f'\tSession created with ID: {session_id}')
        
        # Display session creation details in table format
        format_session_creation_table(
            response,
            instance_type=instance,
            storage_size=storage,
            backend_type=backend_type,
            r_version=r_version,
            spark_master=spark_master,
            spark_core=spark_core,
            spark_workers=spark_workers,
            data_files=parsed_data_files,
            s3_mounts=parsed_s3_mounts
        )
        
        if verbose:
            print('\tSession creation completed successfully!')
    
    except BadRequestException as e:
        error_str = str(e)
        if '401' in error_str or 'Unauthorized' in error_str:
            click.secho(f'Error: Failed to create interactive session. Please check your credentials (API key and CloudOS URL).', fg='red', err=True)
        else:
            click.secho(f'Error: Failed to create interactive session: {e}', fg='red', err=True)
        raise SystemExit(1)
    except Exception as e:
        error_str = str(e)
        # Check for DNS/connection errors
        if 'Failed to resolve' in error_str or 'Name or service not known' in error_str or 'nodename nor servname provided' in error_str:
            click.secho(f'Error: Unable to connect to CloudOS URL. Please verify the CloudOS URL is correct.', fg='red', err=True)
        # Check for 401 Unauthorized
        elif '401' in error_str or 'Unauthorized' in error_str:
            click.secho(f'Error: Failed to create interactive session. Please check your credentials (API key and CloudOS URL).', fg='red', err=True)
        else:
            click.secho(f'Error: {str(e)}', fg='red', err=True)
        raise SystemExit(1)

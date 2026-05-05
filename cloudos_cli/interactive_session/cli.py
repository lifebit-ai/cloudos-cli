"""CLI commands for Lifebit Platform interactive session management."""

import rich_click as click
import json
import time
from cloudos_cli.clos import Cloudos
from cloudos_cli.datasets import Datasets
from cloudos_cli.utils.errors import BadRequestException
from cloudos_cli.utils.resources import ssl_selector
from cloudos_cli.interactive_session.interactive_session import (
    create_interactive_session_list_table,
    process_interactive_session_list,
    save_interactive_session_list_to_csv,
    parse_shutdown_duration,
    parse_watch_timeout_duration,
    parse_data_file,
    parse_link_path,
    build_session_payload,
    format_session_creation_table,
    resolve_data_file_id,
    validate_session_id,
    validate_instance_type,
    get_interactive_session_status,
    format_session_status_table,
    transform_session_response,
    export_session_status_json,
    export_session_status_csv,
    map_status,
    PRE_RUNNING_STATUSES,
    format_stop_success_output,
    poll_session_termination,
    build_resume_payload,
    fetch_interactive_session_page
)
from cloudos_cli.configure.configure import with_profile_config, CLOUDOS_URL
from cloudos_cli.utils.cli_helpers import pass_debug_to_subcommands


# Create the interactive_session group
@click.group(cls=pass_debug_to_subcommands())
def interactive_session():
    """Lifebit Platform interactive session functionality: list and manage interactive sessions."""
    print(interactive_session.__doc__ + '\n')


@interactive_session.command('list')
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
@click.option('--filter-status',
              multiple=True,
              type=click.Choice(['setup', 'initialising', 'initializing', 'running', 'scheduled', 'paused'], case_sensitive=False),
              help='Filter sessions by status. Can be specified multiple times to filter by multiple statuses. (Supports both initialising and initializing spellings)')
@click.option('--limit',
              type=int,
              default=10,
              help='Number of results per page. Default=10, max=100.')
@click.option('--page',
              type=int,
              default=1,
              help='Page number to retrieve. Default=1.')
@click.option('--filter-only-mine',
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
                    'Available columns: backend, cost, cost_limit, created_at, id, instance, name, owner, project, resources, runtime, saved_at, spot, status, time_left, type, version. ' +
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
                  filter_only_mine,
                  archived,
                  output_format,
                  output_basename,
                  table_columns,
                  all_fields,
                  verbose,
                  disable_ssl_verification,
                  ssl_cert,
                  profile):
    """List interactive sessions for a Lifebit Platform team."""

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
    # Validate table columns if specified

    valid_columns = {'id', 'name', 'status', 'type', 'instance', 'cost', 'owner', 'project', 
                     'created_at', 'runtime', 'saved_at', 'resources', 'backend', 'version',
                     'spot', 'cost_limit', 'time_left'}
    selected_columns = table_columns

    if selected_columns:
        # Parse columns (split by comma and strip whitespace)
        col_list = [col.strip() for col in selected_columns.split(',')]
        invalid_cols = [col for col in col_list if col not in valid_columns]
        if invalid_cols:
            click.secho(f'Error: Invalid column(s): {", ".join(invalid_cols)}', fg='red', err=True)
            click.secho(f'Valid columns: {", ".join(sorted(valid_columns))}', fg='yellow', err=True)
            click.secho(f'\nTip: Use --help without other options to see command help', fg='cyan', err=True)
            raise SystemExit(1)

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
            owner_only=filter_only_mine,
            include_archived=archived,
            verify=verify_ssl
        )
        sessions = result.get('sessions', [])
        pagination_metadata = result.get('pagination_metadata', None)

        # Create callback function for fetching additional pages
        fetch_page = lambda page_num: fetch_interactive_session_page(
            cl, workspace_id, page_num, limit, filter_status, filter_only_mine, archived, verify_ssl
        )

        # Handle empty results
        if len(sessions) == 0:
            if filter_status:
                # Show helpful message when filtering returns no results
                status_flow = 'scheduled → initialising → setup → running → paused'
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
            save_interactive_session_list_to_csv(sessions_df, outfile, count=len(sessions))
        elif output_format == 'json':
            with open(outfile, 'w') as o:
                o.write(json.dumps(sessions, indent=2))
            print(f'\tInteractive session list collected with a total of {len(sessions)} sessions on this page.')
            print(f'\tInteractive session list saved to {outfile}')        
        else:
            raise ValueError('Unrecognised output format. Please use one of [stdout|csv|json]')

    except BadRequestException as e:
        error_str = str(e)
        # Check if the error is related to authentication
        if '401' in error_str or 'Unauthorized' in error_str:
            click.secho(f'Error: Failed to retrieve interactive sessions. Please check your credentials (API key and Lifebit Platform URL).', fg='red', err=True)
            raise SystemExit(1)
        # Check if the error is related to status filtering
        elif filter_status and ('400' in error_str or 'Invalid' in error_str):
            status_flow = 'scheduled → initialising → setup → running → paused'
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
            click.secho(f'Error: Unable to connect to Lifebit Platform URL. Please verify the Lifebit Platform URL is correct.', fg='red', err=True)
        # Check for 401 Unauthorized
        elif '401' in error_str or 'Unauthorized' in error_str:
            click.secho(f'Error: Failed to retrieve interactive sessions. Please check your credentials (API key and Lifebit Platform URL).', fg='red', err=True)
        else:
            click.secho(f'Error: {str(e)}', fg='red', err=True)
        raise SystemExit(1)


@interactive_session.command('create')
@click.option('-k',
              '--apikey',
              help='Your Lifebit Platform API key',
              required=False)
@click.option('-c',
              '--cloudos-url',
              help=(f'The Lifebit Platform url you are trying to access to. Default={CLOUDOS_URL}.'),
              default=CLOUDOS_URL,
              required=False)
@click.option('--workspace-id',
              help='The specific Lifebit Platform workspace id.',
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
              help='Auto-shutdown duration (e.g., 8h, 2d). Default=12h.',
              default='12h')
@click.option('--mount',
              multiple=True,
              help='Mount a data file into the session. Supports both Lifebit Platform datasets and S3 files. Format: project_name/dataset_path (e.g., leila-test/Data/file.csv) or s3://bucket/path/to/file (e.g., s3://my-bucket/data/file.csv). Can be used multiple times.')
@click.option('--link',
              multiple=True,
              help='Link a folder into the session for read access. Supports S3 folders (s3://bucket/path/) and File Explorer folders (project-name/folder/path - must include project name). Both types can be combined. Provide multiple paths as comma-separated values or use --link multiple times. Examples: --link s3://bucket/data/,my-project/Data/results OR --link s3://bucket1/path/ --link my-project/Data')
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

    # Validate instance type format
    is_valid, error_msg = validate_instance_type(instance, execution_platform)
    if not is_valid:
        click.secho(f'Error: {error_msg}', fg='red', err=True)
        click.secho(f'Hint: Check your instance type spelling and format for {execution_platform.upper()}.', fg='yellow', err=True)
        raise SystemExit(1)

    # Validate Spark instance types if session type is spark
    if session_type.lower() == 'spark':
        # Spark is AWS only, so use 'aws' for validation
        is_valid_master, error_msg_master = validate_instance_type(spark_master, 'aws')
        if not is_valid_master:
            click.secho(f'Error: Invalid Spark master instance type: {error_msg_master}', fg='red', err=True)
            raise SystemExit(1)
        is_valid_core, error_msg_core = validate_instance_type(spark_core, 'aws')
        if not is_valid_core:
            click.secho(f'Error: Invalid Spark core instance type: {error_msg_core}', fg='red', err=True)
            raise SystemExit(1)
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

        # Parse and resolve mounted data files (both Lifebit Platform and S3)
        parsed_data_files = []
        parsed_s3_mounts = []  # S3 folders go into FUSE mounts
        if mount:
            try:
                for df in mount:
                    parsed = parse_data_file(df)
                    if parsed['type'] == 's3':
                        # S3 files are only supported on AWS
                        if execution_platform != 'aws':
                            click.secho(f'Error: S3 mounts are only supported on AWS. Use Lifebit Platform file explorer paths for Azure.', fg='red', err=True)
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
                        # Lifebit Platform dataset file: resolve via Datasets API
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
        # Flatten comma-separated paths within --link options
        all_link_paths = []
        for link_entry in link:
            # Split by comma to support comma-separated paths
            paths = [p.strip() for p in link_entry.split(',') if p.strip()]
            all_link_paths.extend(paths)
        
        mount_names_seen = {}  # Track mount names to detect duplicates
        for link_path in all_link_paths:
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
                    # Generate unique mount name from last segment of prefix, or use provided mount_name (legacy format)
                    if 'mount_name' in parsed:
                        mount_name = parsed['mount_name']
                    else:
                        # Extract last meaningful segment from prefix for unique mount name
                        prefix_parts = [p for p in parsed['s3_prefix'].rstrip('/').split('/') if p]
                        mount_name = prefix_parts[-1] if prefix_parts else parsed['s3_bucket']
                    
                    # Check for duplicate mount names
                    if mount_name in mount_names_seen:
                        click.secho(
                            f"Error: Duplicate mount name '{mount_name}' detected. "
                            f"The folders '{mount_names_seen[mount_name]}' and '{link_path}' "
                            f"would both be mounted with the same name. Please use folders with unique names.",
                            fg='red', err=True
                        )
                        raise SystemExit(1)
                    mount_names_seen[mount_name] = link_path
                    
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
                    # Lifebit Platform folder: resolve via Datasets API
                    folder_project = parsed['project_name']
                    folder_path = parsed['folder_path']
                    if verbose:
                        print(f'\tLinking Lifebit Platform folder: {folder_project}/{folder_path}')
                    # Create Datasets API instance for this project
                    try:
                        datasets_api = Datasets(
                            cloudos_url=cloudos_url,
                            apikey=apikey,
                            workspace_id=workspace_id,
                            project_name=folder_project,
                            verify=verify_ssl,
                            cromwell_token=None
                        )
                        # Validate project and folder exist
                        _ = datasets_api.list_folder_content("")  # Check if project accessible
                        
                        # If there's a folder path, validate it exists
                        if folder_path:
                            folder_parts = folder_path.strip("/").split("/")
                            parent_path = "/".join(folder_parts[:-1]) if len(folder_parts) > 1 else ""
                            item_name = folder_parts[-1]
                            contents = datasets_api.list_folder_content(parent_path)
                            
                            # Check if the folder exists
                            found = None
                            for item in contents.get("folders", []):
                                if item.get("name") == item_name:
                                    found = item
                                    break
                            
                            if not found:
                                raise ValueError(
                                    f"Folder '{item_name}' not found at path '{parent_path}' in project '{folder_project}'. "
                                    f"Please verify the folder exists using 'cloudos datasets ls --project-name {folder_project}'."
                                )
                            
                            # Check if it's a virtual folder
                            if found.get("folderType") == "VirtualFolder":
                                raise ValueError(
                                    f"The folder '{link_path}' is a virtual folder and cannot be linked. "
                                    f"Virtual folders only exist in File Explorer. Please use a regular folder or S3 path instead."
                                )
                            
                            # Check if the folder is empty
                            folder_contents = datasets_api.list_folder_content(folder_path)
                            has_files = len(folder_contents.get("files", [])) > 0
                            has_folders = len(folder_contents.get("folders", [])) > 0
                            if not has_files and not has_folders:
                                raise ValueError(
                                    f"The folder '{link_path}' is empty and cannot be linked. "
                                    f"Please add files or subfolders to this folder before linking it."
                                )
                    except ValueError:
                        raise  # Re-raise our validation errors
                    except Exception as e:
                        error_msg = str(e)
                        if "404" in error_msg or "not found" in error_msg.lower():
                            raise ValueError(
                                f"Project '{folder_project}' not found. "
                                f"Please verify the project name exists in your workspace."
                            )
                        else:
                            raise ValueError(f"Failed to validate folder '{link_path}': {error_msg}")
                    
                    # For Lifebit Platform folders, we create a mount item
                    mount_name = folder_path.split('/')[-1] if folder_path else folder_project
                    
                    # Check for duplicate mount names
                    if mount_name in mount_names_seen:
                        click.secho(
                            f"Error: Duplicate mount name '{mount_name}' detected. "
                            f"The folders '{mount_names_seen[mount_name]}' and '{link_path}' "
                            f"would both be mounted with the same name. Please use folders with unique names.",
                            fg='red', err=True
                        )
                        raise SystemExit(1)
                    mount_names_seen[mount_name] = link_path
                    
                    cloudos_mount_item = {
                        "type": "S3Folder",
                        "data": {
                            "name": mount_name,
                            "s3BucketName": folder_project,
                            "s3Prefix": folder_path + ("/" if folder_path and not folder_path.endswith('/') else "")
                        },
                        "_isFileExplorer": True,  # Marker for display formatting
                        "_originalPath": f"{folder_project}/{folder_path}"  # Original path for display
                    }
                    parsed_s3_mounts.append(cloudos_mount_item)

                    if verbose:
                        print(f'\t  ✓ Linked Lifebit Platform folder: {mount_name}')

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
            s3_mounts=parsed_s3_mounts,
            shutdown_in=shutdown_in
        )
        # Output session link in greppable format for CI/automation
        click.echo(f"Session link: {cloudos_url}/app/data-science/interactive-analysis/view/{session_id}")
        if verbose:
            print('\tSession creation completed successfully!')

    except BadRequestException as e:
        error_str = str(e)
        if '401' in error_str or 'Unauthorized' in error_str:
            click.secho(f'Error: Failed to create interactive session. Please check your credentials (API key and Lifebit Platform URL).', fg='red', err=True)
        else:
            click.secho(f'Error: Failed to create interactive session: {e}', fg='red', err=True)
        raise SystemExit(1)
    except Exception as e:
        error_str = str(e)
        # Check for DNS/connection errors
        if 'Failed to resolve' in error_str or 'Name or service not known' in error_str or 'nodename nor servname provided' in error_str:
            click.secho(f'Error: Unable to connect to Lifebit Platform URL. Please verify the Lifebit Platform URL is correct.', fg='red', err=True)
        # Check for 401 Unauthorized
        elif '401' in error_str or 'Unauthorized' in error_str:
            click.secho(f'Error: Failed to create interactive session. Please check your credentials (API key and Lifebit Platform URL).', fg='red', err=True)
        else:
            click.secho(f'Error: {str(e)}', fg='red', err=True)
        raise SystemExit(1)


@interactive_session.command('status')
@click.option('-k',
              '--apikey',
              help='Your Lifebit Platform API key',
              required=False)
@click.option('-c',
              '--cloudos-url',
              help=(f'The Lifebit Platform url you are trying to access to. Default={CLOUDOS_URL}.'),
              default=CLOUDOS_URL,
              required=False)
@click.option('--session-id',
              help='The session ID to retrieve status for (24-character hex string).',
              required=True)
@click.option('--workspace-id',
              help='The specific Lifebit Platform workspace id.',
              required=False)
@click.option('--output-format',
              help='Output format for session status.',
              type=click.Choice(['stdout', 'csv', 'json'], case_sensitive=False),
              default='stdout')
@click.option('--output-basename',
              help=('Output file base name to save session status. ' +
                    'Default=interactive_session_status'),
              default='interactive_session_status',
              required=False)
@click.option('--watch',
              is_flag=True,
              help='Continuously poll status until session reaches running state (only for pre-running statuses).')
@click.option('--watch-interval',
              type=int,
              default=30,
              help='Poll interval in seconds when using --watch. Default=30.')
@click.option('--max-wait-time',
              type=str,
              default='30m',
              help='Maximum time to wait for session in watch mode. Accepts formats: 30s, 5m, 2h, 1d. Default=30m (30 minutes).')
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
def get_session_status(ctx,
                       apikey,
                       cloudos_url,
                       session_id,
                       workspace_id,
                       output_format,
                       output_basename,
                       watch,
                       watch_interval,
                       max_wait_time,
                       verbose,
                       disable_ssl_verification,
                       ssl_cert,
                       profile):
    """Get status of an interactive session."""

    verify_ssl = ssl_selector(disable_ssl_verification, ssl_cert)
    # Validate session ID format
    if not validate_session_id(session_id):
        click.secho(f'Error: Invalid session ID format. Expected 24-character hex string, got: {session_id}', fg='red', err=True)
        raise SystemExit(1)
    # Validate watch-interval
    if watch_interval <= 0:
        click.secho(f'Error: --watch-interval must be a positive number, got: {watch_interval}', fg='red', err=True)
        raise SystemExit(1)
    # Parse and validate max-wait-time
    try:
        max_wait_time_seconds = parse_watch_timeout_duration(max_wait_time)
    except ValueError as e:
        click.secho(f'Error: Invalid --max-wait-time format: {str(e)}', fg='red', err=True)
        raise SystemExit(1)
    # Validate output format
    if output_format.lower() not in ['stdout', 'csv', 'json']:
        click.secho(f'Error: Invalid output format. Must be one of: stdout, csv, json', fg='red', err=True)
        raise SystemExit(1)
    if verbose:
        print('Executable: get interactive session status...')
        print('\t...Preparing objects')

    try:
        # Get initial status
        if verbose:
            print(f'\tRetrieving session status from: {cloudos_url}')
        session_response = get_interactive_session_status(
            cloudos_url=cloudos_url,
            apikey=apikey,
            session_id=session_id,
            team_id=workspace_id,
            verify_ssl=verify_ssl,
            verbose=verbose
        )
        if verbose:
            print(f'\t✓ Session retrieved successfully')
        # Get mapped status for display
        api_status = session_response.get('status', '')
        display_status = map_status(api_status)
        # Apply watch mode if requested
        if watch:
            # Check if watch mode is appropriate for this session status
            if display_status not in PRE_RUNNING_STATUSES:
                click.secho(
                    f'⚠ Warning: Watch mode only works for pre-running statuses (setup, initialising, scheduled). '
                    f'Current status: {display_status}. Showing session status instead.',
                    fg='yellow',
                    err=True
                )
            else:
                # Print initial status message before starting watch
                click.echo(f'Session {session_id} currently is in {display_status}...')
                start_time = time.time()
                previous_status = display_status  # Track previous status to detect changes
                while True:
                    # Get current status
                    api_status = session_response.get('status', '')
                    display_status = map_status(api_status)
                    elapsed = time.time() - start_time
                    if verbose:
                        print(f'\tPolling... Status: {display_status} | Elapsed: {int(elapsed)}s')
                    # Print status change message
                    if display_status != previous_status:
                        click.echo(f'Status changed: {previous_status} → {display_status}')
                        previous_status = display_status
                    # Exit watch mode if session is ready or terminated
                    if display_status == 'running':
                        click.secho('✓ Session is now running and ready to use!', fg='green')
                        break
                    elif display_status in ['paused', 'terminated']:
                        click.secho(f'⚠ Session reached terminal state: {display_status}', fg='yellow')
                        break
                    # Check timeout AFTER evaluating current status
                    if elapsed > max_wait_time_seconds:
                        click.secho(
                            f'Timeout: Session did not reach running state within {max_wait_time}. '
                            f'Current status: {display_status}. Exiting watch mode.',
                            fg='red',
                            err=True
                        )
                        break
                    # Wait before next poll
                    time.sleep(watch_interval)
                    # Fetch updated status for next iteration
                    session_response = get_interactive_session_status(
                        cloudos_url=cloudos_url,
                        apikey=apikey,
                        session_id=session_id,
                        team_id=workspace_id,
                        verify_ssl=verify_ssl,
                        verbose=False
                    )

        # Transform and display response based on format
        if output_format.lower() == 'json':
            json_output = export_session_status_json(session_response)
            outfile = f"{output_basename}.json"
            with open(outfile, 'w') as f:
                f.write(json_output)
            click.echo(f'Session status saved to {outfile}')
        elif output_format.lower() == 'csv':
            transformed_data = transform_session_response(session_response)
            csv_output = export_session_status_csv(transformed_data)
            outfile = f"{output_basename}.csv"
            with open(outfile, 'w') as f:
                f.write(csv_output)
            click.echo(f'Session status saved to {outfile}')
        else:  # stdout (default)
            transformed_data = transform_session_response(session_response)
            format_session_status_table(transformed_data, cloudos_url=cloudos_url)

    except ValueError as e:
        # Handle validation errors (e.g., session not found)
        click.secho(f'Error: {str(e)}', fg='red', err=True)
        raise SystemExit(1)

    except PermissionError as e:
        # Handle authentication/permission errors
        click.secho(f'Error: {str(e)}', fg='red', err=True)
        if '401' in str(e) or 'Unauthorized' in str(e):
            click.secho('Please check your API credentials (apikey and cloudos-url).', fg='yellow', err=True)
        raise SystemExit(1)

    except KeyboardInterrupt:
        click.secho('\n⚠ Watch mode interrupted by user.', fg='yellow', err=True)
        raise SystemExit(0)

    except Exception as e:
        error_str = str(e)
        # Check for network errors
        if 'Failed to resolve' in error_str or 'Name or service not known' in error_str:
            click.secho(f'Error: Unable to connect to Lifebit Platform. Please verify the Lifebit Platform URL is correct.', fg='red', err=True)
        elif '401' in error_str or 'Unauthorized' in error_str:
            click.secho(f'Error: Failed to retrieve session status. Please check your credentials.', fg='red', err=True)
        else:
            click.secho(f'Error: Failed to retrieve session status: {str(e)}', fg='red', err=True)
        raise SystemExit(1)


@interactive_session.command('pause')
@click.option('--session-id',
              help='The session ID to pause (24-character hex string).',
              required=True)
@click.option('-k',
              '--apikey',
              help='Your Lifebit Platform API key',
              required=False)
@click.option('-c',
              '--cloudos-url',
              help=(f'The Lifebit Platform url you are trying to access to. Default={CLOUDOS_URL}.'),
              default=CLOUDOS_URL,
              required=False)
@click.option('--workspace-id',
              help='The specific Lifebit Platform workspace id.',
              required=False)
@click.option('--no-upload',
              is_flag=True,
              help='Don\'t save session data before pausing (use with caution).')
@click.option('--force',
              is_flag=True,
              help='Force immediate termination and skip confirmation prompt.')
@click.option('--wait',
              is_flag=True,
              help='Wait for session to fully pause.')
@click.option('--yes', '-y',
              'skip_confirmation',
              is_flag=True,
              help='Skip confirmation prompt.')
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
def pause_session(ctx,
                  session_id,
                  apikey,
                  cloudos_url,
                  workspace_id,
                  no_upload,
                  force,
                  wait,
                  skip_confirmation,
                  verbose,
                  disable_ssl_verification,
                  ssl_cert,
                  profile):
    """Pause a running interactive session."""

    verify_ssl = ssl_selector(disable_ssl_verification, ssl_cert)
    # Validate session ID format
    if not validate_session_id(session_id):
        click.secho(f'Error: Invalid session ID format. Expected 24-character hex string, got: {session_id}', fg='red', err=True)
        raise SystemExit(1)
    if verbose:
        print('Executing pause interactive session...')
        print('\t...Preparing objects')

    try:
        # Check session status BEFORE prompting for confirmation
        if verbose:
            print('\t...Checking session status')

        try:
            session_response = get_interactive_session_status(
                cloudos_url=cloudos_url,
                apikey=apikey,
                session_id=session_id,
                team_id=workspace_id,
                verify_ssl=verify_ssl,
                verbose=False
            )
        except Exception as e:
            # Handle invalid session ID or API errors
            error_msg = str(e).lower()
            if 'not found' in error_msg or '404' in error_msg:
                click.secho(f'Error: Session ID not found: {session_id}', fg='red', err=True)
            else:
                click.secho(f'Error: Unable to retrieve session status: {str(e)}', fg='red', err=True)
            raise SystemExit(1)

        # Check if session is already paused or terminated
        api_status = session_response.get('status', '')
        if api_status == 'aborted':
            click.secho(f'Error: Cannot pause session - the session is already paused.', fg='red', err=True)
            click.secho(f'Tip: Check the session status with: cloudos interactive-session status --session-id {session_id}', fg='yellow', err=True)
            raise SystemExit(1)
        elif  api_status == 'aborting':
            click.secho(f'Error: Cannot pause session - the session is already being paused.', fg='red', err=True)
            click.secho(f'Tip: Wait a moment and check status with: cloudos interactive-session status --session-id {session_id}', fg='yellow', err=True)
            raise SystemExit(1)
        if api_status == 'terminated':
            click.secho(f'Error: Session is terminated and cannot be paused.', fg='red', err=True)
            raise SystemExit(1)
        # Show confirmation prompt unless --yes or --force flag is used
        if not skip_confirmation and not force:
            click.echo(f'About to pause session: {session_id}')
            click.echo(f'Upload data before pausing: {not no_upload}')
            click.echo(f'Force immediate termination: {force}')
            # Get user confirmation
            try:
                response = click.prompt('Continue? [y/N]', type=str, default='N')
                if response.lower() != 'y':
                    click.echo('Cancelled.')
                    raise SystemExit(0)
            except KeyboardInterrupt:
                click.secho('\n⚠ Operation cancelled by user.', fg='yellow', err=True)
                raise SystemExit(0)
        # Prepare abort parameters
        upload_on_close = not no_upload  # Invert no_upload to get upload_on_close
        force_abort = force
        # Create Cloudos client and abort session
        cl = Cloudos(cloudos_url, apikey, None)
        if verbose:
            print('\t...Sending abort request to Lifebit Platform')

        # Call the abort endpoint
        status_code = cl.abort_interactive_session(
            session_id=session_id,
            team_id=workspace_id,
            upload_on_close=upload_on_close,
            force_abort=force_abort,
            verify=verify_ssl
        )
        if verbose:
            print(f'\t✓ Abort request sent successfully (HTTP {status_code})')
        # Show force abort warning if applicable
        if force:
            click.secho('\n⚠ Warning: Session was force-aborted by the user. Some data may have not been saved.', fg='yellow', err=True)
        # If --wait flag is set, poll until session is paused
        if wait:
            if verbose:
                print('\t...Waiting for session to fully pause')
            try:
                final_response = poll_session_termination(
                    cloudos_url=cloudos_url,
                    apikey=apikey,
                    session_id=session_id,
                    team_id=workspace_id,
                    max_wait=300,  # 5 minutes timeout
                    poll_interval=5,  # Poll every 5 seconds
                    verify_ssl=verify_ssl
                )
                # Display final status (pass raw API response, not transformed data)
                format_stop_success_output(final_response, wait=True)
            except TimeoutError as e:
                click.secho(f'⚠ Timeout: {str(e)}', fg='yellow', err=True)
                click.echo('The session pause command has been sent, but the session did not fully terminate within the timeout period.')
                click.echo(f'You can check the session status using: cloudos interactive-session status --session-id {session_id} --profile {profile or "default"}')
                raise SystemExit(1)
        else:
            # Show success message without waiting
            click.secho('✓ Session pause request sent successfully.', fg='green')
            click.echo(f'You can monitor the session status using: cloudos interactive-session status --session-id {session_id} --profile {profile or "default"}')

    except ValueError as e:
        # Handle validation errors
        click.secho(f'Error: {str(e)}', fg='red', err=True)
        raise SystemExit(1)

    except PermissionError as e:
        # Handle authentication/permission errors
        click.secho(f'Error: {str(e)}', fg='red', err=True)
        if '401' in str(e) or 'Unauthorized' in str(e):
            click.secho('Please check your API credentials (apikey and cloudos-url).', fg='yellow', err=True)
        raise SystemExit(1)

    except BadRequestException as e:
        # Handle API errors with better messages
        error_str = str(e)
        # Show the original error for other bad request errors
        click.secho(f'Error: {str(e)}', fg='red', err=True)
        raise SystemExit(1)

    except KeyboardInterrupt:
        click.secho('\n⚠ Operation interrupted by user.', fg='yellow', err=True)
        raise SystemExit(0)

    except Exception as e:
        error_str = str(e)
        # Check for network errors
        if 'Failed to resolve' in error_str or 'Name or service not known' in error_str:
            click.secho(f'Error: Unable to connect to Lifebit Platform. Please verify the Lifebit Platform URL is correct.', fg='red', err=True)
        elif '401' in error_str or 'Unauthorized' in error_str:
            click.secho(f'Error: Failed to pause session. Please check your credentials.', fg='red', err=True)
        elif 'Session not found' in error_str:
            click.secho(f'Error: Session not found. Please check the session ID.', fg='red', err=True)
        elif 'aborted in aborted status' in error_str.lower() or 'aborted in aborting status' in error_str.lower():
            # Session is already paused/pausing
            if 'aborted status' in error_str.lower():
                click.secho(f'Error: Cannot pause session - the session is already paused.', fg='red', err=True)
                click.secho(f'Tip: Check the session status with: cloudos interactive-session status --session-id {session_id}', fg='yellow', err=True)
            else:
                click.secho(f'Error: Cannot pause session - the session is already being paused.', fg='red', err=True)
                click.secho(f'Tip: Wait a moment and check status with: cloudos interactive-session status --session-id {session_id}', fg='yellow', err=True)
        else:
            click.secho(f'Error: Failed to pause session: {str(e)}', fg='red', err=True)
        raise SystemExit(1)


@interactive_session.command('resume')
@click.option('--session-id',
              help='Session ID to resume.',
              required=True)
@click.option('-k',
              '--apikey',
              help='Your Lifebit Platform API key',
              required=False)
@click.option('-c',
              '--cloudos-url',
              help=(f'The Lifebit Platform url you are trying to access to. Default={CLOUDOS_URL}.'),
              default=CLOUDOS_URL,
              required=False)
@click.option('--workspace-id',
              help='The specific Lifebit Platform workspace id.',
              required=False)
@click.option('--instance',
              help='Change instance type when resuming.',
              default=None)
@click.option('--storage',
              type=int,
              help='Update storage size in GB (100-5000).',
              default=None)
@click.option('--cost-limit',
              type=float,
              help='Update compute cost limit in USD. Default=-1 (unlimited).',
              default=None)
@click.option('--shutdown-in',
              help='Update auto-shutdown duration (e.g., 8h, 2d).',
              default=None)
@click.option('--mount',
              multiple=True,
              help='Mount additional data file. Format: project_name/dataset_path or s3://bucket/path/to/file. Can be used multiple times.')
@click.option('--link',
              multiple=True,
              help='Link additional folder. Supports S3 folders (s3://bucket/path/) and File Explorer folders (project-name/folder/path - must include project name). Both types can be combined. Provide multiple paths as comma-separated values or use --link multiple times. Examples: --link s3://bucket/data/,my-project/Data/results OR --link s3://bucket1/path/ --link my-project/Data')
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
def resume_session(ctx,
                   session_id,
                   apikey,
                   cloudos_url,
                   workspace_id,
                   instance,
                   storage,
                   cost_limit,
                   shutdown_in,
                   mount,
                   link,
                   verbose,
                   disable_ssl_verification,
                   ssl_cert,
                   profile):
    """Resume a paused interactive session with optional configuration updates."""

    verify_ssl = ssl_selector(disable_ssl_verification, ssl_cert)
    # Validate session ID format
    if not validate_session_id(session_id):
        click.secho(f'Error: Invalid session ID format. Expected 24-character hex string, got: {session_id}', fg='red', err=True)
        raise SystemExit(1)
    # Validate storage if provided
    if storage is not None and not (100 <= storage <= 5000):
        click.secho('Error: Storage size must be between 100-5000 GB', fg='red', err=True)
        raise SystemExit(1)
    if verbose:
        print('Executing resume interactive session...')
        print('\t...Preparing objects')

    cl = Cloudos(cloudos_url, apikey, None)
    if verbose:
        print('\tThe following Cloudos object was created:')
        print('\t' + str(cl) + '\n')
        print(f'\tResuming session: {session_id}')

    try:
        # Get current session details to determine execution platform
        try:
            session_data = get_interactive_session_status(
                cloudos_url=cloudos_url,
                apikey=apikey,
                session_id=session_id,
                team_id=workspace_id,
                verify_ssl=verify_ssl,
                verbose=False
            )
            current_config = session_data.get('interactiveSessionConfiguration', {})
            execution_platform = current_config.get('executionPlatform', 'aws')
            if verbose:
                print(f'\tCurrent session platform: {execution_platform}')
                print(f'\tCurrent status: {session_data.get("status", "unknown")}')
        except Exception as e:
            # If we can't get session details, default to aws
            execution_platform = 'aws'
            if verbose:
                print(f'\tCould not retrieve session details (using default platform: aws)')

        # Parse shutdown duration if provided
        shutdown_at_parsed = None
        if shutdown_in:
            try:
                shutdown_at_parsed = parse_shutdown_duration(shutdown_in)
                if verbose:
                    print(f'\tParsed shutdown duration: {shutdown_in} -> {shutdown_at_parsed}')
            except ValueError as e:
                click.secho(f'Error: Invalid shutdown duration: {str(e)}', fg='red', err=True)
                raise SystemExit(1)

        # Parse and resolve mounted data files
        parsed_data_files = []
        if mount:
            try:
                for df in mount:
                    parsed = parse_data_file(df)
                    if parsed['type'] == 's3':
                        # S3 files are only supported on AWS
                        if execution_platform != 'aws':
                            click.secho(f'Error: S3 mounts are only supported on AWS.', fg='red', err=True)
                            raise SystemExit(1)
                        if verbose:
                            print(f'\tMounting S3 file: s3://{parsed["s3_bucket"]}/{parsed["s3_prefix"]}')
                        s3_file_item = {
                            "type": "S3File",
                            "data": {
                                "name": parsed["s3_prefix"],
                                "s3BucketName": parsed["s3_bucket"],
                                "s3ObjectKey": parsed["s3_prefix"]
                            }
                        }
                        parsed_data_files.append(s3_file_item)
                    else:  # Lifebit Platform dataset
                        data_project = parsed['project_name']
                        dataset_path = parsed['dataset_path']
                        if verbose:
                            print(f'\tResolving dataset: {data_project}/{dataset_path}')
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

        # Parse and add linked folders
        parsed_s3_mounts = []
        if link:
            try:
                # Flatten comma-separated paths within --link options
                all_link_paths = []
                for link_entry in link:
                    # Split by comma to support comma-separated paths
                    paths = [p.strip() for p in link_entry.split(',') if p.strip()]
                    all_link_paths.extend(paths)
                
                mount_names_seen = {}  # Track mount names to detect duplicates
                for link_path in all_link_paths:
                    # Block all linking on Azure
                    if execution_platform == 'azure':
                        click.secho(f'Error: Linking folders is not supported on Azure. Please use --mount instead.', fg='red', err=True)
                        raise SystemExit(1)
                    parsed = parse_link_path(link_path)
                    if parsed['type'] == 's3':
                        if verbose:
                            print(f'\tLinking S3: s3://{parsed["s3_bucket"]}/{parsed["s3_prefix"]}')
                        # Generate unique mount name from last segment of prefix, or use provided mount_name (legacy format)
                        if 'mount_name' in parsed:
                            mount_name = parsed['mount_name']
                        else:
                            # Extract last meaningful segment from prefix for unique mount name
                            prefix_parts = [p for p in parsed['s3_prefix'].rstrip('/').split('/') if p]
                            mount_name = prefix_parts[-1] if prefix_parts else parsed['s3_bucket']
                        
                        # Check for duplicate mount names
                        if mount_name in mount_names_seen:
                            click.secho(
                                f"Error: Duplicate mount name '{mount_name}' detected. "
                                f"The folders '{mount_names_seen[mount_name]}' and '{link_path}' "
                                f"would both be mounted with the same name. Please use folders with unique names.",
                                fg='red', err=True
                            )
                            raise SystemExit(1)
                        mount_names_seen[mount_name] = link_path
                        
                        s3_mount_item = {
                            "type": "S3Folder",
                            "data": {
                                "name": mount_name,
                                "s3BucketName": parsed["s3_bucket"],
                                "s3Prefix": parsed["s3_prefix"]
                            }
                        }
                        parsed_s3_mounts.append(s3_mount_item)
                    else:  # Lifebit Platform folder
                        folder_project = parsed['project_name']
                        folder_path = parsed['folder_path']
                        if verbose:
                            print(f'\tLinking Lifebit Platform folder: {folder_project}/{folder_path}')
                        # Create Datasets API instance for this project
                        try:
                            datasets_api = Datasets(
                                cloudos_url=cloudos_url,
                                apikey=apikey,
                                workspace_id=workspace_id,
                                project_name=folder_project,
                                verify=verify_ssl,
                                cromwell_token=None
                            )
                            # Validate project and folder exist
                            _ = datasets_api.list_folder_content("")  # Check if project accessible
                            
                            # If there's a folder path, validate it exists
                            if folder_path:
                                folder_parts = folder_path.strip("/").split("/")
                                parent_path = "/".join(folder_parts[:-1]) if len(folder_parts) > 1 else ""
                                item_name = folder_parts[-1]
                                contents = datasets_api.list_folder_content(parent_path)
                                
                                # Check if the folder exists
                                found = None
                                for item in contents.get("folders", []):
                                    if item.get("name") == item_name:
                                        found = item
                                        break
                                
                                if not found:
                                    raise ValueError(
                                        f"Folder '{item_name}' not found at path '{parent_path}' in project '{folder_project}'. "
                                        f"Please verify the folder exists using 'cloudos datasets ls --project-name {folder_project}'."
                                    )
                                
                                # Check if it's a virtual folder
                                if found.get("folderType") == "VirtualFolder":
                                    raise ValueError(
                                        f"The folder '{link_path}' is a virtual folder and cannot be linked. "
                                        f"Virtual folders only exist in File Explorer. Please use a regular folder or S3 path instead."
                                    )
                                
                                # Check if the folder is empty
                                folder_contents = datasets_api.list_folder_content(folder_path)
                                has_files = len(folder_contents.get("files", [])) > 0
                                has_folders = len(folder_contents.get("folders", [])) > 0
                                if not has_files and not has_folders:
                                    raise ValueError(
                                        f"The folder '{link_path}' is empty and cannot be linked. "
                                        f"Please add files or subfolders to this folder before linking it."
                                    )
                        except ValueError:
                            raise  # Re-raise our validation errors
                        except Exception as e:
                            error_msg = str(e)
                            if "404" in error_msg or "not found" in error_msg.lower():
                                raise ValueError(
                                    f"Project '{folder_project}' not found. "
                                    f"Please verify the project name exists in your workspace."
                                )
                            else:
                                raise ValueError(f"Failed to validate folder '{link_path}': {error_msg}")
                        
                        # AWS-only: Create S3Folder mount for Lifebit Platform folders
                        mount_name = folder_path.split('/')[-1] if folder_path else folder_project
                        
                        # Check for duplicate mount names
                        if mount_name in mount_names_seen:
                            click.secho(
                                f"Error: Duplicate mount name '{mount_name}' detected. "
                                f"The folders '{mount_names_seen[mount_name]}' and '{link_path}' "
                                f"would both be mounted with the same name. Please use folders with unique names.",
                                fg='red', err=True
                            )
                            raise SystemExit(1)
                        mount_names_seen[mount_name] = link_path
                        
                        cloudos_mount_item = {
                            "type": "S3Folder",
                            "data": {
                                "name": mount_name,
                                "s3BucketName": folder_project,
                                "s3Prefix": folder_path + ("/" if folder_path and not folder_path.endswith('/') else "")
                            },
                            "_isFileExplorer": True,  # Marker for display formatting
                            "_originalPath": f"{folder_project}/{folder_path}"  # Original path for display
                        }
                        parsed_s3_mounts.append(cloudos_mount_item)
                        if verbose:
                            print(f'\t  ✓ Linked Lifebit Platform folder: {mount_name}')
            except Exception as e:
                click.secho(f'Error: Failed to parse link path: {str(e)}', fg='red', err=True)
                raise SystemExit(1)

        # Build the resume payload
        payload = build_resume_payload(
            instance_type=instance,
            storage_size=storage,
            cost_limit=cost_limit,
            shutdown_at=shutdown_at_parsed,
            data_files=parsed_data_files,
            s3_mounts=parsed_s3_mounts if execution_platform == 'aws' else None
        )
        if verbose:
            print('\tResume payload constructed:')
            print(json.dumps(payload, indent=2))
        # Resume the session via API
        response = cl.resume_interactive_session(session_id, workspace_id, payload, verify=verify_ssl)
        if verbose:
            print(f'\tSession resumed successfully')
        # Display success message
        click.secho(f'✓ Session {session_id} has been resumed successfully!', fg='green')
        # Show updated configuration
        updated_config = response.get('interactiveSessionConfiguration', {})
        if instance or storage or cost_limit is not None or shutdown_at_parsed:
            click.echo('\nUpdated configuration:')
            if instance:
                click.echo(f'  Instance type: {updated_config.get("instanceType", instance)}')
            if storage:
                click.echo(f'  Storage: {updated_config.get("storageSizeInGb", storage)} GB')
            if cost_limit is not None:
                exec_config = updated_config.get('execution', {})
                click.echo(f'  Cost limit: ${exec_config.get("computeCostLimit", cost_limit)}')
            if shutdown_at_parsed:
                exec_config = updated_config.get('execution', {})
                click.echo(f'  Auto-shutdown: {exec_config.get("autoShutdownAtDate", shutdown_at_parsed)}')
        if parsed_data_files:
            click.echo(f'\n  {len(parsed_data_files)} additional file(s) mounted')
        if parsed_s3_mounts:
            click.echo(f'  {len(parsed_s3_mounts)} additional folder(s) linked')
        click.echo(f'\nSession status: {response.get("status", "unknown")}')
        click.secho(f'\nTip: Check session status with: cloudos interactive-session status --session-id {session_id}', fg='yellow')

    except BadRequestException as e:
        error_str = str(e)
        # Check for specific error patterns
        if '401' in error_str or 'Unauthorized' in error_str:
            click.secho(f'Error: Failed to resume session. Please check your credentials.', fg='red', err=True)
        elif '404' in error_str or 'not found' in error_str.lower():
            click.secho(f'Error: Session not found. Please check the session ID.', fg='red', err=True)
        elif 'not in a resumable status' in error_str.lower():
            # Try to fetch the current session status to show the user
            try:
                from cloudos_cli.interactive_session.interactive_session import get_interactive_session_status, map_status
                status_response = get_interactive_session_status(
                    cloudos_url=cloudos_url,
                    apikey=apikey,
                    session_id=session_id,
                    team_id=workspace_id,
                    verify_ssl=verify_ssl,
                    verbose=False
                )
                current_status = map_status(status_response.get('status', 'unknown'))
                click.secho(f'Error: Cannot resume session - current status is "{current_status}".', fg='red', err=True)
                click.secho(f'Only sessions with status "paused" can be resumed.', fg='yellow', err=True)
                if current_status == 'running':
                    click.secho(f'Tip: This session is already running. Use the Lifebit Platform web interface to access it.', fg='yellow', err=True)
                elif current_status == 'terminated':
                    click.secho(f'Tip: Terminated sessions cannot be resumed. Please create a new session instead.', fg='yellow', err=True)
                else:
                    click.secho(f'Tip: Wait for the session to reach "paused" status, or check: cloudos interactive-session status --session-id {session_id}', fg='yellow', err=True)
            except:
                # Fallback if we can't fetch status
                click.secho(f'Error: Cannot resume session - it is not in a resumable status.', fg='red', err=True)
                click.secho(f'Only sessions with status "paused" can be resumed.', fg='yellow', err=True)
                click.secho(f'Tip: Check current status with: cloudos interactive-session status --session-id {session_id}', fg='yellow', err=True)
        elif 'already running' in error_str.lower() or 'ready' in error_str.lower():
            click.secho(f'Error: Cannot resume session - the session is already running.', fg='red', err=True)
            click.secho(f'Tip: Check status with: cloudos interactive-session status --session-id {session_id}', fg='yellow', err=True)
        else:
            click.secho(f'Error: Failed to resume session: {str(e)}', fg='red', err=True)
        raise SystemExit(1)

    except Exception as e:
        error_str = str(e)
        # Check for network errors
        if 'Failed to resolve' in error_str or 'Name or service not known' in error_str:
            click.secho(f'Error: Unable to connect to Lifebit Platform. Please verify the Lifebit Platform URL is correct.', fg='red', err=True)
        elif '401' in error_str or 'Unauthorized' in error_str:
            click.secho(f'Error: Failed to resume session. Please check your credentials.', fg='red', err=True)
        else:
            click.secho(f'Error: Failed to resume session: {str(e)}', fg='red', err=True)
        raise SystemExit(1)


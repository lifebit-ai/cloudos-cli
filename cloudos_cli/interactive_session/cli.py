"""CLI commands for CloudOS interactive session management."""

import rich_click as click
import json
from cloudos_cli.clos import Cloudos
from cloudos_cli.utils.errors import BadRequestException
from cloudos_cli.utils.resources import ssl_selector
from cloudos_cli.utils.details import create_job_list_table
from cloudos_cli.interactive_session.interactive_session import (
    create_interactive_session_list_table,
    process_interactive_session_list,
    save_interactive_session_list_to_csv
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
              type=click.Choice(['running', 'stopped', 'provisioning', 'scheduled'], case_sensitive=False),
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
            if output_format == 'stdout':
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
        click.secho(f'Error: Failed to retrieve interactive sessions: {e}', fg='red', err=True)
        raise SystemExit(1)
    except Exception as e:
        click.secho(f'Error: {str(e)}', fg='red', err=True)
        raise SystemExit(1)

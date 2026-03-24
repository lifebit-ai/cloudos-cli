"""Interactive session helper functions for CloudOS."""

import pandas as pd
import sys
import re
import json
import time
from datetime import datetime, timedelta, timezone
from rich.table import Table
from rich.console import Console
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from cloudos_cli.utils.requests import retry_requests_get



def validate_instance_type(instance_type, execution_platform='aws'):
    """Validate instance type format for the given execution platform.
    
    Parameters
    ----------
    instance_type : str
        Instance type to validate
    execution_platform : str
        'aws' or 'azure'
    
    Returns
    -------
    tuple
        (is_valid: bool, error_message: str or None)
    """
    if not instance_type or not isinstance(instance_type, str):
        return False, "Instance type must be a non-empty string"
    
    if execution_platform == 'aws':
        # AWS EC2 instance format: <family><generation>.<size>
        # Examples: c5.xlarge, m5.2xlarge, r6i.large, t3.medium, g4dn.xlarge
        # Family: c, m, r, t, g, p, i, d, x, z, h, etc. (1-4 chars)
        # Generation: digit(s) optionally followed by letter(s) for variants
        # Size: nano, micro, small, medium, large, xlarge, 2xlarge, 4xlarge, etc.
        aws_pattern = r'^[a-z]{1,4}\d+[a-z]*\.(\d+)?(nano|micro|small|medium|large|xlarge|metal)$'
        
        if not re.match(aws_pattern, instance_type, re.IGNORECASE):
            return False, (f"Invalid AWS instance type format: '{instance_type}'. "
                          f"Expected format: <family><generation>.<size> (e.g., c5.xlarge, m5.2xlarge)")
    
    elif execution_platform == 'azure':
        # Azure VM format: Standard_<series><version>_<size> or Basic_<series><version>
        # Examples: Standard_F1s, Standard_D4as_v4, Standard_B2ms, Basic_A1
        azure_pattern = r'^(Standard|Basic)_[A-Z]\d+[a-z]*(_v\d+)?$'
        
        if not re.match(azure_pattern, instance_type):
            return False, (f"Invalid Azure instance type format: '{instance_type}'. "
                          f"Expected format: Standard_<series><size> (e.g., Standard_F1s, Standard_D4as_v4)")
    
    else:
        # Unknown platform - skip validation
        return True, None
    
    return True, None


def _map_session_type_to_friendly_name(session_type):
    """Map internal session type names to user-friendly display names.
    
    Parameters
    ----------
    session_type : str
        Internal session type (e.g., 'awsJupyterNotebook')
    
    Returns
    -------
    str
        User-friendly type name (e.g., 'Jupyter')
    """
    type_mapping = {
        'awsJupyterNotebook': 'Jupyter',
        'azureJupyterNotebook': 'Jupyter',
        'awsVSCode': 'VS Code',
        'azureVSCode': 'VS Code',
        'awsRstudio': 'RStudio',
        'azureRstudio': 'RStudio',
        'awsSpark': 'Spark',
        'awsJupyterSparkNotebook': 'Spark',
        'azureJupyterSparkNotebook': 'Spark',
        'azureSpark': 'Spark',
        'awsRStudio': 'RStudio',  # Handle both capitalizations
        'azureRStudio': 'RStudio'
    }
    return type_mapping.get(session_type, session_type)


def create_interactive_session_list_table(sessions, pagination_metadata=None, selected_columns=None, page_size=10, fetch_page_callback=None):
    """Create a rich table displaying interactive sessions with interactive pagination.
    
    Parameters
    ----------
    sessions : list
        List of session objects from the API
    pagination_metadata : dict, optional
        Pagination information from the API response
    selected_columns : str or list, optional
        Comma-separated string or list of column names to display.
        If None, uses responsive column selection based on terminal width.
        Available columns: id, name, status, type, instance, cost, owner
    page_size : int, optional
        Number of sessions per page for interactive pagination. Default=10.
    fetch_page_callback : callable, optional
        Callback function to fetch a specific page of results.
        Should accept page number (1-indexed) and return dict with 'sessions' and 'pagination_metadata' keys.
    """
    console = Console()
    
    # Define all available columns with their configuration
    all_columns = {
        'id': {
            'header': 'ID',
            'style': 'cyan',
            'no_wrap': True,
            'max_width': 24,
            'accessor': '_id'
        },
        'name': {
            'header': 'Name',
            'style': 'green',
            'overflow': 'ellipsis',
            'max_width': 25,
            'accessor': 'name'
        },
        'status': {
            'header': 'Status',
            'style': 'yellow',
            'no_wrap': True,
            'max_width': 12,
            'accessor': 'status'
        },
        'type': {
            'header': 'Type',
            'style': 'magenta',
            'overflow': 'fold',
            'max_width': 20,
            'accessor': 'interactiveSessionType'
        },
        'instance': {
            'header': 'Instance',
            'style': 'cyan',
            'overflow': 'ellipsis',
            'max_width': 15,
            'accessor': 'resources.instanceType'
        },
        'cost': {
            'header': 'Cost',
            'style': 'green',
            'no_wrap': True,
            'max_width': 12,
            'accessor': 'totalCostInUsd'
        },
        'owner': {
            'header': 'Owner',
            'style': 'white',
            'overflow': 'ellipsis',
            'max_width': 20,
            'accessor': 'user.name'
        },
        'project': {
            'header': 'Project',
            'style': 'cyan',
            'overflow': 'ellipsis',
            'max_width': 20,
            'accessor': 'project.name'
        },
        'created_at': {
            'header': 'Created At',
            'style': 'white',
            'overflow': 'ellipsis',
            'max_width': 20,
            'accessor': 'createdAt'
        },
        'runtime': {
            'header': 'Total Running Time',
            'style': 'white',
            'no_wrap': True,
            'max_width': 18,
            'accessor': 'totalRunningTimeInSeconds'
        },
        'saved_at': {
            'header': 'Last Time Saved',
            'style': 'white',
            'overflow': 'ellipsis',
            'max_width': 20,
            'accessor': 'lastSavedAt'
        },
        'resources': {
            'header': 'Resources',
            'style': 'cyan',
            'overflow': 'ellipsis',
            'max_width': 30,
            'accessor': 'resources.instanceType'
        },
        'backend': {
            'header': 'Backend',
            'style': 'magenta',
            'overflow': 'fold',
            'max_width': 15,
            'accessor': 'interactiveSessionType'
        },
        'version': {
            'header': 'Version',
            'style': 'white',
            'no_wrap': True,
            'max_width': 15,
            'accessor': 'rVersion'
        },
        'spot': {
            'header': 'Spot',
            'style': 'cyan',
            'no_wrap': True,
            'max_width': 6,
            'accessor': 'resources.isCostSaving'
        },
        'cost_limit': {
            'header': 'Cost Limit Left',
            'style': 'yellow',
            'no_wrap': True,
            'max_width': 15,
            'accessor': 'execution'
        },
        'time_left': {
            'header': 'Time Until Shutdown',
            'style': 'magenta',
            'no_wrap': True,
            'max_width': 20,
            'accessor': 'execution.autoShutdownAtDate'
        }
    }
    
    # Determine columns to display
    if selected_columns:
        if isinstance(selected_columns, str):
            selected_columns = [col.strip() for col in selected_columns.split(',')]
        columns_to_show = selected_columns
    else:
        # Responsive column selection based on terminal width
        terminal_width = console.width
        if terminal_width < 60:
            columns_to_show = ['status', 'name', 'id']
        elif terminal_width < 90:
            columns_to_show = ['status', 'name', 'type', 'id', 'owner']
        elif terminal_width < 130:
            columns_to_show = ['status', 'name', 'type', 'instance', 'cost', 'id', 'owner']
        else:
            columns_to_show = ['id', 'name', 'status', 'type', 'instance', 'cost', 'owner']
    
    # Handle empty results
    if len(sessions) == 0:
        console.print('[yellow]No interactive sessions found.[/yellow]')
        return
    
    # Prepare rows data
    rows = []
    for session in sessions:
        row_data = []
        for col_name in columns_to_show:
            if col_name not in all_columns:
                continue
            col_config = all_columns[col_name]
            accessor = col_config['accessor']
            
            # Extract value from session object
            value = _get_nested_value(session, accessor)
            
            # Format the value
            formatted_value = _format_session_field(col_name, value)
            row_data.append(formatted_value)
        
        rows.append(row_data)
    
    # Interactive pagination - use API pagination metadata if available
    if pagination_metadata:
        # Server-side pagination
        current_api_page = pagination_metadata.get('page', 1)
        total_sessions = pagination_metadata.get('count', len(sessions))
        total_pages = pagination_metadata.get('totalPages', 1)
    else:
        # Client-side pagination (fallback)
        current_api_page = 0
        total_sessions = len(sessions)
        total_pages = (len(sessions) + page_size - 1) // page_size if len(sessions) > 0 else 1
    
    show_error = None  # Track error messages to display

    while True:
        # For client-side pagination, start/end are indices into the local rows array
        # For server-side pagination, we use the API page directly
        if fetch_page_callback and pagination_metadata:
            # Server-side pagination - sessions list contains current page data
            page_rows = rows[:]  # All rows are from current page
        else:
            # Client-side pagination
            start = current_api_page * page_size
            end = start + page_size
            page_rows = rows[start:end]

        # Clear console first
        console.clear()

        # Create table
        table = Table(title='Interactive Sessions')
        
        # Add columns to table
        for col_name in columns_to_show:
            if col_name not in all_columns:
                continue
            col_config = all_columns[col_name]
            table.add_column(
                col_config['header'],
                style=col_config.get('style', 'white'),
                no_wrap=col_config.get('no_wrap', False)
            )

        # Add rows to table
        for row in page_rows:
            table.add_row(*row)

        # Print table
        console.print(table)

        # Display pagination info
        console.print(f"\n[cyan]Total sessions:[/cyan] {total_sessions}")
        if total_pages > 1:
            console.print(f"[cyan]Page:[/cyan] {current_api_page} of {total_pages}")
            console.print(f"[cyan]Sessions on this page:[/cyan] {len(page_rows)}")

        # Show error message if any
        if show_error:
            console.print(show_error)
            show_error = None  # Reset error after displaying

        # Show pagination controls
        if total_pages > 1:
            # Check if we're in an interactive environment
            if not sys.stdin.isatty():
                console.print("\n[yellow]Note: Pagination not available in non-interactive mode. Showing page 1 of {0}.[/yellow]".format(total_pages))
                console.print("[yellow]Run in an interactive terminal to navigate through all pages.[/yellow]")
                break
            
            console.print(f"\n[bold cyan]n[/] = next, [bold cyan]p[/] = prev, [bold cyan]q[/] = quit")

            # Get user input for navigation
            try:
                choice = input(">>> ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                # Handle non-interactive environments or user interrupt
                console.print("\n[yellow]Pagination interrupted.[/yellow]")
                break

            if choice in ("q", "quit"):
                break
            elif choice in ("n", "next"):
                if current_api_page < total_pages:
                    # Try to fetch the next page
                    if fetch_page_callback:
                        try:
                            next_page_data = fetch_page_callback(current_api_page + 1)
                            sessions = next_page_data.get('sessions', [])
                            pagination_metadata = next_page_data.get('pagination_metadata', {})
                            current_api_page = pagination_metadata.get('page', current_api_page + 1)
                            total_pages = pagination_metadata.get('totalPages', total_pages)
                            
                            # Rebuild rows for the new page
                            rows = []
                            for session in sessions:
                                row_data = []
                                for col_name in columns_to_show:
                                    if col_name not in all_columns:
                                        continue
                                    col_config = all_columns[col_name]
                                    accessor = col_config['accessor']
                                    value = _get_nested_value(session, accessor)
                                    formatted_value = _format_session_field(col_name, value)
                                    row_data.append(formatted_value)
                                rows.append(row_data)
                        except Exception as e:
                            show_error = f"[red]Error fetching next page: {str(e)}[/red]"
                    else:
                        current_api_page += 1
                else:
                    show_error = "[red]Invalid choice. Already on the last page.[/red]"
            elif choice in ("p", "prev"):
                if current_api_page > 1:
                    # Try to fetch the previous page
                    if fetch_page_callback:
                        try:
                            prev_page_data = fetch_page_callback(current_api_page - 1)
                            sessions = prev_page_data.get('sessions', [])
                            pagination_metadata = prev_page_data.get('pagination_metadata', {})
                            current_api_page = pagination_metadata.get('page', current_api_page - 1)
                            total_pages = pagination_metadata.get('totalPages', total_pages)
                            
                            # Rebuild rows for the new page
                            rows = []
                            for session in sessions:
                                row_data = []
                                for col_name in columns_to_show:
                                    if col_name not in all_columns:
                                        continue
                                    col_config = all_columns[col_name]
                                    accessor = col_config['accessor']
                                    value = _get_nested_value(session, accessor)
                                    formatted_value = _format_session_field(col_name, value)
                                    row_data.append(formatted_value)
                                rows.append(row_data)
                        except Exception as e:
                            show_error = f"[red]Error fetching previous page: {str(e)}[/red]"
                    else:
                        current_api_page -= 1
                else:
                    show_error = "[red]Invalid choice. Already on the first page.[/red]"
            else:
                show_error = "[red]Invalid choice. Please enter 'n' (next), 'p' (prev), or 'q' (quit).[/red]"
        else:
            # Only one page, no need for input, just exit
            break



def process_interactive_session_list(sessions, all_fields=False):
    """Process interactive sessions data into a pandas DataFrame.
    
    Parameters
    ----------
    sessions : list
        List of session objects from the API
    all_fields : bool, default=False
        If True, include all fields from the API response.
        If False, include only the most relevant fields.
    
    Returns
    -------
    df : pandas.DataFrame
        DataFrame with session data
    """
    if all_fields:
        # Return all fields from the API response
        df = pd.json_normalize(sessions)
    else:
        # Return only selected fields
        rows = []
        for session in sessions:
            # Get user info (API uses 'name' and 'surname', not 'firstName' and 'lastName')
            user_obj = session.get('user', {})
            user_name = ''
            if user_obj:
                first_name = user_obj.get('name', '')
                last_name = user_obj.get('surname', '')
                user_name = f'{first_name} {last_name}'.strip()
            
            row = {
                '_id': session.get('_id', ''),
                'name': session.get('name', ''),
                'status': session.get('status', ''),
                'interactiveSessionType': _map_session_type_to_friendly_name(session.get('interactiveSessionType', '')),
                'user': user_name,
                'instanceType': session.get('resources', {}).get('instanceType', ''),
                'totalCostInUsd': session.get('totalCostInUsd', 0),
            }
            rows.append(row)
        df = pd.DataFrame(rows)
    
    return df


def _get_nested_value(obj, path):
    """Get a nested value from an object using dot notation.
    
    Parameters
    ----------
    obj : dict
        The object to extract from
    path : str
        Dot-separated path (e.g., 'user.firstName')
    
    Returns
    -------
    value
        The value at the path, or empty string if not found
    """
    parts = path.split('.')
    value = obj
    for part in parts:
        if isinstance(value, dict):
            value = value.get(part)
        else:
            return ''
    return value if value is not None else ''


def _format_session_field(field_name, value):
    """Format a session field for display.
    
    Parameters
    ----------
    field_name : str
        The name of the field
    value
        The value to format
    
    Returns
    -------
    str
        The formatted value
    """
    if value == '' or value is None:
        return '-'
    
    if field_name == 'status':
        # Color code status and map display values
        status_lower = str(value).lower()
        # Map API statuses to display values
        # API 'ready' and 'aborted' are mapped to user-friendly names
        display_status = 'running' if status_lower == 'ready' else ('stopped' if status_lower == 'aborted' else value)
        
        if status_lower in ['ready', 'running']:
            return f'[bold green]{display_status}[/bold green]'
        elif status_lower in ['stopped', 'aborted']:
            return f'[bold red]{display_status}[/bold red]'
        elif status_lower in ['setup', 'initialising', 'initializing', 'scheduled']:
            return f'[bold yellow]{display_status}[/bold yellow]'
        else:
            return str(display_status)
    
    elif field_name == 'cost':
        # Format cost with currency symbol
        try:
            cost = float(value)
            return f'${cost:.2f}'
        except (ValueError, TypeError):
            return str(value)
    
    elif field_name == 'id':
        # Return full ID without truncation (MongoDB ObjectIds are always 24 chars)
        # Full ID is needed for status command and other operations
        return str(value)
    
    elif field_name == 'name':
        # Truncate long names
        value_str = str(value)
        if len(value_str) > 25:
            return value_str[:22] + '…'
        return value_str
    
    elif field_name == 'runtime':
        # Convert seconds to human-readable format (e.g., "1h 52m 52s")
        try:
            total_seconds = int(float(value))
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            if hours > 0:
                return f'{hours}h {minutes}m {seconds}s'
            elif minutes > 0:
                return f'{minutes}m {seconds}s'
            else:
                return f'{seconds}s'
        except (ValueError, TypeError):
            return str(value)
    
    elif field_name == 'created_at' or field_name == 'saved_at':
        # Format ISO8601 datetime to readable format
        try:
            dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d %H:%M')
        except (ValueError, TypeError, ImportError):
            return str(value)[:19] if value else '-'
    
    elif field_name == 'version':
        # Version is only available for RStudio sessions
        if value and str(value).lower() != 'none':
            return f'R {value}'
        return '-'
    
    elif field_name == 'type':
        # Map internal type names to user-friendly names
        return _map_session_type_to_friendly_name(str(value))
    
    elif field_name == 'spot':
        # Indicate if instance is cost-saving (spot)
        if value is True:
            return '[bold cyan]Yes[/bold cyan]'
        elif value is False:
            return 'No'
        else:
            return '-'
    
    elif field_name == 'cost_limit':
        # Calculate remaining cost limit (execution object contains computeCostLimit and computeCostSpent)
        if isinstance(value, dict):
            cost_limit = value.get('computeCostLimit', -1)
            cost_spent = value.get('computeCostSpent', 0)
            
            # -1 means unlimited
            if cost_limit == -1:
                return 'Unlimited'
            
            try:
                remaining = float(cost_limit) - float(cost_spent)
                if remaining < 0:
                    remaining = 0
                return f'${remaining:.2f}'
            except (ValueError, TypeError):
                return '-'
        return '-'
    
    elif field_name == 'time_left':
        # Calculate time until auto-shutdown
        if value and value != 'null' and str(value).strip():
            try:
                shutdown_time = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
                now = datetime.now(timezone.utc)
                
                if shutdown_time > now:
                    time_diff = shutdown_time - now
                    total_seconds = int(time_diff.total_seconds())
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    
                    if hours > 24:
                        days = hours // 24
                        remaining_hours = hours % 24
                        return f'{days}d {remaining_hours}h'
                    elif hours > 0:
                        return f'{hours}h {minutes}m'
                    else:
                        return f'{minutes}m'
                else:
                    return '[red]Expired[/red]'
            except (ValueError, TypeError, ImportError):
                return '-'
        return '-'
    
    return str(value)


def save_interactive_session_list_to_csv(df, outfile, count=None):
    """Save interactive session list to CSV file.
    
    Parameters
    ----------
    df : pandas.DataFrame
        The session data to save
    outfile : str
        Path to the output CSV file
    count : int, optional
        Total number of sessions on this page for display message
    """
    df.to_csv(outfile, index=False)
    if count is not None:
        print(f'\tInteractive session list collected with a total of {count} sessions on this page.')
    print(f'\tInteractive session list saved to {outfile}')


def parse_shutdown_duration(duration_str):
    """Parse shutdown duration string to ISO8601 datetime string.
    
    Accepts formats: 30m, 2h, 8h, 1d, 2d
    
    Parameters
    ----------
    duration_str : str
        Duration string (e.g., "2h", "30m", "1d")
    
    Returns
    -------
    str
        ISO8601 formatted datetime string (future time)
    """
    match = re.match(r'^(\d+)([mhd])$', duration_str.lower())
    if not match:
        raise ValueError(f"Invalid duration format: {duration_str}. Use format like '2h', '30m', '1d'")
    
    value = int(match.group(1))
    unit = match.group(2)
    
    if unit == 'm':
        delta = timedelta(minutes=value)
    elif unit == 'h':
        delta = timedelta(hours=value)
    elif unit == 'd':
        delta = timedelta(days=value)
    future_time = datetime.now(timezone.utc) + delta
    return future_time.isoformat().replace('+00:00', 'Z')

def parse_watch_timeout_duration(duration_str):
    """Parse watch timeout duration string to seconds.
    
    Accepts formats: 30m, 2h, 1d, 30s
    
    Parameters
    ----------
    duration_str : str
        Duration string (e.g., "30m", "2h", "1d", "30s")
    
    Returns
    -------
    int
        Duration in seconds
    """
    match = re.match(r'^(\d+)([smhd])$', duration_str.lower())
    if not match:
        raise ValueError(f"Invalid duration format: {duration_str}. Use format like '30s', '30m', '2h', '1d'")
    
    value = int(match.group(1))
    unit = match.group(2)
    
    if unit == 's':
        return value
    elif unit == 'm':
        return value * 60
    elif unit == 'h':
        return value * 3600
    elif unit == 'd':
        return value * 86400

def parse_data_file(data_file_str):
    """Parse data file format: either S3 or CloudOS dataset path.
    
    Supports mounting both S3 files and CloudOS dataset files into the session.
    
    Parameters
    ----------
    data_file_str : str
        Format:
        - S3 file: s3://bucket_name/path/to/file.txt
        - CloudOS dataset: project_name/dataset_path or project_name > dataset_path
        
        Examples:
        - s3://lifebit-featured-datasets/pipelines/phewas/data.csv
        - leila-test/Data/3_vcf_list.txt
    
    Returns
    -------
    dict
        Parsed data item. For S3:
        {"type": "s3", "s3_bucket": "...", "s3_prefix": "..."}
        
        For CloudOS dataset:
        {"type": "cloudos", "project_name": "...", "dataset_path": "..."}
    
    Raises
    ------
    ValueError
        If format is invalid
    """
    # Check if it's an S3 path
    if data_file_str.startswith('s3://'):
        # Parse S3 path: s3://bucket/prefix/file
        s3_path = data_file_str[5:]  # Remove 's3://'
        parts = s3_path.split('/', 1)
        
        bucket = parts[0]
        if not bucket:
            raise ValueError(f"Invalid S3 path: {data_file_str}. Expected: s3://bucket_name/path/to/file")
        
        prefix = parts[1] if len(parts) > 1 else "/"
        
        return {
            "type": "s3",
            "s3_bucket": bucket,
            "s3_prefix": prefix
        }
    
    # Otherwise, parse as CloudOS dataset path
    # Determine which separator to use: > takes precedence over /
    separator = None
    if '>' in data_file_str:
        separator = '>'
    elif '/' in data_file_str:
        separator = '/'
    else:
        raise ValueError(
            f"Invalid data file format: {data_file_str}. Expected one of:\n"
            f"  - S3 file: s3://bucket/path/file.txt\n"
            f"  - CloudOS dataset: project_name/dataset_path or project_name > dataset_path"
        )
    
    # Split only on the first separator to handle nested paths
    parts = data_file_str.split(separator, 1)
    if len(parts) != 2:
        raise ValueError(f"Invalid data file format: {data_file_str}. Expected: project_name/dataset_path where dataset_path can be nested")
    
    project_name, dataset_path = parts
    return {
        "type": "cloudos",
        "project_name": project_name.strip(),
        "dataset_path": dataset_path.strip()
    }


def resolve_data_file_id(datasets_api, dataset_path: str) -> dict:
    """Resolve nested dataset path to actual file ID.
    
    Searches across all datasets in the project to find the target file.
    This allows paths like 'Data/file.txt' to work even if 'Data' is a folder
    within a dataset (not a dataset name itself).
    
    Parameters
    ----------
    datasets_api : Datasets
        Initialized Datasets API instance (with correct project_name)
    dataset_path : str
        Nested path to file within the project (e.g., 'Data/file.txt' or 'Folder/subfolder/file.txt')
        Can start with a dataset name or a folder name within any dataset.
    
    Returns
    -------
    dict
        Data item object with resolved file ID:
        {"kind": "File", "item": "<fileId>", "name": "<fileName>"}
    
    Raises
    ------
    ValueError
        If file not found in any dataset/folder
    """
    try:
        path_parts = dataset_path.strip('/').split('/')
        file_name = path_parts[-1]
        
        # First, try the path as-is (assuming first part is a dataset name)
        try:
            result = datasets_api.list_folder_content(dataset_path)
            
            # Check if it's in the files list
            for file_item in result.get('files', []):
                if file_item.get('name') == file_name:
                    return {
                        "kind": "File",
                        "item": file_item.get('_id'),
                        "name": file_item.get('name')
                    }
            # If we got here, quick path didn't work, continue to search
        except (Exception):
            # First path attempt failed, try searching across all datasets
            pass
        
        # If the quick path didn't work, search across all datasets
        # This handles the case where the first part is a folder, not a dataset name
        project_content = datasets_api.list_project_content()
        datasets = project_content.get('folders', [])
        
        if not datasets:
            raise ValueError(f"No datasets found in project. Cannot locate path '{dataset_path}'")
        
        # Try to find the file in each dataset
        found_files = []
        for dataset in datasets:
            dataset_name = dataset.get('name')
            try:
                # Try with the dataset name prepended to the path
                full_path = f"{dataset_name}/{dataset_path}"
                result = datasets_api.list_folder_content(full_path)
                
                # Check files list
                for file_item in result.get('files', []):
                    if file_item.get('name') == file_name:
                        found_files.append({
                            "kind": "File",
                            "item": file_item.get('_id'),
                            "name": file_item.get('name')
                        })
                        # Return first match (most direct path)
                        return found_files[0]
            except Exception:
                # This dataset doesn't contain the path, continue
                continue
        
        # Also try searching without dataset prefix (path is from root of datasets)
        for dataset in datasets:
            try:
                dataset_name = dataset.get('name')
                # List what's in this dataset at the top level
                dataset_content = datasets_api.list_datasets_content(dataset_name)
                
                # Check if the target file is directly in this dataset's files
                for file_item in dataset_content.get('files', []):
                    if file_item.get('name') == file_name:
                        found_files.append({
                            "kind": "File",
                            "item": file_item.get('_id'),
                            "name": file_item.get('name')
                        })
                
                # Check folders and navigate if needed
                for folder in dataset_content.get('folders', []):
                    if folder.get('name') == path_parts[0]:
                        # This dataset has the target folder
                        full_path = f"{dataset_name}/{dataset_path}"
                        try:
                            result = datasets_api.list_folder_content(full_path)
                            for file_item in result.get('files', []):
                                if file_item.get('name') == file_name:
                                    return {
                                        "kind": "File",
                                        "item": file_item.get('_id'),
                                        "name": file_item.get('name')
                                    }
                        except Exception:
                            continue
            except Exception:
                continue
        
        # If we found files, return the first one
        if found_files:
            return found_files[0]
        
        # Nothing found - provide helpful error message
        available_datasets = [d.get('name') for d in datasets]
        raise ValueError(
            f"File at path '{dataset_path}' not found in any dataset. "
            f"Available datasets: {available_datasets}. "
            f"Try using 'cloudos datasets ls' to explore your data structure."
        )
    
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Error resolving dataset file at path '{dataset_path}': {str(e)}")


def parse_link_path(link_path_str):
    """Parse link path format: supports S3, CloudOS, or legacy colon format.
    
    Links an S3 folder or CloudOS folder to the session for read/write access.
    
    Parameters
    ----------
    link_path_str : str
        Format (one of):
        - S3 path: s3://bucketName/s3Prefix (e.g., s3://my-bucket/data/)
        - CloudOS folder: project/folder_path (e.g., leila-test/Data)
        - Legacy format (deprecated): mountName:bucketName:s3Prefix
    
    Returns
    -------
    dict
        Tuple of (type, data) where type is 's3' or 'cloudos' and data contains:
        For S3: {"s3_bucket": "...", "s3_prefix": "..."}
        For CloudOS: {"project_name": "...", "folder_path": "..."}
    """
    # Check for Azure blob storage paths and provide helpful error
    if link_path_str.startswith('az://') or link_path_str.startswith('https://') and '.blob.core.windows.net' in link_path_str:
        raise ValueError(
            f"Azure blob storage paths are not supported for linking. "
            f"Folder linking is not supported on Azure execution platforms. "
            f"Please use CloudOS file explorer to access your data directly."
        )
    
    # Check for S3 path
    if link_path_str.startswith('s3://'):
        # Parse S3 path: s3://bucket/prefix
        s3_path = link_path_str[5:]  # Remove 's3://'
        parts = s3_path.split('/', 1)
        
        if len(parts) < 1:
            raise ValueError(f"Invalid S3 path: {link_path_str}. Expected: s3://bucket_name/prefix/")
        
        bucket = parts[0]
        prefix = parts[1] if len(parts) > 1 else ""
        
        # Ensure prefix ends with / for S3 folders
        if prefix and not prefix.endswith('/'):
            prefix = prefix + '/'
        
        return {
            "type": "s3",
            "s3_bucket": bucket,
            "s3_prefix": prefix
        }
    
    # Check for legacy colon format
    if ':' in link_path_str and '//' not in link_path_str:
        # Legacy format: mountName:bucketName:s3Prefix
        parts = link_path_str.split(':')
        if len(parts) != 3:
            raise ValueError(f"Invalid link format: {link_path_str}. Expected: mountName:bucketName:s3Prefix")
        
        mount_name, bucket, prefix = parts
        
        # Ensure prefix ends with /
        if prefix and not prefix.endswith('/'):
            prefix = prefix + '/'
        
        return {
            "type": "s3",
            "mount_name": mount_name,
            "s3_bucket": bucket,
            "s3_prefix": prefix
        }
    
    # Otherwise, parse as CloudOS folder path
    # Format: project_name/folder_path or project_name > folder_path
    separator = None
    if '>' in link_path_str:
        separator = '>'
    elif '/' in link_path_str:
        separator = '/'
    else:
        raise ValueError(
            f"Invalid link path format: {link_path_str}. Expected one of:\n"
            f"  - S3 path: s3://bucket/prefix/\n"
            f"  - CloudOS folder: project/folder/path\n"
            f"  - Legacy format (deprecated): mountName:bucketName:prefix"
        )
    
    parts = link_path_str.split(separator, 1)
    if len(parts) != 2:
        raise ValueError(f"Invalid link path: {link_path_str}")
    
    project_name, folder_path = parts
    return {
        "type": "cloudos",
        "project_name": project_name.strip(),
        "folder_path": folder_path.strip()
    }



def build_session_payload(
    name,
    backend,
    project_id,
    execution_platform='aws',
    instance_type='c5.xlarge',
    storage_size=500,
    is_spot=False,
    is_shared=False,
    cost_limit=-1,
    shutdown_at=None,
    data_files=None,
    s3_mounts=None,
    r_version=None,
    spark_master_type=None,
    spark_core_type=None,
    spark_workers=1
):
    """Build the complex session creation payload for the API.
    
    Parameters
    ----------
    name : str
        Session name (1-100 characters)
    backend : str
        Backend type: regular, vscode, spark, rstudio
    project_id : str
        Project MongoDB ObjectId
    execution_platform : str, optional
        Execution platform: 'aws' (default) or 'azure'
    instance_type : str
        Instance type (EC2 for AWS, e.g., c5.xlarge; Azure VM size, e.g., Standard_F1s)
    storage_size : int
        Storage in GB (default: 500, range: 100-5000)
    is_spot : bool
        Use spot instances (AWS only, default: False)
    is_shared : bool
        Make session shared (default: False)
    cost_limit : float
        Compute cost limit in USD (default: -1 for unlimited)
    shutdown_at : str
        ISO8601 datetime for auto-shutdown (optional)
    data_files : list
        List of data file dicts. For AWS: CloudOS or S3. For Azure: CloudOS only.
    s3_mounts : list
        List of S3 mount dicts (AWS only, ignored for Azure)
    r_version : str
        R version for RStudio (required for rstudio backend)
    spark_master_type : str
        Spark master instance type (required for spark backend, AWS only)
    spark_core_type : str
        Spark core instance type (required for spark backend, AWS only)
    spark_workers : int
        Initial number of Spark workers (default: 1, AWS only)
    
    Returns
    -------
    dict
        Complete payload for API request
    """
    # Validate inputs
    if not 1 <= len(name) <= 100:
        raise ValueError("Session name must be 1-100 characters")
    
    if not 100 <= storage_size <= 5000:
        raise ValueError("Storage size must be between 100-5000 GB")
    
    if backend not in ['regular', 'vscode', 'spark', 'rstudio']:
        raise ValueError("Invalid backend type")
    
    if execution_platform not in ['aws', 'azure']:
        raise ValueError("Execution platform must be 'aws' or 'azure'")
    
    # Spark is AWS only
    if backend == 'spark' and execution_platform != 'aws':
        raise ValueError("Spark backend is only available on AWS")
    
    if backend == 'rstudio' and not r_version:
        raise ValueError("R version (--r-version) is required for RStudio backend")
    
    if backend == 'spark' and (not spark_master_type or not spark_core_type):
        raise ValueError("Spark master and core instance types are required for Spark backend")
    
    # Default shutdown to 24 hours if not provided
    if not shutdown_at:
        shutdown_at = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat().replace('+00:00', 'Z')
    
    # Build interactiveSessionConfiguration
    config = {
        "name": name,
        "backend": backend,
        "executionPlatform": execution_platform,
        "instanceType": instance_type,
        "isCostSaving": is_spot,
        "storageSizeInGb": storage_size,
        "storageMode": "regular",
        "visibility": "workspace" if is_shared else "private",
        "execution": {
            "computeCostLimit": cost_limit,
            "autoShutdownAtDate": shutdown_at
        }
    }
    
    # Add backend-specific fields
    if backend == 'rstudio':
        config['rVersion'] = r_version
    
    if backend == 'spark':
        master_type = spark_master_type
        core_type = spark_core_type
        
        config['cluster'] = {
            "name": f"{name}-cluster",
            "releaseLabel": "emr-7.3.0",
            "ebsRootVolumeSizeInGb": 100,
            "instances": {
                "master": {
                    "type": master_type,
                    "costSaving": is_spot,
                    "storage": {
                        "type": "gp2",
                        "sizeInGbs": 50,
                        "volumesPerInstance": 1
                    }
                },
                "core": {
                    "type": core_type,
                    "costSaving": is_spot,
                    "storage": {
                        "type": "gp2",
                        "sizeInGbs": 50,
                        "volumesPerInstance": 1
                    },
                    "minNumberOfInstances": spark_workers,
                    "autoscaling": {
                        "minCapacity": spark_workers,
                        "maxCapacity": max(spark_workers * 2, 10)
                    }
                },
                "tasks": []
            },
            "autoscaling": {
                "minCapacity": spark_workers,
                "maxCapacity": max(spark_workers * 2, 10)
            },
            "id": None
        }
    
    # Build complete payload
    # For Azure, S3 mounts are not supported (fuseFileSystems should be empty)
    payload = {
        "interactiveSessionConfiguration": config,
        "dataItems": data_files or [],
        "fileSystemIds": [],  # Always empty (legacy compatibility)
        "fuseFileSystems": s3_mounts or [] if execution_platform == 'aws' else [],
        "projectId": project_id
    }
    
    return payload


def format_session_creation_table(session_data, instance_type=None, storage_size=None,
                                  backend_type=None, r_version=None,
                                  spark_master=None, spark_core=None, spark_workers=None,
                                  data_files=None, s3_mounts=None):
    """Display session creation result in table format.
    
    Parameters
    ----------
    session_data : dict
        Session data from API response
    instance_type : str, optional
        Instance type that was requested (for display if not in response)
    storage_size : int, optional
        Storage size that was requested (for display if not in response)
    backend_type : str, optional
        Backend type (regular, vscode, spark, rstudio) for backend-specific display
    r_version : str, optional
        R version for RStudio backend
    spark_master : str, optional
        Spark master instance type
    spark_core : str, optional
        Spark core instance type
    spark_workers : int, optional
        Number of Spark workers
    data_files : list, optional
        List of parsed data file objects to display
    s3_mounts : list, optional
        List of parsed S3 mount objects to display
    
    Returns
    -------
    str
        Formatted table output
    """
    console = Console()
    
    table = Table(title="✓ Interactive Session Created Successfully")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Session ID", session_data.get('_id', 'N/A'))
    table.add_row("Name", session_data.get('name', 'N/A'))
    table.add_row("Backend", session_data.get('interactiveSessionType', 'N/A'))
    table.add_row("Status", session_data.get('status', 'N/A'))
    
    # Try to get instance type from response, fallback to provided value
    response_instance = session_data.get('resources', {}).get('instanceType') or \
                        session_data.get('interactiveSessionConfiguration', {}).get('instanceType')
    instance_display = response_instance or instance_type or 'N/A'
    table.add_row("Instance Type", instance_display)
    
    # Try to get storage size from response, fallback to provided value
    response_storage = session_data.get('resources', {}).get('storageSizeInGb') or \
                       session_data.get('interactiveSessionConfiguration', {}).get('storageSizeInGb')
    storage_display = f"{response_storage} GB" if response_storage else (f"{storage_size} GB" if storage_size else "N/A")
    table.add_row("Storage", storage_display)
    
    # Add backend-specific information
    if backend_type == 'rstudio' and r_version:
        table.add_row("R Version", r_version)
    
    if backend_type == 'spark':
        spark_config = []
        if spark_master:
            spark_config.append(f"Master: {spark_master}")
        if spark_core:
            spark_config.append(f"Core: {spark_core}")
        if spark_workers:
            spark_config.append(f"Workers: {spark_workers}")
        
        if spark_config:
            table.add_row("Spark Cluster", ", ".join(spark_config))
    
    # Display mounted data files
    if data_files:
        mounted_files = []
        for df in data_files:
            if isinstance(df, dict):
                # Handle CloudOS dataset files
                if df.get('kind') == 'File':
                    name = df.get('name', 'Unknown')
                    mounted_files.append(name)
                # Handle S3 files
                elif df.get('type') == 'S3File':
                    data = df.get('data', {})
                    name = data.get('name', 'Unknown')
                    mounted_files.append(f"{name} (S3)")
        
        if mounted_files:
            table.add_row("Mounted Data", ", ".join(mounted_files))
    
    # Display linked S3 buckets
    if s3_mounts:
        linked_s3 = []
        for s3 in s3_mounts:
            if isinstance(s3, dict):
                data = s3.get('data', {})
                bucket = data.get('s3BucketName', '')
                prefix = data.get('s3Prefix', '')
                # For CloudOS mounts, show project/path; for S3, show bucket/path
                if prefix and bucket:
                    linked_s3.append(f"s3://{bucket}/{prefix}")
                elif bucket:
                    linked_s3.append(f"s3://{bucket}/")
        
        if linked_s3:
            table.add_row("Linked S3", "\n".join(linked_s3))
    
    console.print(table)
    console.print("\n[yellow]Note:[/yellow] Session provisioning typically takes 3-10 minutes.")
    console.print("[cyan]Next steps:[/cyan] Use 'cloudos interactive-session status' to monitor status")


# ============================================================================
# Interactive Session Status Helper Functions
# ============================================================================

# Backend type mapping for status display
BACKEND_MAPPING = {
    'awsJupyterNotebook': 'Jupyter Notebook',
    'azureJupyterNotebook': 'Jupyter Notebook',
    'awsVSCode': 'VS Code',
    'azureVSCode': 'VS Code',
    'awsJupyterSparkNotebook': 'Spark',
    'azureJupyterSparkNotebook': 'Spark',
    'awsRstudio': 'RStudio',
    'azureRstudio': 'RStudio',
}

# Status color mapping for Rich terminal
STATUS_COLORS = {
    'running': 'green',
    'stopped': 'red',
    'terminated': 'red',
    'provisioning': 'yellow',
    'scheduled': 'yellow',
}

# Terminal states where watch mode should exit
TERMINAL_STATES = {'running', 'stopped', 'terminated'}

# Status mapping from API to user-friendly display
API_STATUS_MAPPING = {
    'ready': 'running',      # API returns 'ready' for running sessions
    'aborted': 'stopped',    # API returns 'aborted' for stopped sessions
    'setup': 'setup',
    'initialising': 'initialising',
    'initializing': 'initialising',
    'scheduled': 'scheduled',
    'running': 'running',    # Some endpoints may return 'running'
    'stopped': 'stopped',    # Some endpoints may return 'stopped'
    'terminated': 'terminated',
}

# Pre-running statuses (watch mode only valid for these)
PRE_RUNNING_STATUSES = {'setup', 'initialising', 'scheduled'}


def format_duration(seconds: int) -> str:
    """Convert seconds to human-readable format.
    
    Examples: "2h 15m", "45m 30s", "30s"
    """
    if not seconds or seconds <= 0:
        return "Not started"
    
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 or not parts:
        parts.append(f"{secs}s")
    
    return " ".join(parts)


def map_backend_type(api_backend: str) -> str:
    """Map API backend type to user-friendly display name."""
    return BACKEND_MAPPING.get(api_backend, api_backend)


def map_status(api_status: str) -> str:
    """Map API status value to user-friendly display status.
    
    Converts API status values (like 'ready', 'aborted') to display values
    (like 'running', 'stopped') matching the list command.
    """
    return API_STATUS_MAPPING.get(api_status, api_status)


def format_timestamp(iso_timestamp: str = None) -> str:
    """Convert ISO8601 timestamp to readable format.
    
    Example: "2026-03-13 10:30:00"
    """
    if not iso_timestamp:
        return "N/A"
    
    try:
        dt = datetime.fromisoformat(
            iso_timestamp.replace('Z', '+00:00')
        )
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, AttributeError):
        return iso_timestamp


def format_cost(cost_value: float = None) -> str:
    """Format cost as currency.
    
    Examples: "$12.50", "$0.00"
    """
    if cost_value is None:
        return "$0.00"
    try:
        return f"${float(cost_value):.2f}"
    except (ValueError, TypeError):
        return "$0.00"


def format_instance_type(instance_type: str, is_cost_saving: bool = False) -> str:
    """Format instance type with spot indicator.
    
    Examples: "c5.xlarge", "c5.xlarge (spot)"
    """
    if is_cost_saving:
        return f"{instance_type} (spot)"
    return instance_type


def validate_session_id(session_id: str) -> bool:
    """Validate session ID format (24-character hex string)."""
    if not session_id:
        return False
    return bool(re.match(r'^[a-f0-9]{24}$', session_id, re.IGNORECASE))


class InteractiveSessionAPI:
    """API client for interactive session operations."""
    
    REQUEST_TIMEOUT = 30  # seconds
    
    def __init__(self, cloudos_url: str, apikey: str, verify_ssl: bool = True):
        """Initialize API client.
        
        Parameters
        ----------
        cloudos_url : str
            Base CloudOS platform URL
        apikey : str
            API key for authentication
        verify_ssl : bool
            Whether to verify SSL certificates
        """
        self.cloudos_url = cloudos_url.rstrip('/')
        self.apikey = apikey
        self.verify_ssl = verify_ssl
        self.session = self._create_session()
    
    def _create_session(self) -> requests.Session:
        """Create requests session with retry strategy."""
        session = requests.Session()
        
        # Configure retry strategy with exponential backoff
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=['GET']
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        
        return session
    
    def get_session_status(self, session_id: str, team_id: str) -> dict:
        """Retrieve session status from API endpoint.
        
        GET /api/v2/interactive-sessions/{sessionId}?teamId={teamId}
        
        Parameters
        ----------
        session_id : str
            Session ID (24-character hex)
        team_id : str
            Team/workspace ID
        
        Returns
        -------
        dict
            Session status response
        
        Raises
        ------
        PermissionError
            If authentication fails (401, 403)
        ValueError
            If session not found (404)
        RuntimeError
            For other API errors
        """
        url = f"{self.cloudos_url}/api/v2/interactive-sessions/{session_id}"
        params = {'teamId': team_id}
        headers = {
            'apikey': self.apikey,
            'Content-Type': 'application/json'
        }
        
        try:
            response = retry_requests_get(
                url,
                params=params,
                headers=headers,
                verify=self.verify_ssl
            )
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                raise PermissionError("Unauthorized: Invalid API key or credentials")
            elif response.status_code == 403:
                raise PermissionError("Forbidden: Insufficient permissions for this session")
            elif response.status_code == 404:
                raise ValueError(
                    f"Session not found. Verify session ID ({session_id}) "
                    f"and team ID ({team_id})"
                )
            elif response.status_code == 500:
                raise RuntimeError("Server error: Unable to retrieve session status")
            else:
                raise RuntimeError(
                    f"API error (HTTP {response.status_code}): {response.text}"
                )
        
        except requests.exceptions.Timeout:
            raise RuntimeError(f"API request timeout after {self.REQUEST_TIMEOUT} seconds")
        except requests.exceptions.ConnectionError as e:
            raise RuntimeError(f"Failed to connect to CloudOS: {str(e)}")



class OutputFormatter:
    """Handles formatting output in different formats."""
    
    @staticmethod
    def format_stdout(session_data: dict, cloudos_url: str) -> None:
        """Display session status as a rich table with color coding."""
        console = Console()
        table = Table(
            title="[bold cyan]Interactive Session Status[/bold cyan]",
            show_header=True,
            header_style="bold magenta"
        )
        
        table.add_column("Property", style="cyan", no_wrap=True)
        table.add_column("Value", style="green")
        
        # Build session link and embed it in the name
        session_id = session_data.get('id', 'N/A')
        session_name = session_data.get('name', 'N/A')
        
        if cloudos_url and session_id != 'N/A':
            base_url = cloudos_url.rstrip('/')
            session_link = f"{base_url}/app/data-science/interactive-analysis/view/{session_id}/"
            session_name_with_link = f"[link={session_link}]{session_name}[/link]"
        else:
            session_name_with_link = session_name
        
        table.add_row("Session ID", session_id)
        table.add_row("Name", session_name_with_link)
        
        # Status with color coding
        status = session_data.get('status', 'N/A')
        status_color = STATUS_COLORS.get(status, 'white')
        status_colored = f"[{status_color}]{status}[/{status_color}]"
        table.add_row("Status", status_colored)
        
        # Add remaining fields
        table.add_row("Backend", session_data.get('backend_type', 'N/A'))
        table.add_row("Owner", session_data.get('owner', 'N/A'))
        table.add_row("Project", session_data.get('project', 'N/A'))
        table.add_row("Instance Type", session_data.get('instance_type', 'N/A'))
        table.add_row("Storage", session_data.get('storage_size', 'N/A'))
        table.add_row("Cost", session_data.get('cost', 'N/A'))
        table.add_row("Runtime", session_data.get('runtime', 'N/A'))
        table.add_row("Created At", session_data.get('created_at', 'N/A'))
        
        if session_data.get('last_saved'):
            table.add_row("Last Saved", session_data.get('last_saved'))
        
        if session_data.get('auto_shutdown'):
            table.add_row("Auto-Shutdown At", session_data.get('auto_shutdown'))
        
        if session_data.get('r_version'):
            table.add_row("R Version", session_data.get('r_version'))
        
        console.print(table)
    
    @staticmethod
    def format_json(raw_response: dict) -> str:
        """Return raw API response as formatted JSON."""
        return json.dumps(raw_response, indent=2, default=str)
    
    @staticmethod
    def format_csv(session_data: dict) -> str:
        """Export as CSV with key fields."""
        csv_data = {
            'ID': session_data.get('id', ''),
            'Name': session_data.get('name', ''),
            'Status': session_data.get('status', ''),
            'Backend': session_data.get('backend_type', ''),
            'Instance': session_data.get('instance_type', ''),
            'Storage': session_data.get('storage_size', ''),
            'Cost': session_data.get('cost', ''),
            'Runtime': session_data.get('runtime', ''),
            'Created': session_data.get('created_at', ''),
        }
        
        lines = []
        lines.append(','.join(csv_data.keys()))
        lines.append(','.join(str(v) if v else '' for v in csv_data.values()))
        
        return '\n'.join(lines)


class WatchModeManager:
    """Manages watch mode polling and display."""
    
    def __init__(self, api_client: InteractiveSessionAPI, 
                 session_id: str, team_id: str, interval: int = 10):
        """Initialize watch mode manager.
        
        Parameters
        ----------
        api_client : InteractiveSessionAPI
            API client instance
        session_id : str
            Session ID to monitor
        team_id : str
            Team ID
        interval : int
            Polling interval in seconds (default: 10)
        """
        self.api_client = api_client
        self.session_id = session_id
        self.team_id = team_id
        self.interval = interval
        self.start_time = time.time()
    
    def watch(self, verbose: bool = False) -> dict:
        """Continuously poll session status until reaching terminal state.
        
        Terminal states: running, stopped, terminated
        
        Handles Ctrl+C gracefully.
        """
        spinner_chars = ['◜', '◝', '◞', '◟']
        spinner_index = 0
        
        try:
            while True:
                # Fetch status
                response = self.api_client.get_session_status(
                    self.session_id, self.team_id
                )
                
                status = response.get('status', '')
                elapsed = int(time.time() - self.start_time)
                
                # Display progress
                spinner = spinner_chars[spinner_index % len(spinner_chars)]
                
                if verbose:
                    print(
                        f"\r{spinner} Status: {status:<12} | "
                        f"Elapsed: {elapsed}s",
                        end='',
                        flush=True
                    )
                
                # Check if reached terminal state
                if status in TERMINAL_STATES:
                    print()  # New line after spinner
                    if status == 'running':
                        print(
                            "✓ Session is now running and ready to use!"
                        )
                    else:
                        print(
                            f"⚠ Session reached terminal state: {status}"
                        )
                    return response
                
                # Wait before next poll
                spinner_index += 1
                time.sleep(self.interval)
        
        except KeyboardInterrupt:
            print("\n⚠ Watch mode interrupted by user.")
            raise
    
    def get_elapsed_time(self) -> str:
        """Get formatted elapsed time."""
        elapsed = int(time.time() - self.start_time)
        return format_duration(elapsed)


def transform_session_response(api_response: dict) -> dict:
    """Transform raw API response to user-friendly display format."""
    session_id = api_response.get('_id', '')
    name = api_response.get('name', 'N/A')
    api_status = api_response.get('status', 'N/A')
    status = map_status(api_status)  # Map API status to display status
    
    # Map backend type
    api_backend = api_response.get('interactiveSessionType', '')
    backend_type = map_backend_type(api_backend)
    
    # Extract user info
    user = api_response.get('user', {})
    owner = f"{user.get('name', '')} {user.get('surname', '')}".strip()
    if not owner:
        owner = user.get('email', 'N/A')
    
    # Extract project info
    project = api_response.get('project', {})
    project_name = project.get('name', 'N/A')
    
    # Extract resource info
    resources = api_response.get('resources', {})
    instance_type = resources.get('instanceType', 'N/A')
    is_spot = resources.get('isCostSaving', False)
    instance_display = format_instance_type(instance_type, is_spot)
    
    storage_size_gb = resources.get('storageSizeInGb', 'N/A')
    storage_display = f"{storage_size_gb} GB" if isinstance(storage_size_gb, int) else 'N/A'
    
    # Cost and runtime
    total_cost = api_response.get('totalCostInUsd', 0)
    cost = format_cost(total_cost)
    
    total_runtime_seconds = api_response.get('totalRunningTimeInSeconds', 0)
    runtime = format_duration(total_runtime_seconds)
    
    # Timestamps
    created_at = format_timestamp(api_response.get('createdAt'))
    last_saved = format_timestamp(api_response.get('lastSavedAt'))
    
    # Execution info
    execution = api_response.get('execution', {})
    auto_shutdown = format_timestamp(execution.get('autoShutdownAtDate'))
    
    # R version (for RStudio)
    r_version = api_response.get('rVersion')
    
    return {
        'id': session_id,
        'name': name,
        'status': status,
        'backend_type': backend_type,
        'owner': owner,
        'project': project_name,
        'instance_type': instance_display,
        'storage_size': storage_display,
        'cost': cost,
        'runtime': runtime,
        'created_at': created_at,
        'last_saved': last_saved if last_saved != 'N/A' else None,
        'auto_shutdown': auto_shutdown if auto_shutdown != 'N/A' else None,
        'r_version': r_version,
    }


def export_session_status_json(session_data: dict, output_file: str = None) -> str:
    """Export session status as JSON.
    
    Parameters
    ----------
    session_data : dict
        Raw API response
    output_file : str, optional
        Path to save JSON file. If None, returns JSON string.
    
    Returns
    -------
    str
        JSON formatted string
    """
    json_str = json.dumps(session_data, indent=2, default=str)
    
    if output_file:
        with open(output_file, 'w') as f:
            f.write(json_str)
    
    return json_str


def export_session_status_csv(session_data: dict, output_file: str = None) -> str:
    """Export session status as CSV.
    
    Parameters
    ----------
    session_data : dict
        Transformed session data (from transform_session_response)
    output_file : str, optional
        Path to save CSV file. If None, returns CSV string.
    
    Returns
    -------
    str
        CSV formatted string
    """
    csv_str = OutputFormatter.format_csv(session_data)
    
    if output_file:
        with open(output_file, 'w') as f:
            f.write(csv_str)
    
    return csv_str


# ============================================================================
# Wrapper Functions for CLI Integration
# ============================================================================

def get_interactive_session_status(cloudos_url: str, apikey: str, session_id: str, 
                                   team_id: str, verify_ssl: bool = True, 
                                   verbose: bool = False) -> dict:
    """Wrapper function to fetch session status from API.
    
    Parameters
    ----------
    cloudos_url : str
        CloudOS platform URL
    apikey : str
        API key for authentication
    session_id : str
        Session ID (24-char hex)
    team_id : str
        Team/workspace ID
    verify_ssl : bool
        Whether to verify SSL certificates
    verbose : bool
        Whether to print verbose output
    
    Returns
    -------
    dict
        Raw API response
    
    Raises
    ------
    ValueError
        If session not found
    PermissionError
        If authentication fails
    RuntimeError
        For other API errors
    """
    api_client = InteractiveSessionAPI(
        cloudos_url=cloudos_url,
        apikey=apikey,
        verify_ssl=verify_ssl
    )
    
    return api_client.get_session_status(session_id, team_id)


def format_session_status_table(session_data: dict, cloudos_url: str = None) -> None:
    """Wrapper function to display session status as a rich table.
    
    Parameters
    ----------
    session_data : dict
        Transformed session data (from transform_session_response)
    cloudos_url : str, optional
        CloudOS URL for creating links
    """
    OutputFormatter.format_stdout(session_data, cloudos_url or '')

"""Interactive session helper functions for CloudOS."""

import pandas as pd
import sys
from rich.table import Table
from rich.console import Console


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
            'max_width': 12,
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
            page_rows = [row for row in rows]  # All rows are from current page
        else:
            # Client-side pagination
            start = current_api_page * page_size
            end = start + page_size
            page_rows = [row for row in rows[start:end]]

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
            row = {
                '_id': session.get('_id', ''),
                'name': session.get('name', ''),
                'status': session.get('status', ''),
                'interactiveSessionType': session.get('interactiveSessionType', ''),
                'user': session.get('user', {}).get('firstName', '') + ' ' + session.get('user', {}).get('lastName', '') if session.get('user') else '',
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
        # Map aborted to stopped for display
        display_status = 'stopped' if status_lower == 'aborted' else value
        
        if status_lower == 'running':
            return f'[bold green]{display_status}[/bold green]'
        elif status_lower in ['stopped', 'aborted']:
            return f'[bold red]{display_status}[/bold red]'
        elif status_lower in ['provisioning', 'scheduled']:
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
        # Truncate long IDs
        value_str = str(value)
        if len(value_str) > 12:
            return value_str[:12] + '…'
        return value_str
    
    elif field_name == 'name':
        # Truncate long names
        value_str = str(value)
        if len(value_str) > 25:
            return value_str[:22] + '…'
        return value_str
    
    return str(value)


def save_interactive_session_list_to_csv(df, outfile):
    """Save interactive session list to CSV file.
    
    Parameters
    ----------
    df : pandas.DataFrame
        The session data to save
    outfile : str
        Path to the output CSV file
    """
    df.to_csv(outfile, index=False)
    print(f'Interactive session list saved to {outfile}')

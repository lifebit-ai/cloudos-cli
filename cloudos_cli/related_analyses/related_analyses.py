from cloudos_cli.clos import Cloudos
import cloudos_cli.jobs.job as jb
import json
import click
from rich.console import Console
from rich.table import Table
from rich.text import Text
from datetime import datetime


def related_analyses(cloudos_url, apikey, j_id, workspace_id, output_format, verify=True):
    """
    Retrieve and display related analyses for a given job in a Cloudos workspace.

    This function fetches the working directory and related analyses information for a specified job.
    If the job is a Bash job (which does not have related analyses), a warning is displayed.
    If the job's intermediate results have been deleted, a message is shown indicating who deleted them and when.
    The related analyses can be output in JSON format or displayed as a formatted table.

    Parameters
    ----------
    cloudos_url: str
        The base URL of the Cloudos instance.
    apikey: str
        API key for authentication.
    j_id: str
        The ID of the job to analyze.
    workspace_id: str
        The ID of the workspace containing the job.
    output_format: str
        Output format, either 'json' or another format for table display.
    verify: bool, optional
        Whether to verify SSL certificates. Defaults to True.

    Raises
    ------
    ValueError: If the job does not have a working directory associated.
    Exception: Propagates exceptions not related to missing 'workDirectory' field.
    """

    job = jb.Job(cloudos_url, apikey, None, workspace_id, None, None, workflow_id=1234, project_id="None",
                 mainfile=None, importsfile=None, verify=verify)

    # Get job working directory
    try:
        j_workdir = job.get_field_from_jobs_endpoint(j_id, field='workDirectory', verify=verify)
    except Exception as e:
        if "Field 'workDirectory' not found in endpoint 'jobs'" in str(e):
            click.secho("Bash jobs do not have 'Related Analyses' information.", fg="yellow", bold=True)
            return
        else:
            raise e

    # Get folder ID
    folder_id = j_workdir.get('folderId')
    if not folder_id:
        raise ValueError("The job does not have a working directory associated.")

    # Get related analyses
    j_related = job.get_job_relatedness(workspace_id, j_workdir['folderId'], verify=verify)
    deleted_by_id = j_workdir.get('deletedBy', {}).get('id')
    deleted_by_name = j_workdir.get('deletedBy', {}).get('name')
    deletion_date_iso = j_workdir.get('deletionDate')
    if deletion_date_iso:
        try:
            dt = datetime.fromisoformat(deletion_date_iso.replace('Z', '+00:00'))
            deletion_date_str = dt.strftime('%d/%m/%Y')
        except Exception:
            deletion_date_str = deletion_date_iso
    else:
        deletion_date_str = "N/A"

    if deleted_by_id and deleted_by_name:
        j_workdir_parent = Text(
            f"Intermediate results of this job were deleted by [bold]{deleted_by_name}[/bold] on [bold]{deletion_date_str}[/bold]. Current job and all other jobs sharing the same working directory are not resumable anymore. You can restore intermediate data by cloning the job.",
            style="yellow"
        )
    else:
        j_workdir_parent = job.get_parent_job(workspace_id, j_workdir['folderId'], verify=verify)

    if output_format.lower() == 'json':
        # Save as JSON file
        save_as_json(j_related, 'related_analyses.json')
        print(f"\nResults saved to: related_analyses.json")
        return
    # Display results as a formatted table
    save_as_stdout(j_related, j_workdir_parent, cloudos_url=cloudos_url)


def save_as_json(data, filename):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)


def save_as_stdout(data, j_workdir_parent, cloudos_url="https://cloudos.lifebit.ai"):
    """Display related analyses in a formatted table with pagination.
    
    Parameters
    ----------
    data : dict
        Dictionary where keys are job IDs and values are dictionaries
        containing job details (status, name, user_name, user_surname,
        _id, createdAt, runTime, computeCostSpent).
    """
    console = Console(markup=True)

    # Helper function to format timestamp
    def format_timestamp(timestamp_str):
        if not timestamp_str:
            return "N/A"
        try:
            dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except (ValueError, AttributeError):
            return timestamp_str

    # Helper function to format runtime
    def format_runtime(runtime_seconds):
        if runtime_seconds is None:
            return "N/A"
        try:
            total_seconds = int(runtime_seconds)
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            if hours > 0:
                return f"{hours}h {minutes}m {seconds}s"
            elif minutes > 0:
                return f"{minutes}m {seconds}s"
            else:
                return f"{seconds}s"
        except (ValueError, TypeError):
            return "N/A"

    # Helper function to format cost
    def format_cost(cost):
        if cost is None or cost == "":
            return "N/A"
        try:
            # Cost is stored in cents, divide by 100 to get dollars
            return f"${float(cost) / 100:.4f}"
        except (ValueError, TypeError):
            return "N/A"

    # Prepare all rows data
    rows = []

    for job_id, job_info in data.items():
        status = job_info.get('status', 'N/A')
        name = job_info.get('name', 'N/A')
        user_name = job_info.get('user_name', '')
        user_surname = job_info.get('user_surname', '')
        owner = f"{user_name} {user_surname}".strip() if user_name or user_surname else "N/A"
        job_id_display = job_info.get('_id', job_id)
        submit_time = format_timestamp(job_info.get('createdAt'))
        run_time = format_runtime(job_info.get('runTime'))
        cost = job_info.get('computeCostSpent')
        total_cost_formatted = format_cost(cost)

        # Add hyperlink to job_id_display
        job_url = f"{cloudos_url}/app/advanced-analytics/analyses/{job_id_display}"
        job_id_with_link = f"[link={job_url}]{job_id_display}[/link]"

        rows.append([
            status,
            name,
            owner,
            job_id_with_link,
            submit_time,
            run_time,
            total_cost_formatted
        ])

    # Pagination setup
    limit = 10  # Display 10 rows per page
    current_page = 0
    total_pages = (len(rows) + limit - 1) // limit if len(rows) > 0 else 1

    # Display with pagination
    show_error = None  # Track error messages to display
    
    while True:
        start = current_page * limit
        end = start + limit

        # Clear console first
        console.clear()

        # Display parent job information (reprinted each iteration after clear)
        if "Intermediate results of this job were deleted by" in str(j_workdir_parent):
            console.print(f"[white on #fff08a]🗑️ {j_workdir_parent}[/white on #fff08a]")
        elif j_workdir_parent is not None:
            link = f"{cloudos_url}/app/advanced-analytics/analyses/{j_workdir_parent}"
            console.print(f"Parent job link: [link={link}]{j_workdir_parent}[/link]")
        else:
            console.print("[dim]No parent job found[/dim]")

        console.print(f"\nTotal related analyses found: {len(data)}")

        # Create and display table
        table = Table(title="Related Analyses")

        # Add columns
        table.add_column("Status", style="cyan", no_wrap=True)
        table.add_column("Name", style="green", overflow="fold")
        table.add_column("Owner", style="blue", overflow="fold")
        table.add_column("ID", style="magenta", overflow="fold", no_wrap=True)
        table.add_column("Submit time", style="yellow", overflow="fold")
        table.add_column("Run time", style="white", overflow="fold")
        table.add_column("Total Cost", style="red", no_wrap=True)

        # Get rows for current page
        page_rows = rows[start:end]

        # Add rows to table
        for row in page_rows:
            table.add_row(*row)

        # Print table
        console.print(table)

        # Show error message if any (before clearing for next iteration)
        if show_error:
            console.print(show_error)
            show_error = None  # Reset error after displaying

        # Show pagination info and controls
        if total_pages > 1:
            console.print(f"\nOn page {current_page + 1}/{total_pages}: [bold cyan]n[/] = next, [bold cyan]p[/] = prev, [bold cyan]q[/] = quit")

            # Get user input for navigation
            choice = input(">>> ").strip().lower()

            if choice in ("q", "quit"):
                break
            elif choice in ("n", "next"):
                if current_page < total_pages - 1:
                    current_page += 1
                else:
                    show_error = "[red]Invalid choice. Already on the last page.[/red]"
            elif choice in ("p", "prev"):
                if current_page > 0:
                    current_page -= 1
                else:
                    show_error = "[red]Invalid choice. Already on the first page.[/red]"
            else:
                show_error = "[red]Invalid choice. Please enter 'n' (next), 'p' (prev), or 'q' (quit).[/red]"
        else:
            # Only one page, no need for input, just exit
            break


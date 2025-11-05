from cloudos_cli.clos import Cloudos
import cloudos_cli.jobs.job as jb
import json
from rich.console import Console
from rich.table import Table
from rich.text import Text
from datetime import datetime



def related_analyses(cloudos_url, apikey, j_id, workspace_id, verify=True):
    cl = Cloudos(cloudos_url, apikey, None)
    job = jb.Job(cloudos_url, apikey, None, workspace_id, None, None, workflow_id=1234, project_id="None",
                 mainfile=None, importsfile=None, verify=verify)

    j_workdir = job.get_field_from_jobs_endpoint(j_id, field='workDirectory', verify=verify)
    j_related = cl.get_job_relatedness(workspace_id, j_workdir['folderId'], verify=verify)

    # Display results as a formatted table
    save_as_stdout(j_related)
    
    # Optionally save as JSON file
    #save_as_json(j_related, 'related_analyses.json')
    #print(f"\nResults also saved to: related_analyses.json")

def save_as_json(data, filename):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)

def save_as_stdout(data):
    """Display related analyses in a formatted table.
    
    Parameters
    ----------
    data : dict
        Dictionary where keys are job IDs and values are dictionaries
        containing job details (status, name, user_name, user_surname,
        _id, createdAt, runTime, computeCostSpent).
    """
    console = Console(markup=True)
    
    # Create table
    table = Table(title="Related Analyses")
    
    # Add columns
    table.add_column("Status", style="cyan", no_wrap=True)
    table.add_column("Name", style="green", overflow="fold")
    table.add_column("Owner", style="blue", overflow="fold")
    #table.add_column("ID", style="magenta", overflow="fold")
    table.add_column("ID", style="magenta", overflow="fold", no_wrap=True)
    table.add_column("Submit time", style="yellow", overflow="fold")
    table.add_column("Run time", style="white", overflow="fold")
    table.add_column("Total Cost", style="red", no_wrap=True)
    
    # Helper function to format timestamp
    def format_timestamp(timestamp_str):
        if not timestamp_str:
            return "N/A"
        try:
            dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d %H:%M:%S UTC')
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
    
    # Add rows to table
    for job_id, job_info in data.items():
        status = job_info.get('status', 'N/A')
        name = job_info.get('name', 'N/A')
        user_name = job_info.get('user_name', '')
        user_surname = job_info.get('user_surname', '')
        owner = f"{user_name} {user_surname}".strip() if user_name or user_surname else "N/A"
        job_id_display = job_info.get('_id', job_id)
        submit_time = format_timestamp(job_info.get('createdAt'))
        run_time = format_runtime(job_info.get('runTime'))
        total_cost = format_cost(job_info.get('computeCostSpent'))
        
        # Add a "❌" icon if status is "failed", otherwise leave empty
        if status.lower() == "failed":
            status_icon = "❌"
        elif status.lower() == "completed":
            status_icon = "✅"
        else:
            status_icon = ""
        # Add hyperlink to job_id_display
        job_url = f"https://cloudos.lifebit.ai/app/advanced-analytics/analyses/{job_id_display}"
        job_id_display = f"[link={job_url}]{job_id_display}[/link]"

        #table.add_row(link_text)
        table.add_row(
            #f"{status_icon} {status}".strip(),
            status,
            name,
            owner,
            job_id_display,
            submit_time,
            run_time,
            total_cost
        )
    
    # Display table
    console.print(table)
    console.print(f"\n[bold]Total related analyses found:[/bold] {len(data)}")


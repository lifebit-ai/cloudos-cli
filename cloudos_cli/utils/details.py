from datetime import datetime
from rich.console import Console
from rich.table import Table
import json
import csv
import os


def get_path(param, param_kind_map, execution_platform, storage_provider, mode="parameters"):
    """
    Constructs a storage path based on the parameter kind and execution platform.

    Parameters
    ----------
    param : dict
        A dictionary containing parameter details. Expected keys include:
            - 'parameterKind': Specifies the kind of parameter (e.g., 'dataItem', 'globPattern').
            - For 'dataItem': Contains nested keys such as 'item', which includes:
                - 's3BucketName', 's3ObjectKey', 's3Prefix' (for AWS Batch).
                - 'blobStorageAccountName', 'blobContainerName', 'blobName' (for other platforms).
            - For 'globPattern': Contains nested keys such as 'folder', which includes:
                - 's3BucketName', 's3Prefix' (for AWS Batch).
                - 'blobStorageAccountName', 'blobContainerName', 'blobPrefix' (for other platforms).
    param_kind_map : dict
        A mapping of parameter kinds to their corresponding keys in the `param` dictionary.
    execution_platform : str
        The platform on which the execution is taking place. 
        Expected values include "Batch AWS" or other non-AWS platforms.
    storage_provider : str
        Either s3:// or az://
    mode : str
        For "parameters" is creating the '*.config' file and it adds the complete path, for "asis"
        leaves the constructed path as generated from the API

    Returns
    -------
    str: A constructed storage path based on the parameter kind and execution platform.
        - For 'dataItem' on AWS Batch: "s3BucketName/s3ObjectKey" or "s3BucketName/s3Prefix".
        - For 'dataItem' on other platforms: "blobStorageAccountName/blobContainerName/blobName".
        - For 'globPattern' on AWS Batch: "s3BucketName/s3Prefix/globPattern".
        - For 'globPattern' on other platforms: "blobStorageAccountName/blobContainerName/blobPrefix/globPattern".
    """
    value = param[param_kind_map[param['parameterKind']]]
    if param['parameterKind'] == 'dataItem':
        if execution_platform == "Batch AWS":
            s3_object_key = value['item'].get('s3ObjectKey', None) if value['item'].get('s3Prefix', None) is None else value['item'].get('s3Prefix', None)
            if mode == "parameters":
                value = storage_provider + value['item']['s3BucketName'] + '/' + s3_object_key
            else:
                value = value['item']['s3BucketName'] + '/' + s3_object_key
        else:
            account_name = value['item']['blobStorageAccountName'] + ".blob.core.windows.net"
            container_name = value['item']['blobContainerName']
            blob_name = value['item']['blobName']
            if mode == "parameters":
                value = storage_provider + account_name + '/' + container_name + '/' + blob_name
            else:
                value = value['item']['blobStorageAccountName'] + '/' + container_name + '/' + blob_name
    elif param['parameterKind'] == 'globPattern':
        if execution_platform == "Batch AWS":
            if mode == "parameters":
                value = storage_provider + param['folder']['s3BucketName'] + '/' + param['folder']['s3Prefix'] + '/' + param['globPattern']
            else:
                value = param['folder']['s3BucketName'] + '/' + param['folder']['s3Prefix'] + '/' + param['globPattern']
        else:
            account_name = param['folder']['blobStorageAccountName'] + ".blob.core.windows.net"
            container_name = param['folder']['blobContainerName']
            blob_name = param['folder']['blobPrefix']
            if mode == "parameters":
                value = storage_provider + account_name + '/' + container_name + '/' + blob_name + '/' + param['globPattern']
            else:
                value = param['folder']['blobStorageAccountName'] + '/' + container_name + '/' + blob_name + '/' + param['globPattern']

    return value


def create_job_details(j_details_h, job_id, output_format, output_basename, parameters, cloudos_url="https://cloudos.lifebit.ai"):
    """
    Creates formatted job details output from job data in multiple formats.

    This function processes job details from the CloudOS API response and outputs
    the information in a user-specified format (stdout table, JSON, or CSV).
    It also optionally creates configuration files with job parameters.

    Parameters
    ----------
    j_details_h : dict
        A dictionary containing job details from the CloudOS API. Expected keys include:
            - 'jobType': The type of job executor (e.g., 'nextflowAWS', 'dockerAWS').
            - 'parameters': List of parameter dictionaries for the job.
            - 'status': Current status of the job.
            - 'name': Name of the job.
            - 'project': Dictionary containing project information with 'name' key.
            - 'user': Dictionary containing user information with 'name' and 'surname' keys.
            - 'workflow': Dictionary containing workflow information.
            - 'startTime': ISO format timestamp of job start.
            - 'endTime': ISO format timestamp of job completion.
            - 'computeCostSpent': Cost in cents (optional).
            - 'masterInstance': Dictionary containing instance information.
            - 'storageSizeInGb': Storage size allocated to the job.
            - 'resourceRequirements': Dictionary with 'cpu' and 'ram' specifications.
            - Additional platform-specific keys based on jobType.
    job_id : str
        Unique identifier for the job.
    output_format : str
        Format for output display. Expected values:
            - 'stdout': Display as a formatted table in the console.
            - 'json': Save as a JSON file.
            - 'csv': Save as a CSV file.
    output_basename : str
        Base name for output files (without extension). Used when output_format
        is 'json' or 'csv'.
    parameters : bool
        Whether to create a separate configuration file containing job parameters.
        If True and parameters exist, creates a '.config' file with Nextflow-style
        parameter formatting.
    cloudos_url : str, optional
        The base URL of the CloudOS instance. Defaults to "https://cloudos.lifebit.ai".

    Returns
    -------
    None
        This function has side effects only:
        - Prints formatted output to console (for 'stdout' format).
        - Creates output files (for 'json' and 'csv' formats).
        - Optionally creates parameter configuration files.
        - Prints status messages about file creation.

    Notes
    -----
    The function handles different job types and execution platforms:
    - AWS Batch (nextflowAWS, dockerAWS, cromwellAWS)
    - Azure Batch (nextflowAzure)
    - Google Cloud Platform (nextflowGcp)
    - HPC clusters (nextflowHpc)
    - Kubernetes (nextflowKubernetes)

    Parameter processing depends on the parameter kind:
    - 'textValue': Simple text parameters
    - 'arrayFileColumn': Column-based array parameters
    - 'globPattern': File pattern matching parameters
    - 'lustreFileSystem': Lustre filesystem parameters
    - 'dataItem': Data file/object parameters

    Time calculations assume UTC timezone and convert ISO format timestamps
    to human-readable duration strings.
    """

    # Determine the execution platform based on jobType
    executors = {
        'nextflowAWS': 'Batch AWS',
        'nextflowAzure': 'Batch Azure',
        'nextflowGcp': 'GCP',
        'nextflowHpc': 'HPC',
        'nextflowKubernetes': 'Kubernetes',
        'dockerAWS': 'Batch AWS',
        'cromwellAWS': 'Batch AWS'
    }
    execution_platform = executors.get(j_details_h["jobType"], "None")
    storage_provider = "s3://" if execution_platform == "Batch AWS" else "az://"

    # Check if the job details contain parameters
    if j_details_h["parameters"] != []:
        param_kind_map = {
            'textValue': 'textValue',
            'arrayFileColumn': 'columnName',
            'globPattern': 'globPattern',
            'lustreFileSystem': 'fileSystem',
            'dataItem': 'dataItem'
        }
        # there are different types of parameters, arrayFileColumn, globPattern, lustreFileSystem
        # get first the type of parameter, then the value based on the parameter kind
        concats = []
        for param in j_details_h["parameters"]:
            concats.append(f"{param['prefix']}{param['name']}={get_path(param, param_kind_map, execution_platform, storage_provider, 'asis')}")
        concat_string = '\n'.join(concats)

        # If the user requested to save the parameters in a config file
        if parameters:
            # Create a config file with the parameters
            config_filename = f"{output_basename}.config"
            with open(config_filename, 'w') as config_file:
                config_file.write("params {\n")
                for param in j_details_h["parameters"]:
                    config_file.write(f"\t{param['name']} = {get_path(param, param_kind_map, execution_platform, storage_provider)}\n")
                config_file.write("}\n")
            print(f"\tJob parameters have been saved to '{config_filename}'")
    else:
        concat_string = 'No parameters provided'
        if parameters:
            print("\tNo parameters found in the job details, no config file will be created.")

    # revision
    if j_details_h["jobType"] == "dockerAWS":
        revision = j_details_h["revision"]["digest"]
    else:
        revision = j_details_h["revision"]["commit"]

    # Output the job details
    status = str(j_details_h.get("status", "None"))
    name = str(j_details_h.get("name", "None"))
    project = str(j_details_h.get("project", {}).get("name", "None"))
    owner = str(j_details_h.get("user", {}).get("name", "None") + " " + j_details_h.get("user", {}).get("surname", "None"))
    pipeline = str(j_details_h.get("workflow", {}).get("name", "None"))
    # calculate the run time
    start_dt = datetime.fromisoformat(str(j_details_h["startTime"]).replace('Z', '+00:00'))
    end_dt = datetime.fromisoformat(str(j_details_h["endTime"]).replace('Z', '+00:00'))
    duration = end_dt - start_dt
    # Format duration as hours:minutes:seconds
    total_seconds = int(duration.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    if hours > 0:
        run_time = f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        run_time = f"{minutes}m {seconds}s"
    else:
        run_time = f"{seconds}s"
    # determine cost
    cost = j_details_h.get("computeCostSpent", None)
    if cost is not None:
        cost_display = "$" + str(round(float(cost) / 100, 4))
    else:
        cost_display = "None"
    # when the job is just running this value might not be present
    master_instance = j_details_h.get("masterInstance", {})
    used_instance = master_instance.get("usedInstance", {})
    instance_type = used_instance.get("type", "N/A")
    storage = str(j_details_h.get("storageSizeInGb", 0)) + " GB"
    pipeline_url = str(j_details_h.get("workflow", {}).get("repository", {}).get("url", "Not Specified"))
    accelerated_file_staging = str(j_details_h.get("usesFusionFileSystem", "None"))
    nextflow_version = str(j_details_h.get("nextflowVersion", "None"))
    profile = str(j_details_h.get("profile", "None"))

    # Create a JSON object with the key-value pairs
    # make these separation to preserve order
    job_details_json = {
        "Status": status,
        "Name": name,
        "Project": project,
        "Owner": owner,
        "Pipeline": pipeline,
        "ID": str(job_id),
        "Submit time": str(start_dt.strftime('%Y-%m-%d %H:%M:%S')),
        "End time": str(end_dt.strftime('%Y-%m-%d %H:%M:%S')),
        "Run time": str(run_time),
        "Commit": str(revision),
        "Cost": cost_display,
        "Master Instance": str(instance_type),
    }
    if j_details_h["jobType"] == "nextflowAzure":
        try:
            job_details_json["Worker Node"] = str(j_details_h["azureBatch"]["vmType"])
        except KeyError:
            job_details_json["Worker Node"] = "Not Specified"

    job_details_json["Storage"] = storage

    # Conditionally add the "Job Queue" key if the jobType is not "nextflowAzure"
    if j_details_h["jobType"] != "nextflowAzure":
        try:
            batch = j_details_h.get("batch", {})
            job_queue = batch.get("jobQueue", {}) if batch is not None else {}
            if job_queue is not None:
                job_details_json["Job Queue ID"] = str(job_queue.get("name", "Not Specified"))
                job_details_json["Job Queue Name"] = str(job_queue.get("label", "Not Specified"))
            else:
                job_details_json["Job Queue ID"] = "Not Specified"
                job_details_json["Job Queue Name"] = "Not Specified"
        except KeyError:
            job_details_json["Job Queue"] = "Master Node"

    job_details_json["Task Resources"] = f"{str(j_details_h['resourceRequirements']['cpu'])} CPUs, " + \
                                         f"{str(j_details_h['resourceRequirements']['ram'])} GB RAM"
    job_details_json["Pipeline url"] = pipeline_url
    job_details_json["Nextflow Version"] = nextflow_version
    job_details_json["Execution Platform"] = execution_platform
    job_details_json["Accelerated File Staging"] = accelerated_file_staging
    job_details_json["Parameters"] = ';'.join(concat_string.split("\n"))

    # Conditionally add the "Command" key if the jobType is "dockerAWS"
    if j_details_h["jobType"] == "dockerAWS":
        job_details_json["Command"] = str(j_details_h["command"])

    job_details_json["Profile"] = profile

    if output_format == 'stdout':
        # Generate a table for stdout output
        console = Console()
        table = Table(title="Job Details")

        table.add_column("Field", style="cyan", no_wrap=True)
        table.add_column("Value", style="magenta", overflow="fold")

        for key, value in job_details_json.items():
            if key == "Parameters":
                table.add_row(key, "\n".join(value.split(";")))
            elif key == "ID":
                # Add hyperlink to job ID
                job_url = f"{cloudos_url}/app/advanced-analytics/analyses/{value}"
                job_id_with_link = f"[link={job_url}]{value}[/link]"
                table.add_row(key, job_id_with_link)
            else:
                table.add_row(key, str(value))

        console.print(table)
    elif output_format == 'json':
        # Write the JSON object to a file
        with open(f"{output_basename}.json", "w") as json_file:
            json.dump(job_details_json, json_file, indent=4, ensure_ascii=False)
        print(f"\tJob details have been saved to '{output_basename}.json'")
    else:
        # Write the same details to a CSV file
        with open(f"{output_basename}.csv", "w", newline='') as csv_file:
            writer = csv.writer(csv_file)
            # Write headers (fields) in the first row
            writer.writerow(job_details_json.keys())
            # Write values in the second row
            writer.writerow(job_details_json.values())
        print(f"\tJob details have been saved to '{output_basename}.csv'")


def create_job_list_table(jobs, cloudos_url, pagination_metadata=None, selected_columns=None):
    """
    Creates a formatted job list table for stdout output with responsive design.

    The table automatically adapts to terminal width by showing different column sets:
    - Very narrow (<60 chars): Essential columns only (status, name, pipeline, id)
    - Narrow (<90 chars): + Important columns (project, owner, run_time, cost)
    - Medium (<120 chars): + Useful columns (submit_time, end_time, commit)
    - Wide (≥120 chars): + Extended columns (resources, storage_type)

    Status symbols are displayed with colors:
    - Green ✓ for completed jobs
    - Grey ◐ for running jobs
    - Red ✗ for failed jobs
    - Orange ■ for aborted jobs
    - Grey ○ for initialising jobs
    - Grey ? for unknown status

    Parameters
    ----------
    jobs : list
        List of job dictionaries from the CloudOS API.
    cloudos_url : str
        The CloudOS service URL for generating job links.
    pagination_metadata : dict, optional
        Pagination metadata from the API response containing:
        - 'Pagination-Count': Total number of jobs matching the filter
        - 'Pagination-Page': Current page number
        - 'Pagination-Limit': Page size
    selected_columns : str or list, optional
        Column names to display. Can be:
        - None: Auto-responsive based on terminal width
        - String: Comma-separated column names (e.g., "status,name,cost")
        - List: List of column names
        Valid columns: 'status', 'name', 'project', 'owner', 'pipeline', 'id',
        'submit_time', 'end_time', 'run_time', 'commit', 'cost', 'resources', 'storage_type'

    Returns
    -------
    None
        Prints the formatted table to console with pagination information.

    Raises
    ------
    ValueError
        If invalid column names are provided in selected_columns.
    """
    console = Console()

    # Get terminal width for responsive design
    try:
        terminal_width = os.get_terminal_size().columns
    except OSError:
        terminal_width = 80  # Default fallback
    
    # Define column priority groups for small terminals
    priority_columns = {
        'essential': ['status', 'name', 'pipeline', 'id'],  # ~40 chars minimum
        'important': ['project', 'owner', 'run_time', 'cost'],  # +30 chars
        'useful': [ 'submit_time', 'end_time', 'commit'],  # +50 chars
        'extended': [ 'resources', 'storage_type']  # +30 chars
    }
    
    # Define all available columns with their configurations
    all_columns = {
        'status': {"header": "Status", "style": "cyan", "no_wrap": True, "min_width": 6, "max_width": 6},
        'name': {"header": "Name", "style": "green", "overflow": "ellipsis", "min_width": 6, "max_width": 20},
        'project': {"header": "Project", "style": "magenta", "overflow": "ellipsis", "min_width": 6, "max_width": 15},
        'owner': {"header": "Owner", "style": "blue", "overflow": "ellipsis", "min_width": 6, "max_width": 12},
        'pipeline': {"header": "Pipeline", "style": "yellow", "overflow": "ellipsis", "min_width": 6, "max_width": 15},
        'id': {"header": "ID", "style": "white", "overflow": "ellipsis", "min_width": 6, "max_width": 12},
        'submit_time': {"header": "Submit", "style": "cyan", "no_wrap": True, "min_width": 10, "max_width": 16},
        'end_time': {"header": "End", "style": "cyan", "no_wrap": True, "min_width": 10, "max_width": 16},
        'run_time': {"header": "Runtime", "style": "green", "no_wrap": True, "min_width": 5, "max_width": 10},
        'commit': {"header": "Commit", "style": "magenta", "no_wrap": True, "min_width": 7, "max_width": 8},
        'cost': {"header": "Cost", "style": "yellow", "no_wrap": True, "min_width": 6, "max_width": 10},
        'resources': {"header": "Resources", "style": "blue", "overflow": "ellipsis", "min_width": 3, "max_width": 15},
        'storage_type': {"header": "Storage", "style": "white", "no_wrap": True, "min_width": 3, "max_width": 8}
    }

    # Validate and process selected_columns
    if selected_columns is None:
        # Auto-select columns based on terminal width if none specified
        if terminal_width < 60:
            columns_to_show = priority_columns['essential']
        elif terminal_width < 90:
            columns_to_show = priority_columns['essential'] + priority_columns['important']
        elif terminal_width < 130:
            columns_to_show = (priority_columns['essential'] + 
                             priority_columns['important'] + 
                             priority_columns['useful'])
        else:  # terminal_width >= 130
            columns_to_show = (priority_columns['essential'] + 
                             priority_columns['important'] + 
                             priority_columns['useful'] +
                             priority_columns['extended'])
    else:
        # Accept either a comma-separated string or a list
        if isinstance(selected_columns, str):
            selected_columns = [col.strip().lower() for col in selected_columns.split(',')]
        valid_columns = list(all_columns.keys())
        invalid_cols = [col for col in selected_columns if col not in valid_columns]
        if invalid_cols:
            raise ValueError(f"Invalid column names: {', '.join(invalid_cols)}. "
                           f"Valid columns are: {', '.join(valid_columns)}")
        columns_to_show = selected_columns  # Preserve user-specified order
    
    if not jobs:
        console.print("\n[yellow]No jobs found matching the criteria.[/yellow]")
        # Still show pagination info even when no jobs
        if pagination_metadata:
            total_jobs = pagination_metadata.get('Pagination-Count', 0)
            current_page = pagination_metadata.get('Pagination-Page', 1)
            page_size = pagination_metadata.get('Pagination-Limit', 10)
            total_pages = (total_jobs + page_size - 1) // page_size if total_jobs > 0 else 1
            
            console.print(f"\n[cyan]Total jobs matching filter:[/cyan] {total_jobs}")
            console.print(f"[cyan]Page:[/cyan] {current_page} of {total_pages}")
            console.print(f"[cyan]Jobs on this page:[/cyan] {len(jobs)}")
        return
    
    # Create table
    table = Table(title="Job List")
    
    # Add columns to table
    for col_key in columns_to_show:
        col_config = all_columns[col_key]
        table.add_column(
            col_config["header"],
            style=col_config.get("style"),
            no_wrap=col_config.get("no_wrap", False),
            overflow=col_config.get("overflow"),
            min_width=col_config.get("min_width"),
            max_width=col_config.get("max_width")
        )
    
    # Process each job
    for job in jobs:
        # Status with colored and bold ANSI symbols
        status_raw = str(job.get("status", "N/A"))
        status_symbol_map = {
            "completed": "[bold green]✓[/bold green]",      # Green check mark
            "running": "[bold bright_black]◐[/bold bright_black]",       # Grey half-filled circle
            "failed": "[bold red]✗[/bold red]",             # Red X mark
            "aborted": "[bold orange3]■[/bold orange3]",    # Orange square
            "initialising": "[bold bright_black]○[/bold bright_black]",  # Grey circle
            "N/A": "[bold bright_black]?[/bold bright_black]"            # Grey question mark
        }
        status = status_symbol_map.get(status_raw.lower(), status_raw)
        
        # Name
        name = str(job.get("name", "N/A"))
        
        # Project
        project = str(job.get("project", {}).get("name", "N/A"))
        
        # Owner (compact format for small terminals)
        user_info = job.get("user", {})
        name_part = user_info.get('name', '')
        surname_part = user_info.get('surname', '')
        if terminal_width < 90:
            # Compact format: just first name or first letter of each
            if name_part and surname_part:
                owner = f"{name_part[0]}.{surname_part[0]}."
            elif name_part or surname_part:
                owner = (name_part or surname_part)[:8]
            else:
                owner = "N/A"
        else:
            # Full format for wider terminals
            if name_part and surname_part:
                owner = f"{name_part}\n{surname_part}"
            elif name_part or surname_part:
                owner = name_part or surname_part
            else:
                owner = "N/A"
        
        # Pipeline
        pipeline = str(job.get("workflow", {}).get("name", "N/A"))
        # Only show the first line if pipeline name contains newlines
        pipeline = pipeline.split('\n')[0].strip()
        # Truncate to 25 chars with ellipsis if longer
        if len(pipeline) > 25:
            pipeline = pipeline[:22] + "..."
        
        # ID with hyperlink
        job_id = str(job.get("_id", "N/A"))
        job_url = f"{cloudos_url}/app/advanced-analytics/analyses/{job_id}"
        job_id_with_link = f"[link={job_url}]{job_id}[/link]"
        
        # Submit time (compact format for small terminals)
        created_at = job.get("createdAt")
        if created_at:
            try:
                dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                if terminal_width < 90:
                    # Compact format: MM-DD HH:MM
                    submit_time = dt.strftime('%m-%d\n%H:%M')
                else:
                    # Full format
                    submit_time = dt.strftime('%Y-%m-%d\n%H:%M:%S')
            except (ValueError, TypeError):
                submit_time = "N/A"
        else:
            submit_time = "N/A"
        
        # End time (compact format for small terminals)
        end_time_raw = job.get("endTime")
        if end_time_raw:
            try:
                dt = datetime.fromisoformat(end_time_raw.replace('Z', '+00:00'))
                if terminal_width < 90:
                    # Compact format: MM-DD HH:MM
                    end_time = dt.strftime('%m-%d\n%H:%M')
                else:
                    # Full format
                    end_time = dt.strftime('%Y-%m-%d\n%H:%M:%S')
            except (ValueError, TypeError):
                end_time = "N/A"
        else:
            end_time = "N/A"
        
        # Run time (calculate from startTime and endTime)
        start_time_raw = job.get("startTime")
        if start_time_raw and end_time_raw:
            try:
                start_dt = datetime.fromisoformat(start_time_raw.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end_time_raw.replace('Z', '+00:00'))
                duration = end_dt - start_dt
                total_seconds = int(duration.total_seconds())
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                seconds = total_seconds % 60
                if hours > 0:
                    run_time = f"{hours}h {minutes}m {seconds}s"
                elif minutes > 0:
                    run_time = f"{minutes}m {seconds}s"
                else:
                    run_time = f"{seconds}s"
            except (ValueError, TypeError):
                run_time = "N/A"
        else:
            run_time = "N/A"
        
        # Commit
        revision = job.get("revision", {})
        if job.get("jobType") == "dockerAWS":
            commit = str(revision.get("digest", "N/A"))
        else:
            commit = str(revision.get("commit", "N/A"))
        # Truncate commit to 7 characters if it's longer
        if commit != "N/A" and len(commit) > 7:
            commit = commit[:7]
        
        # Cost
        cost_raw = job.get("computeCostSpent") or job.get("realInstancesExecutionCost")
        if cost_raw is not None:
            try:
                cost = f"${float(cost_raw) / 100:.4f}"
            except (ValueError, TypeError):
                cost = "N/A"
        else:
            cost = "N/A"
        
        # Resources (instance type only)
        master_instance = job.get("masterInstance", {})
        used_instance = master_instance.get("usedInstance", {})
        instance_type = used_instance.get("type", "N/A")
        resources = instance_type if instance_type else "N/A"
        
        # Storage type
        storage_mode = job.get("storageMode", "N/A")
        if storage_mode == "regular":
            storage_type = "Regular"
        elif storage_mode == "lustre":
            storage_type = "Lustre"
        else:
            storage_type = str(storage_mode).capitalize() if storage_mode != "N/A" else "N/A"
        
        # Map column keys to their values
        column_values = {
            'status': status,
            'name': name,
            'project': project,
            'owner': owner,
            'pipeline': pipeline,
            'id': job_id_with_link,
            'submit_time': submit_time,
            'end_time': end_time,
            'run_time': run_time,
            'commit': commit,
            'cost': cost,
            'resources': resources,
            'storage_type': storage_type
        }
        
        # Add row to table with only selected columns
        row_values = [column_values[col] for col in columns_to_show]
        table.add_row(*row_values)
    
    console.print(table)
    
    # Display pagination info at the bottom
    if pagination_metadata:
        total_jobs = pagination_metadata.get('Pagination-Count', 0)
        current_page = pagination_metadata.get('Pagination-Page', 1)
        page_size = pagination_metadata.get('Pagination-Limit', 10)
        total_pages = (total_jobs + page_size - 1) // page_size if total_jobs > 0 else 1
        
        console.print(f"\n[cyan]Showing {len(jobs)} of {total_jobs} total jobs | Page {current_page} of {total_pages}[/cyan]")

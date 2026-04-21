from datetime import datetime
from rich.console import Console
from rich.table import Table
import json
import csv
import os
import sys

from cloudos_cli.constants import (
    JOB_STATUS_SYMBOLS,
    COLUMN_PRIORITY_GROUPS,
    ESSENTIAL_COLUMN_PRIORITY,
    ADDITIONAL_COLUMN_PRIORITY,
    COLUMN_CONFIGS
)


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
    # Handle unsupported parameter kinds (e.g., legacy 'lustreFileSystem' from historical jobs)
    parameter_kind = param['parameterKind']
    if parameter_kind not in param_kind_map:
        # Return the parameterKind as-is to indicate an unsupported/legacy parameter type
        return f"<unsupported parameter type: {parameter_kind}>"
    
    value = param[param_kind_map[parameter_kind]]
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
            'dataItem': 'dataItem'
        }
        # there are different types of parameters, arrayFileColumn, globPattern
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
    start_time_raw = j_details_h.get("startTime")
    end_time_raw = j_details_h.get("endTime")

    if start_time_raw and end_time_raw:
        try:
            start_dt = datetime.fromisoformat(str(start_time_raw).replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(str(end_time_raw).replace('Z', '+00:00'))
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
            submit_time = str(start_dt.strftime('%Y-%m-%d %H:%M:%S'))
            end_time = str(end_dt.strftime('%Y-%m-%d %H:%M:%S'))
        except (ValueError, TypeError):
            run_time = "N/A"
            submit_time = "N/A"
            end_time = "N/A"
    else:
        run_time = "N/A"
        submit_time = "N/A" if not start_time_raw else str(datetime.fromisoformat(str(start_time_raw).replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S'))
        end_time = "N/A" if not end_time_raw else str(datetime.fromisoformat(str(end_time_raw).replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S'))
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
        "Submit time": submit_time,
        "End time": end_time,
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


def _build_job_row_values(job, cloudos_url, terminal_width, columns_to_show):
    """Helper function to build row values for a single job.
    
    Parameters
    ----------
    job : dict
        Job dictionary from CloudOS API
    cloudos_url : str
        CloudOS service URL for generating job links
    terminal_width : int
        Current terminal width for responsive formatting
    columns_to_show : list
        List of column keys to include
        
    Returns
    -------
    list
        Row values in the order of columns_to_show
    """
    # Status with colored and bold ANSI symbols
    status_raw = str(job.get("status", "N/A"))
    status = JOB_STATUS_SYMBOLS.get(status_raw.lower(), status_raw)

    # Name
    name = str(job.get("name", "N/A"))

    # Project
    project = str(job.get("project", {}).get("name", "N/A"))

    # Owner (single-line format, no wrapping)
    user_info = job.get("user", {})
    name_part = user_info.get('name', '')
    surname_part = user_info.get('surname', '')
    if name_part and surname_part:
        owner = f"{name_part} {surname_part}"
    elif name_part or surname_part:
        owner = name_part or surname_part
    else:
        owner = "N/A"

    # Pipeline
    pipeline = str(job.get("workflow", {}).get("name", "N/A")).split('\n')[0].strip()
    if len(pipeline) > 25:
        pipeline = pipeline[:22] + "..."

    # ID with hyperlink
    job_id = str(job.get("_id", "N/A"))
    job_url = f"{cloudos_url}/app/advanced-analytics/analyses/{job_id}"
    job_id_with_link = f"[link={job_url}]{job_id}[/link]"

    # Submit time (single-line format)
    created_at = job.get("createdAt")
    if created_at:
        try:
            dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            submit_time = dt.strftime('%m-%d %H:%M') if terminal_width < 90 else dt.strftime('%Y-%m-%d %H:%M')
        except (ValueError, TypeError):
            submit_time = "N/A"
    else:
        submit_time = "N/A"

    # End time (single-line format)
    end_time_raw = job.get("endTime")
    if end_time_raw:
        try:
            dt = datetime.fromisoformat(end_time_raw.replace('Z', '+00:00'))
            end_time = dt.strftime('%m-%d %H:%M') if terminal_width < 90 else dt.strftime('%Y-%m-%d %H:%M')
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

    # Return row values in the order of columns_to_show
    return [column_values[col] for col in columns_to_show]


def _create_status_legend():
    """Create a formatted legend for job status symbols.
    
    Returns
    -------
    str
        Formatted legend string with status symbols and their meanings.
    """
    legend_items = [
        "[bold green]✓[/bold green] = Completed",
        "[bold bright_black]◐[/bold bright_black] = Running",
        "[bold red]✗[/bold red] = Failed",
        "[bold orange3]■[/bold orange3] = Aborted",
        "[bold orange3]⊡[/bold orange3] = Aborting",
        "[bold bright_black]○[/bold bright_black] = Initialising",
        "[bold cyan]◷[/bold cyan] = Scheduled",
        "[bold bright_black]?[/bold bright_black] = Unknown"
    ]
    return "[cyan]Legend:[/cyan] " + "  |  ".join(legend_items)


def _build_job_table(jobs, cloudos_url, terminal_width, columns_to_show, column_configs):
    """Helper function to build a complete job table.
    
    Parameters
    ----------
    jobs : list
        List of job dictionaries from CloudOS API
    cloudos_url : str
        CloudOS service URL for generating job links
    terminal_width : int
        Current terminal width for responsive formatting
    columns_to_show : list
        List of column keys to include
    column_configs : dict
        Dictionary of all column configurations
        
    Returns
    -------
    Table
        Rich Table object populated with job rows
    """
    table = Table()

    # Add columns to table
    for col_key in columns_to_show:
        col_config = column_configs[col_key]
        table.add_column(
            col_config["header"],
            style=col_config.get("style"),
            no_wrap=col_config.get("no_wrap", False),
            overflow=col_config.get("overflow"),
            min_width=col_config.get("min_width"),
            max_width=col_config.get("max_width")
        )

    # Add rows for each job
    for job in jobs:
        row_values = _build_job_row_values(job, cloudos_url, terminal_width, columns_to_show)
        table.add_row(*row_values)

    return table


def _calculate_table_width(column_list, col_configs):
    """Calculate total table width including all overhead."""
    borders_and_separators = 2 + (len(column_list) - 1)
    column_widths = sum(
        col_configs[col].get('max_width', col_configs[col].get('min_width', 10)) + 2
        for col in column_list
    )
    buffer = 2

    return borders_and_separators + column_widths + buffer


def _fit_columns_to_terminal(cols, terminal_w, col_configs, preserve_order=False):
    """Build column list progressively, only adding columns that fit completely.
    
    Parameters
    ----------
    cols : list
        List of column keys to fit
    terminal_w : int
        Terminal width to fit columns into
    col_configs : dict
        Column configuration dictionary
    preserve_order : bool
        If True, preserve the order of cols. If False, reorder by priority.
        
    Returns
    -------
    list
        Columns that fit in the terminal, in appropriate order
    """
    if len(cols) == 0:
        return cols

    if preserve_order:
        # User explicitly specified column order - preserve it
        result = []
        for col in cols:
            test_list = result + [col]
            width = _calculate_table_width(test_list, col_configs)
            if width <= terminal_w:
                result.append(col)
            else:
                # Stop adding columns once we exceed width
                break
        
        # Ensure at least one column is shown, even if terminal is very narrow
        if len(result) == 0 and len(cols) > 0:
            # Force the first requested column to display
            result.append(cols[0])
        
        return result
    
    # Auto-selection mode: reorder by priority for better UX
    essential_requested = [col for col in ESSENTIAL_COLUMN_PRIORITY if col in cols]
    additional_requested = [col for col in cols if col not in ESSENTIAL_COLUMN_PRIORITY]

    additional_ordered = [col for col in ADDITIONAL_COLUMN_PRIORITY if col in additional_requested]
    additional_ordered.extend([col for col in additional_requested if col not in ADDITIONAL_COLUMN_PRIORITY])

    result = []
    for col in essential_requested:
        test_list = result + [col]
        width = _calculate_table_width(test_list, col_configs)
        if width <= terminal_w:
            result.append(col)
        else:
            # Column doesn't fit - continue trying remaining columns
            # Special case: always show at least status on very narrow terminals
            if len(result) == 0 and col == 'status':
                result.append(col)
    
    # Try to add additional columns one by one
    for col in additional_ordered:
        test_list = result + [col]
        width = _calculate_table_width(test_list, col_configs)
        if width <= terminal_w:
            result.append(col)
        # Continue trying remaining columns even if this one doesn't fit
    
    return result


def create_job_list_table(jobs, cloudos_url, pagination_metadata=None, selected_columns=None, fetch_page_callback=None):
    """Creates a formatted job list table with responsive design and pagination."""
    # Get terminal width for responsive design
    try:
        terminal_width = os.get_terminal_size().columns
    except OSError:
        terminal_width = 80  # Default fallback

    if selected_columns is None:
        if terminal_width < 80:
            columns_to_show = COLUMN_PRIORITY_GROUPS['minimal']
        elif terminal_width <= 100:
            columns_to_show = COLUMN_PRIORITY_GROUPS['essential']
        elif terminal_width < 150:
            columns_to_show = COLUMN_PRIORITY_GROUPS['essential'] + COLUMN_PRIORITY_GROUPS['important']
        elif terminal_width < 180:
            columns_to_show = (COLUMN_PRIORITY_GROUPS['essential'] +
                             COLUMN_PRIORITY_GROUPS['important'] +
                             COLUMN_PRIORITY_GROUPS['useful'])
        else:
            columns_to_show = (COLUMN_PRIORITY_GROUPS['essential'] +
                             COLUMN_PRIORITY_GROUPS['important'] +
                             COLUMN_PRIORITY_GROUPS['useful'] +
                             COLUMN_PRIORITY_GROUPS['extended'])
    else:
        if isinstance(selected_columns, str):
            selected_columns = [col.strip().lower() for col in selected_columns.split(',')]
        valid_columns = list(COLUMN_CONFIGS.keys())
        invalid_cols = [col for col in selected_columns if col not in valid_columns]
        if invalid_cols:
            raise ValueError(f"Invalid column names: {', '.join(invalid_cols)}. "
                           f"Valid columns are: {', '.join(valid_columns)}")
        columns_to_show = selected_columns

    effective_width = terminal_width - 5
    console = Console(width=terminal_width)
    # Preserve user-specified column order; auto-selected columns are reordered by priority
    preserve_order = selected_columns is not None
    columns_to_show = _fit_columns_to_terminal(columns_to_show, effective_width, COLUMN_CONFIGS, preserve_order)

    # Warn if user-requested columns were truncated due to narrow terminal
    if preserve_order and selected_columns:
        original_count = len(selected_columns)
        if len(columns_to_show) < original_count:
            console.print(f"[yellow]Warning: Terminal too narrow. Showing {len(columns_to_show)} of {original_count} requested columns.[/yellow]")
            console.print(f"[yellow]Increase terminal width to see all columns.[/yellow]\n")

    if not jobs:
        console.print("\n[yellow]No jobs found matching the criteria.[/yellow]")
        return

    table = _build_job_table(jobs, cloudos_url, effective_width, columns_to_show, COLUMN_CONFIGS)

    if not fetch_page_callback or not pagination_metadata:
        console.print(table)
        legend = _create_status_legend()
        console.print(f"\n{legend}\n")

        if pagination_metadata:
            total_jobs = pagination_metadata.get('Pagination-Count', 0)
            current_page = pagination_metadata.get('Pagination-Page', 1)
            page_size = pagination_metadata.get('Pagination-Limit', 10)
            total_pages = (total_jobs + page_size - 1) // page_size if total_jobs > 0 else 1

            console.print(f"\n[cyan]Showing {len(jobs)} of {total_jobs} total jobs | Page {current_page} of {total_pages}[/cyan]")
        return

    current_page = pagination_metadata.get('Pagination-Page', 1) or 1
    total_jobs = pagination_metadata.get('Pagination-Count', 0)
    page_size_value = pagination_metadata.get('Pagination-Limit', 10)
    total_pages = (total_jobs + page_size_value - 1) // page_size_value if total_jobs > 0 else 1
    show_error = None

    while True:
        console.clear()
        console.print(table)
        legend = _create_status_legend()
        console.print(f"{legend}\n")
        console.print(f"\n[cyan]Total jobs:[/cyan] {total_jobs}")
        if total_pages > 1:
            console.print(f"[cyan]Page:[/cyan] {current_page} of {total_pages}")
            console.print(f"[cyan]Jobs on this page:[/cyan] {len(jobs)}")
        
        # Show error message if any
        if show_error:
            console.print(show_error)
            show_error = None
        
        # Show pagination controls only if there are multiple pages
        if total_pages > 1:
            if not sys.stdin.isatty():
                console.print("\n[yellow]Note: Pagination not available in non-interactive mode. Showing page 1 of {0}.[/yellow]".format(total_pages))
                console.print("[yellow]Run in an interactive terminal to navigate through all pages.[/yellow]")
                break

            console.print(f"\n[bold cyan]n[/] = next, [bold cyan]p[/] = prev, [bold cyan]q[/] = quit")

            try:
                choice = input(">>> ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                console.print("\n[yellow]Pagination interrupted.[/yellow]")
                break

            if choice in ("q", "quit"):
                break
            elif choice in ("n", "next"):
                if current_page < total_pages:
                    try:
                        result = fetch_page_callback(current_page + 1)
                        jobs = result.get('jobs', [])
                        pagination_metadata = result.get('pagination_metadata', {})
                        current_page = pagination_metadata.get('Pagination-Page', current_page + 1)
                        total_pages = pagination_metadata.get('totalPages',
                                                             (pagination_metadata.get('Pagination-Count', 0) + page_size_value - 1) // page_size_value
                                                             if pagination_metadata.get('Pagination-Count', 0) > 0 else 1)
                        table = _build_job_table(jobs, cloudos_url, effective_width, columns_to_show, COLUMN_CONFIGS)
                    except Exception as e:
                        show_error = f"[red]Error fetching page: {str(e)}[/red]"
                else:
                    show_error = "[yellow]Already on last page[/yellow]"
            elif choice in ("p", "prev", "previous"):
                if current_page > 1:
                    try:
                        result = fetch_page_callback(current_page - 1)
                        jobs = result.get('jobs', [])
                        pagination_metadata = result.get('pagination_metadata', {})
                        current_page = pagination_metadata.get('Pagination-Page', current_page - 1)
                        total_pages = pagination_metadata.get('totalPages',
                                                             (pagination_metadata.get('Pagination-Count', 0) + page_size_value - 1) // page_size_value
                                                             if pagination_metadata.get('Pagination-Count', 0) > 0 else 1)
                        table = _build_job_table(jobs, cloudos_url, effective_width, columns_to_show, COLUMN_CONFIGS)
                    except Exception as e:
                        show_error = f"[red]Error fetching page: {str(e)}[/red]"
                else:
                    show_error = "[yellow]Already on first page[/yellow]"
            else:
                show_error = "[yellow]Invalid choice. Use 'n' (next), 'p' (previous), or 'q' (quit)[/yellow]"
        else:
            break


def create_workflow_list_table(workflows, cloudos_url="https://cloudos.lifebit.ai", page_size=10):
    """Display workflows in a rich formatted table with pagination.

    Parameters
    ----------
    workflows : list
        A list of dicts, each corresponding to a workflow.
    cloudos_url : str
        The CloudOS URL for creating hyperlinks.
    page_size : int
        Number of workflows to display per page. Default is 10.
    """
    console = Console()

    # Handle empty workflow list
    if len(workflows) == 0:
        console.print("\n[yellow]No workflows found in this workspace.[/yellow]")
        return

    # Prepare rows data
    rows = []
    for workflow in workflows:
        # Get workflow ID for the hyperlink
        workflow_id = str(workflow.get("_id", "N/A"))
        workflow_url = f"{cloudos_url}/app/advanced-analytics/pipelines-and-tools/workspace/{workflow_id}"
        
        # Name with hyperlink
        name = str(workflow.get("name", "N/A"))
        name_with_link = f"[link={workflow_url}]{name}[/link]"

        # Archived status
        # archived_status = workflow.get("archived", {})
        # if isinstance(archived_status, dict):
        #     archived = str(archived_status.get("status", "N/A"))
        # else:
        #     archived = str(archived_status)

        # Repository name
        repository = workflow.get("repository", {})
        repo_name = str(repository.get("name", "N/A"))
        repo_url = str(repository.get("url", "N/A"))
        
        # Create hyperlink for repository name if URL is available
        if repo_url != "N/A" and repo_url:
            repo_name_with_link = f"[link={repo_url}]{repo_name}[/link]"
        else:
            repo_name_with_link = repo_name

        # Repository platform
        #repo_platform = str(repository.get("platform", "N/A"))

        # Repository URL
        #repo_url = str(repository.get("url", "N/A"))

        # Is private
        # is_private = str(repository.get("isPrivate", "N/A"))

        rows.append([
            name_with_link,
            #archived,
            repo_name_with_link,
            #repo_platform,
            #repo_url,
            #is_private
        ])

    # Pagination
    current_page = 0
    total_pages = (len(rows) + page_size - 1) // page_size if len(rows) > 0 else 1
    show_error = None  # Track error messages to display

    while True:
        start = current_page * page_size
        end = start + page_size

        # Clear console first
        console.clear()

        # Create and display table
        table = Table(title="Workflow List")

        # Add columns
        table.add_column("Name", style="green", overflow="fold")
        #table.add_column("Archived", style="yellow", no_wrap=True)
        table.add_column("Repository", style="cyan", overflow="fold")
        #table.add_column("Platform", style="green", no_wrap=True)
        #table.add_column("Repository URL", style="blue", overflow="fold")
        #table.add_column("Private", style="red", no_wrap=True)

        # Get rows for current page
        page_rows = rows[start:end]

        # Add rows to table
        for row in page_rows:
            table.add_row(*row)

        # Print table
        console.print(table)

        # Display total count and page info
        console.print(f"\n[cyan]Total workflows:[/cyan] {len(workflows)}")
        if total_pages > 1:
            console.print(f"[cyan]Page:[/cyan] {current_page + 1} of {total_pages}")
            console.print(f"[cyan]Workflows on this page:[/cyan] {len(page_rows)}")

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


def create_queue_list_table(queues, cloudos_url="https://cloudos.lifebit.ai"):
    """Display job queues in a rich formatted table.

    Parameters
    ----------
    queues : list
        A list of dicts, each corresponding to a job queue.
    cloudos_url : str
        The CloudOS URL for context (currently not used for hyperlinks).

    Returns
    -------
    None
        Prints the formatted table to console.
    """
    console = Console()

    # Handle empty queue list
    if len(queues) == 0:
        console.print("\n[yellow]No job queues found in this workspace.[/yellow]")
        return

    # Create table
    table = Table(title="Job Queue List")

    # Add columns
    table.add_column("Label", style="green", overflow="fold", min_width=10)
    table.add_column("Default", style="cyan", no_wrap=True, min_width=7, justify="center")
    table.add_column("Resource Type", style="magenta", overflow="fold", min_width=12)
    table.add_column("Status", style="yellow", no_wrap=True, min_width=8, justify="center")

    # Process each queue
    for queue in queues:
        # Label
        label = str(queue.get("label", "N/A"))

        # Default (show as checkmark or dash)
        is_default = queue.get("isDefault", False)
        if is_default:
            default_display = "[bold green]Default[/bold green]"
        else:
            default_display = "[dim]—[/dim]"

        # Resource Type
        resource_type = str(queue.get("resourceType", "N/A"))
        if not resource_type or resource_type == "":
            resource_type = "N/A"
        elif resource_type == "teamBatchJobQueue":
            resource_type = "Batch Queues"
        elif resource_type == "systemBatchJobQueue":
            resource_type = "System Queue"

        # Status with checkmark/X icons
        status_raw = str(queue.get("status", "N/A"))
        if status_raw.lower() == "ready":
            status = "[bold green]Ready[/bold green]"
        else:
            status = "[bold red]Not Ready[/bold red]"

        # Add row
        table.add_row(label, default_display, resource_type, status)

    # Print table
    console.print(table)

    # Display total count
    console.print(f"\n[cyan]Total job queues:[/cyan] {len(queues)}")


def create_project_list_table(projects, cloudos_url="https://cloudos.lifebit.ai", page_size=10):
    """Display projects in a rich formatted table with pagination.

    Parameters
    ----------
    projects : list
        A list of dicts, each corresponding to a project.
    cloudos_url : str
        The CloudOS URL for creating hyperlinks.
    page_size : int
        Number of projects to display per page. Default is 10.
    """
    console = Console()

    # Handle empty project list
    if len(projects) == 0:
        console.print("\n[yellow]No projects found in this workspace.[/yellow]")
        return

    # Prepare rows data
    rows = []
    for project in projects:
        # Name with hyperlink
        project_id = str(project.get("_id", "N/A"))
        project_url = f"{cloudos_url}/app/data-science/datasets/projects/{project_id}"
        name = str(project.get("name", "N/A"))
        name_with_link = f"[link={project_url}]{name}[/link]"

        # User (combine name and surname)
        user_info = project.get("user", {})
        user_name = user_info.get("name", "")
        user_surname = user_info.get("surname", "")
        if user_name and user_surname:
            user = f"{user_name} {user_surname}"
        elif user_name:
            user = user_name
        elif user_surname:
            user = user_surname
        else:
            user = "N/A"

        # Created date (format: yyyy.mm.dd)
        created_at = project.get("createdAt")
        if created_at:
            try:
                created_dt = datetime.fromisoformat(str(created_at).replace('Z', '+00:00'))
                created = created_dt.strftime('%Y.%m.%d')
            except (ValueError, TypeError):
                created = "N/A"
        else:
            created = "N/A"

        # Updated date (format: yyyy.mm.dd)
        updated_at = project.get("updatedAt")
        if updated_at:
            try:
                updated_dt = datetime.fromisoformat(str(updated_at).replace('Z', '+00:00'))
                updated = updated_dt.strftime('%Y.%m.%d')
            except (ValueError, TypeError):
                updated = "N/A"
        else:
            updated = "N/A"

        # Job count
        job_count = str(project.get("jobCount", 0))

        # Notebook session count
        notebook_count = str(project.get("notebookSessionCount", 0))

        rows.append([
            name_with_link,
            user,
            created,
            updated,
            job_count,
            notebook_count
        ])

    # Pagination
    current_page = 0
    total_pages = (len(rows) + page_size - 1) // page_size if len(rows) > 0 else 1
    show_error = None  # Track error messages to display

    while True:
        start = current_page * page_size
        end = start + page_size

        # Clear console first
        console.clear()

        # Create and display table
        table = Table(title="Project List")

        # Add columns
        table.add_column("Name", style="green", overflow="fold", min_width=15)
        table.add_column("User", style="cyan", overflow="ellipsis", min_width=12, max_width=20)
        table.add_column("Created", style="magenta", no_wrap=True, min_width=10)
        table.add_column("Updated", style="blue", no_wrap=True, min_width=10)
        table.add_column("Jobs", style="yellow", no_wrap=True, min_width=4, justify="right")
        table.add_column("Notebooks", style="white", no_wrap=True, min_width=9, justify="right")

        # Get rows for current page
        page_rows = rows[start:end]

        # Add rows to table
        for row in page_rows:
            table.add_row(*row)

        # Print table
        console.print(table)

        # Display total count and page info
        console.print(f"\n[cyan]Total projects:[/cyan] {len(projects)}")
        if total_pages > 1:
            console.print(f"[cyan]Page:[/cyan] {current_page + 1} of {total_pages}")
            console.print(f"[cyan]Projects on this page:[/cyan] {len(page_rows)}")

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

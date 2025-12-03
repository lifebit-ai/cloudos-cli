from datetime import datetime
from rich.console import Console
from rich.table import Table
import json
import csv


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

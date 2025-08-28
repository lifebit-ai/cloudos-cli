"""
This is the main class of the package.
"""

import requests
import time
import json
from dataclasses import dataclass
from cloudos_cli.utils.cloud import find_cloud
from cloudos_cli.utils.errors import BadRequestException, JoBNotCompletedException, NotAuthorisedException
from cloudos_cli.utils.requests import retry_requests_get, retry_requests_post, retry_requests_put
import pandas as pd
from cloudos_cli.utils.last_wf import youngest_workflow_id_by_name
from datetime import datetime


# GLOBAL VARS
JOB_COMPLETED = 'completed'
JOB_FAILED = 'failed'
JOB_ABORTED = 'aborted'


@dataclass
class Cloudos:
    """A simple class to contain the required connection information.

    Parameters
    ----------
    cloudos_url : string
        The CloudOS service url.
    apikey : string
        Your CloudOS API key.
    cromwell_token : string
        Cromwell server token. If None, apikey will be used instead.
    """
    cloudos_url: str
    apikey: str
    cromwell_token: str

    def get_job_status(self, j_id, verify=True):
        """Get job status from CloudOS.

        Parameters
        ----------
        j_id : string
            The CloudOS job id of the job just launched.
        verify: [bool|string]
            Whether to use SSL verification or not. Alternatively, if
            a string is passed, it will be interpreted as the path to
            the SSL certificate file.

        Returns
        -------
        r : requests.models.Response
            The server response
        """
        cloudos_url = self.cloudos_url
        apikey = self.apikey
        headers = {
            "Content-type": "application/json",
            "apikey": apikey
        }
        r = retry_requests_get("{}/api/v1/jobs/{}".format(cloudos_url,
                                                          j_id),
                               headers=headers, verify=verify)
        if r.status_code >= 400:
            raise BadRequestException(r)
        return r

    def wait_job_completion(self, job_id, wait_time=3600, request_interval=30, verbose=False,
                            verify=True):
        """Checks job status from CloudOS and wait for its complation.

        Parameters
        ----------
        j_id : string
            The CloudOS job id of the job just launched.
        wait_time : int
            Max time to wait (in seconds) to job completion.
        request_interval : int
            Time interval (in seconds) to request job status.
        verbose : bool
            Whether to output status on every request or not.
        verify: [bool|string]
            Whether to use SSL verification or not. Alternatively, if
            a string is passed, it will be interpreted as the path to
            the SSL certificate file.

        Returns
        -------
        : dict
            A dict with three elements collected from the job status: 'name', 'id', 'status'.
        """
        j_url = f'{self.cloudos_url}/app/advanced-analytics/analyses/{job_id}'
        elapsed = 0
        j_status_h_old = ''
        # make sure user doesn't surpass the wait time
        if request_interval > wait_time:
            request_interval = wait_time
        while elapsed < wait_time:
            j_status = self.get_job_status(job_id, verify)
            j_status_content = json.loads(j_status.content)
            j_status_h = j_status_content["status"]
            j_name = j_status_content["name"]
            if j_status_h == JOB_COMPLETED:
                if verbose:
                    print(f'\tYour job "{j_name}" (ID: {job_id}) took {elapsed} seconds to complete ' +
                          'successfully.')
                return {'name': j_name, 'id': job_id, 'status': j_status_h}
            elif j_status_h == JOB_FAILED:
                if verbose:
                    print(f'\tYour job "{j_name}" (ID: {job_id}) took {elapsed} seconds to fail.')
                return {'name': j_name, 'id': job_id, 'status': j_status_h}
            elif j_status_h == JOB_ABORTED:
                if verbose:
                    print(f'\tYour job "{j_name}" (ID: {job_id}) took {elapsed} seconds to abort.')
                return {'name': j_name, 'id': job_id, 'status': j_status_h}
            else:
                elapsed += request_interval
                if j_status_h != j_status_h_old:
                    if verbose:
                        print(f'\tYour current job "{j_name}" (ID: {job_id}) status is: {j_status_h}.')
                    j_status_h_old = j_status_h
                time.sleep(request_interval)
        j_status = self.get_job_status(job_id, verify)
        j_status_content = json.loads(j_status.content)
        j_status_h = j_status_content["status"]
        j_name = j_status_content["name"]
        if j_status_h != JOB_COMPLETED and verbose:
            print(f'\tYour current job "{j_name}" (ID: {job_id}) status is: {j_status_h}. The ' +
                  f'selected wait-time of {wait_time} was exceeded. Please, ' +
                  'consider to set a longer wait-time.')
            print('\tTo further check your job status you can either go to ' +
                  f'{j_url} or use the following command:\n' +
                  '\tcloudos job status \\\n' +
                  '\t\t--apikey $MY_API_KEY \\\n' +
                  f'\t\t--cloudos-url {self.cloudos_url} \\\n' +
                  f'\t\t--job-id {job_id}\n')
        return {'name': j_name, 'id': job_id, 'status': j_status_h}

    def get_storage_contents(self,  cloud_name, cloud_meta, container, path, workspace_id, verify):
        """
        Retrieves the contents of a storage container from the specified cloud service.

        This method fetches the contents of a specified path within a storage container
        on a cloud service (e.g., AWS S3 or Azure Blob). The request is authenticated
        using an API key and requires valid parameters such as the workspace ID and path.

        Parameters:
            cloud_name (str): The name of the cloud service (e.g., 'aws' or 'azure').
            container (str): The name of the storage container or bucket.
            path (str): The file path or directory within the storage container.
            workspace_id (str): The identifier of the workspace or team.
            verify (bool): Whether to verify SSL certificates for the request.

        Returns:
            list: A list of contents retrieved from the specified cloud storage.

        Raises:
            BadRequestException: If the request to retrieve the contents fails with a
            status code indicating an error.
        """
        headers = {
            "Content-type": "application/json",
            "apikey": self.apikey
        }
        cloud_data = {
            "aws": {
                "url": f"{self.cloudos_url}/api/v1/data-access/s3/bucket-contents",
                "params": {
                    "bucket": container,
                    "path": path,
                    "teamId": workspace_id
                }
            },
            "azure": {
                "url": f"{self.cloudos_url}/api/v1/data-access/azure/container-contents",
                "container": "containerName",
                "params": {
                    "containerName": container,
                    "path": path + "/",
                    "storageAccountName": "",
                    "teamId": workspace_id
                }
            }
        }
        if cloud_name == "azure":
            cloud_data[cloud_name]["params"]["storageAccountName"] = cloud_meta["storage"]["storageAccount"]
        params = cloud_data[cloud_name]["params"]
        contents_req = retry_requests_get(cloud_data[cloud_name]["url"], params=params, headers=headers, verify=verify)
        if contents_req.status_code >= 400:
            raise BadRequestException(contents_req)
        return contents_req.json()["contents"]

    def get_job_logs(self, j_id, workspace_id, verify=True):
        """
        Get the location of the logs for the specified job
        """
        cloudos_url = self.cloudos_url
        apikey = self.apikey
        headers = {
            "Content-type": "application/json",
            "apikey": apikey
        }
        r = retry_requests_get(f"{cloudos_url}/api/v1/jobs/{j_id}", headers=headers, verify=verify)
        if r.status_code == 401:
            raise NotAuthorisedException
        elif r.status_code >= 400:
            raise BadRequestException(r)
        r_json = r.json()
        logs_obj = r_json["logs"]
        job_workspace = r_json["team"]
        if job_workspace != workspace_id:
            raise ValueError("Workspace provided or configured is different from workspace where the job was executed")
        cloud_name, cloud_meta, cloud_storage = find_cloud(self.cloudos_url, self.apikey, workspace_id, logs_obj)
        container_name = cloud_storage["container"]
        prefix_name = cloud_storage["prefix"]
        logs_bucket = logs_obj[container_name]
        logs_path = logs_obj[prefix_name]
        contents_obj = self.get_storage_contents(cloud_name, cloud_meta, logs_bucket, logs_path, workspace_id, verify)
        logs = {}
        cloude_scheme = cloud_storage["scheme"]
        storage_account_prefix = ''
        if cloude_scheme == 'az':
            storage_account_prefix = f'{workspace_id}.blob.core.windows.net/'
        for item in contents_obj:
            if not item["isDir"]:
                filename = item["name"]
                if filename == "stdout.txt":
                    filename = "Nextflow standard output"
                if filename == ".nextflow.log":
                    filename = "Nextflow log"
                if filename == "trace.txt":
                    filename = "Trace file"
                logs[filename] = f"{cloude_scheme}://{storage_account_prefix}{logs_bucket}/{item['path']}"
        return logs

    def get_job_results(self, j_id, workspace_id, verify=True):
        """
        Get the location of the results for the specified job
        """
        cloudos_url = self.cloudos_url
        apikey = self.apikey
        headers = {
            "Content-type": "application/json",
            "apikey": apikey
        }
        status = self.get_job_status(j_id, verify).json()["status"]
        if status != JOB_COMPLETED:
            raise JoBNotCompletedException(j_id, status)

        r = retry_requests_get(f"{cloudos_url}/api/v1/jobs/{j_id}",
                               headers=headers, verify=verify)
        if r.status_code == 401:
            raise NotAuthorisedException
        if r.status_code >= 400:
            raise BadRequestException(r)
        req_obj = r.json()
        job_workspace = req_obj["team"]
        if job_workspace != workspace_id:
            raise ValueError("Workspace provided or configured is different from workspace where the job was executed")
        cloud_name, meta, cloud_storage = find_cloud(self.cloudos_url, self.apikey, workspace_id, req_obj["logs"])
        # cont_name
        results_obj = req_obj["results"]
        results_container = results_obj[cloud_storage["container"]]
        results_path = results_obj[cloud_storage["prefix"]]
        scheme = cloud_storage["scheme"]
        contents_obj = self.get_storage_contents(cloud_name, meta, results_container,
                                                 results_path, workspace_id, verify)
        storage_account_prefix = ''
        if scheme == 'az':
            storage_account_prefix = f'{workspace_id}.blob.core.windows.net/'
        results = dict()
        for item in contents_obj:
            if item["isDir"]:
                filename = item["name"]
                results[filename] = f"{scheme}://{storage_account_prefix}{results_container}/{item['path']}"
        return results

    def _create_cromwell_header(self):
        """Generates cromwell header.

        This methods is responsible for using personal API key instead of
        specific Cromwell API when the later is not provided.

        Returns
        -------
        headers : dict
            The correct headers based on using cromwell specific token or
            personal API key.
        """
        if self.cromwell_token is None:
            headers = {
                "Accept": "application/json",
                "apikey": self.apikey
            }
        else:
            headers = {
                "Accept": "application/json",
                "Authorization": f'Bearer {self.cromwell_token}'
            }
        return headers

    def get_cromwell_status(self, workspace_id, verify=True):
        """Get Cromwell server status from CloudOS.

        Parameters
        ----------
        workspace_id : string
            The CloudOS workspace id from to check the Cromwell status.
        verify: [bool|string]
            Whether to use SSL verification or not. Alternatively, if
            a string is passed, it will be interpreted as the path to
            the SSL certificate file.

        Returns
        -------
        r : requests.models.Response
            The server response
        """
        cloudos_url = self.cloudos_url
        headers = self._create_cromwell_header()
        r = retry_requests_get("{}/api/v1/cromwell?teamId={}".format(cloudos_url,
                                                                     workspace_id),
                               headers=headers, verify=verify)
        if r.status_code >= 400:
            raise BadRequestException(r)
        return r

    def cromwell_switch(self, workspace_id, action, verify=True):
        """Restart Cromwell server.

        Parameters
        ----------
        workspace_id : string
            The CloudOS workspace id in which restart/stop Cromwell status.
        action : string [restart|stop]
            The action to perform.
        verify: [bool|string]
            Whether to use SSL verification or not. Alternatively, if
            a string is passed, it will be interpreted as the path to
            the SSL certificate file.

        Returns
        -------
        r : requests.models.Response
            The server response
        """
        cloudos_url = self.cloudos_url
        headers = self._create_cromwell_header()
        r = requests.put("{}/api/v1/cromwell/{}?teamId={}".format(cloudos_url,
                                                                  action,
                                                                  workspace_id),
                         headers=headers, verify=verify)
        if r.status_code >= 400:
            raise BadRequestException(r)
        return r

    def get_job_list(self, workspace_id, last_n_jobs=30, page=1, archived=False,
                     verify=True, filter_status=None, filter_job_name=None,
                     filter_project=None, filter_workflow=None, filter_job_id=None,
                     filter_only_mine=False, filter_owner=None, filter_queue=None, last=False):
        """Get jobs from a CloudOS workspace with optional filtering.
        
        Fetches jobs page by page, applies all filters after fetching.
        Stops when enough jobs are collected or no more jobs are available.

        Parameters
        ----------
        workspace_id : string
            The CloudOS workspace id from to collect the jobs.
        last_n_jobs : [int | 'all']
            How many of the last jobs from the user to retrieve. You can specify a
            very large int or 'all' to get all user's jobs.
        page : int
            Response page to get (ignored when using filters - starts from page 1).
        archived : bool
            When True, only the archived jobs are retrieved.
        verify: [bool|string]
            Whether to use SSL verification or not. Alternatively, if
            a string is passed, it will be interpreted as the path to
            the SSL certificate file.
        filter_status : string, optional
            Filter jobs by status (e.g., 'completed', 'running', 'failed').
        filter_job_name : string, optional
            Filter jobs by name.
        filter_project : string, optional
            Filter jobs by project name (will be resolved to project ID).
        filter_workflow : string, optional
            Filter jobs by workflow name (will be resolved to workflow ID).
        filter_job_id : string, optional
            Filter jobs by specific job ID.
        filter_only_mine : bool, optional
            Filter to show only jobs belonging to the current user.
        filter_queue : string, optional
            Filter jobs by queue name (will be resolved to queue ID).
            Only applies to jobs running in batch environment.
            Non-batch jobs are preserved in results as they don't use queues.
        last : bool, optional
            When workflows are duplicated, use the latest imported workflow (by date).

        Returns
        -------
        r : list
            A list of dicts, each corresponding to a jobs from the user and the workspace.
        """
        if not workspace_id or not isinstance(workspace_id, str):
            raise ValueError("Invalid workspace_id: must be a non-empty string")
    
        if last_n_jobs != 'all' and (not isinstance(last_n_jobs, int) or last_n_jobs <= 0):
            raise ValueError("last_n_jobs must be a positive integer or 'all'")
        
        # Validate filter_status values
        if filter_status:
            valid_statuses = ['completed', 'running', 'failed', 'aborted', 'queued', 'pending', 'initializing']
            if filter_status.lower() not in valid_statuses:
                raise ValueError(f"Invalid filter_status '{filter_status}'. Valid values: {', '.join(valid_statuses)}")

        headers = {
            "Content-type": "application/json",
            "apikey": self.apikey
        }
        
        # Build query parameters for server-side filtering
        params = {
            "teamId": workspace_id,
            "archived.status": str(archived).lower(),
            "limit": 100,  # Use a reasonable page size
            "page": 1     # Always start from page 1
        }
        
        # --- Resolve IDs once (before pagination loop) ---
        
        # Add simple server-side filters
        if filter_status:
            params["status"] = filter_status.lower()
        if filter_job_name:
            params["name"] = filter_job_name
        if filter_job_id:
            params["id"] = filter_job_id
            
        # Resolve project name to ID
        if filter_project:
            try:
                project_id = self.get_project_id_from_name(workspace_id, filter_project, verify=verify)
                if project_id:
                    params["project.id"] = project_id
                else:
                    raise ValueError(f"Project '{filter_project}' not found.")
            except Exception as e:
                raise ValueError(f"Error resolving project '{filter_project}': {str(e)}")
        
        # Resolve workflow name to ID
        if filter_workflow:
            try:
                workflow_content = self.get_workflow_content(workspace_id, filter_workflow, verify=verify, last=last)
                if workflow_content and workflow_content.get("workflows"):
                    # Extract the first (and should be only) workflow from the list
                    workflow = workflow_content["workflows"][0]
                    workflow_id = workflow.get("_id")
                    if workflow_id:
                        params["workflow.id"] = workflow_id
                    else:
                        raise ValueError(f"Workflow '{filter_workflow}' not found.")
                else:
                    raise ValueError(f"Workflow '{filter_workflow}' not found.")
            except Exception as e:
                raise ValueError(f"Error resolving workflow '{filter_workflow}': {str(e)}")
        
        # Get current user ID for filter_only_mine
        if filter_only_mine:
            try:
                user_info = self.get_user_info(verify=verify)
                user_id = user_info.get("id") or user_info.get("_id")
                if user_id:
                    params["user.id"] = user_id
                else:
                    raise ValueError("Could not retrieve current user information.")
            except Exception as e:
                raise ValueError(f"Error getting current user info: {str(e)}")
        

        # --- Fetch jobs page by page ---
        all_jobs = []
        current_page = 1
        
        while True:
            params["page"] = current_page
            
            r = retry_requests_get(f"{self.cloudos_url}/api/v2/jobs", params=params, headers=headers, verify=verify)
            if r.status_code >= 400:
                raise BadRequestException(r)
            
            content = r.json()
            page_jobs = content.get('jobs', [])
            
            # No jobs returned, we've reached the end
            if not page_jobs:
                break
                
            all_jobs.extend(page_jobs)
            
            # Check if we have enough jobs or reached the last page
            if last_n_jobs != 'all' and len(all_jobs) >= last_n_jobs:
                break
            if len(page_jobs) < params["limit"]:
                break  # Last page (fewer jobs than requested page size)
                
            current_page += 1

        # --- Local queue filtering (not supported by API) ---
        if filter_queue:
            try:
                batch_jobs=[job for job in all_jobs if job.get("batch", {})]
                if batch_jobs:
                    from cloudos_cli.queue.queue import Queue
                    queue_api = Queue(self.cloudos_url, self.apikey, self.cromwell_token, workspace_id, verify)
                    queues = queue_api.get_job_queues()
                    
                    queue_id = None
                    for queue in queues:
                        if queue.get("label") == filter_queue or queue.get("name") == filter_queue:
                            queue_id = queue.get("id") or queue.get("_id")
                            break
                    
                    if not queue_id:
                        raise ValueError(f"Queue with name '{filter_queue}' not found in workspace '{workspace_id}'")
                    
                    all_jobs = [job for job in all_jobs if job.get("batch", {}).get("jobQueue", {}).get("id") == queue_id]
                else:
                    raise ValueError(f"The environment is not a batch environment so queues do not exist. Please remove the --filter-queue option.")
            except Exception as e:
                raise ValueError(f"Error filtering by queue '{filter_queue}': {str(e)}")

        # --- Apply limit after all filtering ---
        if last_n_jobs != 'all' and isinstance(last_n_jobs, int) and last_n_jobs > 0:
            all_jobs = all_jobs[:last_n_jobs]

        return all_jobs

    @staticmethod
    def process_job_list(r, all_fields=False):
        """Process a job list from a self.get_job_list call.

        Parameters
        ----------
        r : list
            A list of dicts, each corresponding to a job from the user and the workspace.
        all_fields : bool. Default=False
            Whether to return a reduced version of the DataFrame containing
            only the selected columns or the full DataFrame.

        Returns
        -------
        df : pandas.DataFrame
            A DataFrame with the requested columns from the jobs.
        """
        COLUMNS = ['status',
                   'name',
                   'project.name',
                   'user.name',
                   'user.surname',
                   'workflow.name',
                   '_id',
                   'startTime',
                   'endTime',
                   'createdAt',
                   'updatedAt',
                   'revision.commit',
                   'realInstancesExecutionCost',
                   'masterInstance.usedInstance.type',
                   'storageMode',
                   'workflow.repository.url',
                   'nextflowVersion',
                   'batch.enabled',
                   'storageSizeInGb',
                   'batch.jobQueue.id',
                   'usesFusionFileSystem'
                   ]
        df_full = pd.json_normalize(r)
        if df_full.empty:
            return df_full
        if all_fields:
            df = df_full
        else:
            # Only select columns that actually exist in the DataFrame
            existing_columns = [col for col in COLUMNS if col in df_full.columns]
            if existing_columns:
                df = df_full.loc[:, existing_columns]
            else:
                # If none of the predefined columns exist, raise missing error
                raise ValueError(f"None of the predefined columns {COLUMNS} exist in retrieved columns:{list(df_full.columns)}")
        return df

    def reorder_job_list(self, my_jobs_df, filename='my_jobs.csv'):
        """Save a job list DataFrame to a CSV file with renamed and ordered columns.

        Parameters
        ----------
        my_jobs_df : pandas.DataFrame
            A DataFrame containing job information from process_job_list.
        filename : str
            The name of the file to save the DataFrame to. Default is 'my_jobs.csv'.

        Returns
        -------
        None
            Saves the DataFrame to a CSV file with renamed and ordered columns.
        """
        # Handle empty DataFrame
        if my_jobs_df.empty:
            print("Warning: DataFrame is empty. Creating empty CSV file.")
            empty_df = pd.DataFrame()
            empty_df.to_csv(filename, index=False)
            return

        # Create a copy to avoid modifying the original DataFrame
        jobs_df = my_jobs_df.copy()

        # 1. Fusion user.name and user.surname into user
        if 'user.name' in jobs_df.columns and 'user.surname' in jobs_df.columns:
            jobs_df['user'] = jobs_df.apply(
                lambda row: f"{row.get('user.name', '')} {row.get('user.surname', '')}".strip()
                if pd.notna(row.get('user.name')) or pd.notna(row.get('user.surname'))
                else None, axis=1
            )
            # Remove original columns
            jobs_df = jobs_df.drop(columns=['user.name', 'user.surname'], errors='ignore')

        # 2. Convert time fields to human-readable format
        time_columns = ['startTime', 'endTime', 'createdAt', 'updatedAt']
        for col in time_columns:
            if col in jobs_df.columns:
                def format_time(x):
                    if pd.notna(x) and isinstance(x, str) and x:
                        try:
                            return datetime.fromisoformat(x.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S UTC')
                        except (ValueError, TypeError):
                            return x  # Return original value if parsing fails
                    return None
                jobs_df[col] = jobs_df[col].apply(format_time)

        # 3. Format realInstancesExecutionCost (divide by 100, show 4 decimals)
        if 'realInstancesExecutionCost' in jobs_df.columns:
            def format_cost(x):
                if pd.notna(x) and x != '' and x is not None:
                    try:
                        return f"{float(x) / 100:.4f}"
                    except (ValueError, TypeError):
                        return x  # Return original value if conversion fails
                return None
            jobs_df['realInstancesExecutionCost'] = jobs_df['realInstancesExecutionCost'].apply(format_cost)

        # 4. Calculate Run time (endTime - startTime)
        if 'startTime' in jobs_df.columns and 'endTime' in jobs_df.columns:
            def calculate_runtime(row):
                start_time = row.get('startTime')
                end_time = row.get('endTime')
                if pd.notna(start_time) and pd.notna(end_time) and start_time and end_time:
                    # Use original times from the original DataFrame for calculation
                    original_start = my_jobs_df.iloc[row.name].get('startTime') if row.name < len(my_jobs_df) else start_time
                    original_end = my_jobs_df.iloc[row.name].get('endTime') if row.name < len(my_jobs_df) else end_time
                    if pd.notna(original_start) and pd.notna(original_end) and original_start and original_end:
                        try:
                            start_dt = datetime.fromisoformat(str(original_start).replace('Z', '+00:00'))
                            end_dt = datetime.fromisoformat(str(original_end).replace('Z', '+00:00'))
                            duration = end_dt - start_dt
                            # Format duration as hours:minutes:seconds
                            total_seconds = int(duration.total_seconds())
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
                            return None
                return None

            jobs_df['Run time'] = jobs_df.apply(calculate_runtime, axis=1)

        # 5. Format batch.enabled (True -> "Batch", else "N/A")
        if 'batch.enabled' in jobs_df.columns:
            jobs_df['batch.enabled'] = jobs_df['batch.enabled'].apply(
                lambda x: "Batch" if x is True else "N/A"
            )

        # 6. Rename columns using the provided dictionary
        column_name_mapping = {
            "status": "Status",
            "name": "Name",
            "project.name": "Project",
            "user": "Owner",
            "workflow.name": "Pipeline",
            "_id": "ID",
            "createdAt": "Submit time",
            "updatedAt": "End time",
            "revision.commit": "Commit",
            "realInstancesExecutionCost": "Cost",
            "masterInstance.usedInstance.type": "Resources",
            "storageMode": "Storage type",
            "workflow.repository.url": "Pipeline url",
            "nextflowVersion": "Nextflow version",
            "batch.enabled": "Executor",
            "storageSizeInGb": "Storage size",
            "batch.jobQueue.id": "Job queue ID",
            "usesFusionFileSystem": "Accelerated file staging"
        }

        # Rename columns that exist in the DataFrame
        jobs_df = jobs_df.rename(columns=column_name_mapping)

        # Remove the original startTime and endTime columns since we now have Submit time, End time, and Run time
        jobs_df = jobs_df.drop(columns=['startTime', 'endTime'], errors='ignore')

        # 7. Define the desired order of columns
        desired_order = [
            "Status", "Name", "Project", "Owner", "Pipeline", "ID",
            "Submit time", "End time", "Run time", "Commit", "Cost",
            "Resources", "Storage type", "Pipeline url",
            "Nextflow version", "Executor", "Storage size", "Job queue ID",
            "Accelerated file staging"
        ]

        # Reorder columns - only include columns that exist in the DataFrame
        available_columns = [col for col in desired_order if col in jobs_df.columns]
        # Add any remaining columns that aren't in the desired order
        remaining_columns = [col for col in jobs_df.columns if col not in desired_order]
        final_column_order = available_columns + remaining_columns

        # Reorder the DataFrame
        jobs_df = jobs_df[final_column_order]
        return jobs_df

    def save_job_list_to_csv(self, my_jobs_df, filename='my_jobs.csv'):
        # Save to CSV
        jobs_df = self.reorder_job_list(my_jobs_df, filename)
        jobs_df.to_csv(filename, index=False)
        print(f'\tJob list collected with a total of {len(jobs_df)} jobs.')
        print(f'\tJob list saved to {filename}')

    def get_workflow_list(self, workspace_id, verify=True, get_all=True,
                          page=1, page_size=10, max_page_size=100,
                          archived_status=False):
        """Get all the workflows from a CloudOS workspace.

        Parameters
        ----------
        workspace_id : string
            The CloudOS workspace id from to collect the workflows.
        verify : [bool|string]
            Whether to use SSL verification or not. Alternatively, if
            a string is passed, it will be interpreted as the path to
            the SSL certificate file.
        get_all : bool
            Whether to get all available curated workflows or just the
            indicated page.
        page : int
            The page number to retrieve, from the paginated response.
        page_size : int
            The number of workflows by page. From 1 to 1000.
        max_page_size : int
            Max page size defined by the API server. It is currently 1000.
        archived_status : bool
            Whether to retrieve archived workflows or not.

        Returns
        -------
        r : list
            A list of dicts, each corresponding to a workflow.
        """
        headers = {
            "Content-type": "application/json",
            "apikey": self.apikey
        }
        archived_status = str(archived_status).lower()
        r = retry_requests_get(
            "{}/api/v3/workflows?teamId={}&pageSize={}&page={}&archived.status={}".format(
                self.cloudos_url, workspace_id, page_size, page, archived_status),
            headers=headers, verify=verify)
        if r.status_code >= 400:
            raise BadRequestException(r)
        content = json.loads(r.content)
        if get_all:
            total_workflows = content['paginationMetadata']['Pagination-Count']
            if total_workflows <= max_page_size:
                r = retry_requests_get(
                    "{}/api/v3/workflows?teamId={}&pageSize={}&page={}&archived.status={}".format(
                        self.cloudos_url, workspace_id, total_workflows, 1, archived_status),
                    headers=headers, verify=verify)
                if r.status_code >= 400:
                    raise BadRequestException(r)
                return json.loads(r.content)['workflows']
            else:
                n_pages = (total_workflows // max_page_size) + int((total_workflows % max_page_size) > 0)
                for p in range(n_pages):
                    p += 1
                    r = retry_requests_get(
                        "{}/api/v3/workflows?teamId={}&pageSize={}&page={}&archived.status={}".format(
                            self.cloudos_url, workspace_id, max_page_size, p, archived_status),
                        headers=headers, verify=verify)
                    if r.status_code >= 400:
                        raise BadRequestException(r)
                    if p == 1:
                        all_content = json.loads(r.content)['workflows']
                    else:
                        all_content += json.loads(r.content)['workflows']
                return all_content
        else:
            return content['workflows']

    @staticmethod
    def process_workflow_list(r, all_fields=False):
        """Process a server response from a self.get_workflow_list call.

        Parameters
        ----------
        r : list
            A list of dicts, each corresponding to a workflow.
        all_fields : bool. Default=False
            Whether to return a reduced version of the DataFrame containing
            only the selected columns or the full DataFrame.

        Returns
        -------
        df : pandas.DataFrame
            A DataFrame with the requested columns from the workflows.
        """
        COLUMNS = ['_id',
                   'name',
                   'archived.status',
                   'mainFile',
                   'workflowType',
                   'group',
                   'repository.name',
                   'repository.platform',
                   'repository.url',
                   'repository.isPrivate'
                   ]
        df_full = pd.json_normalize(r)
        if all_fields:
            df = df_full
        else:
            present_columns = []
            for column in COLUMNS:
                if column in df_full.columns:
                    present_columns.append(column)
            df = df_full.loc[:, present_columns]
        return df

    def detect_workflow(self, workflow_name, workspace_id, verify=True, last=False):
        """Detects workflow type: nextflow or wdl.

        Parameters
        ----------
        workflow_name : string
            Name of the workflow.
        workspace_id : string
            The CloudOS workspace id from to collect the workflows.
        verify: [bool|string]
            Whether to use SSL verification or not. Alternatively, if
            a string is passed, it will be interpreted as the path to
            the SSL certificate file.

        Returns
        -------
        wt : string ['nextflow'|'wdl']
            The workflow type detected
        """
        # get list with workflow types
        wt_all = self.workflow_content_query(workspace_id, workflow_name, verify=verify, query="workflowType", last=last)
        # make unique
        wt = list(dict.fromkeys(wt_all))
        if len(wt) > 1:
            raise ValueError(f'More than one workflow type detected for {workflow_name}: {wt}')
        return str(wt[0])

    def is_module(self, workflow_name, workspace_id, verify=True, last=False):
        """Detects whether the workflow is a system module or not.

        System modules use fixed queues, so this check is important to
        properly manage queue selection.

        Parameters
        ----------
        workflow_name : string
            Name of the workflow.
        workspace_id : string
            The CloudOS workspace id from to collect the workflows.
        verify: [bool|string]
            Whether to use SSL verification or not. Alternatively, if
            a string is passed, it will be interpreted as the path to
            the SSL certificate file.

        Returns
        -------
        bool
            True, if the workflow is a system module, false otherwise.
        """
        # get a list of all groups
        group = self.workflow_content_query(workspace_id, workflow_name, verify=verify, query="group", last=last)

        module_groups = ['system-tools',
                         'data-factory-data-connection-etl',
                         'data-factory',
                         'data-factory-omics-etl',
                         'drug-discovery',
                         'data-factory-omics-insights',
                         'intermediate'
                         ]
        if group[0] in module_groups:
            return True
        else:
            return False

    def get_project_list(self, workspace_id, verify=True, get_all=True,
                         page=1, page_size=10, max_page_size=100):
        """Get all the project from a CloudOS workspace.

        Parameters
        ----------
        workspace_id : string
            The CloudOS workspace id from to collect the projects.
        verify: [bool|string]
            Whether to use SSL verification or not. Alternatively, if
            a string is passed, it will be interpreted as the path to
            the SSL certificate file.
        get_all : bool
            Whether to get all available curated workflows or just the
            indicated page.
        page : int
            The page number to retrieve, from the paginated response.
        page_size : int
            The number of workflows by page. From 1 to 1000.
        max_page_size : int
            Max page size defined by the API server. It is currently 1000.

        Returns
        -------
        r : requests.models.Response
            The server response
        """
        headers = {
            "Content-type": "application/json",
            "apikey": self.apikey
        }
        r = retry_requests_get("{}/api/v2/projects?teamId={}&pageSize={}&page={}".format(
                self.cloudos_url, workspace_id, page_size, page),
                               headers=headers, verify=verify)
        if r.status_code >= 400:
            raise BadRequestException(r)
        content = json.loads(r.content)
        if get_all:
            total_projects = content['total']
            if total_projects <= max_page_size:
                r = retry_requests_get("{}/api/v2/projects?teamId={}&pageSize={}&page={}".format(
                        self.cloudos_url, workspace_id, total_projects, 1),
                                       headers=headers, verify=verify)
                if r.status_code >= 400:
                    raise BadRequestException(r)
                return json.loads(r.content)['projects']
            else:
                n_pages = (total_projects // max_page_size) + int((total_projects % max_page_size) > 0)
                for p in range(n_pages):
                    p += 1
                    r = retry_requests_get(
                        "{}/api/v2/projects?teamId={}&pageSize={}&page={}".format(
                            self.cloudos_url, workspace_id, max_page_size, p),
                        headers=headers, verify=verify)
                    if r.status_code >= 400:
                        raise BadRequestException(r)
                    if p == 1:
                        all_content_p = json.loads(r.content)['projects']
                    else:
                        all_content_p += json.loads(r.content)['projects']
                return all_content_p
        else:
            return content['projects']

    @staticmethod
    def process_project_list(r, all_fields=False):
        """Process a server response from a self.get_project_list call.

        Parameters
        ----------
        r : requests.models.Response
            A list of dicts, each corresponding to a project.
        all_fields : bool. Default=False
            Whether to return a reduced version of the DataFrame containing
            only the selected columns or the full DataFrame.

        Returns
        -------
        df : pandas.DataFrame
            A DataFrame with the requested columns from the projects.
        """
        COLUMNS = ['_id',
                   'name',
                   'user.id',
                   'user.name',
                   'user.surname',
                   'user.email',
                   'createdAt',
                   'updatedAt',
                   'workflowCount',
                   'jobCount',
                   'notebookSessionCount'
                   ]
        df_full = pd.json_normalize(r)
        if df_full.empty:
            return df_full
        if all_fields:
            df = df_full
        else:
            df = df_full.loc[:, COLUMNS]
        return df

    def workflow_import(self, workspace_id, workflow_url, workflow_name,
                        repository_project_id, workflow_docs_link='',
                        repository_id=None, verify=True):
        """Imports workflows to CloudOS.

        Parameters
        ----------
        workspace_id : string
            The CloudOS workspace id from to collect the projects.
        workflow_url : string
            The URL of the workflow. Only Github or Bitbucket are allowed.
        workflow_name : string
            A name for the imported pipeline in CloudOS.
        repository_project_id : int
            The repository project ID.
        workflow_docs_link : string
            Link to the documentation URL.
        repository_id : int
            The repository ID. Only required for GitHub repositories.
        verify: [bool|string]
            Whether to use SSL verification or not. Alternatively, if
            a string is passed, it will be interpreted as the path to
            the SSL certificate file.

        returns
        -------
        workflow_id : string
            The newly imported worflow ID.
        """
        platform_url = workflow_url.split('/')[2].split('.')[0]
        repository_name = workflow_url.split('/')[-1]
        if platform_url == 'github':
            platform = 'github'
            repository_project = workflow_url.split('/')[3]
            if repository_id is None:
                raise ValueError('Please, specify --repository-id when importing a GitHub repository')
        elif platform_url == 'bitbucket':
            platform = 'bitbucketServer'
            repository_project = workflow_url.split('/')[4]
            repository_id = repository_name
        else:
            raise ValueError(f'Your repository platform is not supported: {platform_url}. ' +
                             'Please use either GitHub or BitbucketServer.')
        repository_name = workflow_url.split('/')[-1]

        data = {
            "workflowType": "nextflow",
            "repository": {
                "platform": platform,
                "repositoryId": repository_id,
                "name": repository_name,
                "owner": {
                    "login": repository_project,
                    "id": repository_project_id},
                "isPrivate": True,
                "url": workflow_url,
                "commit": "",
                "branch": ""
            },
            "name": workflow_name,
            "description": "",
            "isPublic": False,
            "mainFile": "main.nf",
            "defaultContainer": None,
            "processes": [],
            "docsLink": workflow_docs_link,
            "team": workspace_id
        }
        headers = {
            "Content-type": "application/json",
            "apikey": self.apikey
        }
        r = retry_requests_post("{}/api/v1/workflows?teamId={}".format(self.cloudos_url,
                                                                       workspace_id),
                                json=data, headers=headers, verify=verify)
        if r.status_code == 401:
            raise ValueError('It seems your API key is not authorised. Please check if ' +
                             'your workspace has support for importing workflows using cloudos-cli')
        elif r.status_code >= 400:
            raise BadRequestException(r)
        content = json.loads(r.content)
        return content['_id']

    def get_user_info(self, verify=True):
        """Gets user information from users/me endpoint

        Parameters
        ----------
        verify: [bool|string]
            Whether to use SSL verification or not. Alternatively, if
            a string is passed, it will be interpreted as the path to
            the SSL certificate file.

        Returns
        -------
        r : requests.models.Response.content
            The server response content
        """
        headers = {
            "Content-type": "application/json",
            "apikey": self.apikey
        }
        r = retry_requests_get("{}/api/v1/users/me".format(self.cloudos_url),
                               headers=headers, verify=verify)
        if r.status_code >= 400:
            raise BadRequestException(r)
        return json.loads(r.content)

    def abort_job(self, job, workspace_id, verify=True):
        """Abort a job.

        Parameters
        ----------
        job : string
            The CloudOS job id of the job to abort.
        verify: [bool|string]
            Whether to use SSL verification or not. Alternatively, if
            a string is passed, it will be interpreted as the path to
            the SSL certificate file.

        Returns
        -------
        r : requests.models.Response
            The server response
        """
        cloudos_url = self.cloudos_url
        apikey = self.apikey
        headers = {
            "Content-type": "application/json",
            "apikey": apikey
        }
        r = retry_requests_put("{}/api/v1/jobs/{}/abort?teamId={}".format(cloudos_url, job, workspace_id),
                               headers=headers, verify=verify)
        if r.status_code >= 400:
            raise BadRequestException(r)
        return r

    def get_project_id_from_name(self, workspace_id, project_name, verify=True):
        """Retrieve the project ID from its name.

        Parameters
        ----------
        workspace_id : str
            The CloudOS workspace ID to search for the project.
        project_name : str
            The name of the project to search for.
        verify : [bool | str], optional
            Whether to use SSL verification or not. Alternatively, if
            a string is passed, it will be interpreted as the path to
            the SSL certificate file. Default is True.

        Returns
        -------
        dict
            The server response containing project details.

        Raises
        ------
        BadRequestException
            If the request to retrieve the project fails with a status code
            indicating an error.
        """
        headers = {
            "Content-type": "application/json",
            "apikey": self.apikey
        }
        url = f"{self.cloudos_url}/api/v2/projects?teamId={workspace_id}&search={project_name}"
        response = retry_requests_get(url, headers=headers, verify=verify)
        if response.status_code >= 400:
            raise BadRequestException(response)
        content = json.loads(response.content)

        project_id = next((p.get("_id") for p in content.get("projects", []) if p.get("name") == project_name), None)
        if project_id is None:
            raise ValueError(f"[Error] Project '{project_name}' was not found in workspace '{workspace_id}'")

        return project_id

    def create_project(self, workspace_id, project_name, verify=True):
        """Create a new project in CloudOS.

        Parameters
        ----------
        workspace_id : str
            The CloudOS workspace ID where the project will be created.
        project_name : str
            The name for the new project.
        verify : [bool | str], optional
            Whether to use SSL verification or not. Alternatively, if
            a string is passed, it will be interpreted as the path to
            the SSL certificate file. Default is True.

        Returns
        -------
        str
            The ID of the newly created project.

        Raises
        ------
        BadRequestException
            If the request to create the project fails with a status code
            indicating an error.
        """
        data = {
            "name": project_name
        }
        headers = {
            "Content-type": "application/json",
            "apikey": self.apikey
        }
        r = retry_requests_post("{}/api/v1/projects?teamId={}".format(self.cloudos_url,
                                                                      workspace_id),
                                json=data, headers=headers, verify=verify)
        if r.status_code == 401:
            raise ValueError('It seems your API key is not authorised. Please check if ' +
                             'you have used the correct API key for the selected workspace')
        elif r.status_code == 409:
            raise ValueError(f'It seems that there is another project named "{project_name}" ' +
                             'in your workspace, please use another name for the new project')
        elif r.status_code >= 400:
            raise BadRequestException(r)
        content = json.loads(r.content)
        return content['_id']

    def get_workflow_max_pagination(self, workspace_id, workflow_name, verify=True):
        """Retrieve the workflows max pages from API.

        Parameters
        ----------
        workspace_id : str
            The CloudOS workspace ID to search for the workflow.
        workflow_name : str
            The name of the workflow to search for.
        verify : [bool | str], optional
            Whether to use SSL verification or not. Alternatively, if
            a string is passed, it will be interpreted as the path to
            the SSL certificate file. Default is True.

        Returns
        -------
        int
            The server response with max pagination for workflows.

        Raises
        ------
        BadRequestException
            If the request to retrieve the project fails with a status code
            indicating an error.
        """
        headers = {
            "Content-type": "application/json",
            "apikey": self.apikey
        }
        # determine pagination, there might be a lot with the same name
        url = f"{self.cloudos_url}/api/v3/workflows?teamId={workspace_id}&search={workflow_name}"
        response = retry_requests_get(url, headers=headers, verify=verify)
        if response.status_code >= 400:
            raise BadRequestException(response)
        pag_content = json.loads(response.content)
        max_pagination = pag_content["paginationMetadata"]["Pagination-Count"]
        if max_pagination == 0:
            raise ValueError(f'No workflow found with name: {workflow_name} in workspace: {workspace_id}')

        return max_pagination

    def get_workflow_content(self, workspace_id, workflow_name, verify=True, last=False, max_page_size=100):
        """Retrieve the workflow content from API.

        Parameters
        ----------
        workspace_id : str
            The CloudOS workspace ID to search for the workflow.
        workflow_name : str
            The name of the workflow to search for.
        verify : [bool | str], optional
            Whether to use SSL verification or not. Alternatively, if
            a string is passed, it will be interpreted as the path to
            the SSL certificate file. Default is True.

        Returns
        -------
        dict
            The server response containing workflow details.

        Raises
        ------
        BadRequestException
            If the request to retrieve the project fails with a status code
            indicating an error.
        """
        headers = {
            "Content-type": "application/json",
            "apikey": self.apikey
        }
        max_pagination = self.get_workflow_max_pagination(workspace_id, workflow_name, verify=verify)

        # get all the matching content
        if max_pagination > max_page_size:
            content = {"workflows": []}
            for page_start in range(0, max_pagination, max_page_size):
                page_size = min(max_page_size, max_pagination - page_start)
                url = f"{self.cloudos_url}/api/v3/workflows?teamId={workspace_id}&search={workflow_name}&pageSize={page_size}&page={page_start // max_page_size + 1}"
                response = retry_requests_get(url, headers=headers, verify=verify)
                # keep structure as a dict
                content["workflows"].extend(json.loads(response.content).get("workflows", []))
        else:
            url = f"{self.cloudos_url}/api/v3/workflows?teamId={workspace_id}&search={workflow_name}&pageSize={max_pagination}"
            response = retry_requests_get(url, headers=headers, verify=verify)
            # return all content
            content = json.loads(response.content)
        if response.status_code >= 400:
            raise BadRequestException(response)

        # check for duplicates
        wf = [wf.get("name") for wf in content.get("workflows", []) if wf.get("name") == workflow_name]

        if len(wf) == 0 or len(content["workflows"]) == 0:
            raise ValueError(f'No workflow found with name: {workflow_name} in workspace: {workspace_id}')
        if len(wf) > 1 and not last:
            raise ValueError(f'More than one workflow found with name: {workflow_name}. ' + \
                             "To run the last imported workflow use '--last' flag.")
        else:
            content = youngest_workflow_id_by_name(content, workflow_name)
        return content

    def workflow_content_query(self, workspace_id, workflow_name, verify=True, query="workflowType", last=False):

        content = self.get_workflow_content(workspace_id, workflow_name, verify=verify, last=last)

        # use 'query' to look in the content
        return [wf.get(query) for wf in content.get("workflows", []) if wf.get("name") == workflow_name]

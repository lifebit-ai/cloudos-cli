"""
This is the main class of the package.
"""

import requests
import time
import json
from dataclasses import dataclass
from cloudos_cli.utils.cloud import find_cloud
from cloudos_cli.utils.errors import BadRequestException, JoBNotCompletedException, NotAuthorisedException, JobAccessDeniedException
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

    def get_job_status(self, j_id, workspace_id=None, verify=True):
        """Get job status from CloudOS.

        Parameters
        ----------
        j_id : string
            The CloudOS job id of the job just launched.
        workspace_id : string
            The CloudOS workspace id from to check the job status.
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
        url = f"{cloudos_url}/api/v1/jobs/{j_id}?teamId={workspace_id}"
        r = retry_requests_get(url, headers=headers, verify=verify)
        if r.status_code == 401:
            raise NotAuthorisedException
        elif r.status_code == 403:
            # Handle 403 with more informative error message
            self._handle_job_access_denied(j_id, workspace_id, verify)
        elif r.status_code >= 400:
            raise BadRequestException(r)
        return r

    def wait_job_completion(self, job_id, workspace_id, wait_time=3600, request_interval=30, verbose=False,
                            verify=True):
        """Checks job status from CloudOS and wait for its complation.

        Parameters
        ----------
        job_id : string
            The CloudOS job id of the job just launched.
        workspace_id : string
            The CloudOS workspace id from to check the job status.
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
            j_status = self.get_job_status(job_id, workspace_id, verify)
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
        j_status = self.get_job_status(job_id, workspace_id, verify)
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

    def get_job_workdir(self, j_id, workspace_id, verify=True):
        """
        Get the working directory for the specified job
        """
        cloudos_url = self.cloudos_url
        apikey = self.apikey
        headers = {
            "Content-type": "application/json",
            "apikey": apikey
        }
        r = self.get_job_status(j_id, workspace_id, verify)
        r_json = r.json()
        job_workspace = r_json["team"]
        if job_workspace != workspace_id:
            raise ValueError("Workspace provided or configured is different from workspace where the job was executed")
        if r_json["status"] =='initializing' or r_json["status"] =='scheduled':
            raise ValueError("Working directories are not yet available. The job is still initializing.")

        if "resumeWorkDir" not in r_json:
            raise ValueError("Working directories are not available. This may be because the analysis was run without resumable mode enabled, or because intermediate results have since been removed.")
        
        # Check if intermediate results have been deleted
        # When intermediate results are deleted, resumeWorkDir becomes None but workDirectory still exists with folderId
        resume_workdir_id = r_json.get("resumeWorkDir")
        if resume_workdir_id is None and "workDirectory" in r_json:
            work_directory = r_json["workDirectory"]
            # If workDirectory has a folderId, it means the job was resumeable but intermediate results were deleted
            if work_directory.get("folderId") is not None:
                # Get the actual deletion status from the folders API
                api_status = None
                try:
                    folder_id = work_directory["folderId"]
                    folder_response = self.get_folder_deletion_status(folder_id, workspace_id, verify)
                    folder_data = json.loads(folder_response.content)
                    
                    # If the API returns the folder, get its status
                    if folder_data and len(folder_data) > 0:
                        api_status = folder_data[0].get("status")
                    else:
                        # If the folder is not returned, check if deletedBy exists in workDirectory
                        if "deletedBy" in work_directory:
                            api_status = "scheduledForDeletion"  # Assume scheduled for deletion
                        
                except Exception:
                    # If we can't get the status, check if deletedBy exists
                    if "deletedBy" in work_directory:
                        api_status = "scheduledForDeletion"  # Assume scheduled for deletion
                
                # Build contextually appropriate error message based on status
                # Only raise error for non-ready statuses (ready means it's available, so no error)
                if api_status == "deleting":
                    error_msg = "Intermediate job results are currently being deleted. The working directory is not accessible."
                    raise ValueError(error_msg)
                elif api_status == "scheduledForDeletion":
                    error_msg = "Intermediate job results have been scheduled for deletion. The working directory is no longer available."
                    raise ValueError(error_msg)
                elif api_status == "deleted":
                    error_msg = "Intermediate job results have been deleted. The working directory is no longer available."
                    raise ValueError(error_msg)
                elif api_status == "failedToDelete":
                    error_msg = "Intermediate job results were marked for deletion but failed to delete. The working directory may not be accessible."
                    raise ValueError(error_msg)
                elif api_status != "ready" and api_status is not None:
                    # For any other unknown status (not ready), raise generic error
                    error_msg = "Intermediate job results have been removed. The working directory is no longer available."
                    raise ValueError(error_msg)
                # If status is "ready", set resume_workdir_id so we can retrieve the workdir path
                elif api_status == "ready":
                    resume_workdir_id = folder_id
        
        # If resumeWorkDir exists, use the folders API to get the shared working directory
        if resume_workdir_id:
            try:
                # Use folders API to get the actual shared working directory
                workdir_bucket_r = retry_requests_get(f"{cloudos_url}/api/v1/folders",
                                                        params=dict(id=resume_workdir_id, teamId=workspace_id), 
                                                        headers=headers, verify=verify)
                if workdir_bucket_r.status_code == 401:
                    raise NotAuthorisedException
                elif workdir_bucket_r.status_code >= 400:
                    raise BadRequestException(workdir_bucket_r)

                workdir_bucket_o = workdir_bucket_r.json()
                if len(workdir_bucket_o) > 1:
                    raise ValueError(f"Request returned more than one result for folder id {resume_workdir_id}")
                workdir_bucket_info = workdir_bucket_o[0]
                
                if workdir_bucket_info["folderType"] == "S3Folder":
                    bucket_name = workdir_bucket_info["s3BucketName"]
                    bucket_path = workdir_bucket_info["s3Prefix"]
                    workdir_path = f"s3://{bucket_name}/{bucket_path}"
                elif workdir_bucket_info["folderType"] == "AzureBlobFolder":
                    storage_account = f"az://{workspace_id}.blob.core.windows.net"
                    container_name = workdir_bucket_info["blobContainerName"]
                    blob_prefix = workdir_bucket_info["blobPrefix"]
                    workdir_path = f"{storage_account}/{container_name}/{blob_prefix}"
                else:
                    raise ValueError("Unsupported cloud provider")
                
                return workdir_path
            except Exception as e:
                # If folders API fails, fall back to logs-based approach
                print(f"Warning: Could not get shared workdir from folders API: {e}")
                pass
        
        # Check if logs field exists for fallback approach
        if "logs" in r_json:
            # Get workdir information from logs object using the same pattern as get_job_logs
            logs_obj = r_json["logs"]
            cloud_name, cloud_meta, cloud_storage = find_cloud(self.cloudos_url, self.apikey, workspace_id, logs_obj)
            container_name = cloud_storage["container"]
            prefix_name = cloud_storage["prefix"]
            logs_bucket = logs_obj[container_name]
            logs_path = logs_obj[prefix_name]
            
            # Construct workdir path by replacing '/logs' with '/work' in the logs path
            workdir_path_suffix = logs_path.replace('/logs', '/work')
            
            if cloud_name == "aws":
                workdir_path = f"s3://{logs_bucket}/{workdir_path_suffix}"
            elif cloud_name == "azure":
                storage_account_prefix = ''
                cloude_scheme = cloud_storage["scheme"]
                if cloude_scheme == 'az':
                    storage_account_prefix = f"az://{cloud_meta['storage']['storageAccount']}.blob.core.windows.net"
                workdir_path = f"{storage_account_prefix}/{logs_bucket}/{workdir_path_suffix}"
            else:
                raise ValueError("Unsupported cloud provider")
            
            return workdir_path
        else:
            # Fallback to original folder-based approach for backward compatibility
            workdir_id = r_json["resumeWorkDir"]

            # This will fail, as the API endpoint is not open. This works when adding
            # the authorisation bearer token manually to the headers
            workdir_bucket_r = retry_requests_get(f"{cloudos_url}/api/v1/folders",
                                                    params=dict(id=workdir_id, teamId=workspace_id), 
                                                    headers=headers, verify=verify)
            if workdir_bucket_r.status_code == 401:
                raise NotAuthorisedException
            elif workdir_bucket_r.status_code >= 400:
                raise BadRequestException(workdir_bucket_r)

            workdir_bucket_o = workdir_bucket_r.json()
            if len(workdir_bucket_o) > 1:
                raise ValueError(f"Request returned more than one result for folder id {workdir_id}")
            workdir_bucket_info = workdir_bucket_o[0]
            if workdir_bucket_info["folderType"] == "S3Folder":
                cloud_name = "aws"
            elif workdir_bucket_info["folderType"] == "AzureBlobFolder":
                cloud_name = "azure"
            else:
                raise ValueError("Unsupported cloud provider")
            if cloud_name == "aws":
                bucket_name = workdir_bucket_info["s3BucketName"]
                bucket_path = workdir_bucket_info["s3Prefix"]
                workdir_path = f"s3://{bucket_name}/{bucket_path}"
            elif cloud_name == "azure":
                storage_account = f"az://{workspace_id}.blob.core.windows.net"
                container_name = workdir_bucket_info["blobContainerName"]
                blob_prefix = workdir_bucket_info["blobPrefix"]
                workdir_path = f"{storage_account}/{container_name}/{blob_prefix}"
            else:
                raise ValueError("Unsupported cloud provider")
            
            return workdir_path

    def _handle_job_access_denied(self, job_id, workspace_id, verify=True):
        """
        Handle 403 errors with more informative messages by checking job ownership
        """
        try:
            # Try to get current user info
            current_user = self.get_user_info(verify)
            current_user_name = f"{current_user.get('name', '')} {current_user.get('surname', '')}".strip()
            if not current_user_name:
                current_user_name = current_user.get('email', 'Unknown')
        except Exception:
            current_user_name = None

        try:
            # Try to get job info from job list to see the owner
            result = self.get_job_list(workspace_id, last_n_jobs='all', verify=verify)
            jobs = result['jobs']  # Extract jobs list from the dictionary
            job_owner_name = None
            
            for job in jobs:
                if job.get('_id') == job_id:
                    user_info = job.get('user', {})
                    job_owner_name = f"{user_info.get('name', '')} {user_info.get('surname', '')}".strip()
                    if not job_owner_name:
                        job_owner_name = user_info.get('email', 'Unknown')
                    break
            
            raise JobAccessDeniedException(job_id, job_owner_name, current_user_name)
        except JobAccessDeniedException:
            # Re-raise the specific exception
            raise
        except Exception:
            # If we can't get detailed info, fall back to generic message
            raise JobAccessDeniedException(job_id)

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
        r = self.get_job_status(j_id, workspace_id, verify)
        r_json = r.json()
        
        job_workspace = r_json["team"]
        if job_workspace != workspace_id:
            raise ValueError("Workspace provided or configured is different from workspace where the job was executed")
        if r_json["status"] =='initializing' or r_json["status"] =='scheduled':
            raise ValueError("Logs are not yet available. The job is still initializing.")
        if "logs" not in r_json:
            raise ValueError("Logs are not available.")
        else:
            logs_obj = r_json["logs"]
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
        status = self.get_job_status(j_id, workspace_id, verify).json()["status"]
        if status != JOB_COMPLETED:
            raise JoBNotCompletedException(j_id, status)

        r = self.get_job_status(j_id, workspace_id, verify)
        req_obj = r.json()
        job_workspace = req_obj["team"]
        if job_workspace != workspace_id:
            raise ValueError("Workspace provided or configured is different from workspace where the job was executed")
        
        # Check if analysis results have been deleted or scheduled for deletion
        # Similar to workdir check - if analysisResults exists with folderId, check its status
        if "analysisResults" in req_obj and req_obj.get("analysisResults"):
            analysis_results = req_obj["analysisResults"]
            results_folder_id = analysis_results.get("folderId")
            
            if results_folder_id:
                # Get the actual deletion status from the folders API
                api_status = None
                try:
                    folder_response = self.get_folder_deletion_status(results_folder_id, workspace_id, verify)
                    folder_data = json.loads(folder_response.content)
                    
                    # If the API returns the folder, get its status
                    if folder_data and len(folder_data) > 0:
                        api_status = folder_data[0].get("status")
                    else:
                        # If the folder is not returned, check if deletedBy exists in analysisResults
                        if "deletedBy" in analysis_results:
                            api_status = "scheduledForDeletion"  # Assume scheduled for deletion
                        
                except Exception:
                    # If we can't get the status, check if deletedBy exists
                    if "deletedBy" in analysis_results:
                        api_status = "scheduledForDeletion"  # Assume scheduled for deletion
                
                # Build contextually appropriate error message based on status
                # Only raise error for non-ready statuses (ready means it's available, so no error)
                if api_status == "deleting":
                    error_msg = "Analysis results are currently being deleted. The results folder is not accessible."
                    raise ValueError(error_msg)
                elif api_status == "scheduledForDeletion":
                    error_msg = "Analysis results have been scheduled for deletion. The results folder is no longer available."
                    raise ValueError(error_msg)
                elif api_status == "deleted":
                    error_msg = "Analysis results have been deleted. The results folder is no longer available."
                    raise ValueError(error_msg)
                elif api_status == "failedToDelete":
                    error_msg = "Analysis results were marked for deletion but failed to delete. The results folder may not be accessible."
                    raise ValueError(error_msg)
                elif api_status != "ready" and api_status is not None:
                    # For any other unknown status (not ready), raise generic error
                    error_msg = "Analysis results have been removed. The results folder is no longer available."
                    raise ValueError(error_msg)
                # If status is "ready" or None, don't raise error - let the code continue to retrieve the results path
        
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
        # Find the results directory - typically there should be only one
        for item in contents_obj:
            if item["isDir"] and item["name"] == "results":
                return f"{scheme}://{storage_account_prefix}{results_container}/{item['path']}"
        
        # Fallback: if no "results" directory found, return the first directory
        for item in contents_obj:
            if item["isDir"]:
                return f"{scheme}://{storage_account_prefix}{results_container}/{item['path']}"
        
        # If no directories found, raise an error
        raise ValueError("No result directories found for this job")

    def get_folder_items_deletion_status(self, folder_id, workspace_id, verify=True):
        """Get deletion status of items within a folder.

        Simple API wrapper to query the datasets API for items in a folder
        with their deletion status (ready/deleting).

        Parameters
        ----------
        folder_id : str
            The CloudOS folder ID.
        workspace_id : str
            The CloudOS workspace ID.
        verify : [bool | str], optional
            Whether to use SSL verification or not. Alternatively, if
            a string is passed, it will be interpreted as the path to
            the SSL certificate file. Default is True.

        Returns
        -------
        Response
            The API response containing folders and files with their status.

        Raises
        ------
        BadRequestException
            If the request fails with a status code indicating an error.
        """
        headers = {
            "Content-type": "application/json",
            "apikey": self.apikey
        }
        
        # Query all possible deletion statuses
        params = {
            "status": ["ready", "deleted", "deleting", "scheduledForDeletion", "failedToDelete"],
            "teamId": workspace_id
        }
        
        url = f"{self.cloudos_url}/api/v1/datasets/{folder_id}/items"
        response = retry_requests_get(url, params=params, headers=headers, verify=verify)
        
        if response.status_code >= 400:
            raise BadRequestException(response)
        
        return response

    def get_results_deletion_status(self, job_id, workspace_id, verify=True):
        """Get the deletion status of a specific job's results folder.

        This method orchestrates finding the job's results folder and retrieving
        the deletion status of items within it.

        Parameters
        ----------
        job_id : str
            The CloudOS job ID.
        workspace_id : str
            The CloudOS workspace ID.
        verify : [bool | str], optional
            Whether to use SSL verification or not. Alternatively, if
            a string is passed, it will be interpreted as the path to
            the SSL certificate file. Default is True.

        Returns
        -------
        dict
            A dictionary containing the deletion status information with the following structure:
            {
                "job_id": str,  # The job ID
                "job_name": str,  # The job name
                "results_folder_id": str,  # The ID of the job's results folder
                "results_folder_name": str,  # The name of the job's results folder
                "items": dict  # Dictionary with 'folders' and 'files' arrays containing items and their status
            }

        Raises
        ------
        BadRequestException
            If the request fails with a status code indicating an error.
        ValueError
            If the job's results folder is not found.
        """
        # First, get job details to find the project and job name
        job_status = self.get_job_status(job_id, workspace_id, verify)
        job_data = json.loads(job_status.content)
        job_name = job_data.get("name", job_id)
        project_info = job_data.get("project")
        
        # Extract deletedBy info from analysisResults if available
        analysis_results_deleted_by = None
        if "analysisResults" in job_data and job_data.get("analysisResults"):
            analysis_results_deleted_by = job_data["analysisResults"].get("deletedBy")
        
        if not project_info:
            raise ValueError(f"Could not find project for job '{job_id}'")
        
        # Extract project ID and name from the project info dict
        project_id = project_info.get("_id")
        project_name = project_info.get("name")
        
        if not project_name or not project_id:
            raise ValueError(f"Could not extract project information from job '{job_id}'")
        
        from cloudos_cli.datasets.datasets import Datasets
        
        # Create Datasets object to navigate to the Analysis Results folder
        ds = Datasets(
            cloudos_url=self.cloudos_url,
            apikey=self.apikey,
            cromwell_token=self.cromwell_token,
            workspace_id=workspace_id,
            project_name=project_name,
            verify=verify
        )
        
        # Get project content to find Analysis Results folder
        try:
            project_content = ds.list_project_content()
        except Exception as e:
            raise ValueError(f"Failed to list project content for project '{project_name}'. {str(e)}")
        
        # Find the Analysis Results folder ID
        analysis_results_id = None
        for folder in project_content.get("folders", []):
            if folder['name'] in ['Analyses Results', 'AnalysesResults']:
                analysis_results_id = folder['_id']
                break
        
        if not analysis_results_id:
            raise ValueError(f"Analyses Results folder not found in project '{project_name}'.")
        
        # Get items in Analysis Results folder to find the job's specific results folder
        # The Analysis Results folder contains folders for each job's results
        try:
            response = self.get_folder_items_deletion_status(analysis_results_id, workspace_id, verify)
            content = json.loads(response.content)
        except Exception as e:
            raise ValueError(f"Failed to get items from Analyses Results folder. {str(e)}")
        
        # The API response contains folders and files arrays
        # Find the entry matching our job_id
        job_status_info = None
        
        # Check if it's a dict with folders/files arrays
        if isinstance(content, dict):
            # Check for 'folders' or 'files' keys (common dataset API response format)
            items_to_search = []
            if 'folders' in content:
                items_to_search.extend(content['folders'])
            if 'files' in content:
                items_to_search.extend(content['files'])
            
            # If no folders/files keys, treat dict values as items
            if not items_to_search:
                items_to_search = list(content.values())
            
            for item in items_to_search:
                if not isinstance(item, dict):
                    continue
                
                item_name = item.get("name", "")
                
                # Match by exact job ID in the item name (format: workflowname-jobid)
                # The folder name should contain the exact job ID
                if job_id in item_name:
                    job_status_info = item
                    break
        elif isinstance(content, list):
            for item in content:
                if not isinstance(item, dict):
                    continue
                
                item_name = item.get("name", "")
                
                # Match by exact job ID in the item name
                if job_id in item_name:
                    job_status_info = item
                    break
        
        if not job_status_info:
            raise ValueError(
                f"Results folder for job '{job_name}' (ID: {job_id}) not found in Analyses Results.\n"
                f"This may indicate that the results have been deleted or are scheduled for deletion."
            )
        
        # Merge the deletedBy info from job data with the folder info
        # The deletedBy from analysisResults is more reliable than folder's user field
        if analysis_results_deleted_by:
            job_status_info["deletedBy"] = analysis_results_deleted_by
        
        return {
            "job_id": job_id,
            "job_name": job_name,
            "results_folder_id": job_status_info.get("_id"),
            "results_folder_name": job_status_info.get("name"),
            "status": job_status_info.get("status"),
            "items": job_status_info
        }

    def get_folder_deletion_status(self, folder_id, workspace_id, verify=True):
        """Get deletion status of a specific folder by ID.

        Simple API wrapper to query the folders API for a specific folder
        with its deletion status (ready/deleting/etc).

        Parameters
        ----------
        folder_id : str
            The CloudOS folder ID.
        workspace_id : str
            The CloudOS workspace ID.
        verify : [bool | str], optional
            Whether to use SSL verification or not. Alternatively, if
            a string is passed, it will be interpreted as the path to
            the SSL certificate file. Default is True.

        Returns
        -------
        Response
            The API response containing folder information with status.

        Raises
        ------
        BadRequestException
            If the request fails with a status code indicating an error.
        """
        headers = {
            "Content-type": "application/json",
            "apikey": self.apikey
        }
        
        # Query with all possible deletion statuses
        params = {
            "id": folder_id,
            "status": ["ready", "deleted", "deleting", "scheduledForDeletion", "failedToDelete"],
            "teamId": workspace_id
        }
        
        url = f"{self.cloudos_url}/api/v1/folders/"
        response = retry_requests_get(url, params=params, headers=headers, verify=verify)
        
        if response.status_code >= 400:
            raise BadRequestException(response)
        
        return response

    def get_workdir_deletion_status(self, job_id, workspace_id, verify=True):
        """Get the deletion status of a specific job's working directory.

        This method retrieves the deletion status of the job's working directory
        using the folders API endpoint.

        Parameters
        ----------
        job_id : str
            The CloudOS job ID.
        workspace_id : str
            The CloudOS workspace ID.
        verify : [bool | str], optional
            Whether to use SSL verification or not. Alternatively, if
            a string is passed, it will be interpreted as the path to
            the SSL certificate file. Default is True.

        Returns
        -------
        dict
            A dictionary containing the deletion status information with the following structure:
            {
                "job_id": str,  # The job ID
                "job_name": str,  # The job name
                "workdir_folder_id": str,  # The ID of the job's working directory folder
                "workdir_folder_name": str,  # The name of the job's working directory folder
                "status": str,  # The deletion status
                "items": dict  # Full folder object with metadata
            }

        Raises
        ------
        BadRequestException
            If the request fails with a status code indicating an error.
        ValueError
            If the job's working directory is not found or not accessible.
        """
        # First, get job details to find the working directory folder ID
        job_status = self.get_job_status(job_id, workspace_id, verify)
        job_data = json.loads(job_status.content)
        job_name = job_data.get("name", job_id)
        
        # Try to get the workdir folder ID from workDirectory.folderId first (new format)
        # If not available, fall back to resumeWorkDir (old format)
        workdir_folder_id = None
        workdir_deleted_by = None
        
        if "workDirectory" in job_data and job_data.get("workDirectory"):
            workdir_folder_id = job_data["workDirectory"].get("folderId")
            # Get deletedBy info if available (contains user who scheduled deletion)
            workdir_deleted_by = job_data["workDirectory"].get("deletedBy")
        
        if not workdir_folder_id and "resumeWorkDir" in job_data:
            workdir_folder_id = job_data.get("resumeWorkDir")
        
        if not workdir_folder_id:
            raise ValueError(
                "Working directory is not available for this job. "
                "This may be because the analysis was run without resumable mode enabled, "
                "or because intermediate results have been removed."
            )
        
        # Use the folders API to get the working directory status
        response = self.get_folder_deletion_status(workdir_folder_id, workspace_id, verify)
        
        # Parse the response
        content = json.loads(response.content)
        
        # The API returns an array with the folder info
        if not content or len(content) == 0:
            raise ValueError(
                f"Working directory for job '{job_name}' (ID: {job_id}) not found.\n"
                f"This may indicate that the working directory has been deleted or is scheduled for deletion."
            )
        
        workdir_info = content[0]  # Get the first (and should be only) result
        
        # Merge the deletedBy info from job data with the folder info
        # The deletedBy from workDirectory is more reliable than folder's user field
        if workdir_deleted_by:
            workdir_info["deletedBy"] = workdir_deleted_by
        
        return {
            "job_id": job_id,
            "job_name": job_name,
            "workdir_folder_id": workdir_info.get("_id"),
            "workdir_folder_name": workdir_info.get("name"),
            "status": workdir_info.get("status"),
            "items": workdir_info
        }

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

    def resolve_user_id(self, filter_owner, workspace_id, verify=True):
        """Resolve a username or display name to a user ID.

        Parameters
        ----------
        filter_owner : str
            The username or display name to search for.
        workspace_id : str
            The CloudOS workspace ID.
        verify : [bool|string]
            Whether to use SSL verification or not. Alternatively, if
            a string is passed, it will be interpreted as the path to
            the SSL certificate file.

        Returns
        -------
        str
            The user ID corresponding to the filter_owner.

        Raises
        ------
        ValueError
            If the user cannot be found or if there's an error during the search.
        """
        try:
            search_headers = {
                "Content-type": "application/json",
                "apikey": self.apikey
            }
            search_params = {
                "q": filter_owner,
                "teamId": workspace_id
            }
            # Note: this endpoint may not be open in all CloudOS instances
            user_search_r = retry_requests_get(f"{self.cloudos_url}/api/v1/users/search-assist",
                                             params=search_params, headers=search_headers, verify=verify)
            if user_search_r.status_code >= 400:
                raise ValueError(f"Error searching for user '{filter_owner}'")
            
            user_search_content = user_search_r.json()
            user_items = user_search_content.get('items', [])
            if user_items and len(user_items) > 0:
                user_match = None
                for user in user_items:
                    if user.get("username") == filter_owner or user.get("name") == filter_owner:
                        user_match = user
                        break
                
                if user_match:
                    return user_match.get("id")
                else:
                    raise ValueError(f"User '{filter_owner}' not found.")
            else:
                raise ValueError(f"User '{filter_owner}' not found.")
        except Exception as e:
            raise ValueError(f"Error resolving user '{filter_owner}'. {str(e)}")

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

    def get_job_list(self, workspace_id, last_n_jobs=None, page=None, page_size=None, archived=False,
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
        last_n_jobs : [int | 'all'], default=None
            How many of the last jobs from the user to retrieve. You can specify a
            very large int or 'all' to get all user's jobs. When specified, page
            and page_size parameters are ignored.
        page : int, default=None
            Response page to get when not using last_n_jobs.
        page_size : int, default=None
            Number of jobs to retrieve per page when not using last_n_jobs.
            Maximum allowed value is 100.
        archived : bool, default=False
            When True, only the archived jobs are retrieved.
        verify: [bool|string], default=True
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
        filter_owner : string, optional
            Filter jobs by owner username (will be resolved to user ID).
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
        # Validate workspace_id
        if not workspace_id or not isinstance(workspace_id, str):
            raise ValueError("Invalid workspace_id: must be a non-empty string")

        # Validate last_n_jobs
        if last_n_jobs is not None:
            if isinstance(last_n_jobs, str):
                if last_n_jobs != 'all':
                    try:
                        last_n_jobs = int(last_n_jobs)
                    except ValueError:
                        raise ValueError("last_n_jobs must be a positive integer or 'all'")

            # Validate that integer last_n_jobs is positive
            if isinstance(last_n_jobs, int) and last_n_jobs <= 0:
                raise ValueError("last_n_jobs must be a positive integer or 'all'")

        # Validate page and page_size
        if page is not None and (page <= 0 or not isinstance(page, int)):
            raise ValueError('Please, use a positive integer (>= 1) for the --page parameter')
        if page_size is not None and (page_size <= 0 or not isinstance(page_size, int)):
            raise ValueError('Please, use a positive integer (>= 1) for the --page-size parameter')

        # Handle parameter interaction and set defaults
        # If last_n_jobs is provided, use pagination mode with last_n_jobs
        # If page/page_size are provided without last_n_jobs, use direct pagination mode
        if last_n_jobs is not None:
            # When last_n_jobs is specified, warn if page/page_size are also specified
            print('[Warning] When using --last-n-jobs option, --page and --page-size are ignored. ' +
                    'To use --page and --page-size, please remove --last-n-jobs option.\n')
            # Use pagination to fetch last_n_jobs, starting from page 1
            use_pagination_mode = True
            target_job_count = last_n_jobs
            current_page = 1
            current_page_size = min(100, int(last_n_jobs)) if last_n_jobs != 'all' else 100
        else:
            # Direct pagination mode - use page and page_size as specified
            use_pagination_mode = False
            target_job_count = page_size  # Only get jobs for this page
            current_page = page if page is not None else 1
            current_page_size = page_size if page_size is not None else 10

            # Validate page_size limit for direct pagination
            if current_page_size > 100:
                raise ValueError('Please, use a page_size value <= 100')

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
            "page": current_page,
            "limit": current_page_size
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
                raise ValueError(f"Error resolving project '{filter_project}'. {str(e)}")

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
                raise ValueError(f"Error resolving workflow '{filter_workflow}'. {str(e)}")

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
                raise ValueError(f"Error getting current user info. {str(e)}")

        # Resolve owner username to user ID
        if filter_owner:
            user_id = self.resolve_user_id(filter_owner, workspace_id, verify)
            params["user.id"] = user_id

        # --- Fetch jobs page by page ---
        all_jobs = []
        params["limit"] = current_page_size
        last_pagination_metadata = None  # Track the last pagination metadata

        while True:
            params["page"] = current_page

            r = retry_requests_get(f"{self.cloudos_url}/api/v2/jobs", params=params, headers=headers, verify=verify)
            if r.status_code >= 400:
                raise BadRequestException(r)

            content = r.json()
            page_jobs = content.get('jobs', [])
            
            # Capture pagination metadata
            last_pagination_metadata = content.get('paginationMetadata', None)

            # No jobs returned, we've reached the end
            if not page_jobs:
                break

            all_jobs.extend(page_jobs)

            # Check stopping conditions based on mode
            if use_pagination_mode:
                # In pagination mode (last_n_jobs), continue until we have enough jobs
                if target_job_count != 'all' and len(all_jobs) >= target_job_count:
                    break
            else:
                # In direct mode (page/page_size), only get one page
                break

            # Check if we reached the last page (fewer jobs than requested page size)
            if len(page_jobs) < params["limit"]:
                break  # Last page

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
                raise ValueError(f"Error filtering by queue '{filter_queue}'. {str(e)}")

        # --- Apply limit after all filtering ---
        if use_pagination_mode and target_job_count != 'all' and isinstance(target_job_count, int) and target_job_count > 0:
            all_jobs = all_jobs[:target_job_count]

        return {'jobs': all_jobs, 'pagination_metadata': last_pagination_metadata}

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
            raise ValueError(f'More than one workflow type ("{wt}") detected for "{workflow_name}". ')
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
            raise ValueError(f'Your repository platform "{platform_url}" is not supported. ' +
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
        r = retry_requests_put("{}/api/v2/jobs/{}/abort?teamId={}".format(cloudos_url, job, workspace_id),
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
            raise ValueError(f"Project '{project_name}' was not found in workspace '{workspace_id}'")

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
            raise ValueError(f'No workflow found with name "{workflow_name}" in workspace "{workspace_id}"')

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
            raise ValueError(f'No workflow found with name "{workflow_name}" in workspace "{workspace_id}"')
        if len(wf) > 1 and not last:
            raise ValueError(f'More than one workflow found with name "{workflow_name}". ' + \
                             "To run the last imported workflow use '--last' flag.")
        else:
            content = youngest_workflow_id_by_name(content, workflow_name)
        return content

    def workflow_content_query(self, workspace_id, workflow_name, verify=True, query="workflowType", last=False):

        content = self.get_workflow_content(workspace_id, workflow_name, verify=verify, last=last)

        # use 'query' to look in the content
        return [wf.get(query) for wf in content.get("workflows", []) if wf.get("name") == workflow_name]

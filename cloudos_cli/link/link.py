"""
This is the main class for linking files to interactive sessions.
"""

from dataclasses import dataclass
from typing import Union, List, Dict
from cloudos_cli.clos import Cloudos
from cloudos_cli.utils.requests import retry_requests_post, retry_requests_get
from cloudos_cli.utils.errors import JoBNotCompletedException
from cloudos_cli.datasets import Datasets
from urllib.parse import urlparse
from cloudos_cli.utils.array_job import extract_project, get_file_or_folder_id
import json
import time
import rich_click as click
        

@dataclass
class Link(Cloudos):
    """Class for linking folders/files to interactive sessions.

    Parameters
    ----------
    cloudos_url : string
        The CloudOS service url.
    apikey : string
        Your CloudOS API key.
    workspace_id : string
        The specific Cloudos workspace id.
    verify: [bool|string]
        Whether to use SSL verification or not. Alternatively, if
        a string is passed, it will be interpreted as the path to
        the SSL certificate file.
    """
    workspace_id: str
    project_name: str
    verify: Union[bool, str] = True

    def link_folder(self,
                    folder: str,
                    session_id: str) -> dict:
        """Link a folder (S3 or File Explorer) to an interactive session.

        Parameters
        ----------
        folder : str
            The folder to link.
        session_id : str
            The interactive session ID.

        Raises
        ------
        ValueError
            If the URL already exists with 'mounted' status
            If the API key is invalid or permissions are insufficient
            If the URL is invalid or the session is not active.
        """
        url = (
            f"{self.cloudos_url}/api/v1/"
            f"interactive-sessions/{session_id}/fuse-filesystem/mount"
            f"?teamId={self.workspace_id}"
        )
        headers = {
            "Content-type": "application/json",
            "apikey": self.apikey
        }
        
        # Block Azure Blob Storage URLs as they are not supported by the API
        if folder.startswith('az://'):
            raise ValueError(
                "Azure Blob Storage paths (az://) are not supported for linking. "
                "Azure environments do not support linking folders to Interactive Analysis sessions. "
            )
        
        # determine if is file explorer or s3
        if folder.startswith('s3://'):
            data = self.parse_s3_path(folder)
            type_folder = "S3"
        else:
            data = self.parse_file_explorer_path(folder)
            type_folder = "File Explorer"
        r = retry_requests_post(url, headers=headers, json=data, verify=self.verify)
        
        if r.status_code == 403:
            raise ValueError(f"Provided {type_folder} folder already exists with 'mounted' status")
        elif r.status_code == 401:
            raise ValueError(f"Forbidden. Invalid API key or insufficient permissions.")
        elif r.status_code == 400:
            r_content = json.loads(r.content)
            if r_content["message"] == "Invalid Supported DataItem folderType. Supported values are S3Folder":
                raise ValueError(f"Invalid Supported DataItem '{type_folder}' folderType. Virtual folders cannot be linked.")
            elif r_content["message"] == "Request failed with status code 403":
                raise ValueError(f"Interactive Analysis session is not active")
            else:
                raise ValueError(f"Cannot link folder")
        elif r.status_code == 204:
            if type_folder == "S3":
                full_path = (
                    f"s3://{data['dataItem']['data']['s3BucketName']}/"
                    f"{data['dataItem']['data']['s3Prefix']}"
                )
                mount_name = data['dataItem']['data']['name']
            else:
                full_path = folder
                mount_name = data['dataItem']['name']
            
            try:
                # Wait for mount completion and check final status
                final_status = self.wait_for_mount_completion(session_id, mount_name)
                
                if final_status["status"] == "mounted":
                    click.secho(f"Successfully mounted {type_folder} folder: {full_path}", fg='green', bold=True)
                elif final_status["status"] == "failed":
                    error_msg = final_status.get("errorMessage", "Unknown error")
                    click.secho(f"Failed to mount {type_folder} folder: {full_path}", fg='red', bold=True)
                    click.secho(f"  Error: {error_msg}", fg='red')
                else:
                    click.secho(f"Mount status: {final_status['status']} for {type_folder} folder: {full_path}", fg='yellow', bold=True)
                    
            except ValueError as e:
                click.secho(f"Warning: Could not verify mount status - {str(e)}", fg='yellow', bold=True)
                click.secho(f"  The linking request was submitted, but verification failed.", fg='yellow')

    def parse_s3_path(self, s3_url):
        """
        Parses an S3 URL and extracts the bucket name, prefix, and base name.

        Parameters
        ----------
        s3_url : str
            The S3 URL to parse. Must start with "s3://".

        Returns
        -------
        dict: A dictionary containing the parsed S3 information structured as:
                "dataItem": {
                    "type": "S3Folder",
                    "data": {
                        "name": str,          # The base name (last segment of the prefix).
                        "s3BucketName": str,  # The name of the S3 bucket.
                        "s3Prefix": str       # The full prefix path in the bucket.

        Raises
        ------
        ValueError
            If the S3 URL does not start with "s3://".
            If the S3 URL does not include a key after the bucket.
        """
        if not s3_url.startswith("s3://"):
            raise ValueError("Invalid S3 URL. Link must start with 's3://'")

        parsed = urlparse(s3_url)
        bucket = parsed.netloc
        prefix = parsed.path.lstrip('/') # Remove leading slash

        if not prefix:
            raise ValueError("S3 URL must include a key after the bucket")

        parts = prefix.rstrip('/').split('/')
        base = parts[-1] # Last segment (file or folder)
        return {
            "dataItem": {
            "type": "S3Folder",
            "data": {
                "name": base,
                "s3BucketName": bucket,
                "s3Prefix": prefix
            }
            }
        }

    def parse_file_explorer_path(self, path):
        """
        Parses a file path and returns the base name and full path.

        Parameters
        ----------
        file_path : str
            The file path to parse.

        Returns
        -------
        dict: A dictionary containing the parsed file information structured as:
                "dataItem": {
                    "type": "File",
                    "data": {
                        "name": str,          # The base name of the file.
                        "fullPath": str      # The full path of the file.
        """
        # get folder id
        folder_id = get_file_or_folder_id(
            self.cloudos_url,
            self.apikey,
            self.workspace_id,
            self.project_name,
            self.verify,
            path.strip("/"),
            "",
            is_file=False
        )
        parts = path.strip("/").split("/")
        return {
            "dataItem": {
                "kind": "Folder",
                "item": f"{folder_id}",
                "name": f"{parts[-1]}"
            }
        }

    def get_fuse_filesystems_status(self, session_id: str) -> List[Dict]:
        """Get the status of fuse filesystems for an interactive session.

        Parameters
        ----------
        session_id : str
            The interactive session ID.

        Returns
        -------
        List[Dict]
            List of fuse filesystem objects with their status information.

        Raises
        ------
        ValueError
            If the API request fails or returns an error.
        """
        url = (
            f"{self.cloudos_url}/api/v1/"
            f"interactive-sessions/{session_id}/fuse-filesystems"
            f"?teamId={self.workspace_id}"
        )
        headers = {
            "Content-type": "application/json",
            "apikey": self.apikey
        }
        
        r = retry_requests_get(url, headers=headers, verify=self.verify)
        
        if r.status_code == 401:
            raise ValueError("Forbidden. Invalid API key or insufficient permissions.")
        elif r.status_code == 404:
            raise ValueError(f"Interactive session {session_id} not found")
        elif r.status_code != 200:
            raise ValueError(f"Failed to get fuse filesystem status: HTTP {r.status_code}")
        
        response_data = json.loads(r.content)
        return response_data.get("fuseFileSystems", [])

    def wait_for_mount_completion(self, session_id: str, mount_name: str, 
                                timeout: int = 360, check_interval: int = 2) -> Dict:
        """Wait for a specific mount to complete and return its final status.

        Parameters
        ----------
        session_id : str
            The interactive session ID.
        mount_name : str
            The name of the mount to check.
        timeout : int, optional
            Maximum time to wait in seconds (default: 60).
        check_interval : int, optional
            Time between status checks in seconds (default: 2).

        Returns
        -------
        Dict
            The final status object of the mount.

        Raises
        ------
        ValueError
            If the mount is not found or timeout is reached.
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            filesystems = self.get_fuse_filesystems_status(session_id)
            
            # Find the mount by name
            target_mount = None
            for fs in filesystems:
                if fs.get("mountName") == mount_name:
                    target_mount = fs
                    break
            
            if target_mount and target_mount.get("status") in ["mounted", "failed"]:
                return target_mount
            # If mount not found or still in progress, continue waiting
            
            time.sleep(check_interval)
        
        raise ValueError(f"Timeout waiting for mount '{mount_name}' to complete after {timeout} seconds")

    def link_job_results(self, job_id: str, workspace_id: str, session_id: str, verify_ssl, verbose: bool = False):
        """
        Link job results to an interactive session.
        
        Parameters
        ----------
        job_id : str
            The job ID to link results from
        workspace_id : str
            The workspace ID
        session_id : str
            The interactive session ID
        verify_ssl : Union[bool, str]
            SSL verification setting
        verbose : bool
            Whether to print verbose output
            
        Returns
        -------
        None
            Prints status messages to console
        """
        try:
            if verbose:
                print('\tFetching job results...')
                
            # Create a temporary Cloudos client for API calls
            cl = Cloudos(self.cloudos_url, self.apikey, None)
            results_path = cl.get_job_results(job_id, workspace_id, verify_ssl)
            
            if results_path:
                print(f'\tLinking results directory...')
                if verbose:
                    print(f'\t\tResults: {results_path}')
                self.link_folder(results_path, session_id)
            else:
                click.secho('\tNo results found to link.', fg='yellow')
                
        except JoBNotCompletedException as e:
            click.secho(f'\tCannot link results: {str(e)}', fg='red')
        except Exception as e:
            error_msg = str(e)
            if "Results are not available" in error_msg or "deleted" in error_msg.lower() or "removed" in error_msg.lower():
                click.secho(f'\tCannot link results: {error_msg}', fg='red')
            else:
                click.secho(f'\tFailed to link results: {error_msg}', fg='red')

    def link_job_workdir(self, job_id: str, workspace_id: str, session_id: str, verify_ssl, verbose: bool = False):
        """
        Link job working directory to an interactive session.
        
        Parameters
        ----------
        job_id : str
            The job ID to link workdir from
        workspace_id : str
            The workspace ID
        session_id : str
            The interactive session ID
        verify_ssl : Union[bool, str]
            SSL verification setting
        verbose : bool
            Whether to print verbose output
            
        Returns
        -------
        None
            Prints status messages to console
        """
        try:
            if verbose:
                print('\tFetching job working directory...')
                
            # Create a temporary Cloudos client for API calls
            cl = Cloudos(self.cloudos_url, self.apikey, None)
            workdir_path = cl.get_job_workdir(job_id, workspace_id, verify_ssl)
            
            if workdir_path:
                print(f'\tLinking working directory...')
                if verbose:
                    print(f'\t\tWorkdir: {workdir_path}')
                self.link_folder(workdir_path.strip(), session_id)
            else:
                click.secho('\tNo working directory found to link.', fg='yellow')
                
        except Exception as e:
            error_msg = str(e)
            if "not yet available" in error_msg.lower() or "initializing" in error_msg.lower() or "not available" in error_msg.lower() or "deleted" in error_msg.lower() or "removed" in error_msg.lower():
                click.secho(f'\tCannot link workdir: {error_msg}', fg='red')
            else:
                click.secho(f'\tFailed to link workdir: {error_msg}', fg='red')

    def link_job_logs(self, job_id: str, workspace_id: str, session_id: str, verify_ssl, verbose: bool = False):
        """
        Link job logs to an interactive session.
        
        Parameters
        ----------
        job_id : str
            The job ID to link logs from
        workspace_id : str
            The workspace ID
        session_id : str
            The interactive session ID
        verify_ssl : Union[bool, str]
            SSL verification setting
        verbose : bool
            Whether to print verbose output
            
        Returns
        -------
        None
            Prints status messages to console
        """
        try:
            if verbose:
                print('\tFetching job logs...')
                
            # Create a temporary Cloudos client for API calls
            cl = Cloudos(self.cloudos_url, self.apikey, None)
            logs_dict = cl.get_job_logs(job_id, workspace_id, verify_ssl)
            
            if logs_dict:
                # Extract the parent logs directory from any log file path
                first_log_path = next(iter(logs_dict.values()))
                logs_dir = '/'.join(first_log_path.split('/')[:-1])
                
                print(f'\tLinking logs directory...')
                if verbose:
                    print(f'\t\tLogs directory: {logs_dir}')
                self.link_folder(logs_dir, session_id)
            else:
                click.secho('\tNo logs found to link.', fg='yellow')
                
        except Exception as e:
            error_msg = str(e)
            if "not yet available" in error_msg.lower() or "initializing" in error_msg.lower() or "not available" in error_msg.lower() or "deleted" in error_msg.lower() or "removed" in error_msg.lower():
                click.secho(f'\tCannot link logs: {error_msg}', fg='red')
            else:
                click.secho(f'\tFailed to link logs: {error_msg}', fg='red')

    def link_path_with_validation(self, path: str, session_id: str, verify_ssl, project_name: str = None, verbose: bool = False):
        """
        Link a path (S3 or File Explorer) to an interactive session with validation.
        
        Parameters
        ----------
        path : str
            The path to link
        session_id : str
            The interactive session ID
        project_name : str, optional
            The project name (required for File Explorer paths)
        verify_ssl : Union[bool, str], optional
            SSL verification setting
        verbose : bool
            Whether to print verbose output
            
        Returns
        -------
        None
            Prints status messages to console
            
        Raises
        ------
        click.UsageError
            If Azure path is provided or validation fails
        ValueError
            If path validation fails
        """        
        # Check for Azure paths and provide informative error message
        if path.startswith("az://"):
            raise click.UsageError("Azure Blob Storage paths (az://) are not supported for linking. Please use S3 paths (s3://) or File Explorer paths instead.")
        
        # Validate path requirements
        if not path.startswith("s3://") and not project_name:
            raise click.UsageError("When using File Explorer paths, '--project-name' must be provided.")
        
        # Use the same validation logic as datasets link command
        is_s3 = path.startswith("s3://")
        is_folder = True
        
        if is_s3:
            # S3 path validation
            try:
                if path.endswith('/'):
                    is_folder = True
                else:
                    path_parts = path.rstrip("/").split("/")
                    if path_parts:
                        last_part = path_parts[-1]
                        if '.' not in last_part:
                            is_folder = True
                        else:
                            is_folder = None
                    else:
                        is_folder = None
            except Exception:
                is_folder = None
        else:
            # File Explorer path validation
            try:
                datasets = Datasets(
                    cloudos_url=self.cloudos_url,
                    apikey=self.apikey,
                    workspace_id=self.workspace_id,
                    project_name=project_name,
                    verify=verify_ssl,
                    cromwell_token=None
                )
                parts = path.strip("/").split("/")
                parent_path = "/".join(parts[:-1]) if len(parts) > 1 else ""
                item_name = parts[-1]
                contents = datasets.list_folder_content(parent_path)
                found = None
                for item in contents.get("folders", []):
                    if item.get("name") == item_name:
                        found = item
                        break
                if not found:
                    for item in contents.get("files", []):
                        if item.get("name") == item_name:
                            found = item
                            break
                if found:
                    if "folderType" not in found:
                        # This is a file
                        is_folder = "file"
                    elif found.get("folderType") == "VirtualFolder":
                        # This is a virtual folder (cannot be linked)
                        is_folder = "virtual_folder"
                else:
                    # Item not found in File Explorer
                    is_folder = "not_found"
            except Exception:
                is_folder = None
        
        if is_folder == "file":
            if is_s3:
                raise ValueError("The path appears to point to a file, not a folder. You can only link folders. Please link the parent folder instead.")
            else:
                raise ValueError("The path points to a file. Only folders can be linked. Please link the parent folder instead.")
        elif is_folder == "virtual_folder":
            raise ValueError("The path points to a virtual folder, which cannot be linked. Virtual folders exist only in File Explorer and don't have physical storage locations. Please link an S3 folder or a regular File Explorer folder instead.")
        elif is_folder == "not_found":
            raise ValueError(f"The specified path '{path}' was not found in File Explorer. Please verify the path exists and try again.")
        elif is_folder is None:
            if is_s3:
                click.secho("Unable to verify whether the S3 path is a folder. Proceeding with linking; " +
                           "however, if the operation fails, please confirm that you are linking a folder rather than a file.", 
                           fg='yellow', bold=True)
            else:
                click.secho("Unable to verify the File Explorer path. Proceeding with linking; " +
                           "however, if the operation fails, please verify the path exists and is a folder.", 
                           fg='yellow', bold=True)
        
        if verbose:
            print(f'\tLinking {path}...')
        
        self.link_folder(path, session_id)


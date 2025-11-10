"""
This is the main class for linking files to interactive sessions.
"""

from dataclasses import dataclass
from typing import Union, List, Dict
from cloudos_cli.clos import Cloudos
from cloudos_cli.utils.requests import retry_requests_post, retry_requests_get
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
        # determine if is file explorer, s3, or azure blob
        if folder.startswith('s3://'):
            data = self.parse_s3_path(folder)
            type_folder = "S3"
        elif folder.startswith('az://'):
            data = self.parse_azure_path(folder)
            type_folder = "Azure Blob"
        else:
            data = self.parse_file_explorer_path(folder)
            type_folder = "File Explorer"
        r = retry_requests_post(url, headers=headers, json=data, verify=self.verify)
        
        if r.status_code == 403:
            raise ValueError(f"Provided {type_folder} folder already exists with 'mounted' status")
        elif r.status_code == 401:
            raise ValueError(f"Forbidden: Invalid API key or insufficient permissions")
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
            elif type_folder == "Azure Blob":
                full_path = (
                    f"az://{data['dataItem']['data']['storageAccount']}.blob.core.windows.net/"
                    f"{data['dataItem']['data']['blobContainerName']}/"
                    f"{data['dataItem']['data']['blobPrefix']}"
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

    def parse_azure_path(self, azure_url):
        """
        Parses an Azure Blob Storage URL and extracts the storage account, container, and blob prefix.

        Parameters
        ----------
        azure_url : str
            The Azure Blob Storage URL to parse. Must start with "az://".
            Format: az://{storage_account}.blob.core.windows.net/{container}/{blob_prefix}

        Returns
        -------
        dict: A dictionary containing the parsed Azure information structured as:
                "dataItem": {
                    "type": "AzureBlobFolder",
                    "data": {
                        "name": str,                  # The base name (last segment of the prefix).
                        "storageAccount": str,        # The storage account name.
                        "blobContainerName": str,     # The blob container name.
                        "blobPrefix": str             # The full blob prefix path.
                    }
                }

        Raises
        ------
        ValueError
            If the Azure URL does not start with "az://".
            If the Azure URL format is invalid.
            If the Azure URL does not include a container and blob prefix.
        """
        if not azure_url.startswith("az://"):
            raise ValueError("Invalid Azure Blob Storage URL. Link must start with 'az://'")

        parsed = urlparse(azure_url)
        # Extract storage account from netloc (e.g., "67d97c06d5f03da2eee9ca8b.blob.core.windows.net")
        storage_account_full = parsed.netloc
        
        if not storage_account_full.endswith(".blob.core.windows.net"):
            raise ValueError("Invalid Azure Blob Storage URL. Must be in format: az://{storage_account}.blob.core.windows.net/{container}/{prefix}")
        
        # Extract just the storage account name (before .blob.core.windows.net)
        storage_account = storage_account_full.replace(".blob.core.windows.net", "")
        
        # Parse the path to extract container and blob prefix
        path_parts = parsed.path.lstrip('/').split('/', 1)
        
        if len(path_parts) < 2:
            raise ValueError("Azure Blob Storage URL must include both container and blob prefix")
        
        container_name = path_parts[0]
        blob_prefix = path_parts[1].rstrip('/')
        
        # Get the base name (last segment of the prefix)
        prefix_parts = blob_prefix.split('/')
        base_name = prefix_parts[-1]
        
        return {
            "dataItem": {
                "type": "AzureBlobFolder",
                "data": {
                    "name": base_name,
                    "storageAccount": storage_account,
                    "blobContainerName": container_name,
                    "blobPrefix": blob_prefix
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
            raise ValueError("Forbidden: Invalid API key or insufficient permissions")
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


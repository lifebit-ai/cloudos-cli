"""
This is the main class for linking files to interactive sessions.
"""

from dataclasses import dataclass
from typing import Union
from cloudos_cli.clos import Cloudos
from cloudos_cli.utils.requests import retry_requests_post
from urllib.parse import urlparse
from cloudos_cli.utils.array_job import extract_project, get_file_or_folder_id
import json


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
            else:
                full_path = folder
            print(f"Succesfully linked {type_folder} folder: {full_path}")

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
"""
This is the main class for linking files to interactive sessions.
"""

from dataclasses import dataclass
from typing import Union
from cloudos_cli.clos import Cloudos
from cloudos_cli.utils.requests import retry_requests_post
from urllib.parse import urlparse


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

    def link_S3_folder(self,
                       s3_folder: str,
                       session_id: str) -> dict:
        """Link an S3 folder to an interactive session.

        Parameters
        ----------
        s3_folder : str
            The S3 folder to link.
        session_id : str
            The interactive session ID.

        Raises
        ------
        ValueError
            If the S3 URL already exists with 'mounted' status
            If the API key is invalid or permissions are insufficient
            If the S3 URL is invalid or the session is not active.
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
        data = self.parse_s3_path(s3_folder)
        r = retry_requests_post(url, headers=headers, json=data, verify=self.verify)

        if r.status_code == 403:
            raise ValueError(f"Provided folder already exists with 'mounted' status")
        elif r.status_code == 401:
            raise ValueError(f"Forbidden: Invalid API key or insufficient permissions")
        elif r.status_code == 400:
            raise ValueError("Bad request: please make sure the S3 URL is valid, and the session is active")
        elif r.status_code == 204:
            full_path = (
                f"s3://{data['dataItem']['data']['s3BucketName']}/"
                f"{data['dataItem']['data']['s3Prefix']}"
            )
            print(f"Succesfully linked S3 folder: {full_path}")


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


"""
This is the main class for linking files to interactive sessions.
"""

from dataclasses import dataclass
from typing import Union
from cloudos_cli.clos import Cloudos
from cloudos_cli.utils.requests import retry_requests_get, retry_requests_put, retry_requests_post
import json
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
        apikey : str
            Your CloudOS API key.
        cloudos_url : str
            The CloudOS service URL.
        resource : str
            The resource to link.
        workspace_id : str
            The specific CloudOS workspace ID.
        s3_folder : str
            The S3 folder to link.
        session_id : str
            The interactive session ID.
        verify : bool, optional
            Whether to use SSL verification or not. Defaults to False.

        Returns
        -------
        dict
            The response from the CloudOS API.
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
        print("data: ", data)
        #r = retry_requests_post(url, headers=headers, json=data, verify=self.verify)

    def parse_s3_path(self, s3_url):
        if not s3_url.startswith("s3://"):
            raise ValueError("Invalid S3 URL. Link must start with 's3://'")

        parsed = urlparse(s3_url)
        bucket = parsed.netloc
        key = parsed.path.lstrip('/') # Remove leading slash

        if not key:
            raise ValueError("S3 URL must include a key after the bucket")

        parts = key.rstrip('/').split('/')
        base = parts[-1] # Last segment (file or folder)

        return {
            "bucket": bucket,
            "key": key + ('' if s3_url.endswith('/') else '/'),
            "base": base
        }

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
        r = retry_requests_post(url, headers=headers, json=data, verify=self.verify)
        print("content: ", r.content)
        print("status: ", r.status_code)
        if r.status_code == 403:
            raise ValueError(f"Provided folder already exists with 'mounted' status")
        elif r.status_code == 401:
            raise ValueError(f"Frobidden: Invalid API key or insufficient permissions")
        elif r.status_code == 204:
            full_path = (
                f"s3://{data['dataItem']['data']['s3BucketName']}/"
                f"{data['dataItem']['data']['s3Prefix']}"
            )
            print(f"Succesfully linked S3 folder: {full_path}")


    def parse_s3_path(self, s3_url):
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
            "dataItem":
                {
                "type":"S3Folder",
                    "data":{
                        "name":f"{base}",
                        "s3BucketName":f"{bucket}",
                        "s3Prefix":f"{prefix}"
                    }
                }
        }
#     raise ValueError(f"Failed to link S3 folder: {r.content.decode('utf-8')}")
# ValueError: Failed to link S3 folder: {"statusCode":403,"code":"Forbidden","message":"Given DataItem is already exists with 'mounted' status","time":"2025-07-01T12:07:36.270Z"}
#     raise ValueError(f"Failed to link S3 folder: {r.content.decode('utf-8')}")
# ValueError: Failed to link S3 folder:

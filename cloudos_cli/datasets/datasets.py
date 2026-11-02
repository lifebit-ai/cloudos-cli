"""
This is the main class for file explorer (datasets).
"""

import base64
import contextlib
import math
import mimetypes
import os
import re
import stat
import tempfile
import requests
from dataclasses import dataclass
from typing import Union
from rich.progress import BarColumn, DownloadColumn, Progress, TimeRemainingColumn, TransferSpeedColumn
from cloudos_cli.clos import Cloudos
from cloudos_cli.utils.errors import BadRequestException
from cloudos_cli.utils.requests import retry_requests_get, retry_requests_put, retry_requests_post, retry_requests_delete
from cloudos_cli.datasets.s3_multipart_upload import (
    MAX_OBJECT_SIZE,
    S3_TIMEOUT,
    S3UploadError,
    SignedS3MultipartUploader,
    TransferError,
    compute_part_size,
    scrubbed_transport_errors,
)
import json

SIGV4_SIGNATURE_RE = re.compile(r"^[0-9a-f]{64}$")

AIRLOCK_BLOCKED_MESSAGES = {
    "upload": (
        "Uploading files from your computer is disabled by this workspace's Airlock policy. "
        "Contact a workspace admin to request access."
    ),
    "download": (
        "Downloading files from the CLI is disabled while Airlock is enabled for this workspace. "
        "Contact a workspace admin to request access."
    ),
    "scan": (
        "This workspace scans imported files through Airlock before they become available, "
        "which the CLI doesn't support yet. Upload the file from the web UI instead."
    ),
}


@contextlib.contextmanager
def _transfer_progress(enabled, total_bytes, description):
    """Yield a callback that advances a progress bar by N bytes (a no-op when not ``enabled``)."""
    if not enabled:
        yield lambda n: None
        return
    with Progress("[progress.description]{task.description}", BarColumn(), DownloadColumn(),
                  TransferSpeedColumn(), TimeRemainingColumn()) as bar:
        task = bar.add_task(description, total=total_bytes)
        yield lambda n: bar.update(task, advance=n)


@dataclass
class Datasets(Cloudos):
    """Class for file explorer.

    Parameters
    ----------
    cloudos_url : string
        The Lifebit Platform service url.
    apikey : string
        Your Lifebit Platform API key.
    workspace_id : string
        The specific Cloudos workspace id.
    project_name : string
        The name of a Lifebit Platform project.
    verify: [bool|string]
        Whether to use SSL verification or not. Alternatively, if
        a string is passed, it will be interpreted as the path to
        the SSL certificate file.
    project_id : string
        The Lifebit Platform project id for a given project name.
    """
    workspace_id: str
    project_name: str
    verify: Union[bool, str] = True
    project_id: str = None

    @property
    def project_id(self) -> str:
        return self._project_id

    @project_id.setter
    def project_id(self, v) -> None:
        if isinstance(v, property):
            # Fetch the value as not defined by user.
            self._project_id = self.fetch_project_id(
                self.workspace_id,
                self.project_name,
                verify=self.verify)
        else:
            # Let the user define the value.
            self._project_id = v

    def fetch_project_id(self,
                         workspace_id,
                         project_name,
                         verify=True):
        """Fetch the project id for a given name.

        Parameters
        ----------
        workspace_id : string
            The specific Cloudos workspace id.
        project_name : string
            The name of a Lifebit Platform project element.
        verify: [bool|string]
            Whether to use SSL verification or not. Alternatively, if
            a string is passed, it will be interpreted as the path to
            the SSL certificate file.

        Returns
        -------
        project_id : string
            The Lifebit Platform project id for a given project name.
        """
        return self.get_project_id_from_name(workspace_id, project_name, verify=verify)

    def list_project_content(self):
        """
        Fetch the information of the directories present in the projects.

        Uses
        ----------
        apikey : string
            Your Lifebit Platform API key
        cloudos_url : string
            The Lifebit Platform service url.
        workspace_id : string
            The specific Cloudos workspace id.
        project_id
            The specific project id
        """
        headers = {
            "Content-type": "application/json",
            "apikey": self.apikey
        }
        r = retry_requests_get("{}/api/v2/datasets?projectId={}&teamId={}".format(self.cloudos_url,
                                                                                  self.project_id,
                                                                                  self.workspace_id),
                               headers=headers, verify=self.verify)
        if r.status_code >= 400:
            raise BadRequestException(r)
        raw = r.json()
        datasets = raw.get("datasets", [])
        #  Normalize response
        for item in datasets:
            item["folderType"] = True
        response = {
                "folders": datasets,
                "files": []
            }
        return response

    def list_datasets_content(self, folder_name):
        """Uses
        ----------
        apikey : string
            Your Lifebit Platform API key
        cloudos_url : string
            The Lifebit Platform service url.
        workspace_id : string
            The specific Cloudos workspace id.
        project_id : string
            The specific project id
        folder_name : string
            The requested folder name
        """
        # Prepare api request for Lifebit Platform to fetch dataset info
        headers = {
            "Content-type": "application/json",
            "apikey": self.apikey
        }
        pro_fol = self.list_project_content()
        folder_id = None

        if folder_name == 'AnalysesResults':
            folder_name = 'Analyses Results'

        for folder in pro_fol.get("folders", []):
            if folder['name'] == folder_name:
                folder_id = folder['_id']
        if not folder_id:
            raise ValueError(f"Folder '{folder_name}' not found in project '{self.project_name}'.")
        r = retry_requests_get("{}/api/v1/datasets/{}/items?teamId={}".format(self.cloudos_url,
                                                                              folder_id,
                                                                              self.workspace_id),
                               headers=headers, verify=self.verify)
        if r.status_code >= 400:
            raise BadRequestException(r)
        return r.json()

    def list_s3_folder_content(self, s3_bucket_name, s3_relative_path):
        """Uses
        ----------
        apikey : string
            Your Lifebit Platform API key
        cloudos_url : string
            The Lifebit Platform service url.
        workspace_id : string
            The specific Cloudos workspace id.
        project_id : string
            The specific project id
        s3_bucket_name : string
            The s3 bucket name
        s3_relative_path: string
            The relative path in the s3 bucket
        """
        # Prepare api request for Lifebit Platform to fetch dataset info
        headers = {
            "Content-type": "application/json",
            "apikey": self.apikey
        }

        r = retry_requests_get("{}/api/v1/data-access/s3/bucket-contents?bucket={}&path={}&teamId={}".format(self.cloudos_url,
                                                                                                             s3_bucket_name,
                                                                                                             s3_relative_path,
                                                                                                             self.workspace_id),
                               headers=headers, verify=self.verify)
        if r.status_code >= 400:
            raise BadRequestException(r)
        raw = r.json()

        #  Normalize response
        normalized = {"folders": [], "files": []}
        for item in raw.get("contents", []):
            if item.get("isDir"):
                item["folderType"] = "S3Folder"  # 👈 inject folderType
                item["s3BucketName"] = s3_bucket_name
                item["s3Prefix"] = item['path']
                normalized["folders"].append(item)
            else:
                item["s3Prefix"] = item['path']
                item["s3BucketName"] = s3_bucket_name
                item["fileType"] = "S3File"
                normalized["files"].append(item)

        return normalized

    def list_virtual_folder_content(self, folder_id):
        """Uses
        ----------
        apikey : string
            Your Lifebit Platform API key
        cloudos_url : string
            The Lifebit Platform service url.
        workspace_id : string
            The specific Cloudos workspace id.
        project_id : string
            The specific project id
        folder_id : string
            The folder id of the folder whose content are to be listed
        """
        headers = {
            "Content-type": "application/json",
            "apikey": self.apikey
        }

        r = retry_requests_get("{}/api/v1/folders/virtual/{}/items?teamId={}".format(self.cloudos_url,
                                                                                     folder_id,
                                                                                     self.workspace_id),
                               headers=headers, verify=self.verify)
        if r.status_code >= 400:
            raise BadRequestException(r)
        return r.json()

    def list_azure_container_content(self, container_name: str, storage_account_name: str, path: str):
        """
        List contents of an Azure Blob container path.
        """
        headers = {
            "Content-type": "application/json",
            "apikey": self.apikey
        }

        url = f"{self.cloudos_url}/api/v1/data-access/azure/container-contents"
        url += f"?containerName={container_name}&storageAccountName={storage_account_name}"
        url += f"&path={path}&teamId={self.workspace_id}"

        r = retry_requests_get(url, headers=headers, verify=self.verify)
        if r.status_code >= 400:
            raise BadRequestException(r)
        raw = r.json()

        # Normalize response to match existing expectations
        normalized = {"folders": [], "files": []}
        for item in raw.get("contents", []):
            is_dir = item.get("isDir", False)

            # Set a name field based on the last part of the blob path
            path_str = item.get("path", "")
            name = item.get("name") or path_str.rstrip("/").split("/")[-1]

            # inject expected structure
            if is_dir:
                normalized["folders"].append({
                    "_id": item.get("_id"),
                    "name": name,
                    "folderType": "AzureBlobFolder",
                    "blobPrefix": path_str,
                    "blobContainerName": container_name,
                    "blobStorageAccountName": storage_account_name,
                    "kind": "Folder"
                })
            else:
                normalized["files"].append({
                    "_id": item.get("_id"),
                    "name": name,
                    "fileType": "AzureBlobFile",
                    "blobName": path_str,
                    "blobContainerName": container_name,
                    "blobStorageAccountName": storage_account_name,
                    "sizeInBytes": item.get("size", 0),
                    "updatedAt": item.get("lastModified"),
                    "kind": "File"
                })

        return normalized

    def list_folder_content(self, path=None):
        """
        Wrapper to list contents of a Lifebit Platform folder.

        Parameters
        ----------
        path : str, optional
            A path like 'TopFolder', 'TopFolder/Subfolder', or deeper.
            If None, lists all top-level datasets in the project.

        Returns
        -------
        dict
            JSON response from the appropriate Lifebit Platform endpoint.
        """
        if not path:
            return self.list_project_content()

        parts = path.strip('/').split('/')

        if len(parts) == 1:
            return self.list_datasets_content(parts[0])

        dataset_name = parts[0]
        folder_content = self.list_datasets_content(dataset_name)

        path_depth = 1
        while path_depth < len(parts):
            job_name = parts[path_depth]
            found = False

            # First, check if this is a folder
            for job_folder in folder_content.get("folders", []):
                if job_folder["name"] == job_name:
                    found = True
                    folder_type = job_folder.get("folderType")

                    if folder_type == "S3Folder":
                        s3_bucket_name = job_folder['s3BucketName']
                        s3_relative_path = job_folder['s3Prefix']
                        if path_depth == len(parts) - 1:
                            return self.list_s3_folder_content(s3_bucket_name, s3_relative_path)
                        else:
                            sub_path = '/'.join(parts[0:path_depth+1])
                            folder_content = self.list_folder_content(sub_path)
                            path_depth += 1
                            break

                    elif folder_type == "VirtualFolder":
                        folder_id = job_folder['_id']
                        if path_depth == len(parts) - 1:
                            return self.list_virtual_folder_content(folder_id)
                        else:
                            sub_path = '/'.join(parts[0:path_depth+1])
                            folder_content = self.list_folder_content(sub_path)
                            path_depth += 1
                            break

                    elif folder_type == "AzureBlobFolder":
                        container_name = job_folder['blobContainerName']
                        storage_account_name = job_folder['blobStorageAccountName']
                        blob_prefix = job_folder['blobPrefix']
                        # trailing slash is mandatory for azure, otherwise it will not list the content of thefolde, just the folder
                        if not blob_prefix.endswith('/'):
                            blob_prefix += '/'

                        if path_depth == len(parts) - 1:
                            return self.list_azure_container_content(container_name, storage_account_name, blob_prefix)
                        else:
                            sub_path = '/'.join(parts[0:path_depth+1])
                            folder_content = self.list_folder_content(sub_path)
                            path_depth += 1
                            break
                    else:
                        raise ValueError(f"Unsupported folder type '{folder_type}' for path '{path}'")

            # If not found as a folder and this is the last part of the path, check if it's a file
            if not found and path_depth == len(parts) - 1:
                for file_item in folder_content.get("files", []):
                    if file_item["name"] == job_name:
                        # Return the file as a single-item result
                        return {
                            "files": [file_item],
                            "folders": []
                        }

                # Also check in contents array (for different API response formats)
                for item in folder_content.get("contents", []):
                    if item["name"] == job_name and not item.get("isDir", True):
                        return {
                            "files": [item],
                            "folders": []
                        }

            if not found:
                # Check if we're looking for a file but it's not the last part (invalid path)
                if path_depth < len(parts) - 1:
                    raise ValueError(f"Folder '{job_name}' not found under dataset '{dataset_name}'")
                else:
                    raise ValueError(f"File or folder '{job_name}' not found under dataset '{dataset_name}'")

        return folder_content

    def move_files_and_folders(self, source_id: str, source_kind: str, target_id: str, target_kind: str):
        """
        Move a file to another dataset in Lifebit Platform.

        Parameters
        ----------
        file_id : str
            The ID of the file to move.

        target_dataset_id : str
            The ID of the target dataset to move the file into.

        Returns
        -------
        response : requests.Response
            The response object from the Lifebit Platform API.
        """
        url = f"{self.cloudos_url}/api/v1/dataItems/move?teamId={self.workspace_id}"
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "ApiKey": self.apikey
        }
        payload = {
            "dataItemToMove": {
                "kind": source_kind,
                "item": source_id
            },
            "toDataItemParent": {
                "kind": target_kind,
                "item": target_id
            }
        }
        response = retry_requests_put(url, headers=headers, data=json.dumps(payload), verify=self.verify)
        if response.status_code >= 400:
            raise BadRequestException(response)
        return response

    def rename_item(self, item_id: str, new_name: str, kind: str):
        """
        Rename a file or folder in Lifebit Platform.

        Parameters
        ----------
        item_id : str
            The ID of the file or folder to rename.
        new_name : str
            The new name to assign to the item.
        kind : str
            Either "File" or "Folder"

        Returns
        -------
        response : requests.Response
            The response object from the Lifebit Platform API.
        """
        if kind not in ("File", "Folder"):
            raise ValueError("Invalid kind provided. Must be 'File' or 'Folder'.")

        endpoint = "files" if kind == "File" else "folders"
        url = f"{self.cloudos_url}/api/v1/{endpoint}/{item_id}?teamId={self.workspace_id}"

        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "ApiKey": self.apikey
        }

        payload = {
            "name": new_name
        }

        response = retry_requests_put(url, headers=headers, data=json.dumps(payload), verify=self.verify)
        if response.status_code >= 400:
            raise BadRequestException(response)
        return response

    def copy_item(self, item, destination_id, destination_kind):
        """Copy a file or folder (S3, Azure or Virtual) to a destination in Lifebit Platform."""
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "ApiKey": self.apikey
        }
        parent = {"kind": destination_kind, "id": destination_id}

        # Virtual folder
        if item.get("folderType") == "VirtualFolder":
            payload = {
                "copyContentsFrom": item["_id"],
                "name": item["name"],
                "parent": parent
            }
            url = f"{self.cloudos_url}/api/v1/folders/virtual?teamId={self.workspace_id}"
        # S3 folder
        elif item.get("folderType") == "S3Folder":
            payload = {
                "s3BucketName": item["s3BucketName"],
                "s3Prefix": item.get("s3Prefix"),
                "name": item["name"],
                "parent": parent,
                "isManagedByLifebit": item.get("isManagedByLifebit", False)
            }
            url = f"{self.cloudos_url}/api/v1/folders/s3?teamId={self.workspace_id}"
        # S3 file
        elif item.get("fileType") == "S3File":
            payload = {
                "s3BucketName": item["s3BucketName"],
                "s3ObjectKey": item.get("s3ObjectKey") or item.get("s3Prefix"),
                "name": item["name"],
                "parent": parent,
                "isManagedByLifebit": item.get("isManagedByLifebit", False),
                "sizeInBytes": item.get("sizeInBytes", 0)
            }
            url = f"{self.cloudos_url}/api/v1/files/s3?teamId={self.workspace_id}"
        # Azure folder
        elif item.get("folderType") == "AzureBlobFolder":
            payload = {
                "blobContainerName": item["blobContainerName"],
                "blobPrefix": item["blobPrefix"],
                "blobStorageAccountName": item["blobStorageAccountName"],
                "name": item["name"],
                "parent": parent
            }
            url = f"{self.cloudos_url}/api/v1/folders/azure-blob?teamId={self.workspace_id}"
        # Azure file
        elif item.get("fileType") == "AzureBlobFile":
            payload = {
                "blobContainerName": item["blobContainerName"],
                "blobName": item["blobName"],
                "blobStorageAccountName": item["blobStorageAccountName"],
                "name": item["name"],
                "parent": parent,
                "isManagedByLifebit": item.get("isManagedByLifebit", False),
                "sizeInBytes": item.get("sizeInBytes", 0)
            }
            url = f"{self.cloudos_url}/api/v1/files/azure-blob?teamId={self.workspace_id}"

        else:
            raise ValueError(f"Unknown item type for copy: {item.get('name')}")
        response = retry_requests_post(url, headers=headers, json=payload)
        if response.status_code >= 400:
            raise BadRequestException(response)
        return response

    def create_virtual_folder(self, name: str, parent_id: str, parent_kind: str):
        """
        Create a new virtual folder in Lifebit Platform under a given parent.

        Parameters
        ----------
        name : str
            The name of the new folder.
        parent_id : str
            The ID of the parent (can be a Dataset or a Folder).
        parent_kind : str
            The type of the parent: either "Dataset" or "Folder".

        Returns
        -------
        response : requests.Response
            The response object from the Lifebit Platform API.
        """
        if parent_kind not in ("Dataset", "Folder"):
            raise ValueError("Invalid parent_kind. Must be 'Dataset' or 'Folder'.")

        url = f"{self.cloudos_url}/api/v1/folders/virtual?teamId={self.workspace_id}"

        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "ApiKey": self.apikey
        }

        payload = {
            "name": name,
            "parent": {
                "kind": parent_kind,
                "id": parent_id
            }
        }

        response = retry_requests_post(url, headers=headers, json=payload, verify=self.verify)
        if response.status_code >= 400:
            raise BadRequestException(response)
        return response

    def delete_item(self, item_id: str, kind: str):
        """
        Delete a file or folder in Lifebit Platform.

        Parameters
        ----------
        item_id : str
            The ID of the file or folder to delete.
        kind : str
            Must be either "File" or "Folder".

        Returns
        -------
        response : requests.Response
            The response object from the Lifebit Platform API.
        """
        if kind not in ("File", "Folder"):
            raise ValueError("Invalid kind provided. Must be 'File' or 'Folder'.")

        endpoint = "files" if kind == "File" else "folders"
        url = f"{self.cloudos_url}/api/v1/{endpoint}/{item_id}?teamId={self.workspace_id}"

        headers = {
            "accept": "application/json",
            "ApiKey": self.apikey
        }

        response = retry_requests_delete(url, headers=headers, verify=self.verify)
        if response.status_code >= 400:
            raise BadRequestException(response)
        return response

    def get_airlock_configuration(self):
        """Return this workspace's Airlock configuration if Airlock is enabled, else None.

        Also None when the policy can't be read (no policy, no permission to view it,
        or a failed request): the precheck is then skipped and the platform still
        enforces the policy on the real request.
        """
        url = (f"{self.cloudos_url}/api/v2/airlock-api/workspaces/{self.workspace_id}"
               f"/configuration?teamId={self.workspace_id}")
        try:
            r = retry_requests_get(url, headers={"Content-type": "application/json", "apikey": self.apikey},
                                   verify=self.verify)
            config = r.json() if r.status_code < 400 else None
        except (requests.RequestException, ValueError):
            return None
        return config if isinstance(config, dict) and config.get("enabled") else None

    def check_airlock_restriction(self, action):
        """Return a message if Airlock is known to block ``action`` ("upload" or "download"), else None."""
        config = self.get_airlock_configuration()
        if not config:
            return None
        if action == "download":
            # The platform rejects every API-key download while Airlock is enabled,
            # even when permissions.members.enableViewFile is true.
            return AIRLOCK_BLOCKED_MESSAGES["download"]
        members = (config.get("permissions") or {}).get("members") or {}
        if members.get("enableImportFromComputer", True) is False:
            return AIRLOCK_BLOCKED_MESSAGES["upload"]
        # A direct upload would skip the import scan and approval the web UI goes through.
        if any((config.get(section) or {}).get("enabled") for section in ("airlockIn", "importSettings")):
            return AIRLOCK_BLOCKED_MESSAGES["scan"]
        return None

    def get_signed_download_url(self, item):
        """Return a short-lived presigned URL for a file item from ``list_folder_content``."""
        def b64(text):
            return base64.b64encode(text.encode("utf-8")).decode("ascii")

        if item.get("fileType") == "S3File" or "s3BucketName" in item:
            provider = "s3"
            params = {"bucket": item["s3BucketName"], "key": b64(item.get("s3ObjectKey") or item.get("s3Prefix"))}
        elif item.get("fileType") == "AzureBlobFile" or "blobContainerName" in item:
            provider = "azure"
            params = {"containerName": item["blobContainerName"],
                      "storageAccountName": item["blobStorageAccountName"], "blobKey": b64(item["blobName"])}
        else:
            raise ValueError(f"Item '{item.get('name')}' is not a supported file type for download.")
        r = retry_requests_get(f"{self.cloudos_url}/api/v1/data-access/{provider}/signed-object-url",
                               headers={"Content-type": "application/json", "apikey": self.apikey},
                               params={**params, "teamId": self.workspace_id}, verify=self.verify)
        if r.status_code >= 400:
            raise BadRequestException(r)
        signed_url = r.json().get("signedUrl")
        if not signed_url:
            raise ValueError("Server did not return a signed download URL.")
        return signed_url

    def download_to_file(self, signed_url, local_path, overwrite=False, expected_size=None,
                         chunk_size=8 * 1024 * 1024, progress=False):
        """Stream a presigned URL to ``local_path``.

        The content goes to a private temporary file next to ``local_path`` and is only
        moved into place once complete, so a failed download never leaves a partial file
        or destroys an existing one. A size other than ``expected_size`` (or the
        Content-Length) counts as a failed download.
        """
        if not overwrite and os.path.lexists(local_path):
            raise FileExistsError(f"'{local_path}' already exists. Use --overwrite/-f to overwrite it.")
        if not signed_url.startswith("https://"):
            raise TransferError("The platform returned a download URL that is not HTTPS.")

        with scrubbed_transport_errors("Download"):
            response = retry_requests_get(signed_url, stream=True, verify=self.verify, timeout=S3_TIMEOUT)
        if response.status_code >= 400:
            raise BadRequestException(response)
        if expected_size is None and response.headers.get("Content-Length", "").isdigit():
            expected_size = int(response.headers["Content-Length"])

        dest_dir = os.path.dirname(os.path.abspath(local_path))
        fd, tmp_path = tempfile.mkstemp(dir=dest_dir, prefix=".cloudos-download-", suffix=".part")
        try:
            if hasattr(os, "fchmod"):
                # mkstemp creates the file 0600; give it the usual permissions for a new file.
                umask = os.umask(0)
                os.umask(umask)
                os.fchmod(fd, 0o666 & ~umask)
            written = 0
            with os.fdopen(fd, "wb") as fh, scrubbed_transport_errors("Download"), \
                    _transfer_progress(progress, expected_size, "Downloading") as advance:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        fh.write(chunk)
                        written += len(chunk)
                        if expected_size is not None and written > expected_size:
                            break
                        advance(len(chunk))
            if expected_size is not None and written != expected_size:
                raise TransferError(f"Download size mismatch: received {written} bytes, expected {expected_size}.")
            if overwrite:
                os.replace(tmp_path, local_path)
            else:
                # Hard-link is an atomic "create only if absent": it fails rather
                # than following a symlink or clobbering a file created meanwhile.
                try:
                    os.link(tmp_path, local_path)
                except OSError:
                    if os.path.lexists(local_path):
                        raise FileExistsError(
                            f"'{local_path}' already exists. Use --overwrite/-f to overwrite it."
                        ) from None
                    # Filesystem without hard links (e.g. FAT or some network drives).
                    os.replace(tmp_path, local_path)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        return local_path

    def _get_workspace_json(self, path):
        r = retry_requests_get(f"{self.cloudos_url}{path}?teamId={self.workspace_id}",
                               headers={"Content-type": "application/json", "apikey": self.apikey},
                               verify=self.verify)
        data = r.json() if r.status_code < 400 else None
        if not data:
            raise BadRequestException(r)
        return data

    def get_cloud_aws_config(self):
        """Return this workspace's AWS bucket, prefix and region; raise BadRequestException if it has none."""
        return self._get_workspace_json("/api/v1/cloud/aws")

    def get_tmp_aws_credentials(self):
        """Return temporary upload credentials: ``credentials`` (an opaque blob only the
        platform signer can use), and base64-encoded ``sessionToken`` and ``key``
        (access key id). They are never logged or written to disk."""
        return self._get_workspace_json("/api/v1/aws/tmp-credentials")

    def sign_upload_for_evaporate(self, to_sign, amz_datetime, canonical_request, credentials_blob):
        """Ask the platform to sign an S3 request (SigV4) and return the hex signature.

        The CLI never holds an AWS secret key: the opaque ``credentials_blob`` is sent
        only in the ``Credentials`` header of this request.
        """
        params = {"to_sign": to_sign, "datetime": amz_datetime,
                  "canonical_request": canonical_request, "teamId": self.workspace_id}
        # The query string carries the canonical request, which includes the STS token.
        with scrubbed_transport_errors("Upload signing request"):
            r = retry_requests_get(f"{self.cloudos_url}/api/v1/s3/signUploadForEvaporate",
                                   headers={"apikey": self.apikey, "Credentials": credentials_blob},
                                   params=params, verify=self.verify, timeout=S3_TIMEOUT)
        if r.status_code >= 400:
            raise BadRequestException(r)
        # Accept {"signature": "..."}, a JSON string, or a plain-text body.
        try:
            data = r.json()
        except ValueError:
            data = r.text
        if isinstance(data, dict):
            data = data.get("signature")
        signature = data.strip() if isinstance(data, str) else ""
        if not SIGV4_SIGNATURE_RE.match(signature):
            raise TransferError("The platform's upload signer returned an unexpected response.")
        return signature

    @staticmethod
    def upload_object_key(cloud_config, destination_parent_kind, destination_folder_id, filename):
        """S3 object key a local upload is stored under.

        The prefix already includes teams/{id}/users/{id}; this mirrors the web
        uploader's layout (dataset/ for a Dataset parent, folder/ for a Folder).
        """
        prefix = cloud_config.get("lifebitBucketS3Prefix", "")
        key_segment = "dataset" if destination_parent_kind == "Dataset" else "folder"
        return f"{prefix}/{key_segment}/{destination_folder_id}/{filename}"

    def upload_local_file(self, local_path, destination_folder_id, destination_parent_kind,
                          cloud_config, destination_name=None, progress=True):
        """Upload a local file to a Dataset or Folder (AWS workspaces only) and register it.

        Like the web uploader, this always uses a multipart upload, even for small files.

        Parameters
        ----------
        local_path : str
            Path to the local file.
        destination_folder_id : str
            ``_id`` of the destination Dataset or Folder.
        destination_parent_kind : str
            ``"Dataset"`` or ``"Folder"``.
        cloud_config : dict
            The workspace's AWS configuration, from ``get_cloud_aws_config``.
        destination_name : str, optional
            File name to register. Defaults to the local file's name.
        progress : bool
            Whether to show a progress bar.

        Returns
        -------
        requests.Response
            The response from registering the file (``POST /api/v1/files/s3``).
        """
        st = os.stat(local_path)
        if not stat.S_ISREG(st.st_mode):
            raise ValueError(f"'{local_path}' is not a regular file and cannot be uploaded.")
        file_size = st.st_size
        if file_size > MAX_OBJECT_SIZE:
            raise ValueError(f"'{local_path}' is {file_size} bytes, more than S3's 5 TiB maximum object size.")

        filename = destination_name or os.path.basename(local_path)
        bucket = cloud_config["lifebitBucketName"]
        object_key = self.upload_object_key(cloud_config, destination_parent_kind,
                                            destination_folder_id, filename)
        creds = self.get_tmp_aws_credentials()
        uploader = SignedS3MultipartUploader(
            datasets_client=self,
            bucket=bucket,
            key=object_key,
            region=cloud_config.get("awsRegion", "us-east-1"),
            content_type=mimetypes.guess_type(filename)[0],
            # Both arrive base64-encoded.
            access_key_id=base64.b64decode(creds["key"]).decode("utf-8"),
            session_token=base64.b64decode(creds["sessionToken"]).decode("utf-8"),
            credentials_blob=creds["credentials"],
            verify=self.verify,
        )
        part_size = compute_part_size(file_size)
        total_parts = max(1, math.ceil(file_size / part_size))

        upload_id = uploader.create_multipart_upload()
        parts = []
        try:
            # Send exactly the size measured above, so the registered sizeInBytes matches S3.
            with open(local_path, "rb") as fh, _transfer_progress(progress, file_size, "Uploading") as advance:
                for part_number in range(1, total_parts + 1):
                    expected = min(part_size, file_size - (part_number - 1) * part_size)
                    chunk = fh.read(expected)
                    if len(chunk) != expected:
                        raise TransferError(f"'{local_path}' changed size while it was being uploaded.")
                    parts.append((part_number, uploader.upload_part(part_number, chunk, upload_id)))
                    advance(len(chunk))
            uploader.complete_multipart_upload(upload_id, parts)
        except Exception as e:
            try:
                uploader.abort_multipart_upload(upload_id)
            except Exception:
                pass  # best-effort cleanup; never mask the original error
            if isinstance(e, S3UploadError) and e.status_code == 412:
                raise ValueError(f"A file named '{filename}' is already stored in this folder's storage "
                                 "location. Rename the local file and try again.") from None
            raise

        # Same payload as the S3-file branch of copy_item.
        payload = {"name": filename, "parent": {"kind": destination_parent_kind, "id": destination_folder_id},
                   "s3BucketName": bucket, "s3ObjectKey": object_key, "sizeInBytes": file_size,
                   "isManagedByLifebit": True, "fileType": "S3File"}
        response = retry_requests_post(f"{self.cloudos_url}/api/v1/files/s3?teamId={self.workspace_id}",
                                       headers={"accept": "application/json", "content-type": "application/json",
                                                "ApiKey": self.apikey},
                                       json=payload, verify=self.verify)
        if response.status_code >= 400:
            raise BadRequestException(response)
        return response

"""
This is the main class for file explorer (datasets).
"""

from dataclasses import dataclass
from typing import Union
from cloudos_cli.clos import Cloudos
from cloudos_cli.utils.errors import BadRequestException
from cloudos_cli.utils.requests import retry_requests_get, retry_requests_put, retry_requests_post, retry_requests_delete
import json

@dataclass
class Datasets(Cloudos):
    """Class for file explorer.

    Parameters
    ----------
    cloudos_url : string
        The CloudOS service url.
    apikey : string
        Your CloudOS API key.
    workspace_id : string
        The specific Cloudos workspace id.
    project_name : string
        The name of a CloudOS project.
    verify: [bool|string]
        Whether to use SSL verification or not. Alternatively, if
        a string is passed, it will be interpreted as the path to
        the SSL certificate file.
    project_id : string
        The CloudOS project id for a given project name.
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
            The name of a CloudOS project element.
        verify: [bool|string]
            Whether to use SSL verification or not. Alternatively, if
            a string is passed, it will be interpreted as the path to
            the SSL certificate file.

        Returns
        -------
        project_id : string
            The CloudOS project id for a given project name.
        """
        return self.get_project_id_from_name(workspace_id, project_name, verify=verify)

    def list_project_content(self):
        """
        Fetch the information of the directories present in the projects.

        Uses
        ----------
        apikey : string
            Your CloudOS API key
        cloudos_url : string
            The CloudOS service url.
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
        response ={
                "folders": datasets,
                "files": []
            }
        return response

    def list_datasets_content(self, folder_name):
        """Uses
        ----------
        apikey : string
            Your CloudOS API key
        cloudos_url : string
            The CloudOS service url.
        workspace_id : string
            The specific Cloudos workspace id.
        project_id : string
            The specific project id
        folder_name : string
            The requested folder name
        """
        # Prepare api request for CloudOS to fetch dataset info
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
            Your CloudOS API key
        cloudos_url : string
            The CloudOS service url.
        workspace_id : string
            The specific Cloudos workspace id.
        project_id : string
            The specific project id
        s3_bucket_name : string
            The s3 bucket name
        s3_relative_path: string
            The relative path in the s3 bucket
        """
        # Prepare api request for CloudOS to fetch dataset info
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
            Your CloudOS API key
        cloudos_url : string
            The CloudOS service url.
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
        Wrapper to list contents of a CloudOS folder.

        Parameters
        ----------
        path : str, optional
            A path like 'TopFolder', 'TopFolder/Subfolder', or deeper.
            If None, lists all top-level datasets in the project.

        Returns
        -------
        dict
            JSON response from the appropriate CloudOS endpoint.
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

            if not found:
                raise ValueError(f"Folder '{job_name}' not found under dataset '{dataset_name}'")

        return folder_content
    
    def move_files_and_folders(self, source_id: str, source_kind: str, target_id: str, target_kind: str):
        """
        Move a file to another dataset in CloudOS.

        Parameters
        ----------
        file_id : str
            The ID of the file to move.

        target_dataset_id : str
            The ID of the target dataset to move the file into.

        Returns
        -------
        response : requests.Response
            The response object from the CloudOS API.
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
        Rename a file or folder in CloudOS.

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
            The response object from the CloudOS API.
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
        """Copy a file or folder (S3, Azure or Virtual) to a destination in CloudOS."""
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
                "s3ObjectKey": item.get("s3ObjectKey") or item.get("s3Prefix"),
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
        Create a new virtual folder in CloudOS under a given parent.

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
            The response object from the CloudOS API.
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
        Delete a file or folder in CloudOS.

        Parameters
        ----------
        item_id : str
            The ID of the file or folder to delete.
        kind : str
            Must be either "File" or "Folder".

        Returns
        -------
        response : requests.Response
            The response object from the CloudOS API.
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
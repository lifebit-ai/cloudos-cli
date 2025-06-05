"""
This is the main class for file explorer (datasets).
"""

from dataclasses import dataclass
from typing import Union
import json
from cloudos_cli.clos import Cloudos
from cloudos_cli.utils.errors import BadRequestException
from cloudos_cli.utils.requests import retry_requests_get


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
            self._project_id = self.fetch_cloudos_id(
                self.apikey,
                self.cloudos_url,
                'projects',
                self.workspace_id,
                self.project_name,
                verify=self.verify)
        else:
            # Let the user define the value.
            self._project_id = v

    def fetch_cloudos_id(self,
                         apikey,
                         cloudos_url,
                         resource,
                         workspace_id,
                         name,
                         mainfile=None,
                         importsfile=None,
                         repository_platform='github',
                         verify=True):
        """Fetch the cloudos id for a given name.

        Parameters
        ----------
        apikey : string
            Your CloudOS API key
        cloudos_url : string
            The CloudOS service url.
        resource : string
            The resource you want to fetch from. E.g.: projects.
        workspace_id : string
            The specific Cloudos workspace id.
        name : string
            The name of a CloudOS resource element.
        mainfile : string
            The name of the mainFile used by the workflow. Only used when resource == 'workflows'.
            Required for WDL pipelines as different mainFiles could be loaded for a single
            pipeline.
        importsfile : string
            The name of the importsFile used by the workflow. Optional and only used for WDL pipelines
            as different importsFiles could be loaded for a single pipeline.
        repository_platform : string
            The name of the repository platform of the workflow resides.
        verify: [bool|string]
            Whether to use SSL verification or not. Alternatively, if
            a string is passed, it will be interpreted as the path to
            the SSL certificate file.

        Returns
        -------
        project_id : string
            The CloudOS project id for a given project name.
        """
        allowed_resources = ['projects', 'workflows']
        if resource not in allowed_resources:
            raise ValueError('Your specified resource is not supported. ' +
                             f'Use one of the following: {allowed_resources}')
        if resource == 'workflows':
            content = self.get_workflow_list(workspace_id, verify=verify)
            for element in content:
                if (element["name"] == name and element["workflowType"] == "docker" and
                        not element["archived"]["status"]):
                    return element["_id"]  # no mainfile or importsfile
                if (element["name"] == name and
                        element["repository"]["platform"] == repository_platform and
                        not element["archived"]["status"]):
                    if mainfile is None:
                        return element["_id"]
                    elif element["mainFile"] == mainfile:
                        if importsfile is None and "importsFile" not in element.keys():
                            return element["_id"]
                        elif "importsFile" in element.keys() and element["importsFile"] == importsfile:
                            return element["_id"]
        elif resource == 'projects':
            content = self.get_project_list(workspace_id, verify=verify)
            # New API projects endpoint spec
            for element in content:
                if element["name"] == name:
                    return element["_id"]
        if mainfile is not None:
            raise ValueError(f'[ERROR] A workflow named \'{name}\' with a mainFile \'{mainfile}\'' +
                             f' and an importsFile \'{importsfile}\' was not found')
        else:
            raise ValueError(f'[ERROR] No {name} element in {resource} was found')
       
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
        #requires cloudos_url, project_id and workspace_id
        # url is: CLOUD_OS_URL/api/v2/datasets?projectId=PROJECT_ID&teamId=WORKSPACE_ID
        # Prepare api request for CloudOS to run a job
        headers = {
            "Content-type": "application/json",
            "apikey": self.apikey
        }
        r = retry_requests_get("{}/api/v2/datasets?projectId={}&teamId={}".format(self.cloudos_url,
                                                                  self.project_id,
                                                                  self.workspace_id),
                                headers=headers, verify=self.verify)
        return r.json()

    def list_datasets_content(self, folder_name):
    # requires cloudos_url, dataset_id, workspace_id
    # url is: CLOUD_OS_URL/api/v1/datasets/DATASET_ID/items?teamId=WORKSPACE_ID
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

        for folder in pro_fol.get("datasets", []):
            if folder['name'] == folder_name:
                folder_id = folder['_id']
        if not folder_id:
            raise ValueError(f"Folder '{folder_name}' not found in project '{self.project_name}'.")
        
        r = retry_requests_get("{}/api/v1/datasets/{}/items?teamId={}".format(self.cloudos_url,
                                                                  folder_id,
                                                                  self.workspace_id),
                                headers=headers, verify=self.verify)
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
        #requires cloudos_url, bucket_name, relative_path, workspace_id
        # url is: CLOUD_OS_URL/api/v1/data-access/s3/bucket-contents?bucket=BUCKET_NAME&path=RELATIVE_PATH_IN_THE_BUCKET&teamId=WORKSPACE_ID
        # Prepare api request for CloudOS to fetch dataset info
        headers = {
            "Content-type": "application/json",
            "apikey": self.apikey
        }
        # s3_bucket_name = None
        # s3_relative_path = None

        # folder_name = path.split('/')[0]
        # job_name = path.split('/')[1]

        # folder_content = self.list_datasets_content(folder_name)
        # ## folder_content is a dictionary of 3 keys files, folders and paginationMetadata
        # ## we expect that the path is referring to a folder not to a file
        # for job_folder in folder_content['folders']:
        #     if job_folder['name'] == job_name:
        #         s3_bucket_name=job_folder['s3BucketName']
        #         s3_relative_path=job_folder['s3Prefix']
        #         break

        # if not s3_bucket_name or not s3_relative_path:
        #     raise ValueError(f"No matching job folder '{job_name}' found in dataset '{folder_name}'")
        
        r = retry_requests_get("{}/api/v1/data-access/s3/bucket-contents?bucket={}&path={}&teamId={}".format(self.cloudos_url,
                                                                  s3_bucket_name,
                                                                  s3_relative_path,
                                                                  self.workspace_id),
                                headers=headers, verify=self.verify)
        return r.json()

    def list_virtual_folder_content(self,folder_id):
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
        #requires cloudos_url, folder_id, workspace_id
        # url is: CLOUD_OS_URL/api/v1/folders/virtual/FOLDER_ID/items?teamId=WORKSPACE_ID
        # Prepare api request for CloudOS to fetch dataset info
        headers = {
            "Content-type": "application/json",
            "apikey": self.apikey
        }

        r = retry_requests_get("{}/api/v1/folders/virtual/{}/items?teamId={}".format(self.cloudos_url,
                                                                  folder_id,
                                                                  self.workspace_id),
                                headers=headers, verify=self.verify)
        return r.json()
    
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

                    else:
                        raise ValueError(f"Unsupported folder type '{folder_type}' for path '{path}'")

            if not found:
                raise ValueError(f"Folder '{job_name}' not found under dataset '{dataset_name}'")

        return folder_content
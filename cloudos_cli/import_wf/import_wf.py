from abc import ABC, abstractmethod
from urllib.parse import urlsplit
from cloudos_cli.utils.errors import BadRequestException, AccountNotLinkedException
from cloudos_cli.utils.requests import retry_requests_post, retry_requests_get
import json
from requests.exceptions import RetryError
import sys


class WFImport(ABC):
    def __init__(self, cloudos_url, cloudos_apikey, workspace_id, platform,
                 workflow_name, workflow_url, workflow_docs_link="", workflow_description="", cost_limit=30, main_file=None, verify=True):
        self.cloudos_url = cloudos_url
        self.workflow_url = workflow_url.rstrip('.git')
        self.workspace_id = workspace_id
        self.platform = platform
        self.parsed_url = urlsplit(self.workflow_url)
        self.main_file = main_file
        self.repo_name = ""
        self.repo_owner = ""
        self.repo_host = f"{self.parsed_url.scheme}://{self.parsed_url.netloc}"
        self.headers = {
            "Content-Type": "application/json",
            "apikey": cloudos_apikey
        }
        self.payload = {
            "workflowType": "nextflow",
            "repository": {
                "platform": platform,
                "repositoryId": None,
                "name": None,
                "owner": {
                    "login": None,
                    "id": None
                },
                "isPrivate": True,
                "url": self.workflow_url,
                "commit": "",
                "branch": ""
            },
            "name": workflow_name,
            "description": workflow_description,
            "isPublic": False,
            "mainFile": "main.nf",
            "defaultContainer": None,
            "processes": [],
            "docsLink": workflow_docs_link,
            "team": workspace_id,
            "executionConfiguration": {
                "costLimitsInUsd": {"value": cost_limit, "editable": True}
            }
        }
        self.get_repo_url = ""
        self.get_repo_params = dict()
        self.get_repo_main_file_url = ""
        self.get_repo_main_file_params = ""
        self.post_request_url = f"{cloudos_url}/api/v2/workflows?teamId={workspace_id}"
        self.verify = verify

    def get_repo_main_file(self):
        repo_owner_urlencode = self.repo_owner.replace("/", "%2F")
        get_repo_main_file_url = f"{self.cloudos_url}/api/v1/git/{self.platform}/getWorkflowConfig/{self.repo_name}/{repo_owner_urlencode}"
        get_repo_main_file_params = dict(host=self.repo_host, teamId=self.workspace_id)
        r = retry_requests_get(get_repo_main_file_url, params=get_repo_main_file_params, headers=self.headers)
        if r.status_code >= 400:
            raise BadRequestException(r)
        r_data = r.json()
        return r_data["mainFile"]

    @abstractmethod
    def get_repo(self, *args, **kwargs):
        pass

    def check_payload(self):
        for required_key in ["repositoryId", "name", ("owner", "login"), ("owner", "id")]:
            if isinstance(required_key, tuple):
                key1, key2 = required_key
                value = self.payload["repository"][key1][key2]
                str_value = f"self.payload['repository']['{key1}']['{key2}']"
            else:
                value = self.payload["repository"][required_key]
                str_value = f"self.payload['repository']['{required_key}']"
            if value is None:
                raise ValueError("The payload dictionary does not have the required data. " +
                                 f"Check that {str_value} is present and the method "
                                 f"self.get_repo() has been executed")

    def import_workflow(self):
        self.get_repo()
        self.check_payload()
        r = retry_requests_post(self.post_request_url, json=self.payload, headers=self.headers, verify=self.verify)
        if r.status_code == 401:
            raise ValueError('It seems your API key is not authorised. Please check if ' +
                             'your workspace has support for importing workflows using cloudos-cli')
        elif r.status_code >= 400:
            raise BadRequestException(r)
        content = json.loads(r.content)
        return content["_id"]


class ImportWorflow(WFImport):
    def get_repo(self):
        get_repo_url = f"{self.cloudos_url}/api/v1/git/{self.platform}/getPublicRepo"
        if self.platform == "bitbucketServer":
            # platform allows to add paths like /browse, so we need to check if the path ends with it
            if self.parsed_url.path.endswith("browse"):
                self.repo_name = self.parsed_url.path.split("/")[-2]
            else:
                self.repo_name = self.parsed_url.path.split("/")[-1]
            self.repo_owner = self.parsed_url.path.split("/")[2]
        else:
            self.repo_name = self.parsed_url.path.split("/")[-1]
            self.repo_owner = "/".join(self.parsed_url.path.split("/")[1:-1])
        self.repo_host = f"{self.parsed_url.scheme}://{self.parsed_url.netloc}"
        get_repo_params = dict(repoName=self.repo_name, repoOwner=self.repo_owner, host=self.repo_host, teamId=self.workspace_id)
        try:
            r = retry_requests_get(get_repo_url, params=get_repo_params, headers=self.headers)
        except RetryError as e:
            # RetryError getting from missing BitBucket Server credentials
            raise AccountNotLinkedException(self.workflow_url)

        # for Github and Gitlab the API gives very general errors on missing credentials
        # therefore we only have these at the moment
        if r.status_code == 404:
            raise AccountNotLinkedException(self.workflow_url)
        elif r.status_code >= 400:
            raise BadRequestException(r)

        r_data = r.json()
        if self.platform == "bitbucketServer":
            self.payload["repository"]["repositoryId"] = r_data["name"]
        else:
            self.payload["repository"]["repositoryId"] = r_data["id"]
        self.payload["repository"]["name"] = r_data["name"]
        owner_data = {
            "bitbucketServer": ("project", "id", "key"),
            "gitlab": ("namespace", "id", "full_path"),
            "github": ("owner", "id", "login")
        }
        key, id_field, login_field = owner_data[self.platform]
        self.payload["repository"]["owner"]["id"] = r_data[key][id_field]
        self.payload["repository"]["owner"]["login"] = r_data[key][login_field]
        self.payload["mainFile"] = self.main_file or self.get_repo_main_file()

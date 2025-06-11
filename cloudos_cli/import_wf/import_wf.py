from abc import ABC, abstractmethod
from urllib.parse import urlsplit
from cloudos_cli.utils.errors import BadRequestException, AccountNotLinkedException
from cloudos_cli.utils.requests import retry_requests_post, retry_requests_get
import json


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


# There are some duplicated lines here and on the github subclass. I did not put them in the abstract class because we
# still don't know if the bitbucket data will come the same. If it does, then I will put as much as possible as part
# of the abstract class
class ImportGitlab(WFImport):
    def get_repo(self):
        get_repo_url = f"{self.cloudos_url}/api/v1/git/gitlab/getPublicRepo"
        self.repo_name = self.parsed_url.path.split("/")[-1]
        self.repo_owner = "/".join(self.parsed_url.path.split("/")[1:-1])
        self.repo_host = f"{self.parsed_url.scheme}://{self.parsed_url.netloc}"
        get_repo_params = dict(repoName=self.repo_name, repoOwner=self.repo_owner, host=self.repo_host, teamId=self.workspace_id)
        r = retry_requests_get(get_repo_url, params=get_repo_params, headers=self.headers)
        if r.status_code == 404:
            raise AccountNotLinkedException(self.workflow_url)
        elif r.status_code >= 400:
            raise BadRequestException(r)
        r_data = r.json()
        self.payload["repository"]["repositoryId"] = r_data["id"]
        self.payload["repository"]["name"] = r_data["name"]
        self.payload["repository"]["owner"]["id"] = r_data["namespace"]["id"]
        self.payload["repository"]["owner"]["login"] = r_data["namespace"]["full_path"]
        self.payload["mainFile"] = self.main_file or self.get_repo_main_file()


class ImportGithub(WFImport):
    def get_repo(self):
        get_repo_url = f"{self.cloudos_url}/api/v1/git/github/getPublicRepo"
        self.repo_name = self.parsed_url.path.split("/")[-1]
        self.repo_owner = "/".join(self.parsed_url.path.split("/")[1:-1])
        self.repo_host = f"{self.parsed_url.scheme}://{self.parsed_url.netloc}"
        get_repo_params = dict(repoName=self.repo_name, repoOwner=self.repo_owner, host=self.repo_host, teamId=self.workspace_id)
        r = retry_requests_get(get_repo_url, params=get_repo_params, headers=self.headers)
        if r.status_code == 404:
            raise AccountNotLinkedException(self.workflow_url)
        elif r.status_code >= 400:
            raise BadRequestException(r)
        r_data = r.json()
        self.payload["repository"]["repositoryId"] = r_data["id"]
        self.payload["repository"]["name"] = r_data["name"]
        self.payload["repository"]["owner"]["id"] = r_data["owner"]["id"]
        self.payload["repository"]["owner"]["login"] = r_data["owner"]["login"]
        self.payload["mainFile"] = self.main_file or self.get_repo_main_file()


class ImportBitbucketServer(WFImport):
    def get_repo(self):
        get_repo_url = f"{self.cloudos_url}/api/v1/git/bitbucketServer/getPublicRepo"
        if self.parsed_url.path.endswith("browse"):
            self.repo_name = self.parsed_url.path.split("/")[-2]
        else:
            self.repo_name = self.parsed_url.path.split("/")[-1]
        self.repo_owner = self.parsed_url.path.split("/")[2]
        self.repo_host = f"{self.parsed_url.scheme}://{self.parsed_url.netloc}"
        get_repo_params = dict(repoName=self.repo_name, repoOwner=self.repo_owner, host=self.repo_host, teamId=self.workspace_id)
        r = retry_requests_get(get_repo_url, params=get_repo_params, headers=self.headers)
        if r.status_code == 404:
            raise AccountNotLinkedException(self.workflow_url)
        elif r.status_code >= 400:
            raise BadRequestException(r)
        r_data = r.json()
        self.payload["repository"]["repositoryId"] = r_data["id"]
        self.payload["repository"]["name"] = r_data["name"]
        self.payload["repository"]["owner"]["id"] = r_data["project"]["id"]
        self.payload["repository"]["owner"]["login"] = r_data["project"]["key"]
        self.payload["mainFile"] = self.main_file or self.get_repo_main_file()

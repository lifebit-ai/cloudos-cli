from cloudos_cli.utils.requests import retry_requests_get
from cloudos_cli.utils import BadRequestException
from cloudos_cli.utils.errors import NoCloudForWorkspaceException


def find_cloud(cloudos_url, apikey, workspace_id):
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "apikey": apikey
    }
    params = dict(teamId=workspace_id)
    clouds = ("aws", "azure")
    for cloud in clouds:
        url = f"{cloudos_url}/api/v1/cloud/{cloud}"
        r = retry_requests_get(url, headers=headers, params=params)
        if r.status_code >= 400:
            raise BadRequestException(r)
        if r.json() and r.text != "null":
            cloud_data =  r.json()
            return cloud, cloud_data
    raise NoCloudForWorkspaceException(workspace_id)
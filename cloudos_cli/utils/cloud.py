from cloudos_cli.utils.requests import retry_requests_get
from cloudos_cli.utils import BadRequestException
from cloudos_cli.utils.errors import NoCloudForWorkspaceException


def find_cloud(cloudos_url, apikey, workspace_id, logs):
    if "s3BucketName" in logs:
        cloud_name = "aws"
        meta = {}
        storage = {
                "container": "s3BucketName",
                "prefix": "s3Prefix",
                "scheme": "s3"
            }
        return cloud_name, meta, storage
    else:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "apikey": apikey
        }
        params = dict(teamId=workspace_id)
        url = f"{cloudos_url}/api/v1/cloud/azure"
        r = retry_requests_get(url, headers=headers, params=params)
        if r.status_code >= 400:
            raise BadRequestException(r)
        if r.json() and r.text != "null":
            cloud_data = r.json()
            cloud_name = "azure"
            storage = {
                "container": "blobContainerName",
                "prefix": "blobPrefix",
                "scheme": "az"
            }
            return cloud_name, cloud_data, storage

    raise NoCloudForWorkspaceException(workspace_id)

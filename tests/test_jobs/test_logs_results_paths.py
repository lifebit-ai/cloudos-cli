import json

import responses
from responses import matchers
from cloudos_cli.clos import Cloudos
from pytest import raises
from cloudos_cli.utils.errors import JoBNotCompletedException, NoCloudForWorkspaceException
from cloudos_cli.utils.cloud import find_cloud
import pytest

CLOUD_OS_URL = "https://cloudos.lifebit.ai"
API_KEY = "secretkey"
BUCKET = "bucketname"
OBJ_PREFIX = "path/to"
WS_ID = "workspace123"
JOB = "jobid123"
PAYLOAD = {
    "contents": [
        {
            "name": x,
            "path": f"{OBJ_PREFIX}/{x}",
            "isDir": False,
            "lastModified": "2025-05-30T09:43:39.000Z",
            "size": 100
        }
        for x in ("stdout.txt", ".nextflow.log", "trace.txt")
    ]
}
PAYLOAD_RESULTS = {
    "contents": [
        {
            "name": "results",
            "path": f"{OBJ_PREFIX}/results",
            "isDir": True,
            "lastModified": "2025-05-30T09:43:39.000Z",
            "size": 100
        }
    ]
}
HEADER = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "apikey": API_KEY
}
DETAILS = {
    "logs": {
        "s3BucketName": BUCKET,
        "s3Prefix": OBJ_PREFIX
    },
    "results": {
        "s3BucketName": BUCKET,
        "s3Bucket": BUCKET,
        "s3Prefix": f"{OBJ_PREFIX}/results"
    },
    "status": "completed",
    "team": WS_ID
}

FIND_CLOUD_PAYLOAD = {
    "aws": {
        "storage": {}
    },
    "azure": {
        "storage": {"storageAccount": "someaccountname"}
    }
}


@pytest.mark.parametrize("cloud_provider,response_data", [
    ("aws", FIND_CLOUD_PAYLOAD["aws"]),
    ("azure", FIND_CLOUD_PAYLOAD["azure"])
])
@responses.activate
def test_cloud_providers(cloud_provider, response_data):
    for provider in ["aws", "azure"]:
        responses.add(
            responses.GET,
            url=f"{CLOUD_OS_URL}/api/v1/cloud/{provider}",
            match=[
                matchers.query_param_matcher(dict(teamId=WS_ID)),
                matchers.header_matcher(HEADER)
            ],
            json=response_data if provider == cloud_provider else {}
        )

    cloud_name, cloud_meta = find_cloud(CLOUD_OS_URL, API_KEY, WS_ID)
    assert cloud_name == cloud_provider


@responses.activate
def test_cloud_no_provider():
    """Test when no cloud provider is configured"""
    # Setup responses for all providers returning None
    for provider in ["aws", "azure"]:
        responses.add(
            responses.GET,
            url=f"{CLOUD_OS_URL}/api/v1/cloud/{provider}",
            match=[
                matchers.query_param_matcher(dict(teamId=WS_ID)),
                matchers.header_matcher(HEADER)
            ],
            json={}
        )

    with pytest.raises(NoCloudForWorkspaceException):
        find_cloud(CLOUD_OS_URL, API_KEY, WS_ID)


@responses.activate
def  test_bucket_contents():
    params = dict(bucket=BUCKET, path=OBJ_PREFIX, teamId=WS_ID)
    responses.add(
        responses.GET,
        url=f"{CLOUD_OS_URL}/api/v1/data-access/s3/bucket-contents",
        match=[matchers.query_param_matcher(params)],
        json=PAYLOAD
    )
    clos = Cloudos(CLOUD_OS_URL, "", None)
    file_paths = clos.get_storage_contents("aws", {}, BUCKET, OBJ_PREFIX, WS_ID, True)
    sample_file = file_paths[0]
    assert sample_file["name"] == "stdout.txt"
    assert sample_file["path"] == "path/to/stdout.txt"
    assert sample_file["isDir"] == False
    assert sample_file["lastModified"] == "2025-05-30T09:43:39.000Z"
    assert sample_file["size"] == 100


@responses.activate
def test_job_logs():
    params = dict(bucket=BUCKET, path=OBJ_PREFIX, teamId=WS_ID)
    responses.add(
        responses.GET,
        url=f"{CLOUD_OS_URL}/api/v1/data-access/s3/bucket-contents",
        match=[matchers.query_param_matcher(params)],
        json=PAYLOAD
    )
    responses.add(
        responses.GET,
        url=f"{CLOUD_OS_URL}/api/v1/jobs/{JOB}",
        json=DETAILS
    )
    for provider in ["aws", "azure"]:
        responses.add(
            responses.GET,
            url=f"{CLOUD_OS_URL}/api/v1/cloud/{provider}",
            match=[
                matchers.query_param_matcher(dict(teamId=WS_ID)),
            ],
            json=dict(storage=1) if provider == "aws" else {}
        )

    clos = Cloudos(CLOUD_OS_URL, "", None)
    logs = clos.get_job_logs(JOB, WS_ID)
    assert logs.get("Nextflow standard output") == f"s3://{BUCKET}/path/to/stdout.txt"
    assert logs.get("Nextflow log") == f"s3://{BUCKET}/path/to/.nextflow.log"
    assert logs.get("Trace file") == f"s3://{BUCKET}/path/to/trace.txt"


@responses.activate
def test_job_results():
    params = dict(bucket=BUCKET, path=f"{OBJ_PREFIX}/results", teamId=WS_ID)
    responses.add(
        responses.GET,
        url=f"{CLOUD_OS_URL}/api/v1/data-access/s3/bucket-contents",
        match=[matchers.query_param_matcher(params)],
        json=PAYLOAD_RESULTS
    )
    responses.add(
        responses.GET,
        url=f"{CLOUD_OS_URL}/api/v1/jobs/{JOB}",
        json=DETAILS
    )
    for provider in ["aws", "azure"]:
        responses.add(
            responses.GET,
            url=f"{CLOUD_OS_URL}/api/v1/cloud/{provider}",
            match=[
                matchers.query_param_matcher(dict(teamId=WS_ID)),
            ],
            json=dict(notNone=1) if provider == "aws" else {}
        )
    clos = Cloudos(CLOUD_OS_URL, "", None)
    results = clos.get_job_results(JOB, WS_ID, True)
    assert results["results"] == 's3://bucketname/path/to/results'


@responses.activate
def test_job_results_not_completed():
    params = dict(bucket=BUCKET, path=f"{OBJ_PREFIX}/results", teamId=WS_ID)
    responses.add(
        responses.GET,
        url=f"{CLOUD_OS_URL}/api/v1/data-access/s3/bucket-contents",
        match=[matchers.query_param_matcher(params)],
        json=PAYLOAD_RESULTS
    )
    not_completed_details = DETAILS
    not_completed_details["status"] = "running"
    responses.add(
        responses.GET,
        url=f"{CLOUD_OS_URL}/api/v1/jobs/{JOB}",
        json=not_completed_details
    )
    for provider in ["aws", "azure"]:
        responses.add(
            responses.GET,
            url=f"{CLOUD_OS_URL}/api/v1/cloud/{provider}",
            match=[
                matchers.query_param_matcher(dict(teamId=WS_ID)),
            ],
            json=dict(notNone=1) if provider == "aws" else {}
        )
    clos = Cloudos(CLOUD_OS_URL, "", None)
    with raises(JoBNotCompletedException) as exception_info:
        clos.get_job_results(JOB, WS_ID, True)
        assert str(
            exception_info) == f"Job {JOB} has status running. Results are only available for jobs with status \"completed\""

import json
import responses
from cloudos_cli.datasets import Datasets
from tests.functions_for_pytest import load_json_file
from responses import matchers
from pathlib import Path
import base64
from cloudos_cli.utils.requests import retry_requests_get


# Constants
APIKEY = 'vnoiweur89u2ongs'
CLOUDOS_URL = 'http://cloudos.lifebit.ai'
WORKSPACE_ID = 'lv89ufc838sdig'
PROJECT_NAME = "lifebit-testing"
DATASET_NAME = 'Data'
DATAPATH = "/Data/sampleArray.csv"

# Files
INPUT_PROJECTS = "tests/test_data/projects.json"
INPUT_DATASETS = "tests/test_data/datasets.json"
INPUT_DATASET_CONTENT = "tests/test_data/bash_array_job_files.json"
COLUMNS_CONTENT = {
    "headers": [
        {"index": 0, "name": "id"},
        {"index": 1, "name": "title"},
        {"index": 2, "name": "filename"},
        {"index": 3, "name": "file2name"},
    ]
}
EXPECTED_COLUMNS = (
    "Columns:\n"
    "\t- id\n"
    "\t- title\n"
    "\t- filename\n"
    "\t- file2name"
)


@responses.activate
def test_get_array_file_columns():
    # Load mocked data
    mock_projects = json.loads(load_json_file(INPUT_PROJECTS))
    mock_datasets = json.loads(load_json_file(INPUT_DATASETS))
    mock_dataset_contents = json.loads(load_json_file(INPUT_DATASET_CONTENT))
    mock_columns_contents = json.loads(json.dumps(COLUMNS_CONTENT))

    # Extract IDs
    project_id = next((p["_id"] for p in mock_projects["projects"] if p["name"] == PROJECT_NAME), None)
    dataset_id2 = next((d["_id"] for d in mock_datasets["datasets"] if d["name"] == DATASET_NAME), None)

    # Matchers
    params_datasets = {"projectId": project_id, "teamId": WORKSPACE_ID}
    params_items = {"teamId": WORKSPACE_ID}

    p = Path(DATAPATH)
    directory = str(p.parent)
    file_name = p.name

    headers = {
        "Content-type": "application/json",
        "apikey": APIKEY
    }

    # Mock endpoints
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v2/datasets?projectId={project_id}&teamId={WORKSPACE_ID}",
        body=json.dumps(mock_datasets),
        match=[matchers.query_param_matcher(params_datasets)],
        status=200
    )

    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/datasets/{dataset_id2}/items?teamId={WORKSPACE_ID}",
        body=json.dumps(mock_dataset_contents),
        match=[matchers.query_param_matcher(params_items)],
        status=200
    )

    # Instantiate and call method
    datasets = Datasets(
        cloudos_url=CLOUDOS_URL,
        apikey=APIKEY,
        workspace_id=WORKSPACE_ID,
        project_name=PROJECT_NAME,
        verify=True,
        project_id=project_id, # avoids a real call
        cromwell_token=None
    )

    result = datasets.list_folder_content(directory)

    # retrieve the S3 bucket name and object key for the specified file
    for file in result['files']:
        if file.get("name") == file_name:
            s3_bucket_name = file.get("s3BucketName")
            s3_object_key = file.get("s3ObjectKey")
            s3_object_key_b64 = base64.b64encode(s3_object_key.encode()).decode()
            break
    else:
        raise ValueError(f'File "{file_name}" not found in the "Data" folder of the project "{project_name}".')

    url = (
        f"{CLOUDOS_URL}/api/v1/jobs/array-file/metadata"
        f"?separator=,"
        f"&s3BucketName={s3_bucket_name}"
        f"&s3ObjectKey={s3_object_key_b64}"
        f"&teamId={WORKSPACE_ID}"
    )

    params_columns = {
        "s3BucketName": s3_bucket_name,
        "s3ObjectKey": s3_object_key_b64,
        "separator": ",",
        "teamId": WORKSPACE_ID
    }

    responses.add(
        responses.GET,
        url=url,
        body=json.dumps(mock_columns_contents),
        match=[matchers.query_param_matcher(params_columns)],
        status=200
    )
    r = retry_requests_get(url, headers=headers, verify=False)

    columns = json.loads(r.content).get("headers", None)

    cols = "Columns:"
    for col in columns:
        cols = cols + f"\n\t- {col['name']}"

    assert cols == EXPECTED_COLUMNS, f"Expected columns do not match: {cols} != {EXPECTED_COLUMNS}"

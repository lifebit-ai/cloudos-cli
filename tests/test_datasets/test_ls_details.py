import json
import responses
from cloudos_cli.datasets import Datasets
from tests.functions_for_pytest import load_json_file
from responses import matchers

# Constants
APIKEY = 'vnoiweur89u2ongs'
CLOUDOS_URL = 'http://cloudos.lifebit.ai'
WORKSPACE_ID = 'lv89ufc838sdig'
PROJECT_NAME = "lifebit-testing"
DATASET_NAME = 'Analyses Results'
FOLDER_PATH = 'AnalysesResults'

# Files
INPUT_PROJECTS = "tests/test_data/projects.json"
INPUT_DATASETS = "tests/test_data/datasets.json"
INPUT_DATASET_CONTENT = "tests/test_data/dataset_folder_results.json"


@responses.activate
def test_list_folder_content_for_s3_dataset():
    # Load mocked data
    mock_projects = json.loads(load_json_file(INPUT_PROJECTS))
    mock_datasets = json.loads(load_json_file(INPUT_DATASETS))
    mock_dataset_contents = json.loads(load_json_file(INPUT_DATASET_CONTENT))

    # Extract IDs
    project_id = next((p["_id"] for p in mock_projects["projects"] if p["name"] == PROJECT_NAME), None)
    dataset_id = next((d["_id"] for d in mock_datasets["datasets"] if d["name"] == DATASET_NAME), None)

    # Matchers
    params_projects = {"teamId": WORKSPACE_ID}
    params_datasets = {"projectId": project_id, "teamId": WORKSPACE_ID}
    params_items = {"teamId": WORKSPACE_ID}

    # Mock endpoints
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v2/projects?teamId={WORKSPACE_ID}",
        body=json.dumps(mock_projects),
        match=[matchers.query_param_matcher(params_projects)],
        status=200
    )

    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v2/datasets?projectId={project_id}&teamId={WORKSPACE_ID}",
        body=json.dumps(mock_datasets),
        match=[matchers.query_param_matcher(params_datasets)],
        status=200
    )

    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/datasets/{dataset_id}/items?teamId={WORKSPACE_ID}",
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
        project_id=project_id,  # avoids a real call
        cromwell_token=None
    )

    result = datasets.list_folder_content(FOLDER_PATH)

    # Assertions
    contents = result.get("contents", [])
    assert any(item["name"] == "flowchart.png" for item in contents)
    assert any(item["name"] == "results" for item in contents)
    assert any(item["size"] == 7576365 for item in contents)
    assert any(item["path"] == "..." for item in contents)

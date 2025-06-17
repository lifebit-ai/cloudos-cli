import json
import responses
from cloudos_cli.datasets import Datasets
from tests.functions_for_pytest import load_json_file
from responses import matchers

APIKEY = 'vnoiweur89u2ongs'
CLOUDOS_URL = 'http://cloudos.lifebit.ai'
WORKSPACE_ID = 'lv89ufc838sdig'
PROJECT_NAME = "lifebit-testing"
FOLDER_PATH = 'Data'

INPUT_PROJECTS = "tests/test_data/projects.json"
INPUT_DATASETS = "tests/test_data/datasets.json"
INPUT_DATASET_CONTENT = "tests/test_data/dataset_folder_results.json"

@responses.activate
def test_rename_folder():
    mock_projects = json.loads(load_json_file(INPUT_PROJECTS))
    mock_datasets = json.loads(load_json_file(INPUT_DATASETS))
    mock_dataset_contents = json.loads(load_json_file(INPUT_DATASET_CONTENT))

    project_id = mock_projects["projects"][0]["_id"]
    dataset_id = mock_datasets["datasets"][0]["_id"]
    folder_id = mock_dataset_contents["folders"][0]["_id"]

    params_projects = {"teamId": WORKSPACE_ID}
    params_datasets = {"projectId": project_id, "teamId": WORKSPACE_ID}
    params_items = {"teamId": WORKSPACE_ID}

    headers = {
        "Content-type": "application/json",
        "apikey": APIKEY
    }

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

    responses.add(
        responses.PUT,
        url=f"{CLOUDOS_URL}/api/v1/folders/{folder_id}?teamId={WORKSPACE_ID}",
        status=200,
        json={"name": "new_folder_name"}
    )

    datasets = Datasets(
        cloudos_url=CLOUDOS_URL,
        apikey=APIKEY,
        workspace_id=WORKSPACE_ID,
        project_name=PROJECT_NAME,
        verify=True,
        project_id=project_id,
        cromwell_token=None
    )

    content = datasets.list_folder_content(FOLDER_PATH)
    folder = next(f for f in content["folders"] if f["name"] == "my_folder")
    response = datasets.rename_item(folder["_id"], "new_folder_name", "Folder")

    assert response.status_code == 200

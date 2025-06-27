import json
import responses
from cloudos_cli.datasets import Datasets
from tests.functions_for_pytest import load_json_file
from responses import matchers

APIKEY = 'vnoiweur89u2ongs'
CLOUDOS_URL = 'http://cloudos.lifebit.ai'
WORKSPACE_ID = 'lv89ufc838sdig'
PROJECT_NAME = "lifebit-testing"
PARENT_PATH = "Data/my_folder"
NEW_FOLDER_NAME = "new_virtual_subfolder"

INPUT_PROJECTS = "tests/test_data/projects.json"
INPUT_DATASETS = "tests/test_data/datasets.json"
INPUT_PARENT_CONTENT = "tests/test_data/dataset_source_content.json"

@responses.activate
def test_create_virtual_folder():
    mock_projects = json.loads(load_json_file(INPUT_PROJECTS))
    mock_datasets = json.loads(load_json_file(INPUT_DATASETS))
    mock_parent_content = json.loads(load_json_file(INPUT_PARENT_CONTENT))

    project_id = mock_projects["projects"][0]["_id"]
    dataset_id = next(d["_id"] for d in mock_datasets["datasets"] if d["name"] == "Data")
    parent_folder = next(f for f in mock_parent_content["folders"] if f["name"] == "my_folder")
    parent_folder_id = parent_folder["_id"]

    # Mock project fetch
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v2/projects?teamId={WORKSPACE_ID}",
        body=json.dumps(mock_projects),
        match=[matchers.query_param_matcher({"teamId": WORKSPACE_ID})],
        status=200
    )

    # Mock dataset list
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v2/datasets?projectId={project_id}&teamId={WORKSPACE_ID}",
        body=json.dumps(mock_datasets),
        match=[matchers.query_param_matcher({"projectId": project_id, "teamId": WORKSPACE_ID})],
        status=200
    )

    # Mock listing of parent folder
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/datasets/{dataset_id}/items?teamId={WORKSPACE_ID}",
        body=json.dumps(mock_parent_content),
        match=[matchers.query_param_matcher({"teamId": WORKSPACE_ID})],
        status=200
    )

    # Mock POST call to create the new virtual folder
    responses.add(
        responses.POST,
        url=f"{CLOUDOS_URL}/api/v1/folders/virtual?teamId={WORKSPACE_ID}",
        json={"name": NEW_FOLDER_NAME, "parent": {"id": parent_folder_id, "kind": "Folder"}},
        status=201
    )

    dataset = Datasets(
        cloudos_url=CLOUDOS_URL,
        apikey=APIKEY,
        workspace_id=WORKSPACE_ID,
        project_name=PROJECT_NAME,
        verify=True,
        project_id=project_id,
        cromwell_token=None
    )

    response = dataset.create_virtual_folder(
        name=NEW_FOLDER_NAME,
        parent_id=parent_folder_id,
        parent_kind="Folder"
    )

    assert response.status_code == 201
    assert response.json()["name"] == NEW_FOLDER_NAME
    assert response.json()["parent"]["id"] == parent_folder_id
    assert response.json()["parent"]["kind"] == "Folder"
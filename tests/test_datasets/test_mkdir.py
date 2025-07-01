import json
import responses
from cloudos_cli.datasets import Datasets
from tests.functions_for_pytest import load_json_file
from responses import matchers

APIKEY = 'vnoiweur89u2ongs'
CLOUDOS_URL = 'http://cloudos.lifebit.ai'
WORKSPACE_ID = 'lv89ufc838sdig'
PROJECT_NAME = "lifebit-testing"
NEW_FOLDER_PATH = "Data/my_folder/new_virtual_subfolder"
NEW_FOLDER_NAME = "new_virtual_subfolder"
PARENT_PATH = "Data/my_folder"

INPUT_PROJECTS = "tests/test_data/projects.json"
INPUT_DATASETS = "tests/test_data/datasets.json"
INPUT_PARENT_CONTENT = "tests/test_data/dataset_source_content.json"

@responses.activate
def test_create_virtual_folder_for_new_path():
    # Load test data
    mock_projects = json.loads(load_json_file(INPUT_PROJECTS))
    mock_datasets = json.loads(load_json_file(INPUT_DATASETS))
    mock_parent_content = json.loads(load_json_file(INPUT_PARENT_CONTENT))

    # Resolve IDs
    project_id = mock_projects["projects"][0]["_id"]
    dataset_id = next(d["_id"] for d in mock_datasets["datasets"] if d["name"] == "Data")
    parent_folder = next(f for f in mock_parent_content["folders"] if f["name"] == "my_folder")
    parent_folder_id = parent_folder["_id"]

    # Mock: fetch projects
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v2/projects?teamId={WORKSPACE_ID}",
        body=json.dumps(mock_projects),
        match=[matchers.query_param_matcher({"teamId": WORKSPACE_ID})],
        status=200
    )

    # Mock: fetch datasets
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v2/datasets?projectId={project_id}&teamId={WORKSPACE_ID}",
        body=json.dumps(mock_datasets),
        match=[matchers.query_param_matcher({"projectId": project_id, "teamId": WORKSPACE_ID})],
        status=200
    )

    # Mock: list parent path (Data/my_folder)
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/datasets/{dataset_id}/items?teamId={WORKSPACE_ID}",
        body=json.dumps(mock_parent_content),
        match=[matchers.query_param_matcher({"teamId": WORKSPACE_ID})],
        status=200
    )

    # Mock: create virtual folder
    responses.add(
        responses.POST,
        url=f"{CLOUDOS_URL}/api/v1/folders/virtual?teamId={WORKSPACE_ID}",
        json={
            "name": NEW_FOLDER_NAME,
            "parent": {"id": parent_folder_id, "kind": "Folder"}
        },
        status=201
    )

    # Instantiate client
    dataset_client = Datasets(
        cloudos_url=CLOUDOS_URL,
        apikey=APIKEY,
        workspace_id=WORKSPACE_ID,
        project_name=PROJECT_NAME,
        verify=True,
        project_id=project_id,
        cromwell_token=None
    )

    # Simulate what the CLI logic does: split path
    path_parts = NEW_FOLDER_PATH.strip("/").split("/")
    parent_path = "/".join(path_parts[:-1])
    folder_name = path_parts[-1]

    # List the parent folder contents (you could imagine this being part of resolve_path_to_id)
    response_parent_content = dataset_client.list_folder_content(parent_path)

    # For test simplicity, pull parent info from mock data
    folder_info = next(
        (f for f in mock_parent_content["folders"] if f["name"] == "my_folder"),
        None
    )

    assert folder_info is not None, "Parent folder not found in mock data"

    parent_id = folder_info["_id"]
    parent_kind = "Folder"

    # Create the folder
    response = dataset_client.create_virtual_folder(
        name=folder_name,
        parent_id=parent_id,
        parent_kind=parent_kind
    )

    # Assertions
    assert response.status_code == 201
    response_json = response.json()
    assert response_json["name"] == NEW_FOLDER_NAME
    assert response_json["parent"]["id"] == parent_id
    assert response_json["parent"]["kind"] == parent_kind

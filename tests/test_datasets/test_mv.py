
import json
import responses
from cloudos_cli.datasets import Datasets
from responses import matchers
from tests.functions_for_pytest import load_json_file

APIKEY = 'vnoiweur89u2ongs'
CLOUDOS_URL = 'http://cloudos.lifebit.ai'
WORKSPACE_ID = 'lv89ufc838sdig'
PROJECT_NAME = "lifebit-testing"
SOURCE_PATH = "Data/flowchart.png"
DEST_PATH = "Data/results"
INPUT_PROJECTS = "tests/test_data/projects.json"
INPUT_DATASETS = "tests/test_data/datasets.json"
INPUT_SOURCE_CONTENT = "tests/test_data/dataset_source_content.json"
INPUT_DEST_CONTENT = "tests/test_data/dataset_destination_content.json"

@responses.activate
def test_move_file_to_folder():
    mock_projects = json.loads(load_json_file(INPUT_PROJECTS))
    mock_datasets = json.loads(load_json_file(INPUT_DATASETS))
    mock_source_contents = json.loads(load_json_file(INPUT_SOURCE_CONTENT))
    mock_dest_contents = json.loads(load_json_file(INPUT_DEST_CONTENT))

    project_id = mock_projects["projects"][0]["_id"]
    dataset_id = mock_datasets["datasets"][0]["_id"]
    file_id = mock_source_contents["files"][0]["_id"]
    folder_id = mock_dest_contents["folders"][0]["_id"]

    responses.add(
        responses.GET,
        f"{CLOUDOS_URL}/api/v2/projects?teamId={WORKSPACE_ID}",
        json=mock_projects,
        match=[matchers.query_param_matcher({"teamId": WORKSPACE_ID})],
        status=200
    )

    responses.add(
        responses.GET,
        f"{CLOUDOS_URL}/api/v2/datasets?projectId={project_id}&teamId={WORKSPACE_ID}",
        json=mock_datasets,
        match=[matchers.query_param_matcher({"projectId": project_id, "teamId": WORKSPACE_ID})],
        status=200
    )

    responses.add(
        responses.GET,
        f"{CLOUDOS_URL}/api/v1/datasets/{dataset_id}/items?teamId={WORKSPACE_ID}",
        json=mock_source_contents,
        match=[matchers.query_param_matcher({"teamId": WORKSPACE_ID})],
        status=200
    )

    responses.add(
        responses.GET,
        f"{CLOUDOS_URL}/api/v1/datasets/{dataset_id}/items?teamId={WORKSPACE_ID}",
        json=mock_dest_contents,
        match=[matchers.query_param_matcher({"teamId": WORKSPACE_ID})],
        status=200
    )

    responses.add(
        responses.PUT,
        f"{CLOUDOS_URL}/api/v1/dataItems/move?teamId={WORKSPACE_ID}",
        json={"success": True},
        status=200
    )

    dataset = Datasets(
        cloudos_url=CLOUDOS_URL,
        apikey=APIKEY,
        workspace_id=WORKSPACE_ID,
        project_name=PROJECT_NAME,
        verify=True,
        project_id=project_id
    )

    result = dataset.move_files_and_folders(
        source_id=file_id,
        source_kind="File",
        target_id=folder_id,
        target_kind="Folder"
    )

    assert result.status_code == 200

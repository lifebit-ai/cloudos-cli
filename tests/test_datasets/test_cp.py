import json
import responses
from responses import matchers
from cloudos_cli.datasets import Datasets
from tests.functions_for_pytest import load_json_file

APIKEY = 'vnoiweur89u2ongs'
CLOUDOS_URL = 'http://cloudos.lifebit.ai'
WORKSPACE_ID = 'lv89ufc838sdig'
PROJECT_NAME = "lifebit-testing"

INPUT_PROJECTS = "tests/test_data/projects.json"
INPUT_DATASETS = "tests/test_data/datasets.json"
INPUT_SOURCE_CONTENT = "tests/test_data/dataset_source_content.json"
INPUT_DEST_CONTENT = "tests/test_data/dataset_destination_content.json"

@responses.activate
def test_copy_file_to_folder():
    mock_projects = json.loads(load_json_file(INPUT_PROJECTS))
    mock_datasets = json.loads(load_json_file(INPUT_DATASETS))
    mock_source_contents = json.loads(load_json_file(INPUT_SOURCE_CONTENT))
    mock_dest_contents = json.loads(load_json_file(INPUT_DEST_CONTENT))

    project_id = mock_projects["projects"][0]["_id"]
    dataset_id = mock_datasets["datasets"][0]["_id"]
    file_item = mock_source_contents["files"][0]
    folder_item = mock_dest_contents["folders"][0]

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
        match=[matchers.query_param_matcher({
            "projectId": project_id,
            "teamId": WORKSPACE_ID
        })],
        status=200
    )

    responses.add(
        responses.GET,
        f"{CLOUDOS_URL}/api/v1/datasets/{dataset_id}/items?teamId={WORKSPACE_ID}",
        json=mock_source_contents,
        status=200
    )

    responses.add(
        responses.GET,
        f"{CLOUDOS_URL}/api/v1/datasets/{dataset_id}/items?teamId={WORKSPACE_ID}",
        json=mock_dest_contents,
        status=200
    )

    responses.add(
        responses.POST,
        f"{CLOUDOS_URL}/api/v1/files/s3?teamId={WORKSPACE_ID}",
        json={"success": True},
        status=200
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

    response = dataset.copy_item(
        item=file_item,
        destination_id=folder_item["_id"],
        destination_kind="Folder"
    )

    assert response.status_code == 200

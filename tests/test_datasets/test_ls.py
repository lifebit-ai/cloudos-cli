import json
import pytest
import responses
from unittest.mock import patch
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

    headers = {
        "Content-type": "application/json",
        "apikey": APIKEY
    }

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


REMOTE_NAME = "[link=https://evil.example]report[/link]\x1b[2J.bam"
REMOTE_KEY = "data/[red]x[/red]\x1b]8;;https://evil.example\x07.bam"


@pytest.mark.parametrize("details", [False, True])
def test_ls_prints_remote_names_as_plain_text(details):
    """Remote names and storage keys are printed literally, without markup or control characters"""
    from click.testing import CliRunner
    from cloudos_cli.datasets.cli import list_files

    contents = [
        {"name": REMOTE_NAME, "fileType": "S3File", "s3BucketName": "bucket", "s3ObjectKey": REMOTE_KEY,
         "user": {"name": "[bold]Eve[/bold]", "surname": "\x1b[31mX"}},
        {"name": "[/oops]", "folderType": "VirtualFolder"},
    ]
    args = ['-k', APIKEY, '-c', CLOUDOS_URL, '--workspace-id', WORKSPACE_ID, '--project-name', PROJECT_NAME]
    if details:
        args.append('--details')
    profile = {"apikey": APIKEY, "cloudos_url": CLOUDOS_URL, "workspace_id": WORKSPACE_ID,
               "project_name": PROJECT_NAME}
    with patch('cloudos_cli.configure.configure.ConfigurationProfile.load_profile_and_validate_data',
               return_value=profile), \
            patch('cloudos_cli.datasets.cli.Datasets') as mock_datasets:
        mock_datasets.return_value.list_folder_content.return_value = {"contents": contents}
        result = CliRunner().invoke(list_files, args, env={"COLUMNS": "400"})

    assert result.exit_code == 0, result.output
    assert "\x1b" not in result.output and "\x07" not in result.output
    assert "[link=https://evil.example]report[/link][2J.bam" in result.output
    assert "[/oops]" in result.output
    if details:
        assert "s3://bucket/data/[red]x[/red]]8;;https://evil.example.bam" in result.output
        assert "[bold]Eve[/bold] [31mX" in result.output

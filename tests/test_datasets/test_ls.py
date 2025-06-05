import os
import sys
import responses
import pytest
from click.testing import CliRunner
from responses import matchers
from cloudos_cli.__main__ import run_cloudos_cli
from tests.functions_for_pytest import load_json_file

# Constants and test data files
APIKEY = 'vnoiweur89u2ongs'
CLOUDOS_URL = 'http://cloudos.lifebit.ai'
WORKSPACE_ID = 'lv89ufc838sdig'
PROJECT_NAME = "lifebit-testing"
PROFILE_NAME = 'pytest-profile'
DATASET_NAME = 'Analyses Results'
FOLDER_PATH = 'AnalysesResults'
INPUT_PROJECTS = "tests/test_data/projects.json"
INPUT_DATASET_CONTENT = "tests/test_data/dataset_folder_results.json"

@pytest.fixture
def cli_runner():
    return CliRunner()

@responses.activate
def test_datasets_ls_s3_folder(cli_runner):
    """
    Test 'cloudos datasets ls' for an S3 folder path.
    """

    # Load mock JSON responses
    mock_projects = load_json_file(INPUT_PROJECTS)
    mock_dataset_contents = load_json_file(INPUT_DATASET_CONTENT)

    # Setup query param matchers
    params_projects = {"teamId": WORKSPACE_ID}
    params_dataset = {"teamId": WORKSPACE_ID}

    # Headers
    headers = {
        "Content-type": "application/json",
        "apikey": APIKEY
    }

    # Mock /projects endpoint
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v2/projects?teamId={WORKSPACE_ID}",
        body=mock_projects,
        headers=headers,
        match=[matchers.query_param_matcher(params_projects)],
        status=200
    )

    # Dataset ID extracted from mock_projects matching PROJECT_NAME
    project_id = next((p["_id"] for p in mock_projects["projects"] if p["name"] == PROJECT_NAME), None)
    dataset_id = next((d["_id"] for d in mock_projects["projects"][0]["datasets"] if d["name"] == DATASET_NAME), None)

    # Mock /datasets/<id>/items endpoint
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/datasets/{dataset_id}/items?teamId={WORKSPACE_ID}",
        body=mock_dataset_contents,
        headers=headers,
        match=[matchers.query_param_matcher(params_dataset)],
        status=200
    )

    # Create a fake config profile in memory
    os.environ["CLOUDOS_PROFILES"] = f"""
    {{
        "{PROFILE_NAME}": {{
            "apikey": "{APIKEY}",
            "cloudos_url": "{CLOUDOS_URL}",
            "workspace_id": "{WORKSPACE_ID}",
            "project_name": "{PROJECT_NAME}",
            "execution_platform": "aws",
            "repository_platform": "github"
        }}
    }}
    """

    # Run the CLI command
    result = cli_runner.invoke(run_cloudos_cli, [
        "datasets", "ls",
        "--profile", PROFILE_NAME,
        FOLDER_PATH
    ])

    assert result.exit_code == 0
    assert "flowchart.png" in result.output
    assert "results" in result.output
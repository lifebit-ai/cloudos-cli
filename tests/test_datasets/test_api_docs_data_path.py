"""Test to verify that project-id resolution is shown when using path Data"""
import json
import responses
from cloudos_cli.datasets import Datasets
from cloudos_cli.datasets.datasets import APICallTracker
from tests.functions_for_pytest import load_json_file

# Constants
APIKEY = 'vnoiweur89u2ongs'
CLOUDOS_URL = 'http://cloudos.lifebit.ai'
WORKSPACE_ID = 'lv89ufc838sdig'
PROJECT_NAME = "lifebit-testing"
DATASET_NAME = 'Data'

# Files
INPUT_PROJECTS = "tests/test_data/projects.json"
INPUT_DATASETS = "tests/test_data/datasets.json"
INPUT_DATASET_CONTENT = "tests/test_data/dataset_folder_results.json"


@responses.activate
def test_api_docs_shows_project_resolution_for_data_path():
    """Test that when listing 'Data' folder, project resolution is tracked."""
    # Load mocked data
    mock_projects = json.loads(load_json_file(INPUT_PROJECTS))
    mock_datasets = json.loads(load_json_file(INPUT_DATASETS))
    mock_dataset_contents = json.loads(load_json_file(INPUT_DATASET_CONTENT))

    # Extract IDs
    project_id = next((p["_id"] for p in mock_projects["projects"] if p["name"] == PROJECT_NAME), None)
    dataset_id = next((d["_id"] for d in mock_datasets["datasets"] if d["name"] == DATASET_NAME), "data_id_123")

    # Mock endpoints
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v2/projects?teamId={WORKSPACE_ID}&search={PROJECT_NAME}",
        body=json.dumps(mock_projects),
        status=200
    )

    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v2/datasets?projectId={project_id}&teamId={WORKSPACE_ID}",
        body=json.dumps(mock_datasets),
        status=200
    )

    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/datasets/{dataset_id}/items?teamId={WORKSPACE_ID}",
        body=json.dumps(mock_dataset_contents),
        status=200
    )

    # Create tracker
    tracker = APICallTracker(
        cloudos_url=CLOUDOS_URL,
        workspace_id=WORKSPACE_ID,
        verify=True
    )

    # Instantiate Datasets with tracker (don't pass project_id to trigger fetch)
    datasets = Datasets(
        cloudos_url=CLOUDOS_URL,
        apikey=APIKEY,
        workspace_id=WORKSPACE_ID,
        project_name=PROJECT_NAME,
        verify=True,
        cromwell_token=None,
        api_docs_tracker=tracker
    )

    # Execute the listing with "Data" path (the reported issue)
    datasets.list_folder_content(DATASET_NAME)

    # Generate documentation
    docs = tracker.get_documentation()

    # Assertions
    print("\n" + "="*80)
    print("Generated API Documentation:")
    print(docs)
    print("="*80 + "\n")

    # The key assertion: project resolution should be documented!
    assert "Resolve project name to project ID" in docs, \
        "Documentation should include project name resolution instructions"
    
    # Should have at least 3 calls: 1. Resolve project, 2. List datasets, 3. List folder items
    assert len(tracker.calls) >= 3, f"Expected at least 3 API calls, but got {len(tracker.calls)}"
    
    # Verify the first call is project resolution
    assert tracker.calls[0]['purpose'] == "Resolve project name to project ID", \
        "First API call should be project name resolution"
    
    # Verify jq extraction hint is present
    assert "jq" in docs, "Documentation should include jq command for extracting project ID"
    assert f'select(.name=="{PROJECT_NAME}")' in docs, \
        "Documentation should show how to filter by project name"


if __name__ == "__main__":
    test_api_docs_shows_project_resolution_for_data_path()
    print("\n✓ Test passed! Project resolution is now shown when using --api-docs with path 'Data'")

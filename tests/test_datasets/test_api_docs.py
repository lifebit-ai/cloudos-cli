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
DATASET_NAME = 'Analyses Results'
FOLDER_PATH = 'AnalysesResults'

# Files
INPUT_PROJECTS = "tests/test_data/projects.json"
INPUT_DATASETS = "tests/test_data/datasets.json"
INPUT_DATASET_CONTENT = "tests/test_data/dataset_folder_results.json"


@responses.activate
def test_api_call_tracker_captures_calls():
    """Test that APICallTracker captures API calls made during dataset listing."""
    # Load mocked data
    mock_projects = json.loads(load_json_file(INPUT_PROJECTS))
    mock_datasets = json.loads(load_json_file(INPUT_DATASETS))
    mock_dataset_contents = json.loads(load_json_file(INPUT_DATASET_CONTENT))

    # Extract IDs
    project_id = next((p["_id"] for p in mock_projects["projects"] if p["name"] == PROJECT_NAME), None)
    dataset_id = next((d["_id"] for d in mock_datasets["datasets"] if d["name"] == DATASET_NAME), None)

    # Mock endpoints
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v2/projects",
        body=json.dumps(mock_projects),
        status=200
    )

    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v2/datasets",
        body=json.dumps(mock_datasets),
        status=200
    )

    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/datasets/{dataset_id}/items",
        body=json.dumps(mock_dataset_contents),
        status=200
    )

    # Create tracker
    tracker = APICallTracker(
        cloudos_url=CLOUDOS_URL,
        workspace_id=WORKSPACE_ID,
        verify=True
    )

    # Instantiate Datasets with tracker
    datasets = Datasets(
        cloudos_url=CLOUDOS_URL,
        apikey=APIKEY,
        workspace_id=WORKSPACE_ID,
        project_name=PROJECT_NAME,
        verify=True,
        cromwell_token=None,
        api_docs_tracker=tracker,
        project_id=project_id  # Pass project_id to avoid fetch call
    )

    # Execute the listing
    datasets.list_folder_content(FOLDER_PATH)

    # Assertions on tracker
    assert len(tracker.calls) > 0, "Tracker should have captured API calls"
    assert tracker.project_id == project_id, "Tracker should have stored project_id"
    assert tracker.project_name == PROJECT_NAME, "Tracker should have stored project_name"

    # Check that first call is for list datasets (not projects, since we passed project_id)
    first_call = tracker.calls[0]
    assert first_call['method'] == 'GET'
    assert 'datasets' in first_call['url']
    assert 'List all top-level datasets' in first_call['purpose']

    # Check that subsequent calls exist (should have dataset items call)
    assert len(tracker.calls) >= 2, "Should have at least 2 API calls (datasets + items)"


@responses.activate
def test_api_documentation_generation():
    """Test that API documentation is properly generated from tracked calls."""
    # Load mocked data
    mock_projects = json.loads(load_json_file(INPUT_PROJECTS))
    mock_datasets = json.loads(load_json_file(INPUT_DATASETS))

    # Extract IDs
    project_id = next((p["_id"] for p in mock_projects["projects"] if p["name"] == PROJECT_NAME), None)

    # Mock endpoints with exact URLs
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

    # Create tracker
    tracker = APICallTracker(
        cloudos_url=CLOUDOS_URL,
        workspace_id=WORKSPACE_ID,
        verify=True
    )

    # Instantiate Datasets with tracker
    # Don't pass project_id to trigger the project resolution API call
    datasets = Datasets(
        cloudos_url=CLOUDOS_URL,
        apikey=APIKEY,
        workspace_id=WORKSPACE_ID,
        project_name=PROJECT_NAME,
        verify=True,
        cromwell_token=None,
        api_docs_tracker=tracker
    )

    # Execute the listing (just top level)
    datasets.list_folder_content(None)

    # Generate documentation
    docs = tracker.get_documentation()

    # Assertions on documentation content
    assert "Platform API Instructions" in docs
    assert "Requirements" in docs
    assert "Used Endpoints" in docs
    assert "How to Use Them" in docs
    assert f"workspace-id = {WORKSPACE_ID}" in docs
    assert f"project-name = {PROJECT_NAME}" in docs
    # project-id should NOT be in requirements since it's derived from the API call
    assert "project-id" not in docs or "project-id" not in docs.split("### Used Endpoints")[0]
    assert "apikey = <YOUR_APIKEY>" in docs
    assert "curl -X GET" in docs
    assert CLOUDOS_URL in docs
    assert "<YOUR_APIKEY>" in docs, "API key should be masked in documentation"
    # Should have at least datasets listing (project resolution may or may not be present)
    assert "List all top-level datasets" in docs


@responses.activate
def test_api_docs_with_ssl_disabled():
    """Test that API documentation includes -k flag when SSL verification is disabled."""
    # Load mocked data
    mock_projects = json.loads(load_json_file(INPUT_PROJECTS))
    mock_datasets = json.loads(load_json_file(INPUT_DATASETS))

    # Mock endpoints
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v2/projects",
        body=json.dumps(mock_projects),
        status=200
    )

    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v2/datasets",
        body=json.dumps(mock_datasets),
        status=200
    )

    # Create tracker with SSL disabled
    tracker = APICallTracker(
        cloudos_url=CLOUDOS_URL,
        workspace_id=WORKSPACE_ID,
        verify=False
    )

    # Instantiate Datasets with tracker
    datasets = Datasets(
        cloudos_url=CLOUDOS_URL,
        apikey=APIKEY,
        workspace_id=WORKSPACE_ID,
        project_name=PROJECT_NAME,
        verify=False,
        cromwell_token=None,
        api_docs_tracker=tracker
    )

    # Execute the listing
    datasets.list_folder_content(None)

    # Generate documentation
    docs = tracker.get_documentation()

    # Assertions
    assert "ssl-verification = disabled" in docs
    assert "curl -X GET -k" in docs, "Documentation should include -k flag for disabled SSL verification"


@responses.activate
def test_api_docs_with_ssl_cert():
    """Test that API documentation includes --cacert flag when SSL cert is provided."""
    # Load mocked data
    mock_projects = json.loads(load_json_file(INPUT_PROJECTS))
    mock_datasets = json.loads(load_json_file(INPUT_DATASETS))

    cert_path = "/path/to/cert.pem"

    # Mock endpoints
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v2/projects",
        body=json.dumps(mock_projects),
        status=200
    )

    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v2/datasets",
        body=json.dumps(mock_datasets),
        status=200
    )

    # Create tracker with SSL cert
    tracker = APICallTracker(
        cloudos_url=CLOUDOS_URL,
        workspace_id=WORKSPACE_ID,
        verify=cert_path
    )

    # Instantiate Datasets with tracker
    datasets = Datasets(
        cloudos_url=CLOUDOS_URL,
        apikey=APIKEY,
        workspace_id=WORKSPACE_ID,
        project_name=PROJECT_NAME,
        verify=cert_path,
        cromwell_token=None,
        api_docs_tracker=tracker
    )

    # Execute the listing
    datasets.list_folder_content(None)

    # Generate documentation
    docs = tracker.get_documentation()

    # Assertions
    assert f"ssl-cert = {cert_path}" in docs
    assert f"--cacert {cert_path}" in docs, "Documentation should include --cacert flag with cert path"

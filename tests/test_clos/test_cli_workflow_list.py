"""Test the CLI workflow list command functionality."""

import pytest
import json
import os
import tempfile
from click.testing import CliRunner
from cloudos_cli.__main__ import run_cloudos_cli
import requests_mock
from unittest.mock import patch, MagicMock


# Test data
APIKEY = 'test_api_key_12345'
CLOUDOS_URL = 'https://cloudos.lifebit.ai'
WORKSPACE_ID = 'test_workspace_id_123'

# Load test workflow data as string (as load_json_file returns a string)
with open("tests/test_data/workflows/workflows.json") as f:
    WORKFLOWS_JSON_STR = f.read()
    WORKFLOWS_JSON_DICT = json.loads(WORKFLOWS_JSON_STR)


def test_workflow_list_command_exists():
    """Test that the workflow list command exists in the workflow group."""
    runner = CliRunner()
    result = runner.invoke(run_cloudos_cli, ['workflow', '--help'])
    assert result.exit_code == 0
    assert 'list' in result.output
    assert 'Collect and display workflows from a CloudOS workspace' in result.output


def test_workflow_list_help():
    """Test that the workflow list command help works."""
    runner = CliRunner()
    result = runner.invoke(run_cloudos_cli, ['workflow', 'list', '--help'])
    assert result.exit_code == 0
    assert '--workspace-id' in result.output
    assert '--apikey' in result.output
    assert '--output-format' in result.output
    assert '--output-basename' in result.output
    assert 'stdout' in result.output
    assert 'csv' in result.output
    assert 'json' in result.output


def test_workflow_list_missing_required_params():
    """Test that the command fails when missing required parameters."""
    runner = CliRunner()
    
    # Mock config file loading to ensure no profile provides default values
    with patch('cloudos_cli.configure.configure.ConfigurationProfile.load_profile') as mock_load:
        mock_load.return_value = {}  # No profile data
        
        result = runner.invoke(run_cloudos_cli, ['workflow', 'list'])
        assert result.exit_code != 0
        # The command should be aborted when required params are missing
        assert 'Missing option' in result.output or 'Error' in result.output or 'Aborted' in result.output


def test_workflow_list_csv_output():
    """Test workflow list with CSV output format."""
    runner = CliRunner()
    
    with requests_mock.Mocker() as m:
        # Mock the workflow list API endpoint with query parameters
        m.get(
            f"{CLOUDOS_URL}/api/v3/workflows",
            text=WORKFLOWS_JSON_STR,
            status_code=200
        )
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, 'test_workflows.csv')
            
            result = runner.invoke(run_cloudos_cli, [
                'workflow', 'list',
                '--apikey', APIKEY,
                '--cloudos-url', CLOUDOS_URL,
                '--workspace-id', WORKSPACE_ID,
                '--output-format', 'csv',
                '--output-basename', output_file.replace('.csv', '')
            ])
            
            # Debug: print output if test fails
            if result.exit_code != 0:
                print(f"Exit code: {result.exit_code}")
                print(f"Output: {result.output}")
                if result.exception:
                    print(f"Exception: {result.exception}")
                    import traceback
                    traceback.print_exception(type(result.exception), result.exception, result.exception.__traceback__)
            
            assert result.exit_code == 0
            assert 'Executing list...' in result.output
            assert os.path.exists(output_file)
            
            # Verify CSV file has content
            with open(output_file, 'r') as f:
                content = f.read()
                assert len(content) > 0
                # Check for expected columns in CSV header
                assert '_id' in content or 'name' in content


def test_workflow_list_json_output():
    """Test workflow list with JSON output format."""
    runner = CliRunner()
    
    with requests_mock.Mocker() as m:
        # Mock the workflow list API endpoint
        m.get(
            f"{CLOUDOS_URL}/api/v3/workflows",
            text=WORKFLOWS_JSON_STR,
            status_code=200
        )
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, 'test_workflows.json')
            
            result = runner.invoke(run_cloudos_cli, [
                'workflow', 'list',
                '--apikey', APIKEY,
                '--cloudos-url', CLOUDOS_URL,
                '--workspace-id', WORKSPACE_ID,
                '--output-format', 'json',
                '--output-basename', output_file.replace('.json', '')
            ])
            
            assert result.exit_code == 0
            assert 'Executing list...' in result.output
            assert os.path.exists(output_file)
            
            # Verify JSON file has valid content
            with open(output_file, 'r') as f:
                data = json.load(f)
                assert isinstance(data, list)
                assert len(data) > 0


def test_workflow_list_stdout_output():
    """Test workflow list with stdout (table) output format."""
    runner = CliRunner()
    
    with requests_mock.Mocker() as m:
        # Mock the workflow list API endpoint
        m.get(
            f"{CLOUDOS_URL}/api/v3/workflows",
            text=WORKFLOWS_JSON_STR,
            status_code=200
        )
        
        result = runner.invoke(run_cloudos_cli, [
            'workflow', 'list',
            '--apikey', APIKEY,
            '--cloudos-url', CLOUDOS_URL,
            '--workspace-id', WORKSPACE_ID,
            '--output-format', 'stdout'
        ])
        
        assert result.exit_code == 0
        assert 'Executing list...' in result.output
        # Table output should contain workflow information
        assert 'Workflow List' in result.output or 'Total workflows' in result.output


def test_workflow_list_default_output_is_stdout():
    """Test that stdout is the default output format."""
    runner = CliRunner()
    
    with requests_mock.Mocker() as m:
        # Mock the workflow list API endpoint
        m.get(
            f"{CLOUDOS_URL}/api/v3/workflows",
            text=WORKFLOWS_JSON_STR,
            status_code=200
        )
        
        result = runner.invoke(run_cloudos_cli, [
            'workflow', 'list',
            '--apikey', APIKEY,
            '--cloudos-url', CLOUDOS_URL,
            '--workspace-id', WORKSPACE_ID
            # No --output-format specified, should default to stdout
        ])
        
        assert result.exit_code == 0
        # Should display table output, not save to file
        assert 'Workflow List' in result.output or 'Total workflows' in result.output


def test_workflow_list_empty_workflows():
    """Test workflow list when no workflows are found."""
    runner = CliRunner()
    
    empty_response = {
        "workflows": [],
        "paginationMetadata": {"Pagination-Count": 0}
    }
    
    with requests_mock.Mocker() as m:
        # Mock the workflow list API endpoint with empty response
        m.get(
            f"{CLOUDOS_URL}/api/v3/workflows",
            json=empty_response,
            status_code=200
        )
        
        result = runner.invoke(run_cloudos_cli, [
            'workflow', 'list',
            '--apikey', APIKEY,
            '--cloudos-url', CLOUDOS_URL,
            '--workspace-id', WORKSPACE_ID,
            '--output-format', 'stdout'
        ])
        
        assert result.exit_code == 0
        # Should show message about no workflows found
        assert 'No workflows found' in result.output or '0 workflows' in result.output


def test_workflow_list_api_error():
    """Test workflow list when API returns an error."""
    runner = CliRunner()
    
    error_response = {
        "statusCode": 400,
        "code": "BadRequest",
        "message": "Invalid workspace ID",
        "time": "2026-03-09_12:00:00"
    }
    
    with requests_mock.Mocker() as m:
        # Mock the workflow list API endpoint with error response
        m.get(
            f"{CLOUDOS_URL}/api/v3/workflows",
            json=error_response,
            status_code=400
        )
        
        result = runner.invoke(run_cloudos_cli, [
            'workflow', 'list',
            '--apikey', APIKEY,
            '--cloudos-url', CLOUDOS_URL,
            '--workspace-id', WORKSPACE_ID,
            '--output-format', 'csv',
            '--output-basename', 'test_output'
        ])
        
        assert result.exit_code != 0
        # Should show error information
        assert 'Error' in result.output or '400' in result.output or result.exception is not None


def test_workflow_list_with_all_fields():
    """Test workflow list with all fields flag for CSV output."""
    runner = CliRunner()
    
    with requests_mock.Mocker() as m:
        # Mock the workflow list API endpoint
        m.get(
            f"{CLOUDOS_URL}/api/v3/workflows",
            text=WORKFLOWS_JSON_STR,
            status_code=200
        )
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, 'test_workflows_full.csv')
            
            result = runner.invoke(run_cloudos_cli, [
                'workflow', 'list',
                '--apikey', APIKEY,
                '--cloudos-url', CLOUDOS_URL,
                '--workspace-id', WORKSPACE_ID,
                '--output-format', 'csv',
                '--all-fields',
                '--output-basename', output_file.replace('.csv', '')
            ])
            
            assert result.exit_code == 0
            assert os.path.exists(output_file)
            
            # Verify CSV file has more columns with --all-fields
            with open(output_file, 'r') as f:
                header = f.readline()
                # Should have more columns when all_fields is True
                assert ',' in header
                # Check for some expected columns
                field_count = len(header.split(','))
                assert field_count > 5  # Should have multiple fields


def test_workflow_list_with_verbose():
    """Test workflow list with verbose flag."""
    runner = CliRunner()
    
    with requests_mock.Mocker() as m:
        # Mock the workflow list API endpoint
        m.get(
            f"{CLOUDOS_URL}/api/v3/workflows",
            text=WORKFLOWS_JSON_STR,
            status_code=200
        )
        
        result = runner.invoke(run_cloudos_cli, [
            'workflow', 'list',
            '--apikey', APIKEY,
            '--cloudos-url', CLOUDOS_URL,
            '--workspace-id', WORKSPACE_ID,
            '--output-format', 'stdout',
            '--verbose'
        ])
        
        assert result.exit_code == 0
        # Verbose should show additional information
        assert '...Preparing objects' in result.output or 'Cloudos object' in result.output


def test_workflow_list_custom_output_basename():
    """Test workflow list with custom output basename."""
    runner = CliRunner()
    
    with requests_mock.Mocker() as m:
        # Mock the workflow list API endpoint
        m.get(
            f"{CLOUDOS_URL}/api/v3/workflows",
            text=WORKFLOWS_JSON_STR,
            status_code=200
        )
        
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_basename = 'my_custom_workflows'
            output_file = os.path.join(tmpdir, f'{custom_basename}.csv')
            
            result = runner.invoke(run_cloudos_cli, [
                'workflow', 'list',
                '--apikey', APIKEY,
                '--cloudos-url', CLOUDOS_URL,
                '--workspace-id', WORKSPACE_ID,
                '--output-format', 'csv',
                '--output-basename', output_file.replace('.csv', '')
            ])
            
            assert result.exit_code == 0
            assert os.path.exists(output_file)
            assert custom_basename in result.output


def test_workflow_list_with_ssl_options():
    """Test workflow list with SSL options."""
    runner = CliRunner()
    
    with requests_mock.Mocker() as m:
        # Mock the workflow list API endpoint
        m.get(
            f"{CLOUDOS_URL}/api/v3/workflows",
            text=WORKFLOWS_JSON_STR,
            status_code=200
        )
        
        # Test with --disable-ssl-verification
        result = runner.invoke(run_cloudos_cli, [
            'workflow', 'list',
            '--apikey', APIKEY,
            '--cloudos-url', CLOUDOS_URL,
            '--workspace-id', WORKSPACE_ID,
            '--output-format', 'stdout',
            '--disable-ssl-verification'
        ])
        
        assert result.exit_code == 0


@pytest.mark.parametrize("output_format", ['stdout', 'csv', 'json'])
def test_workflow_list_all_output_formats(output_format):
    """Test workflow list with all valid output formats."""
    runner = CliRunner()
    
    with requests_mock.Mocker() as m:
        # Mock the workflow list API endpoint
        m.get(
            f"{CLOUDOS_URL}/api/v3/workflows",
            text=WORKFLOWS_JSON_STR,
            status_code=200
        )
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_basename = os.path.join(tmpdir, 'test_workflows')
            
            result = runner.invoke(run_cloudos_cli, [
                'workflow', 'list',
                '--apikey', APIKEY,
                '--cloudos-url', CLOUDOS_URL,
                '--workspace-id', WORKSPACE_ID,
                '--output-format', output_format,
                '--output-basename', output_basename
            ])
            
            assert result.exit_code == 0
            
            if output_format != 'stdout':
                # For csv and json, check file was created
                output_file = f"{output_basename}.{output_format}"
                assert os.path.exists(output_file)


def test_workflow_list_multiple_workflows():
    """Test workflow list with multiple workflows in response."""
    runner = CliRunner()
    
    # Create test data with multiple workflows
    multiple_workflows = {
        "workflows": [
            {
                "_id": "workflow1",
                "name": "Test Workflow 1",
                "workflowType": "nextflow",
                "repository": {
                    "name": "test-repo-1",
                    "platform": "github",
                    "url": "https://github.com/test/repo1"
                }
            },
            {
                "_id": "workflow2",
                "name": "Test Workflow 2",
                "workflowType": "wdl",
                "repository": {
                    "name": "test-repo-2",
                    "platform": "gitlab",
                    "url": "https://gitlab.com/test/repo2"
                }
            },
            {
                "_id": "workflow3",
                "name": "Test Workflow 3",
                "workflowType": "docker",
                "repository": {
                    "name": "test-repo-3",
                    "platform": "github",
                    "url": "https://github.com/test/repo3"
                }
            }
        ],
        "paginationMetadata": {"Pagination-Count": 3}
    }
    
    with requests_mock.Mocker() as m:
        # Mock the workflow list API endpoint
        m.get(
            f"{CLOUDOS_URL}/api/v3/workflows",
            json=multiple_workflows,
            status_code=200
        )
        
        result = runner.invoke(run_cloudos_cli, [
            'workflow', 'list',
            '--apikey', APIKEY,
            '--cloudos-url', CLOUDOS_URL,
            '--workspace-id', WORKSPACE_ID,
            '--output-format', 'stdout'
        ])
        
        assert result.exit_code == 0
        assert '3' in result.output  # Should show count of 3 workflows

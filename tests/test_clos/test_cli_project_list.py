"""Test the CLI project list command functionality."""

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

# Load test project data
with open("tests/test_data/projects.json") as f:
    PROJECTS_JSON_STR = f.read()
    PROJECTS_JSON_DICT = json.loads(PROJECTS_JSON_STR)


def test_project_list_command_exists():
    """Test that the project list command exists in the project group."""
    runner = CliRunner()
    result = runner.invoke(run_cloudos_cli, ['project', '--help'])
    assert result.exit_code == 0
    assert 'list' in result.output
    assert 'Collect and display all projects from a Lifebit Platform workspace.' in result.output


def test_project_list_help():
    """Test that the project list command help works."""
    runner = CliRunner()
    result = runner.invoke(run_cloudos_cli, ['project', 'list', '--help'])
    assert result.exit_code == 0
    assert '--workspace-id' in result.output
    assert '--apikey' in result.output
    assert '--output-format' in result.output
    assert '--output-basename' in result.output
    assert 'stdout' in result.output
    assert 'csv' in result.output
    assert 'json' in result.output


def test_project_list_missing_required_params():
    """Test that the command fails when missing required parameters."""
    runner = CliRunner()
    
    # Mock config file loading to ensure no profile provides default values
    with patch('cloudos_cli.configure.configure.ConfigurationProfile.load_profile') as mock_load:
        mock_load.return_value = {}  # No profile data
        
        result = runner.invoke(run_cloudos_cli, ['project', 'list'])
        assert result.exit_code != 0
        # The command should be aborted when required params are missing
        assert 'Missing option' in result.output or 'Error' in result.output or 'Aborted' in result.output


def test_project_list_csv_output():
    """Test project list with CSV output format."""
    runner = CliRunner()
    
    with requests_mock.Mocker() as m:
        # Mock the project list API endpoint with query parameters
        m.get(
            f"{CLOUDOS_URL}/api/v2/projects",
            text=PROJECTS_JSON_STR,
            status_code=200
        )
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, 'test_projects.csv')
            
            result = runner.invoke(run_cloudos_cli, [
                'project', 'list',
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


def test_project_list_json_output():
    """Test project list with JSON output format."""
    runner = CliRunner()
    
    with requests_mock.Mocker() as m:
        # Mock the project list API endpoint
        m.get(
            f"{CLOUDOS_URL}/api/v2/projects",
            text=PROJECTS_JSON_STR,
            status_code=200
        )
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, 'test_projects.json')
            
            result = runner.invoke(run_cloudos_cli, [
                'project', 'list',
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


def test_project_list_stdout_output():
    """Test project list with stdout (table) output format."""
    runner = CliRunner()
    
    with requests_mock.Mocker() as m:
        # Mock the project list API endpoint
        m.get(
            f"{CLOUDOS_URL}/api/v2/projects",
            text=PROJECTS_JSON_STR,
            status_code=200
        )
        
        result = runner.invoke(run_cloudos_cli, [
            'project', 'list',
            '--apikey', APIKEY,
            '--cloudos-url', CLOUDOS_URL,
            '--workspace-id', WORKSPACE_ID,
            '--output-format', 'stdout'
        ])
        
        assert result.exit_code == 0
        assert 'Executing list...' in result.output
        # Table output should contain project information
        assert 'Project List' in result.output or 'Total projects' in result.output


def test_project_list_default_output_is_stdout():
    """Test that stdout is the default output format."""
    runner = CliRunner()
    
    with requests_mock.Mocker() as m:
        # Mock the project list API endpoint
        m.get(
            f"{CLOUDOS_URL}/api/v2/projects",
            text=PROJECTS_JSON_STR,
            status_code=200
        )
        
        result = runner.invoke(run_cloudos_cli, [
            'project', 'list',
            '--apikey', APIKEY,
            '--cloudos-url', CLOUDOS_URL,
            '--workspace-id', WORKSPACE_ID
            # No --output-format specified, should default to stdout
        ])
        
        assert result.exit_code == 0
        # Should display table output, not save to file
        assert 'Project List' in result.output or 'Total projects' in result.output


def test_project_list_empty_projects():
    """Test project list when no projects are found."""
    runner = CliRunner()
    
    empty_response = {
        "total": 0,
        "projects": []
    }
    
    with requests_mock.Mocker() as m:
        # Mock the project list API endpoint with empty response
        m.get(
            f"{CLOUDOS_URL}/api/v2/projects",
            json=empty_response,
            status_code=200
        )
        
        result = runner.invoke(run_cloudos_cli, [
            'project', 'list',
            '--apikey', APIKEY,
            '--cloudos-url', CLOUDOS_URL,
            '--workspace-id', WORKSPACE_ID,
            '--output-format', 'stdout'
        ])
        
        assert result.exit_code == 0
        # Should show message about no projects found
        assert 'No projects found' in result.output or '0 projects' in result.output


def test_project_list_api_error():
    """Test project list when API returns an error."""
    runner = CliRunner()
    
    error_response = {
        "statusCode": 400,
        "code": "BadRequest",
        "message": "Invalid workspace ID",
        "time": "2026-03-10_12:00:00"
    }
    
    with requests_mock.Mocker() as m:
        # Mock the project list API endpoint with error response
        m.get(
            f"{CLOUDOS_URL}/api/v2/projects",
            json=error_response,
            status_code=400
        )
        
        result = runner.invoke(run_cloudos_cli, [
            'project', 'list',
            '--apikey', APIKEY,
            '--cloudos-url', CLOUDOS_URL,
            '--workspace-id', WORKSPACE_ID,
            '--output-format', 'csv',
            '--output-basename', 'test_output'
        ])
        
        assert result.exit_code != 0
        # Should show error information
        assert 'Error' in result.output or '400' in result.output or result.exception is not None


def test_project_list_with_all_fields():
    """Test project list with all fields flag for CSV output."""
    runner = CliRunner()
    
    with requests_mock.Mocker() as m:
        # Mock the project list API endpoint
        m.get(
            f"{CLOUDOS_URL}/api/v2/projects",
            text=PROJECTS_JSON_STR,
            status_code=200
        )
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, 'test_projects_full.csv')
            
            result = runner.invoke(run_cloudos_cli, [
                'project', 'list',
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


def test_project_list_with_verbose():
    """Test project list with verbose flag."""
    runner = CliRunner()
    
    with requests_mock.Mocker() as m:
        # Mock the project list API endpoint
        m.get(
            f"{CLOUDOS_URL}/api/v2/projects",
            text=PROJECTS_JSON_STR,
            status_code=200
        )
        
        result = runner.invoke(run_cloudos_cli, [
            'project', 'list',
            '--apikey', APIKEY,
            '--cloudos-url', CLOUDOS_URL,
            '--workspace-id', WORKSPACE_ID,
            '--output-format', 'stdout',
            '--verbose'
        ])
        
        assert result.exit_code == 0
        # Verbose should show additional information
        assert '...Preparing objects' in result.output or 'Cloudos object' in result.output


def test_project_list_custom_output_basename():
    """Test project list with custom output basename."""
    runner = CliRunner()
    
    with requests_mock.Mocker() as m:
        # Mock the project list API endpoint
        m.get(
            f"{CLOUDOS_URL}/api/v2/projects",
            text=PROJECTS_JSON_STR,
            status_code=200
        )
        
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_basename = 'my_custom_projects'
            output_file = os.path.join(tmpdir, f'{custom_basename}.csv')
            
            result = runner.invoke(run_cloudos_cli, [
                'project', 'list',
                '--apikey', APIKEY,
                '--cloudos-url', CLOUDOS_URL,
                '--workspace-id', WORKSPACE_ID,
                '--output-format', 'csv',
                '--output-basename', output_file.replace('.csv', '')
            ])
            
            assert result.exit_code == 0
            assert os.path.exists(output_file)
            assert custom_basename in result.output


def test_project_list_with_ssl_options():
    """Test project list with SSL options."""
    runner = CliRunner()
    
    with requests_mock.Mocker() as m:
        # Mock the project list API endpoint
        m.get(
            f"{CLOUDOS_URL}/api/v2/projects",
            text=PROJECTS_JSON_STR,
            status_code=200
        )
        
        # Test with --disable-ssl-verification
        result = runner.invoke(run_cloudos_cli, [
            'project', 'list',
            '--apikey', APIKEY,
            '--cloudos-url', CLOUDOS_URL,
            '--workspace-id', WORKSPACE_ID,
            '--output-format', 'stdout',
            '--disable-ssl-verification'
        ])
        
        assert result.exit_code == 0


def test_project_list_with_profile():
    """Test project list with profile option."""
    runner = CliRunner()
    
    with requests_mock.Mocker() as m:
        # Mock the project list API endpoint
        m.get(
            f"{CLOUDOS_URL}/api/v2/projects",
            text=PROJECTS_JSON_STR,
            status_code=200
        )
        
        result = runner.invoke(run_cloudos_cli, [
            'project', 'list',
            '--apikey', APIKEY,
            '--cloudos-url', CLOUDOS_URL,
            '--workspace-id', WORKSPACE_ID,
            '--output-format', 'stdout',
            '--profile', 'default'
        ])
        
        # Profile option should be accepted (even if profile doesn't exist)
        assert result.exit_code in [0, 1]  # May fail if profile not found, but option is valid


@pytest.mark.parametrize("output_format", ['stdout', 'csv', 'json'])
def test_project_list_all_output_formats(output_format):
    """Test project list with all valid output formats."""
    runner = CliRunner()
    
    with requests_mock.Mocker() as m:
        # Mock the project list API endpoint
        m.get(
            f"{CLOUDOS_URL}/api/v2/projects",
            text=PROJECTS_JSON_STR,
            status_code=200
        )
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_basename = os.path.join(tmpdir, 'test_projects')
            
            result = runner.invoke(run_cloudos_cli, [
                'project', 'list',
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


def test_project_list_multiple_projects():
    """Test project list with multiple projects in response."""
    runner = CliRunner()
    
    # Create test data with multiple projects
    multiple_projects = {
        "total": 3,
        "projects": [
            {
                "_id": "project1",
                "name": "Test Project 1",
                "user": {
                    "id": "user1",
                    "name": "John",
                    "surname": "Doe",
                    "email": "john@example.com"
                },
                "createdAt": "2024-01-01T10:00:00.000Z",
                "updatedAt": "2024-01-15T12:00:00.000Z",
                "jobCount": 10,
                "notebookSessionCount": 2
            },
            {
                "_id": "project2",
                "name": "Test Project 2",
                "user": {
                    "id": "user2",
                    "name": "Jane",
                    "surname": "Smith",
                    "email": "jane@example.com"
                },
                "createdAt": "2024-02-01T10:00:00.000Z",
                "updatedAt": "2024-02-15T12:00:00.000Z",
                "jobCount": 25,
                "notebookSessionCount": 5
            },
            {
                "_id": "project3",
                "name": "Test Project 3",
                "user": {
                    "id": "user3",
                    "name": "Bob",
                    "surname": "Johnson",
                    "email": "bob@example.com"
                },
                "createdAt": "2024-03-01T10:00:00.000Z",
                "updatedAt": "2024-03-15T12:00:00.000Z",
                "jobCount": 15,
                "notebookSessionCount": 3
            }
        ]
    }
    
    with requests_mock.Mocker() as m:
        # Mock the project list API endpoint
        m.get(
            f"{CLOUDOS_URL}/api/v2/projects",
            json=multiple_projects,
            status_code=200
        )
        
        result = runner.invoke(run_cloudos_cli, [
            'project', 'list',
            '--apikey', APIKEY,
            '--cloudos-url', CLOUDOS_URL,
            '--workspace-id', WORKSPACE_ID,
            '--output-format', 'stdout'
        ])
        
        assert result.exit_code == 0
        assert '3' in result.output  # Should show count of 3 projects


def test_project_list_with_page_option():
    """Test project list with page option."""
    runner = CliRunner()
    
    with requests_mock.Mocker() as m:
        # Mock the project list API endpoint with pagination
        m.get(
            f"{CLOUDOS_URL}/api/v2/projects",
            text=PROJECTS_JSON_STR,
            status_code=200
        )
        
        result = runner.invoke(run_cloudos_cli, [
            'project', 'list',
            '--apikey', APIKEY,
            '--cloudos-url', CLOUDOS_URL,
            '--workspace-id', WORKSPACE_ID,
            '--output-format', 'stdout',
            '--page', '2'
        ])
        
        assert result.exit_code == 0
        # Page option should be accepted
        assert 'Executing list...' in result.output


def test_project_list_table_contains_expected_columns():
    """Test that stdout table output contains expected columns."""
    runner = CliRunner()
    
    test_project = {
        "total": 1,
        "projects": [
            {
                "_id": "test_project_123",
                "name": "My Test Project",
                "user": {
                    "id": "user123",
                    "name": "Test",
                    "surname": "User",
                    "email": "test@example.com"
                },
                "createdAt": "2024-01-01T10:00:00.000Z",
                "updatedAt": "2024-01-15T12:00:00.000Z",
                "jobCount": 42,
                "notebookSessionCount": 7
            }
        ]
    }
    
    with requests_mock.Mocker() as m:
        # Mock the project list API endpoint
        m.get(
            f"{CLOUDOS_URL}/api/v2/projects",
            json=test_project,
            status_code=200
        )
        
        result = runner.invoke(run_cloudos_cli, [
            'project', 'list',
            '--apikey', APIKEY,
            '--cloudos-url', CLOUDOS_URL,
            '--workspace-id', WORKSPACE_ID,
            '--output-format', 'stdout'
        ])
        
        assert result.exit_code == 0
        # Check for expected output elements
        assert 'Project List' in result.output
        assert 'Total projects' in result.output
        assert '1' in result.output  # Should show 1 project

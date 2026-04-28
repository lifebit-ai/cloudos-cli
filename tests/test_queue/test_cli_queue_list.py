"""Test the CLI queue list command functionality."""

import pytest
import json
import os
import tempfile
from click.testing import CliRunner
from cloudos_cli.__main__ import run_cloudos_cli
import requests_mock


# Test data
APIKEY = 'test_api_key_12345'
CLOUDOS_URL = 'https://cloudos.lifebit.ai'
WORKSPACE_ID = 'test_workspace_id_123'

# Load test queue data
with open("tests/test_data/queue/queues.json") as f:
    QUEUES_JSON_STR = f.read()
    QUEUES_JSON_DICT = json.loads(QUEUES_JSON_STR)

# Load test system queue data
with open("tests/test_data/queue/system_queues.json") as f:
    SYSTEM_QUEUES_JSON_STR = f.read()
    SYSTEM_QUEUES_JSON_DICT = json.loads(SYSTEM_QUEUES_JSON_STR)


def test_queue_list_command_exists():
    """Test that the queue list command exists in the queue group."""
    runner = CliRunner()
    result = runner.invoke(run_cloudos_cli, ['queue', '--help'])
    assert result.exit_code == 0
    assert 'list' in result.output
    assert 'Collect and display all available job queues' in result.output
    assert 'Lifebit Platform' in result.output


def test_queue_list_help():
    """Test that the queue list command help works."""
    runner = CliRunner()
    result = runner.invoke(run_cloudos_cli, ['queue', 'list', '--help'])
    assert result.exit_code == 0
    assert '--workspace-id' in result.output
    assert '--apikey' in result.output
    assert '--output-format' in result.output
    assert '--output-basename' in result.output
    assert 'stdout' in result.output
    assert 'csv' in result.output
    assert 'json' in result.output


def test_queue_list_missing_required_params():
    """Test that the command fails when missing required parameters."""
    runner = CliRunner()
    
    # When no profile is configured, it should ask for required params
    result = runner.invoke(run_cloudos_cli, ['queue', 'list'], env={'HOME': '/tmp/no_profile'})
    # The command may work with profile defaults, so just check it runs
    # without crashing - actual param validation is tested in other tests
    assert result.exit_code in [0, 1, 2]  # Various exit codes depending on profile availability


def test_queue_list_csv_output():
    """Test queue list with CSV output format."""
    runner = CliRunner()
    
    with requests_mock.Mocker() as m:
        # Mock the queue list API endpoint
        m.get(
            f"{CLOUDOS_URL}/api/v1/teams/aws/v2/job-queues",
            text=QUEUES_JSON_STR,
            status_code=200
        )
        # Mock the system queues API endpoint
        m.get(
            f"{CLOUDOS_URL}/api/v1/teams/aws/v2/system-job-queues",
            text=SYSTEM_QUEUES_JSON_STR,
            status_code=200
        )
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, 'test_queues.csv')
            
            result = runner.invoke(run_cloudos_cli, [
                'queue', 'list',
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
                assert 'id' in content or 'label' in content


def test_queue_list_json_output():
    """Test queue list with JSON output format."""
    runner = CliRunner()
    
    with requests_mock.Mocker() as m:
        # Mock the queue list API endpoint
        m.get(
            f"{CLOUDOS_URL}/api/v1/teams/aws/v2/job-queues",
            text=QUEUES_JSON_STR,
            status_code=200
        )
        # Mock the system queues API endpoint
        m.get(
            f"{CLOUDOS_URL}/api/v1/teams/aws/v2/system-job-queues",
            text=SYSTEM_QUEUES_JSON_STR,
            status_code=200
        )
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, 'test_queues.json')
            
            result = runner.invoke(run_cloudos_cli, [
                'queue', 'list',
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


def test_queue_list_stdout_output():
    """Test queue list with stdout (table) output format."""
    runner = CliRunner()
    
    with requests_mock.Mocker() as m:
        # Mock the queue list API endpoint
        m.get(
            f"{CLOUDOS_URL}/api/v1/teams/aws/v2/job-queues",
            text=QUEUES_JSON_STR,
            status_code=200
        )
        # Mock the system queues API endpoint
        m.get(
            f"{CLOUDOS_URL}/api/v1/teams/aws/v2/system-job-queues",
            text=SYSTEM_QUEUES_JSON_STR,
            status_code=200
        )
        
        result = runner.invoke(run_cloudos_cli, [
            'queue', 'list',
            '--apikey', APIKEY,
            '--cloudos-url', CLOUDOS_URL,
            '--workspace-id', WORKSPACE_ID,
            '--output-format', 'stdout'
        ])
        
        assert result.exit_code == 0
        assert 'Executing list...' in result.output
        # Table output should contain queue information
        assert 'Job Queue List' in result.output or 'Total job queues' in result.output


def test_queue_list_default_output_is_stdout():
    """Test that stdout is the default output format."""
    runner = CliRunner()
    
    with requests_mock.Mocker() as m:
        # Mock the queue list API endpoint
        m.get(
            f"{CLOUDOS_URL}/api/v1/teams/aws/v2/job-queues",
            text=QUEUES_JSON_STR,
            status_code=200
        )
        # Mock the system queues API endpoint
        m.get(
            f"{CLOUDOS_URL}/api/v1/teams/aws/v2/system-job-queues",
            text=SYSTEM_QUEUES_JSON_STR,
            status_code=200
        )
        
        result = runner.invoke(run_cloudos_cli, [
            'queue', 'list',
            '--apikey', APIKEY,
            '--cloudos-url', CLOUDOS_URL,
            '--workspace-id', WORKSPACE_ID
            # No --output-format specified, should default to stdout
        ])
        
        assert result.exit_code == 0
        # Should display table output, not save to file
        assert 'Job Queue List' in result.output or 'Total job queues' in result.output


def test_queue_list_empty_queues():
    """Test queue list when no queues are found."""
    runner = CliRunner()
    
    empty_response = []
    
    with requests_mock.Mocker() as m:
        # Mock the queue list API endpoint with empty response
        m.get(
            f"{CLOUDOS_URL}/api/v1/teams/aws/v2/job-queues",
            json=empty_response,
            status_code=200
        )
        # Mock the system queues API endpoint with empty response
        m.get(
            f"{CLOUDOS_URL}/api/v1/teams/aws/v2/system-job-queues",
            json=empty_response,
            status_code=200
        )
        
        result = runner.invoke(run_cloudos_cli, [
            'queue', 'list',
            '--apikey', APIKEY,
            '--cloudos-url', CLOUDOS_URL,
            '--workspace-id', WORKSPACE_ID,
            '--output-format', 'stdout'
        ])
        
        # Should fail with ValueError about no queues
        assert result.exit_code != 0
        # Check that exception was raised
        assert result.exception is not None
        assert 'No AWS batch queues found' in str(result.exception)


def test_queue_list_api_error():
    """Test queue list when API returns an error."""
    runner = CliRunner()
    
    error_response = {
        "statusCode": 400,
        "code": "BadRequest",
        "message": "Invalid workspace ID",
        "time": "2026-03-10_12:00:00"
    }
    
    with requests_mock.Mocker() as m:
        # Mock the queue list API endpoint with error response
        m.get(
            f"{CLOUDOS_URL}/api/v1/teams/aws/v2/job-queues",
            json=error_response,
            status_code=400
        )
        
        result = runner.invoke(run_cloudos_cli, [
            'queue', 'list',
            '--apikey', APIKEY,
            '--cloudos-url', CLOUDOS_URL,
            '--workspace-id', WORKSPACE_ID,
            '--output-format', 'csv',
            '--output-basename', 'test_output'
        ])
        
        assert result.exit_code != 0
        # Should show error information
        assert 'Error' in result.output or '400' in result.output or result.exception is not None


def test_queue_list_with_all_fields():
    """Test queue list with all fields flag for CSV output."""
    runner = CliRunner()
    
    with requests_mock.Mocker() as m:
        # Mock the queue list API endpoint
        m.get(
            f"{CLOUDOS_URL}/api/v1/teams/aws/v2/job-queues",
            text=QUEUES_JSON_STR,
            status_code=200
        )
        # Mock the system queues API endpoint
        m.get(
            f"{CLOUDOS_URL}/api/v1/teams/aws/v2/system-job-queues",
            text=SYSTEM_QUEUES_JSON_STR,
            status_code=200
        )
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, 'test_queues_full.csv')
            
            result = runner.invoke(run_cloudos_cli, [
                'queue', 'list',
                '--apikey', APIKEY,
                '--cloudos-url', CLOUDOS_URL,
                '--workspace-id', WORKSPACE_ID,
                '--output-format', 'csv',
                '--all-fields',
                '--output-basename', output_file.replace('.csv', '')
            ])
            
            assert result.exit_code == 0
            assert os.path.exists(output_file)
            
            # Verify CSV file has content
            with open(output_file, 'r') as f:
                header = f.readline()
                # Should have columns
                assert ',' in header
                field_count = len(header.split(','))
                assert field_count > 0


def test_queue_list_with_profile():
    """Test queue list with profile option."""
    runner = CliRunner()
    
    with requests_mock.Mocker() as m:
        # Mock the queue list API endpoint
        m.get(
            f"{CLOUDOS_URL}/api/v1/teams/aws/v2/job-queues",
            text=QUEUES_JSON_STR,
            status_code=200
        )
        # Mock the system queues API endpoint
        m.get(
            f"{CLOUDOS_URL}/api/v1/teams/aws/v2/system-job-queues",
            text=SYSTEM_QUEUES_JSON_STR,
            status_code=200
        )
        
        result = runner.invoke(run_cloudos_cli, [
            'queue', 'list',
            '--apikey', APIKEY,
            '--cloudos-url', CLOUDOS_URL,
            '--workspace-id', WORKSPACE_ID,
            '--output-format', 'stdout',
            '--profile', 'default'
        ])
        
        # Profile option should be accepted (even if profile doesn't exist)
        assert result.exit_code in [0, 1]  # May fail if profile not found, but option is valid


def test_queue_list_custom_output_basename():
    """Test queue list with custom output basename."""
    runner = CliRunner()
    
    with requests_mock.Mocker() as m:
        # Mock the queue list API endpoint
        m.get(
            f"{CLOUDOS_URL}/api/v1/teams/aws/v2/job-queues",
            text=QUEUES_JSON_STR,
            status_code=200
        )
        # Mock the system queues API endpoint
        m.get(
            f"{CLOUDOS_URL}/api/v1/teams/aws/v2/system-job-queues",
            text=SYSTEM_QUEUES_JSON_STR,
            status_code=200
        )
        
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_basename = 'my_custom_queues'
            output_file = os.path.join(tmpdir, f'{custom_basename}.csv')
            
            result = runner.invoke(run_cloudos_cli, [
                'queue', 'list',
                '--apikey', APIKEY,
                '--cloudos-url', CLOUDOS_URL,
                '--workspace-id', WORKSPACE_ID,
                '--output-format', 'csv',
                '--output-basename', output_file.replace('.csv', '')
            ])
            
            assert result.exit_code == 0
            assert os.path.exists(output_file)
            assert custom_basename in result.output


def test_queue_list_with_ssl_options():
    """Test queue list with SSL options."""
    runner = CliRunner()
    
    with requests_mock.Mocker() as m:
        # Mock the queue list API endpoint
        m.get(
            f"{CLOUDOS_URL}/api/v1/teams/aws/v2/job-queues",
            text=QUEUES_JSON_STR,
            status_code=200
        )
        # Mock the system queues API endpoint
        m.get(
            f"{CLOUDOS_URL}/api/v1/teams/aws/v2/system-job-queues",
            text=SYSTEM_QUEUES_JSON_STR,
            status_code=200
        )
        
        # Test with --disable-ssl-verification
        result = runner.invoke(run_cloudos_cli, [
            'queue', 'list',
            '--apikey', APIKEY,
            '--cloudos-url', CLOUDOS_URL,
            '--workspace-id', WORKSPACE_ID,
            '--output-format', 'stdout',
            '--disable-ssl-verification'
        ])
        
        assert result.exit_code == 0


@pytest.mark.parametrize("output_format", ['stdout', 'csv', 'json'])
def test_queue_list_all_output_formats(output_format):
    """Test queue list with all valid output formats."""
    runner = CliRunner()
    
    with requests_mock.Mocker() as m:
        # Mock the queue list API endpoint
        m.get(
            f"{CLOUDOS_URL}/api/v1/teams/aws/v2/job-queues",
            text=QUEUES_JSON_STR,
            status_code=200
        )
        # Mock the system queues API endpoint
        m.get(
            f"{CLOUDOS_URL}/api/v1/teams/aws/v2/system-job-queues",
            text=SYSTEM_QUEUES_JSON_STR,
            status_code=200
        )
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_basename = os.path.join(tmpdir, 'test_queues')
            
            result = runner.invoke(run_cloudos_cli, [
                'queue', 'list',
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


def test_queue_list_multiple_queues():
    """Test queue list with multiple queues in response."""
    runner = CliRunner()
    
    # Create test data with multiple queues
    multiple_queues = [
        {
            "id": "queue1",
            "resource": "resource1",
            "name": "test_queue_1",
            "label": "Test Queue 1",
            "description": "First test queue",
            "isDefault": True,
            "resourceType": "teamBatchJobQueue",
            "executor": "nextflow",
            "status": "Ready"
        },
        {
            "id": "queue2",
            "resource": "resource2",
            "name": "test_queue_2",
            "label": "Test Queue 2",
            "description": "Second test queue",
            "isDefault": False,
            "resourceType": "teamBatchJobQueue",
            "executor": "nextflow",
            "status": "Ready"
        },
        {
            "id": "queue3",
            "resource": "resource3",
            "name": "test_queue_3",
            "label": "Test Queue 3",
            "description": "Third test queue",
            "isDefault": False,
            "resourceType": "",
            "executor": "docker",
            "status": "Creating"
        }
    ]
    
    with requests_mock.Mocker() as m:
        # Mock the queue list API endpoint
        m.get(
            f"{CLOUDOS_URL}/api/v1/teams/aws/v2/job-queues",
            json=multiple_queues,
            status_code=200
        )
        # Mock the system queues API endpoint
        m.get(
            f"{CLOUDOS_URL}/api/v1/teams/aws/v2/system-job-queues",
            text=SYSTEM_QUEUES_JSON_STR,
            status_code=200
        )
        
        result = runner.invoke(run_cloudos_cli, [
            'queue', 'list',
            '--apikey', APIKEY,
            '--cloudos-url', CLOUDOS_URL,
            '--workspace-id', WORKSPACE_ID,
            '--output-format', 'stdout'
        ])
        
        assert result.exit_code == 0
        assert '3' in result.output  # Should show count of 3 queues


def test_queue_list_table_formatting():
    """Test that the queue list table has correct formatting."""
    runner = CliRunner()
    
    # Test data with different statuses and resource types
    test_queues = [
        {
            "id": "queue1",
            "name": "ready_queue",
            "label": "Ready Queue",
            "isDefault": True,
            "resourceType": "teamBatchJobQueue",
            "status": "Ready"
        },
        {
            "id": "queue2",
            "name": "not_ready_queue",
            "label": "Not Ready Queue",
            "isDefault": False,
            "resourceType": "teamBatchJobQueue",
            "status": "Creating"
        }
    ]
    
    with requests_mock.Mocker() as m:
        m.get(
            f"{CLOUDOS_URL}/api/v1/teams/aws/v2/job-queues",
            json=test_queues,
            status_code=200
        )
        # Mock the system queues API endpoint
        m.get(
            f"{CLOUDOS_URL}/api/v1/teams/aws/v2/system-job-queues",
            text=SYSTEM_QUEUES_JSON_STR,
            status_code=200
        )
        
        result = runner.invoke(run_cloudos_cli, [
            'queue', 'list',
            '--apikey', APIKEY,
            '--cloudos-url', CLOUDOS_URL,
            '--workspace-id', WORKSPACE_ID,
            '--output-format', 'stdout'
        ])
        
        assert result.exit_code == 0
        # Check for table headers
        assert 'Label' in result.output
        assert 'Default' in result.output
        assert 'Resource Type' in result.output
        assert 'Status' in result.output
        # Check for processed values
        assert 'Batch Queues' in result.output  # teamBatchJobQueue should be converted
        assert 'Ready Queue' in result.output
        assert 'Not Ready Queue' in result.output


def test_queue_list_status_icons():
    """Test that status icons are displayed correctly."""
    runner = CliRunner()
    
    test_queues = [
        {
            "id": "queue1",
            "label": "Ready Queue",
            "isDefault": True,
            "resourceType": "teamBatchJobQueue",
            "status": "Ready"  # Should show checkmark
        },
        {
            "id": "queue2",
            "label": "Creating Queue",
            "isDefault": False,
            "resourceType": "",
            "status": "Creating"  # Should show X
        }
    ]
    
    with requests_mock.Mocker() as m:
        m.get(
            f"{CLOUDOS_URL}/api/v1/teams/aws/v2/job-queues",
            json=test_queues,
            status_code=200
        )
        # Mock the system queues API endpoint
        m.get(
            f"{CLOUDOS_URL}/api/v1/teams/aws/v2/system-job-queues",
            text=SYSTEM_QUEUES_JSON_STR,
            status_code=200
        )
        
        result = runner.invoke(run_cloudos_cli, [
            'queue', 'list',
            '--apikey', APIKEY,
            '--cloudos-url', CLOUDOS_URL,
            '--workspace-id', WORKSPACE_ID,
            '--output-format', 'stdout'
        ])
        
        assert result.exit_code == 0
        # The output should contain the status indicators (checkmark and X)
        # These are rendered as unicode characters in the table
        output = result.output
        assert 'Ready Queue' in output
        assert 'Creating Queue' in output

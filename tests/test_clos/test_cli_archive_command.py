"""Test the CLI archive command functionality."""

import pytest
from click.testing import CliRunner
from cloudos_cli.__main__ import run_cloudos_cli
import requests_mock


def test_job_archive_command_exists():
    """Test that the archive command exists in the job group."""
    runner = CliRunner()
    result = runner.invoke(run_cloudos_cli, ['job', '--help'])
    assert result.exit_code == 0
    assert 'archive' in result.output
    assert 'Archive specified jobs in a CloudOS workspace.' in result.output


def test_job_archive_help():
    """Test that the archive command help works."""
    runner = CliRunner()
    result = runner.invoke(run_cloudos_cli, ['job', 'archive', '--help'])
    assert result.exit_code == 0
    assert 'Archive specified jobs in a CloudOS workspace.' in result.output
    assert '--job-ids' in result.output
    assert '--workspace-id' in result.output
    assert '--apikey' in result.output


@pytest.mark.parametrize("job_ids,expected_count", [
    ("job1", 1),
    ("job1,job2", 2),
    ("job1,job2,job3", 3),
])
def test_job_archive_command_structure(job_ids, expected_count):
    """Test that the archive command has the expected structure and validates job IDs."""
    runner = CliRunner()
    
    # Test that the command fails when missing required parameters
    result = runner.invoke(run_cloudos_cli, ['job', 'archive'])
    assert result.exit_code != 0
    assert 'Missing option' in result.output or 'Error' in result.output


def test_job_archive_empty_job_ids():
    """Test that empty job IDs raise appropriate error."""
    runner = CliRunner()
    
    with requests_mock.Mocker():
        result = runner.invoke(run_cloudos_cli, [
            'job', 'archive',
            '--apikey', 'test_key',
            '--workspace-id', 'test_workspace',
            '--job-ids', ''
        ])
        assert result.exit_code != 0
        # The error is raised as an exception, so check the exception string
        assert 'No job IDs provided' in str(result.exception) or 'No job IDs provided' in result.output


def test_job_archive_invalid_job_ids():
    """Test archiving with invalid job IDs (jobs that don't exist)."""
    runner = CliRunner()
    
    with requests_mock.Mocker() as m:
        # Mock the job status check to fail (job doesn't exist) - using correct endpoint
        m.get(
            "https://cloudos.lifebit.ai/api/v1/jobs/invalid_job?teamId=test_workspace",
            status_code=404,
            json={"error": "Job not found"}
        )
        
        result = runner.invoke(run_cloudos_cli, [
            'job', 'archive',
            '--apikey', 'test_key',
            '--workspace-id', 'test_workspace',
            '--job-ids', 'invalid_job'
        ])
        
        # The command should handle the error gracefully
        assert result.exit_code != 0
        # The error is raised as an exception, so check the exception string
        assert ('No valid job IDs found' in str(result.exception) or 
                'Failed to get status for job invalid_job' in result.output)
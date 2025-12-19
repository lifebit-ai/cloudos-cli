"""Integration test for successful job unarchiving."""

import pytest
from click.testing import CliRunner
from cloudos_cli.__main__ import run_cloudos_cli
import requests_mock


def test_job_unarchive_successful_flow():
    """Test a successful job unarchiving flow end-to-end."""
    runner = CliRunner()
    
    with requests_mock.Mocker() as m:
        # Mock the job status check to succeed 
        m.get(
            "https://cloudos.lifebit.ai/api/v1/jobs/archived_job_123?teamId=workspace_123",
            status_code=200,
            json={"status": "completed", "id": "archived_job_123", "archived": {"status": True}}
        )
        
        # Mock the unarchive API call to succeed
        m.put(
            "https://cloudos.lifebit.ai/api/v1/jobs?teamId=workspace_123",
            status_code=200,
            json={"success": True}
        )
        
        result = runner.invoke(run_cloudos_cli, [
            'job', 'unarchive',
            '--apikey', 'test_key',
            '--workspace-id', 'workspace_123', 
            '--job-ids', 'archived_job_123'
        ])
        
        # Should succeed
        assert result.exit_code == 0
        assert "Job 'archived_job_123' unarchived successfully." in result.output
        assert "Unarchiving jobs..." in result.output


def test_job_unarchive_multiple_jobs_successful_flow():
    """Test successful unarchiving of multiple jobs."""
    runner = CliRunner()
    
    with requests_mock.Mocker() as m:
        # Mock job status checks for multiple jobs
        for job_id in ['job1', 'job2', 'job3']:
            m.get(
                f"https://cloudos.lifebit.ai/api/v1/jobs/{job_id}?teamId=workspace_123",
                status_code=200,
                json={"status": "completed", "id": job_id, "archived": {"status": True}}
            )
        
        # Mock the unarchive API call to succeed
        m.put(
            "https://cloudos.lifebit.ai/api/v1/jobs?teamId=workspace_123",
            status_code=200,
            json={"success": True}
        )
        
        result = runner.invoke(run_cloudos_cli, [
            'job', 'unarchive',
            '--apikey', 'test_key',
            '--workspace-id', 'workspace_123',
            '--job-ids', 'job1,job2,job3'
        ])
        
        # Should succeed
        assert result.exit_code == 0
        assert "3 jobs unarchived successfully: job1, job2, job3" in result.output
        assert "Unarchiving jobs..." in result.output


def test_job_unarchive_mixed_valid_invalid_jobs():
    """Test unarchiving when some jobs are valid and others are not."""
    runner = CliRunner()
    
    with requests_mock.Mocker() as m:
        # Mock job status check - valid job
        m.get(
            "https://cloudos.lifebit.ai/api/v1/jobs/valid_archived_job?teamId=workspace_123",
            status_code=200,
            json={"status": "completed", "id": "valid_archived_job", "archived": {"status": True}}
        )
        
        # Mock job status check - invalid job (404)
        m.get(
            "https://cloudos.lifebit.ai/api/v1/jobs/invalid_job?teamId=workspace_123",
            status_code=404,
            json={"error": "Job not found"}
        )
        
        # Mock the unarchive API call to succeed for valid jobs
        m.put(
            "https://cloudos.lifebit.ai/api/v1/jobs?teamId=workspace_123",
            status_code=200,
            json={"success": True}
        )
        
        result = runner.invoke(run_cloudos_cli, [
            'job', 'unarchive',
            '--apikey', 'test_key',
            '--workspace-id', 'workspace_123',
            '--job-ids', 'valid_archived_job,invalid_job'
        ])
        
        # Should succeed for the valid job
        assert result.exit_code == 0
        assert "Job 'valid_archived_job' unarchived successfully." in result.output
        assert "Failed to get status for job invalid_job" in result.output
        assert "Unarchiving jobs..." in result.output


def test_job_unarchive_verbose_output():
    """Test unarchiving with verbose output."""
    runner = CliRunner()
    
    with requests_mock.Mocker() as m:
        # Mock checking if job is archived (should return the job since it's archived)
        m.get(
            "https://cloudos.lifebit.ai/api/v2/jobs?teamId=workspace_123&archived.status=true&page=1&limit=1&id=archived_job",
            status_code=200,
            json={"jobs": [{"_id": "archived_job", "status": "completed"}], "pagination_metadata": {"Pagination-Count": 1}}
        )
        
        # Mock the unarchive API call to succeed
        m.put(
            "https://cloudos.lifebit.ai/api/v1/jobs?teamId=workspace_123",
            status_code=200,
            json={"success": True}
        )
        
        result = runner.invoke(run_cloudos_cli, [
            'job', 'unarchive',
            '--apikey', 'test_key',
            '--workspace-id', 'workspace_123',
            '--job-ids', 'archived_job',
            '--verbose'
        ])
        
        # Should succeed with verbose output
        assert result.exit_code == 0
        assert "Unarchiving jobs..." in result.output
        assert "Preparing objects" in result.output
        assert "Job archived_job found with status: completed" in result.output
        assert "Job 'archived_job' unarchived successfully." in result.output

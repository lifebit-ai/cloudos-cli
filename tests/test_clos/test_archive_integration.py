"""Integration test for successful job archiving."""

import pytest
from click.testing import CliRunner
from cloudos_cli.__main__ import run_cloudos_cli
import requests_mock


def test_job_archive_successful_flow():
    """Test a successful job archiving flow end-to-end."""
    runner = CliRunner()

    with requests_mock.Mocker() as m:
        # Mock checking if job is archived (should return empty for unarchived job)
        m.get(
            "https://cloudos.lifebit.ai/api/v2/jobs?teamId=workspace_123&archived.status=true&page=1&limit=1&id=valid_job_123",
            status_code=200,
            json={"jobs": [], "pagination_metadata": {"Pagination-Count": 0}}
        )
        
        # Mock checking if job exists in unarchived list (should return the job)
        m.get(
            "https://cloudos.lifebit.ai/api/v2/jobs?teamId=workspace_123&archived.status=false&page=1&limit=1&id=valid_job_123",
            status_code=200,
            json={"jobs": [{"_id": "valid_job_123", "status": "completed"}], "pagination_metadata": {"Pagination-Count": 1}}
        )
        
        # Mock the archive API call to succeed
        m.put(
            "https://cloudos.lifebit.ai/api/v1/jobs?teamId=workspace_123",
            status_code=200,
            json={"success": True}
        )
        
        result = runner.invoke(run_cloudos_cli, [
            'job', 'archive',
            '--apikey', 'test_key',
            '--workspace-id', 'workspace_123', 
            '--job-ids', 'valid_job_123'
        ])
        
        # Should succeed
        assert result.exit_code == 0
        assert "Job 'valid_job_123' archived successfully." in result.output
        assert "Archiving jobs..." in result.output


def test_job_archive_multiple_jobs_successful_flow():
    """Test successful archiving of multiple jobs."""
    runner = CliRunner()

    with requests_mock.Mocker() as m:
        # Mock job status checks for multiple jobs
        for job_id in ['job1', 'job2', 'job3']:
            # Mock checking if job is archived (should return empty for unarchived jobs)
            m.get(
                f"https://cloudos.lifebit.ai/api/v2/jobs?teamId=workspace_123&archived.status=true&page=1&limit=1&id={job_id}",
                status_code=200,
                json={"jobs": [], "pagination_metadata": {"Pagination-Count": 0}}
            )
            
            # Mock checking if job exists in unarchived list (should return the job)
            m.get(
                f"https://cloudos.lifebit.ai/api/v2/jobs?teamId=workspace_123&archived.status=false&page=1&limit=1&id={job_id}",
                status_code=200,
                json={"jobs": [{"_id": job_id, "status": "completed"}], "pagination_metadata": {"Pagination-Count": 1}}
            )
        
        # Mock the archive API call to succeed
        m.put(
            "https://cloudos.lifebit.ai/api/v1/jobs?teamId=workspace_123",
            status_code=200,
            json={"success": True}
        )
        
        result = runner.invoke(run_cloudos_cli, [
            'job', 'archive',
            '--apikey', 'test_key',
            '--workspace-id', 'workspace_123',
            '--job-ids', 'job1,job2,job3'
        ])
        
        # Should succeed
        assert result.exit_code == 0
        assert "3 jobs archived successfully: job1, job2, job3" in result.output
        assert "Archiving jobs..." in result.output


def test_job_archive_mixed_valid_invalid_jobs():
    """Test archiving when some jobs are valid and others are not."""
    runner = CliRunner()

    with requests_mock.Mocker() as m:
        # Mock job status check - valid job (not archived)
        m.get(
            "https://cloudos.lifebit.ai/api/v2/jobs?teamId=workspace_123&archived.status=true&page=1&limit=1&id=valid_job",
            status_code=200,
            json={"jobs": [], "pagination_metadata": {"Pagination-Count": 0}}
        )
        m.get(
            "https://cloudos.lifebit.ai/api/v2/jobs?teamId=workspace_123&archived.status=false&page=1&limit=1&id=valid_job",
            status_code=200,
            json={"jobs": [{"_id": "valid_job", "status": "completed"}], "pagination_metadata": {"Pagination-Count": 1}}
        )
        
        # Mock job status check - invalid job (not in either list)
        m.get(
            "https://cloudos.lifebit.ai/api/v2/jobs?teamId=workspace_123&archived.status=true&page=1&limit=1&id=invalid_job",
            status_code=200,
            json={"jobs": [], "pagination_metadata": {"Pagination-Count": 0}}
        )
        m.get(
            "https://cloudos.lifebit.ai/api/v2/jobs?teamId=workspace_123&archived.status=false&page=1&limit=1&id=invalid_job",
            status_code=200,
            json={"jobs": [], "pagination_metadata": {"Pagination-Count": 0}}
        )
        
        # Mock the archive API call to succeed for valid jobs
        m.put(
            "https://cloudos.lifebit.ai/api/v1/jobs?teamId=workspace_123",
            status_code=200,
            json={"success": True}
        )
        
        result = runner.invoke(run_cloudos_cli, [
            'job', 'archive',
            '--apikey', 'test_key',
            '--workspace-id', 'workspace_123',
            '--job-ids', 'valid_job,invalid_job'
        ])
        
        # Command should exit gracefully when encountering invalid job
        assert result.exit_code == 0
        assert "Failed to get status for job invalid_job" in result.output
        assert "Archiving jobs..." in result.output
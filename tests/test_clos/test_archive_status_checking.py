"""Test archive status checking functionality."""

import pytest
from click.testing import CliRunner
from cloudos_cli.__main__ import run_cloudos_cli
import requests_mock


def test_archive_already_archived_job():
    """Test archiving a job that is already archived."""
    runner = CliRunner()
    
    with requests_mock.Mocker() as m:
        # Mock checking if job is archived (should return the job since it's archived)
        m.get(
            "https://cloudos.lifebit.ai/api/v2/jobs?teamId=workspace_123&archived.status=true&page=1&limit=1&id=already_archived_job",
            status_code=200,
            json={"jobs": [{"_id": "already_archived_job", "status": "completed"}], "pagination_metadata": {"Pagination-Count": 1}}
        )
        
        result = runner.invoke(run_cloudos_cli, [
            'job', 'archive',
            '--apikey', 'test_key',
            '--workspace-id', 'workspace_123',
            '--job-ids', 'already_archived_job'
        ])
        
        # Should succeed but indicate no action needed
        assert result.exit_code == 0
        assert "is already archived. No action needed." in result.output
        assert "archived successfully" not in result.output
        # Ensure the message appears only once
        assert result.output.count("already archived") == 1


def test_unarchive_already_unarchived_job():
    """Test unarchiving a job that is already unarchived."""
    runner = CliRunner()
    
    with requests_mock.Mocker() as m:
        # Mock checking if job is archived (should return empty for unarchived job)
        m.get(
            "https://cloudos.lifebit.ai/api/v2/jobs?teamId=workspace_123&archived.status=true&page=1&limit=1&id=not_archived_job",
            status_code=200,
            json={"jobs": [], "pagination_metadata": {"Pagination-Count": 0}}
        )
        
        # Mock checking if job exists in unarchived list (should return the job)
        m.get(
            "https://cloudos.lifebit.ai/api/v2/jobs?teamId=workspace_123&archived.status=false&page=1&limit=1&id=not_archived_job",
            status_code=200,
            json={"jobs": [{"_id": "not_archived_job", "status": "completed"}], "pagination_metadata": {"Pagination-Count": 1}}
        )
        
        result = runner.invoke(run_cloudos_cli, [
            'job', 'unarchive',
            '--apikey', 'test_key',
            '--workspace-id', 'workspace_123',
            '--job-ids', 'not_archived_job'
        ])
        
        # Should succeed but indicate no action needed
        assert result.exit_code == 0
        assert "is already unarchived. No action needed." in result.output
        assert "unarchived successfully" not in result.output
        # Ensure the message appears only once
        assert result.output.count("already unarchived") == 1


def test_archive_mixed_status_jobs():
    """Test archiving a mix of archived and unarchived jobs."""
    runner = CliRunner()
    
    with requests_mock.Mocker() as m:
        # Mock job status - one archived, one not archived
        m.get(
            "https://cloudos.lifebit.ai/api/v2/jobs?teamId=workspace_123&archived.status=true&page=1&limit=1&id=already_archived",
            status_code=200,
            json={"jobs": [{"_id": "already_archived", "status": "completed"}], "pagination_metadata": {"Pagination-Count": 1}}
        )
        
        m.get(
            "https://cloudos.lifebit.ai/api/v2/jobs?teamId=workspace_123&archived.status=true&page=1&limit=1&id=not_archived",
            status_code=200,
            json={"jobs": [], "pagination_metadata": {"Pagination-Count": 0}}
        )
        m.get(
            "https://cloudos.lifebit.ai/api/v2/jobs?teamId=workspace_123&archived.status=false&page=1&limit=1&id=not_archived",
            status_code=200,
            json={"jobs": [{"_id": "not_archived", "status": "completed"}], "pagination_metadata": {"Pagination-Count": 1}}
        )
        
        # Mock the archive API call for the unarchived job
        m.put(
            "https://cloudos.lifebit.ai/api/v1/jobs?teamId=workspace_123",
            status_code=200,
            json={"success": True}
        )
        
        result = runner.invoke(run_cloudos_cli, [
            'job', 'archive',
            '--apikey', 'test_key',
            '--workspace-id', 'workspace_123',
            '--job-ids', 'already_archived,not_archived'
        ])
        
        # Should succeed and handle both scenarios
        assert result.exit_code == 0
        assert "Job 'not_archived' archived successfully" in result.output
        assert "Job 'already_archived' was already archived" in result.output


def test_unarchive_mixed_status_jobs():
    """Test unarchiving a mix of archived and unarchived jobs."""
    runner = CliRunner()
    
    with requests_mock.Mocker() as m:
        # Mock job status - one archived, one not archived
        m.get(
            "https://cloudos.lifebit.ai/api/v2/jobs?teamId=workspace_123&archived.status=true&page=1&limit=1&id=archived_job",
            status_code=200,
            json={"jobs": [{"_id": "archived_job", "status": "completed"}], "pagination_metadata": {"Pagination-Count": 1}}
        )
        
        m.get(
            "https://cloudos.lifebit.ai/api/v2/jobs?teamId=workspace_123&archived.status=true&page=1&limit=1&id=not_archived",
            status_code=200,
            json={"jobs": [], "pagination_metadata": {"Pagination-Count": 0}}
        )
        m.get(
            "https://cloudos.lifebit.ai/api/v2/jobs?teamId=workspace_123&archived.status=false&page=1&limit=1&id=not_archived",
            status_code=200,
            json={"jobs": [{"_id": "not_archived", "status": "completed"}], "pagination_metadata": {"Pagination-Count": 1}}
        )
        
        # Mock the unarchive API call for the archived job
        m.put(
            "https://cloudos.lifebit.ai/api/v1/jobs?teamId=workspace_123",
            status_code=200,
            json={"success": True}
        )
        
        result = runner.invoke(run_cloudos_cli, [
            'job', 'unarchive',
            '--apikey', 'test_key',
            '--workspace-id', 'workspace_123',
            '--job-ids', 'archived_job,not_archived'
        ])
        
        # Should succeed and handle both scenarios
        assert result.exit_code == 0
        assert "Job 'archived_job' unarchived successfully" in result.output
        assert "Job 'not_archived' was already unarchived" in result.output


def test_archive_verbose_already_archived():
    """Test archiving with verbose output for already archived job."""
    runner = CliRunner()
    
    with requests_mock.Mocker() as m:
        # Mock checking if job is archived (should return the job since it's archived)
        m.get(
            "https://cloudos.lifebit.ai/api/v2/jobs?teamId=workspace_123&archived.status=true&page=1&limit=1&id=already_archived",
            status_code=200,
            json={"jobs": [{"_id": "already_archived", "status": "completed"}], "pagination_metadata": {"Pagination-Count": 1}}
        )
        
        result = runner.invoke(run_cloudos_cli, [
            'job', 'archive',
            '--apikey', 'test_key',
            '--workspace-id', 'workspace_123',
            '--job-ids', 'already_archived',
            '--verbose'
        ])
        
        # Should show verbose information about already archived status
        assert result.exit_code == 0
        assert "Job already_archived is already archived" in result.output
        assert "No action needed" in result.output
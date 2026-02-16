"""Test the archive_jobs functionality."""

import pytest
import json
import requests_mock
from cloudos_cli.clos import Cloudos
from cloudos_cli.utils.errors import BadRequestException


class TestArchiveJobs:
    """Test archive_jobs method in Cloudos class."""

    def test_archive_jobs_correct_response(self):
        """Test successful archive of jobs."""
        cloudos_url = "https://cloudos.lifebit.ai"
        apikey = "test_apikey"
        workspace_id = "workspace123"
        job_ids = ["69413101b07d5f5bb46891b4", "another_job_id"]

        with requests_mock.Mocker() as m:
            # Mock the PUT request to the archive endpoint
            m.put(
                f"{cloudos_url}/api/v1/jobs?teamId={workspace_id}",
                status_code=200,
                json={"success": True}
            )

            cl = Cloudos(cloudos_url, apikey, None)
            response = cl.archive_jobs(job_ids, workspace_id)

            assert response.status_code == 200
            # Check that the request was made with correct data
            request_data = json.loads(m.last_request.text)
            assert request_data["jobIds"] == job_ids
            assert request_data["update"]["archived"]["status"] is True
            assert "archivalTimestamp" in request_data["update"]["archived"]
            # Verify timestamp is ISO format string
            timestamp = request_data["update"]["archived"]["archivalTimestamp"]
            assert isinstance(timestamp, str)
            assert timestamp.endswith("Z")

    def test_archive_jobs_bad_request_response(self):
        """Test archive jobs with bad request response."""
        cloudos_url = "https://cloudos.lifebit.ai"
        apikey = "test_apikey"
        workspace_id = "workspace123"
        job_ids = ["invalid_job_id"]

        with requests_mock.Mocker() as m:
            # Mock a 400 bad request response
            m.put(
                f"{cloudos_url}/api/v1/jobs?teamId={workspace_id}",
                status_code=400,
                json={"error": "Invalid job ID"}
            )

            cl = Cloudos(cloudos_url, apikey, None)
            with pytest.raises(BadRequestException):
                cl.archive_jobs(job_ids, workspace_id)

    def test_archive_jobs_with_ssl_verification(self):
        """Test archive jobs with SSL verification disabled."""
        cloudos_url = "https://cloudos.lifebit.ai"
        apikey = "test_apikey"
        workspace_id = "workspace123"
        job_ids = ["69413101b07d5f5bb46891b4"]

        with requests_mock.Mocker() as m:
            m.put(
                f"{cloudos_url}/api/v1/jobs?teamId={workspace_id}",
                status_code=200,
                json={"success": True}
            )

            cl = Cloudos(cloudos_url, apikey, None)
            response = cl.archive_jobs(job_ids, workspace_id, verify=False)

            assert response.status_code == 200

    def test_archive_jobs_single_job(self):
        """Test archiving a single job."""
        cloudos_url = "https://cloudos.lifebit.ai"
        apikey = "test_apikey" 
        workspace_id = "workspace123"
        job_ids = ["69413101b07d5f5bb46891b4"]

        with requests_mock.Mocker() as m:
            m.put(
                f"{cloudos_url}/api/v1/jobs?teamId={workspace_id}",
                status_code=200,
                json={"success": True}
            )

            cl = Cloudos(cloudos_url, apikey, None)
            response = cl.archive_jobs(job_ids, workspace_id)

            assert response.status_code == 200
            request_data = json.loads(m.last_request.text)
            assert len(request_data["jobIds"]) == 1
            assert request_data["jobIds"][0] == job_ids[0]

    def test_archive_jobs_multiple_jobs(self):
        """Test archiving multiple jobs."""
        cloudos_url = "https://cloudos.lifebit.ai"
        apikey = "test_apikey"
        workspace_id = "workspace123" 
        job_ids = ["job1", "job2", "job3"]

        with requests_mock.Mocker() as m:
            m.put(
                f"{cloudos_url}/api/v1/jobs?teamId={workspace_id}",
                status_code=200,
                json={"success": True}
            )

            cl = Cloudos(cloudos_url, apikey, None)
            response = cl.archive_jobs(job_ids, workspace_id)

            assert response.status_code == 200
            request_data = json.loads(m.last_request.text)
            assert len(request_data["jobIds"]) == 3
            assert set(request_data["jobIds"]) == set(job_ids)
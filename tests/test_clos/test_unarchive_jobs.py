"""Test the unarchive_jobs method in the Cloudos class."""

import pytest
import requests_mock
from cloudos_cli.clos import Cloudos
from cloudos_cli.utils.errors import BadRequestException


class TestUnarchiveJobs:
    """Test cases for the unarchive_jobs method."""

    def test_unarchive_jobs_correct_response(self):
        """Test unarchiving jobs with a successful response."""
        with requests_mock.Mocker() as m:
            m.put(
                "https://cloudos.lifebit.ai/api/v1/jobs?teamId=test_workspace",
                status_code=200,
                json={"success": True}
            )

            cl = Cloudos("https://cloudos.lifebit.ai", "test_apikey", None)
            job_ids = ["job1", "job2"]
            response = cl.unarchive_jobs(job_ids, "test_workspace")

            assert response.status_code == 200
            assert m.called
            assert m.call_count == 1

            # Verify the request payload
            request = m.request_history[0]
            import json
            payload = json.loads(request.body)
            assert payload["jobIds"] == job_ids
            assert payload["update"]["archived"]["status"] is False
            assert "archivalTimestamp" in payload["update"]["archived"]

    def test_unarchive_jobs_bad_request_response(self):
        """Test unarchiving jobs with a bad request response."""
        with requests_mock.Mocker() as m:
            m.put(
                "https://cloudos.lifebit.ai/api/v1/jobs?teamId=test_workspace",
                status_code=400,
                json={"error": "Bad request"}
            )

            cl = Cloudos("https://cloudos.lifebit.ai", "test_apikey", None)
            job_ids = ["invalid_job"]

            with pytest.raises(BadRequestException):
                cl.unarchive_jobs(job_ids, "test_workspace")

    def test_unarchive_jobs_with_ssl_verification(self):
        """Test unarchiving jobs with SSL verification enabled."""
        with requests_mock.Mocker() as m:
            m.put(
                "https://cloudos.lifebit.ai/api/v1/jobs?teamId=test_workspace",
                status_code=200,
                json={"success": True}
            )

            cl = Cloudos("https://cloudos.lifebit.ai", "test_apikey", None)
            job_ids = ["job1"]
            response = cl.unarchive_jobs(job_ids, "test_workspace", verify=True)

            assert response.status_code == 200
            assert m.called

    def test_unarchive_jobs_single_job(self):
        """Test unarchiving a single job."""
        with requests_mock.Mocker() as m:
            m.put(
                "https://cloudos.lifebit.ai/api/v1/jobs?teamId=test_workspace",
                status_code=200,
                json={"success": True}
            )

            cl = Cloudos("https://cloudos.lifebit.ai", "test_apikey", None)
            job_ids = ["single_job"]
            response = cl.unarchive_jobs(job_ids, "test_workspace")

            assert response.status_code == 200

            # Verify the request payload
            request = m.request_history[0]
            import json
            payload = json.loads(request.body)
            assert len(payload["jobIds"]) == 1
            assert payload["jobIds"][0] == "single_job"
            assert payload["update"]["archived"]["status"] is False

    def test_unarchive_jobs_multiple_jobs(self):
        """Test unarchiving multiple jobs."""
        with requests_mock.Mocker() as m:
            m.put(
                "https://cloudos.lifebit.ai/api/v1/jobs?teamId=test_workspace",
                status_code=200,
                json={"success": True}
            )

            cl = Cloudos("https://cloudos.lifebit.ai", "test_apikey", None)
            job_ids = ["job1", "job2", "job3"]
            response = cl.unarchive_jobs(job_ids, "test_workspace")

            assert response.status_code == 200

            # Verify the request payload
            request = m.request_history[0]
            import json
            payload = json.loads(request.body)
            assert len(payload["jobIds"]) == 3
            assert payload["jobIds"] == job_ids
            assert payload["update"]["archived"]["status"] is False

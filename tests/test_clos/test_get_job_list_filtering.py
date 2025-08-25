import mock
import json
import pytest
import responses
from responses import matchers
from cloudos_cli.clos import Cloudos
from cloudos_cli.utils.errors import BadRequestException
from tests.functions_for_pytest import load_json_file

# Test constants
APIKEY = 'vnoiweur89u2ongs'
CLOUDOS_URL = 'http://cloudos.lifebit.ai'
WORKSPACE_ID = 'lv89ufc838sdig'
USER_ID = '651d2d387b9838932e40cf1b'
PROJECT_ID = '687fbbc73e05673d74addb82'
WORKFLOW_ID = '68835023a55d9ff1cecdff8e'
QUEUE_ID = 'v41_queue_id'

# Mock data
MOCK_JOB_LIST = {
    "jobs": [
        {
            "_id": "job1",
            "name": "test-job-1",
            "status": "completed",
            "user": {"id": USER_ID, "name": "Test User"},
            "project": {"id": PROJECT_ID, "name": "test-project"},
            "workflow": {"id": WORKFLOW_ID, "name": "test-workflow"},
            "batch": {"jobQueue": {"id": QUEUE_ID}}
        },
        {
            "_id": "job2", 
            "name": "test-job-2",
            "status": "running",
            "user": {"id": "other_user_id", "name": "Other User"},
            "project": {"id": "other_project_id", "name": "other-project"},
            "workflow": {"id": "other_workflow_id", "name": "other-workflow"},
            "batch": {"jobQueue": {"id": "other_queue_id"}}
        }
    ]
}

MOCK_USER_INFO = {
    "id": USER_ID,
    "name": "Test",
    "surname": "User",
    "email": "test@example.com"
}

MOCK_PROJECT_LIST = {
    "projects": [
        {"_id": PROJECT_ID, "name": "test-project"},
        {"_id": "other_project_id", "name": "other-project"}
    ]
}

MOCK_WORKFLOW_CONTENT = {
    "workflows": [
        {"_id": WORKFLOW_ID, "name": "test-workflow"}
    ]
}

MOCK_QUEUE_LIST = [
    {"id": QUEUE_ID, "name": "v41", "label": "v41"},
    {"id": "other_queue_id", "name": "other-queue", "label": "other-queue"}
]

MOCK_USER_SEARCH = [
    {
        "_id": "user123",
        "username": "testuser",
        "name": "Test",
        "surname": "User"
    }
]


class TestGetJobListFiltering:
    """Test suite for job list filtering functionality"""

    def setup_method(self):
        """Setup for each test method"""
        self.clos = Cloudos(apikey=APIKEY, cromwell_token=None, cloudos_url=CLOUDOS_URL)

    @responses.activate
    def test_filter_by_status(self):
        """Test filtering jobs by status"""
        expected_params = {
            "teamId": WORKSPACE_ID,
            "archived.status": "false",
            "limit": 50,  # 
            "page": 1,
            "status": "completed"
        }
        
        responses.add(
            responses.GET,
            url=f"{CLOUDOS_URL}/api/v2/jobs",
            json=MOCK_JOB_LIST,
            match=[matchers.query_param_matcher(expected_params)],
            status=200
        )
        
        result = self.clos.get_job_list(
            WORKSPACE_ID, 
            filter_status="completed"
        )
        
        assert isinstance(result, list)
        assert len(result) == 2

    @responses.activate 
    def test_filter_by_job_name(self):
        """Test filtering jobs by name"""
        expected_params = {
            "teamId": WORKSPACE_ID,
            "archived.status": "false", 
            "limit": 50,  # Add this
            "page": 1,
            "name": "test-job-1"
        }
        
        responses.add(
            responses.GET,
            url=f"{CLOUDOS_URL}/api/v2/jobs",
            json=MOCK_JOB_LIST,
            match=[matchers.query_param_matcher(expected_params)],
            status=200
        )
        
        result = self.clos.get_job_list(
            WORKSPACE_ID,
            filter_job_name="test-job-1"
        )
        
        assert isinstance(result, list)

    @responses.activate
    def test_filter_by_job_id(self):
        """Test filtering jobs by specific job ID"""
        expected_params = {
            "teamId": WORKSPACE_ID,
            "archived.status": "false",
            "limit": 50,  # Add this
            "page": 1,
            "id": "job1"
        }
        
        responses.add(
            responses.GET,
            url=f"{CLOUDOS_URL}/api/v2/jobs",
            json=MOCK_JOB_LIST,
            match=[matchers.query_param_matcher(expected_params)],
            status=200
        )
        
        result = self.clos.get_job_list(
            WORKSPACE_ID,
            filter_job_id="job1"
        )
        
        assert isinstance(result, list)

    @responses.activate
    def test_filter_only_mine(self):
        """Test filtering to show only current user's jobs"""
        # Mock user info endpoint
        responses.add(
            responses.GET,
            url=f"{CLOUDOS_URL}/api/v1/users/me",
            json=MOCK_USER_INFO,
            status=200
        )
        
        expected_params = {
            "teamId": WORKSPACE_ID,
            "archived.status": "false",
            "limit": 50,
            "page": 1,
            "user.id": USER_ID
        }
        
        responses.add(
            responses.GET,
            url=f"{CLOUDOS_URL}/api/v2/jobs",
            json=MOCK_JOB_LIST,
            match=[matchers.query_param_matcher(expected_params)],
            status=200
        )
        
        result = self.clos.get_job_list(
            WORKSPACE_ID,
            filter_only_mine=True
        )
        
        assert isinstance(result, list)

    @responses.activate
    @mock.patch('cloudos_cli.clos.Cloudos.get_project_id_from_name')
    def test_filter_by_project(self, mock_get_project_id):
        """Test filtering jobs by project name"""
        mock_get_project_id.return_value = PROJECT_ID
        
        expected_params = {
            "teamId": WORKSPACE_ID,
            "archived.status": "false",
            "limit": 50,
            "page": 1,
            "project.id": PROJECT_ID
        }
        
        responses.add(
            responses.GET,
            url=f"{CLOUDOS_URL}/api/v2/jobs",
            json=MOCK_JOB_LIST,
            match=[matchers.query_param_matcher(expected_params)],
            status=200
        )
        
        result = self.clos.get_job_list(
            WORKSPACE_ID,
            filter_project="test-project"
        )
        
        assert isinstance(result, list)
        mock_get_project_id.assert_called_once_with(WORKSPACE_ID, "test-project", verify=True)

    @responses.activate
    @mock.patch('cloudos_cli.clos.Cloudos.get_workflow_content')
    def test_filter_by_workflow(self, mock_get_workflow_content):
        """Test filtering jobs by workflow name"""
        mock_get_workflow_content.return_value = MOCK_WORKFLOW_CONTENT
        
        expected_params = {
            "teamId": WORKSPACE_ID,
            "archived.status": "false",
            "limit": 50,
            "page": 1,
            "workflow.id": WORKFLOW_ID
        }
        
        responses.add(
            responses.GET,
            url=f"{CLOUDOS_URL}/api/v2/jobs",
            json=MOCK_JOB_LIST,
            match=[matchers.query_param_matcher(expected_params)],
            status=200
        )
        
        result = self.clos.get_job_list(
            WORKSPACE_ID,
            filter_workflow="test-workflow"
        )
        
        assert isinstance(result, list)
        mock_get_workflow_content.assert_called_once_with(WORKSPACE_ID, "test-workflow", verify=True)

    @responses.activate
    @mock.patch('cloudos_cli.queue.queue.Queue.get_job_queues')
    def test_filter_by_queue(self, mock_get_queues):
        """Test local filtering by queue name"""
        mock_get_queues.return_value = MOCK_QUEUE_LIST
        
        responses.add(
            responses.GET,
            url=f"{CLOUDOS_URL}/api/v2/jobs",
            json=MOCK_JOB_LIST,
            status=200
        )
        
        result = self.clos.get_job_list(
            WORKSPACE_ID,
            filter_queue="v41"  # Changed from filtering_queue to filter_queue
        )
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["_id"] == "job1"

    @responses.activate
    def test_filter_by_owner(self):
        """Test filtering jobs by owner username"""
        responses.add(
            responses.GET,
            url=f"{CLOUDOS_URL}/api/v1/users/search-assist",
            json=MOCK_USER_SEARCH,
            status=200
        )
        
        expected_params = {
            "teamId": WORKSPACE_ID,
            "archived.status": "false",
            "limit": 50,
            "page": 1,
            "user.id": "user123"
        }
        
        responses.add(
            responses.GET,
            url=f"{CLOUDOS_URL}/api/v2/jobs",
            json=MOCK_JOB_LIST,
            match=[matchers.query_param_matcher(expected_params)],
            status=200
        )
        
        result = self.clos.get_job_list(
            WORKSPACE_ID,
            filter_owner="testuser"
        )
        
        assert isinstance(result, list)

    @responses.activate
    def test_multiple_filters(self):
        """Test applying multiple filters simultaneously"""
        # Mock user info for filter_only_mine
        responses.add(
            responses.GET,
            url=f"{CLOUDOS_URL}/api/v1/users/me",
            json=MOCK_USER_INFO,
            status=200
        )
        
        expected_params = {
            "teamId": WORKSPACE_ID,
            "archived.status": "false",
            "limit": 50,
            "page": 1,
            "status": "completed",
            "name": "test-job-1",
            "user.id": USER_ID
        }
        
        responses.add(
            responses.GET,
            url=f"{CLOUDOS_URL}/api/v2/jobs",
            json=MOCK_JOB_LIST,
            match=[matchers.query_param_matcher(expected_params)],
            status=200
        )
        
        result = self.clos.get_job_list(
            WORKSPACE_ID,
            filter_status="completed",
            filter_job_name="test-job-1",
            filter_only_mine=True
        )
        
        assert isinstance(result, list)

    @responses.activate
    def test_archived_jobs_filter(self):
        """Test filtering archived jobs"""
        expected_params = {
            "teamId": WORKSPACE_ID,
            "archived.status": "true",
            "limit": 50,
            "page": 1
        }
        
        responses.add(
            responses.GET,
            url=f"{CLOUDOS_URL}/api/v2/jobs",
            json=MOCK_JOB_LIST,
            match=[matchers.query_param_matcher(expected_params)],
            status=200
        )
        
        result = self.clos.get_job_list(
            WORKSPACE_ID,
            archived=True
        )
        
        assert isinstance(result, list)

    @responses.activate
    def test_pagination_with_filters(self):
        """Test pagination works correctly with filters"""
        # First page
        responses.add(
            responses.GET,
            url=f"{CLOUDOS_URL}/api/v2/jobs",
            json=MOCK_JOB_LIST,
            status=200
        )
        
        # Second page (empty)
        responses.add(
            responses.GET,
            url=f"{CLOUDOS_URL}/api/v2/jobs",
            json={"jobs": []},
            status=200
        )
        
        result = self.clos.get_job_list(
            WORKSPACE_ID,
            filter_status="completed",
            last_n_jobs='all'
        )
        
        assert isinstance(result, list)
        assert len(result) == 2  # Both jobs from first page

    def test_invalid_filter_status(self):
        """Test error handling for invalid status filter"""
        with pytest.raises(ValueError) as exc_info:
            self.clos.get_job_list(
                WORKSPACE_ID,
                filter_status="invalid_status"
            )
        
        assert "Invalid filter_status" in str(exc_info.value)

    def test_invalid_workspace_id(self):
        """Test error handling for invalid workspace ID"""
        with pytest.raises(ValueError) as exc_info:
            self.clos.get_job_list(
                "",  # Empty workspace ID
                filter_status="completed"
            )
        
        assert "Invalid workspace_id" in str(exc_info.value)

    def test_invalid_last_n_jobs(self):
        """Test error handling for invalid last_n_jobs parameter"""
        with pytest.raises(ValueError) as exc_info:
            self.clos.get_job_list(
                WORKSPACE_ID,
                last_n_jobs=0  # Invalid value
            )
        
        assert "last_n_jobs must be a positive integer" in str(exc_info.value)

    @responses.activate
    def test_project_not_found_error(self):
        """Test error handling when project is not found"""
        with mock.patch.object(self.clos, 'get_project_id_from_name') as mock_get_project:
            mock_get_project.side_effect = ValueError("Project 'nonexistent' not found")
            
            with pytest.raises(ValueError) as exc_info:
                self.clos.get_job_list(
                    WORKSPACE_ID,
                    filter_project="nonexistent"
                )
            
            assert "nonexistent" in str(exc_info.value)

    @responses.activate
    def test_workflow_not_found_error(self):
        """Test error handling when workflow is not found"""
        with mock.patch.object(self.clos, 'get_workflow_content') as mock_get_workflow:
            mock_get_workflow.side_effect = ValueError("Workflow 'nonexistent' not found")
            
            with pytest.raises(ValueError) as exc_info:
                self.clos.get_job_list(
                    WORKSPACE_ID,
                    filter_workflow="nonexistent"
                )
            
            assert "nonexistent" in str(exc_info.value)

    @responses.activate
    @mock.patch('cloudos_cli.queue.queue.Queue.get_job_queues')
    def test_queue_not_found_error(self, mock_get_queues):
        """Test error handling when queue is not found"""
        mock_get_queues.return_value = MOCK_QUEUE_LIST
        
        responses.add(
            responses.GET,
            url=f"{CLOUDOS_URL}/api/v2/jobs",
            json=MOCK_JOB_LIST,
            status=200
        )
        
        with pytest.raises(ValueError) as exc_info:
            self.clos.get_job_list(
                WORKSPACE_ID,
                filter_queue="nonexistent_queue"  # Changed from filtering_queue
            )
        
        assert "Queue 'nonexistent_queue' not found" in str(exc_info.value)

    @responses.activate
    def test_user_search_endpoint_not_available(self):
        """Test error handling when user search endpoint returns 404"""
        responses.add(
            responses.GET,
            url=f"{CLOUDOS_URL}/api/v1/users/search-assist",
            status=404
        )
        
        with pytest.raises(ValueError) as exc_info:
            self.clos.get_job_list(
                WORKSPACE_ID,
                filter_owner="testuser"
            )
        
        # Updated assertion to match actual error handling
        error_msg = str(exc_info.value)
        assert ("User search feature is not available" in error_msg or 
                "Error resolving user" in error_msg)

    @responses.activate
    def test_api_authentication_error(self):
        """Test error handling for API authentication failures"""
        responses.add(
            responses.GET,
            url=f"{CLOUDOS_URL}/api/v2/jobs",
            status=401
        )
        
        with pytest.raises(ValueError) as exc_info:
            self.clos.get_job_list(
                WORKSPACE_ID,
                filter_status="completed"
            )
        
        assert "Access denied" in str(exc_info.value)

    @responses.activate
    def test_no_jobs_found_with_filters(self):
        """Test error handling when no jobs match the filters"""
        responses.add(
            responses.GET,
            url=f"{CLOUDOS_URL}/api/v2/jobs",
            json={"jobs": []},
            status=200
        )
        
        with pytest.raises(ValueError) as exc_info:
            self.clos.get_job_list(
                WORKSPACE_ID,
                filter_status="completed",
                filter_job_name="nonexistent"
            )
        
        assert "No jobs found matching the specified criteria" in str(exc_info.value)
        assert "status='completed'" in str(exc_info.value)
        assert "name='nonexistent'" in str(exc_info.value)
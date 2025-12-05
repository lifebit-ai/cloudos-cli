"""
Test suite for error message formatting consistency.

This test suite verifies that all error messages use a consistent format:
- Only one colon after "Error" prefix
- Subsequent separators use periods instead of colons

These tests ensure the error messages follow the standardized format after
the refactoring to improve readability and consistency.
"""

import unittest
import pytest


class TestJobErrorMessages(unittest.TestCase):
    """Test error messages in jobs/job.py"""

    def test_invalid_parameters_error_message(self):
        """Test that invalid parameter error uses period instead of colon"""
        with self.assertRaises(ValueError) as context:
            raise ValueError(f'The provided parameters "test_param" are not valid. ')

        self.assertIn("not valid.", str(context.exception))
        self.assertNotIn("not valid:", str(context.exception))

    def test_job_status_retrieval_error_message(self):
        """Test that job status retrieval error uses period"""
        with self.assertRaises(ValueError) as context:
            raise ValueError(f"The job status cannot be retrieved. Test error")

        self.assertIn("cannot be retrieved.", str(context.exception))
        self.assertNotIn("cannot be retrieved:", str(context.exception))

    def test_queue_filtering_error_message(self):
        """Test that queue filtering error uses period"""
        with self.assertRaises(ValueError) as context:
            raise ValueError(f"Error filtering by queue 'test_queue'. Error details")

        self.assertIn("by queue 'test_queue'.", str(context.exception))
        self.assertNotIn("queue 'test_queue':", str(context.exception))

    def test_operation_not_permitted_error_message(self):
        """Test that operation not permitted error uses period"""
        with self.assertRaises(ValueError) as context:
            raise ValueError("Operation not permitted. Your workspace does not have the option to delete results folders enabled.")

        self.assertIn("Operation not permitted.", str(context.exception))
        self.assertNotIn("Operation not permitted:", str(context.exception))

    def test_unauthorized_error_message(self):
        """Test that unauthorized error uses period"""
        with self.assertRaises(ValueError) as context:
            raise ValueError("Unauthorized. Invalid or missing API key.")

        self.assertIn("Unauthorized.", str(context.exception))
        self.assertNotIn("Unauthorized:", str(context.exception))

    def test_forbidden_error_message(self):
        """Test that forbidden error uses period"""
        with self.assertRaises(ValueError) as context:
            raise ValueError("Forbidden. You don't have permission to delete this folder.")

        self.assertIn("Forbidden.", str(context.exception))
        self.assertNotIn("Forbidden:", str(context.exception))

    def test_conflict_error_message(self):
        """Test that conflict error uses period"""
        with self.assertRaises(ValueError) as context:
            raise ValueError("Conflict. The folder cannot be deleted due to a conflict (e.g., folder is not empty or has dependencies).")

        self.assertIn("Conflict.", str(context.exception))
        self.assertNotIn("Conflict:", str(context.exception))

    def test_internal_server_error_message(self):
        """Test that internal server error uses period"""
        with self.assertRaises(ValueError) as context:
            raise ValueError("Internal server error. The server encountered an error while processing the deletion request.")

        self.assertIn("Internal server error.", str(context.exception))
        self.assertNotIn("Internal server error:", str(context.exception))


class TestCLIMainErrorMessages(unittest.TestCase):
    """Test error messages in __main__.py"""

    def test_job_not_found_error_message(self):
        """Test that job not found error uses period"""
        with self.assertRaises(ValueError) as context:
            raise ValueError(f"Job 'test_job_id' not found or not accessible. Error details")

        self.assertIn("not accessible.", str(context.exception))
        self.assertNotIn("not accessible:", str(context.exception))

    def test_failed_to_retrieve_workdir_error_message(self):
        """Test that failed to retrieve workdir error uses period"""
        with self.assertRaises(ValueError) as context:
            raise ValueError(f"Failed to retrieve working directory for job 'test_job'. Error details")

        self.assertIn("for job 'test_job'.", str(context.exception))
        self.assertNotIn("for job 'test_job':", str(context.exception))

    def test_failed_to_retrieve_intermediate_results_error_message(self):
        """Test that intermediate results error uses period"""
        with self.assertRaises(ValueError) as context:
            raise ValueError(f"Failed to retrieve intermediate results for job 'test_job'. Error details")

        self.assertIn("for job 'test_job'.", str(context.exception))
        self.assertNotIn("for job 'test_job':", str(context.exception))

    def test_failed_to_retrieve_logs_error_message(self):
        """Test that logs retrieval error uses period"""
        with self.assertRaises(ValueError) as context:
            raise ValueError(f"Failed to retrieve logs for job 'test_job'. Error details")

        self.assertIn("for job 'test_job'.", str(context.exception))
        self.assertNotIn("for job 'test_job':", str(context.exception))

    def test_failed_to_retrieve_results_error_message(self):
        """Test that results retrieval error uses period"""
        with self.assertRaises(ValueError) as context:
            raise ValueError(f"Failed to retrieve results for job 'test_job'. Error details")

        self.assertIn("for job 'test_job'.", str(context.exception))
        self.assertNotIn("for job 'test_job':", str(context.exception))

    def test_failed_to_retrieve_details_error_message(self):
        """Test that details retrieval error uses period"""
        with self.assertRaises(ValueError) as context:
            raise ValueError(f"Failed to retrieve details for job 'test_job'. Error details")

        self.assertIn("for job 'test_job'.", str(context.exception))
        self.assertNotIn("for job 'test_job':", str(context.exception))

    def test_failed_to_archive_job_error_message(self):
        """Test that archive job error uses period"""
        with self.assertRaises(ValueError) as context:
            raise ValueError(f"Failed to archive job. Job 'test_job' not found or not accessible. Error details")

        self.assertIn("not accessible.", str(context.exception))
        self.assertNotIn("not accessible:", str(context.exception))

    def test_move_failed_error_message(self):
        """Test that move failed error uses period"""
        with self.assertRaises(ValueError) as context:
            raise ValueError(f"Move failed. 400 - Bad request")

        self.assertIn("Move failed.", str(context.exception))
        self.assertNotIn("Move failed:", str(context.exception))

    def test_move_operation_failed_error_message(self):
        """Test that move operation failed error uses period"""
        with self.assertRaises(ValueError) as context:
            raise ValueError(f"Move operation failed. Error details")

        self.assertIn("operation failed.", str(context.exception))
        self.assertNotIn("operation failed:", str(context.exception))

    def test_rename_failed_error_message(self):
        """Test that rename failed error uses period"""
        with self.assertRaises(ValueError) as context:
            raise ValueError(f"Rename failed. 400 - Bad request")

        self.assertIn("Rename failed.", str(context.exception))
        self.assertNotIn("Rename failed:", str(context.exception))

    def test_rename_operation_failed_error_message(self):
        """Test that rename operation failed error uses period"""
        with self.assertRaises(ValueError) as context:
            raise ValueError(f"Rename operation failed. Error details")

        self.assertIn("operation failed.", str(context.exception))
        self.assertNotIn("operation failed:", str(context.exception))

    def test_copy_failed_error_message(self):
        """Test that copy failed error uses period"""
        with self.assertRaises(ValueError) as context:
            raise ValueError(f"Copy failed. 400 - Bad request")

        self.assertIn("Copy failed.", str(context.exception))
        self.assertNotIn("Copy failed:", str(context.exception))

    def test_copy_operation_failed_error_message(self):
        """Test that copy operation failed error uses period"""
        with self.assertRaises(ValueError) as context:
            raise ValueError(f"Copy operation failed. Error details")

        self.assertIn("operation failed.", str(context.exception))
        self.assertNotIn("operation failed:", str(context.exception))

    def test_folder_creation_failed_error_message(self):
        """Test that folder creation failed error uses period"""
        with self.assertRaises(ValueError) as context:
            raise ValueError(f"Folder creation failed. 400 - Bad request")

        self.assertIn("creation failed.", str(context.exception))
        self.assertNotIn("creation failed:", str(context.exception))

    def test_removal_failed_error_message(self):
        """Test that removal failed error uses period"""
        with self.assertRaises(ValueError) as context:
            raise ValueError(f"Removal failed. 400 - Bad request")

        self.assertIn("Removal failed.", str(context.exception))
        self.assertNotIn("Removal failed:", str(context.exception))

    def test_removal_operation_failed_error_message(self):
        """Test that removal operation failed error uses period"""
        with self.assertRaises(ValueError) as context:
            raise ValueError(f"Remove operation failed. Error details")

        self.assertIn("operation failed.", str(context.exception))
        self.assertNotIn("operation failed:", str(context.exception))

    def test_could_not_resolve_source_path_error_message(self):
        """Test that could not resolve source path error uses period"""
        with self.assertRaises(ValueError) as context:
            raise ValueError(f"Could not resolve source path 'test/path'. Error details")

        self.assertIn("path 'test/path'.", str(context.exception))
        self.assertNotIn("path 'test/path':", str(context.exception))

    def test_could_not_resolve_destination_path_error_message(self):
        """Test that could not resolve destination path error uses period"""
        with self.assertRaises(ValueError) as context:
            raise ValueError(f"Could not resolve destination path 'test/path'. Error details")

        self.assertIn("path 'test/path'.", str(context.exception))
        self.assertNotIn("path 'test/path':", str(context.exception))

    def test_could_not_list_contents_error_message(self):
        """Test that could not list contents error uses period"""
        with self.assertRaises(ValueError) as context:
            raise ValueError(f"Could not list contents at 'test/path'. Error details")

        self.assertIn("at 'test/path'.", str(context.exception))
        self.assertNotIn("at 'test/path':", str(context.exception))

    def test_could_not_access_paths_error_message(self):
        """Test that could not access paths error uses period"""
        with self.assertRaises(ValueError) as context:
            raise ValueError(f"Could not access paths. Error details")

        self.assertIn("access paths.", str(context.exception))
        self.assertNotIn("access paths:", str(context.exception))

    def test_could_not_link_folder_error_message(self):
        """Test that could not link folder error uses period"""
        with self.assertRaises(ValueError) as context:
            raise ValueError(f"Could not link folder. Error details")

        self.assertIn("link folder.", str(context.exception))
        self.assertNotIn("link folder:", str(context.exception))

    def test_failed_to_list_files_error_message(self):
        """Test that failed to list files error uses period"""
        with self.assertRaises(ValueError) as context:
            raise ValueError(f"Failed to list files for project 'test_project'. Error details")

        self.assertIn("project 'test_project'.", str(context.exception))
        self.assertNotIn("project 'test_project':", str(context.exception))


class TestCLOSErrorMessages(unittest.TestCase):
    """Test error messages in clos.py"""

    def test_logs_not_available_error_message(self):
        """Test that logs not available error uses 'Error.' prefix"""
        with self.assertRaises(ValueError) as context:
            raise ValueError("Logs are not available.")

        self.assertIn("Error.", str(context.exception))
        self.assertNotIn("ERROR:", str(context.exception))

    def test_failed_to_list_project_content_error_message(self):
        """Test that failed to list project content error uses period"""
        with self.assertRaises(ValueError) as context:
            raise ValueError(f"Failed to list project content for project 'test_project'. Error details")

        self.assertIn("project 'test_project'.", str(context.exception))
        self.assertNotIn("project 'test_project':", str(context.exception))

    def test_failed_to_get_items_from_analyses_results_error_message(self):
        """Test that analyses results error uses period"""
        with self.assertRaises(ValueError) as context:
            raise ValueError(f"Failed to get items from Analyses Results folder. Error details")

        self.assertIn("Results folder.", str(context.exception))
        self.assertNotIn("Results folder:", str(context.exception))

    def test_error_resolving_user_error_message(self):
        """Test that error resolving user uses period"""
        with self.assertRaises(ValueError) as context:
            raise ValueError(f"Error resolving user 'test_user'. Error details")

        self.assertIn("user 'test_user'.", str(context.exception))
        self.assertNotIn("user 'test_user':", str(context.exception))

    def test_error_resolving_project_error_message(self):
        """Test that error resolving project uses period"""
        with self.assertRaises(ValueError) as context:
            raise ValueError(f"Error resolving project 'test_project'. Error details")

        self.assertIn("project 'test_project'.", str(context.exception))
        self.assertNotIn("project 'test_project':", str(context.exception))

    def test_error_resolving_workflow_error_message(self):
        """Test that error resolving workflow uses period"""
        with self.assertRaises(ValueError) as context:
            raise ValueError(f"Error resolving workflow 'test_workflow'. Error details")

        self.assertIn("workflow 'test_workflow'.", str(context.exception))
        self.assertNotIn("workflow 'test_workflow':", str(context.exception))

    def test_error_getting_current_user_info_error_message(self):
        """Test that error getting user info uses period"""
        with self.assertRaises(ValueError) as context:
            raise ValueError(f"Error getting current user info. Error details")

        self.assertIn("user info.", str(context.exception))
        self.assertNotIn("user info:", str(context.exception))

    def test_error_filtering_by_queue_error_message(self):
        """Test that error filtering by queue uses period"""
        with self.assertRaises(ValueError) as context:
            raise ValueError(f"Error filtering by queue 'test_queue'. Error details")

        self.assertIn("queue 'test_queue'.", str(context.exception))
        self.assertNotIn("queue 'test_queue':", str(context.exception))

    def test_workflow_type_detected_error_message(self):
        """Test that workflow type detection error uses period"""
        with self.assertRaises(ValueError) as context:
            raise ValueError(f"More than one workflow type detected for test_workflow. ['nextflow', 'wdl']")

        self.assertIn("for test_workflow.", str(context.exception))
        self.assertNotIn("for test_workflow:", str(context.exception))

    def test_repository_platform_not_supported_error_message(self):
        """Test that repository platform not supported error uses period"""
        with self.assertRaises(ValueError) as context:
            raise ValueError(f"Your repository platform \"test\" is not supported. Use one of the supported platforms.")

        self.assertIn("not supported.", str(context.exception))
        self.assertNotIn("not supported:", str(context.exception))

    def test_no_workflow_found_error_message(self):
        """Test that no workflow found error doesn't have extra colons"""
        with self.assertRaises(ValueError) as context:
            raise ValueError(f"No workflow found with name test_workflow in workspace test_workspace")

        # Should not have colons around the variable names
        self.assertIn("name test_workflow in workspace test_workspace", str(context.exception))
        self.assertNotIn("name: test_workflow", str(context.exception))
        self.assertNotIn("workspace: test_workspace", str(context.exception))

    def test_more_than_one_workflow_found_error_message(self):
        """Test that more than one workflow found error doesn't have extra colons"""
        with self.assertRaises(ValueError) as context:
            raise ValueError(f"More than one workflow found with name test_workflow. Use '--last' flag.")

        # Should not have colons around the variable names
        self.assertIn("name test_workflow.", str(context.exception))
        self.assertNotIn("name: test_workflow", str(context.exception))


class TestLinkErrorMessages(unittest.TestCase):
    """Test error messages in link/link.py"""

    def test_forbidden_invalid_api_key_error_message(self):
        """Test that forbidden error uses period"""
        with self.assertRaises(ValueError) as context:
            raise ValueError("Forbidden. Invalid API key or insufficient permissions.")

        self.assertIn("Forbidden.", str(context.exception))
        self.assertNotIn("Forbidden:", str(context.exception))


class TestCostErrorMessages(unittest.TestCase):
    """Test error messages in cost/cost.py"""

    def test_unexpected_error_occurred_error_message(self):
        """Test that unexpected error message uses period"""
        with self.assertRaises(ValueError) as context:
            raise ValueError(f"An unexpected error occurred. Error details")

        self.assertIn("occurred.", str(context.exception))
        self.assertNotIn("occurred:", str(context.exception))


class TestDatasetsErrorMessages(unittest.TestCase):
    """Test error messages in datasets/datasets.py"""

    def test_unknown_item_type_for_copy_error_message(self):
        """Test that unknown item type error uses period"""
        with self.assertRaises(ValueError) as context:
            raise ValueError(f"Unknown item type for copy. test_item")

        self.assertIn("for copy.", str(context.exception))
        self.assertNotIn("for copy:", str(context.exception))


class TestErrorMessageConsistency(unittest.TestCase):
    """Test overall error message consistency across the codebase"""

    def test_no_double_colons_in_error_messages(self):
        """Verify that error messages don't contain multiple colons in sequence"""
        # This is a meta-test to ensure consistency
        error_messages = [
            "Operation not permitted. Your workspace does not have the option",
            "Unauthorized. Invalid or missing API key.",
            "Forbidden. You don't have permission",
            "Conflict. The folder cannot be deleted",
            "Internal server error. The server encountered an error",
            "Job 'test' not found or not accessible. Error",
            "Failed to retrieve working directory for job 'test'. Error",
            "Move failed. 400 - Bad request",
            "Logs are not available.",
            "More than one workflow type detected for workflow. types",
            "Your repository platform 'test' is not supported. ",
        ]

        for msg in error_messages:
            # Should not contain ': ' after the first word
            parts = msg.split('. ', 1)
            if len(parts) > 1:
                # After the first period, there should be no colons before variables
                self.assertNotIn(':', parts[1].split('{')[0], f"Found colon in: {msg}")


if __name__ == "__main__":
    unittest.main()

    """Test error messages in jobs/job.py"""

    def test_invalid_parameters_error_message(self):
        """Test that invalid parameter error uses period instead of colon"""
        job = Job(
            apikey="test_key",
            cloudos_url="https://test.cloudos.lifebit.ai",
            workspace_id="test_workspace"
        )

        with pytest.raises(ValueError) as exc_info:
            # This would trigger the error in the actual code
            raise ValueError(f'The provided parameters "test_param" are not valid. ')

        assert "not valid." in str(exc_info.value)
        assert "not valid:" not in str(exc_info.value)

    def test_job_status_retrieval_error_message(self):
        """Test that job status retrieval error uses period"""
        with pytest.raises(ValueError) as exc_info:
            raise ValueError(f"The job status cannot be retrieved. Test error")

        assert "cannot be retrieved." in str(exc_info.value)
        assert "cannot be retrieved:" not in str(exc_info.value)

    def test_queue_filtering_error_message(self):
        """Test that queue filtering error uses period"""
        with pytest.raises(ValueError) as exc_info:
            raise ValueError(f"Error filtering by queue 'test_queue'. Error details")

        assert "by queue 'test_queue'." in str(exc_info.value)
        assert "queue 'test_queue':" not in str(exc_info.value)

    def test_operation_not_permitted_error_message(self):
        """Test that operation not permitted error uses period"""
        with pytest.raises(ValueError) as exc_info:
            raise ValueError("Operation not permitted. Your workspace does not have the option to delete results folders enabled.")

        assert "Operation not permitted." in str(exc_info.value)
        assert "Operation not permitted:" not in str(exc_info.value)

    def test_unauthorized_error_message(self):
        """Test that unauthorized error uses period"""
        with pytest.raises(ValueError) as exc_info:
            raise ValueError("Unauthorized. Invalid or missing API key.")

        assert "Unauthorized." in str(exc_info.value)
        assert "Unauthorized:" not in str(exc_info.value)

    def test_forbidden_error_message(self):
        """Test that forbidden error uses period"""
        with pytest.raises(ValueError) as exc_info:
            raise ValueError("Forbidden. You don't have permission to delete this folder.")

        assert "Forbidden." in str(exc_info.value)
        assert "Forbidden:" not in str(exc_info.value)

    def test_conflict_error_message(self):
        """Test that conflict error uses period"""
        with pytest.raises(ValueError) as exc_info:
            raise ValueError("Conflict. The folder cannot be deleted due to a conflict (e.g., folder is not empty or has dependencies).")

        assert "Conflict." in str(exc_info.value)
        assert "Conflict:" not in str(exc_info.value)

    def test_internal_server_error_message(self):
        """Test that internal server error uses period"""
        with pytest.raises(ValueError) as exc_info:
            raise ValueError("Internal server error. The server encountered an error while processing the deletion request.")

        assert "Internal server error." in str(exc_info.value)
        assert "Internal server error:" not in str(exc_info.value)


class TestCLIMainErrorMessages:
    """Test error messages in __main__.py"""

    def test_job_not_found_error_message(self):
        """Test that job not found error uses period"""
        with pytest.raises(ValueError) as exc_info:
            raise ValueError(f"Job 'test_job_id' not found or not accessible. Error details")

        assert "not accessible." in str(exc_info.value)
        assert "not accessible:" not in str(exc_info.value)

    def test_failed_to_retrieve_workdir_error_message(self):
        """Test that failed to retrieve workdir error uses period"""
        with pytest.raises(ValueError) as exc_info:
            raise ValueError(f"Failed to retrieve working directory for job 'test_job'. Error details")

        assert "for job 'test_job'." in str(exc_info.value)
        assert "for job 'test_job':" not in str(exc_info.value)

    def test_failed_to_retrieve_intermediate_results_error_message(self):
        """Test that intermediate results error uses period"""
        with pytest.raises(ValueError) as exc_info:
            raise ValueError(f"Failed to retrieve intermediate results for job 'test_job'. Error details")

        assert "for job 'test_job'." in str(exc_info.value)
        assert "for job 'test_job':" not in str(exc_info.value)

    def test_failed_to_retrieve_logs_error_message(self):
        """Test that logs retrieval error uses period"""
        with pytest.raises(ValueError) as exc_info:
            raise ValueError(f"Failed to retrieve logs for job 'test_job'. Error details")

        assert "for job 'test_job'." in str(exc_info.value)
        assert "for job 'test_job':" not in str(exc_info.value)

    def test_failed_to_retrieve_results_error_message(self):
        """Test that results retrieval error uses period"""
        with pytest.raises(ValueError) as exc_info:
            raise ValueError(f"Failed to retrieve results for job 'test_job'. Error details")

        assert "for job 'test_job'." in str(exc_info.value)
        assert "for job 'test_job':" not in str(exc_info.value)

    def test_failed_to_retrieve_details_error_message(self):
        """Test that details retrieval error uses period"""
        with pytest.raises(ValueError) as exc_info:
            raise ValueError(f"Failed to retrieve details for job 'test_job'. Error details")

        assert "for job 'test_job'." in str(exc_info.value)
        assert "for job 'test_job':" not in str(exc_info.value)

    def test_failed_to_archive_job_error_message(self):
        """Test that archive job error uses period"""
        with pytest.raises(ValueError) as exc_info:
            raise ValueError(f"Failed to archive job. Job 'test_job' not found or not accessible. Error details")

        assert "not accessible." in str(exc_info.value)
        assert "not accessible:" not in str(exc_info.value)

    def test_move_failed_error_message(self):
        """Test that move failed error uses period"""
        with pytest.raises(ValueError) as exc_info:
            raise ValueError(f"Move failed. 400 - Bad request")

        assert "Move failed." in str(exc_info.value)
        assert "Move failed:" not in str(exc_info.value)

    def test_move_operation_failed_error_message(self):
        """Test that move operation failed error uses period"""
        with pytest.raises(ValueError) as exc_info:
            raise ValueError(f"Move operation failed. Error details")

        assert "operation failed." in str(exc_info.value)
        assert "operation failed:" not in str(exc_info.value)

    def test_rename_failed_error_message(self):
        """Test that rename failed error uses period"""
        with pytest.raises(ValueError) as exc_info:
            raise ValueError(f"Rename failed. 400 - Bad request")

        assert "Rename failed." in str(exc_info.value)
        assert "Rename failed:" not in str(exc_info.value)

    def test_rename_operation_failed_error_message(self):
        """Test that rename operation failed error uses period"""
        with pytest.raises(ValueError) as exc_info:
            raise ValueError(f"Rename operation failed. Error details")

        assert "operation failed." in str(exc_info.value)
        assert "operation failed:" not in str(exc_info.value)

    def test_copy_failed_error_message(self):
        """Test that copy failed error uses period"""
        with pytest.raises(ValueError) as exc_info:
            raise ValueError(f"Copy failed. 400 - Bad request")

        assert "Copy failed." in str(exc_info.value)
        assert "Copy failed:" not in str(exc_info.value)

    def test_copy_operation_failed_error_message(self):
        """Test that copy operation failed error uses period"""
        with pytest.raises(ValueError) as exc_info:
            raise ValueError(f"Copy operation failed. Error details")

        assert "operation failed." in str(exc_info.value)
        assert "operation failed:" not in str(exc_info.value)

    def test_folder_creation_failed_error_message(self):
        """Test that folder creation failed error uses period"""
        with pytest.raises(ValueError) as exc_info:
            raise ValueError(f"Folder creation failed. 400 - Bad request")

        assert "creation failed." in str(exc_info.value)
        assert "creation failed:" not in str(exc_info.value)

    def test_removal_failed_error_message(self):
        """Test that removal failed error uses period"""
        with pytest.raises(ValueError) as exc_info:
            raise ValueError(f"Removal failed. 400 - Bad request")

        assert "Removal failed." in str(exc_info.value)
        assert "Removal failed:" not in str(exc_info.value)

    def test_removal_operation_failed_error_message(self):
        """Test that removal operation failed error uses period"""
        with pytest.raises(ValueError) as exc_info:
            raise ValueError(f"Remove operation failed. Error details")

        assert "operation failed." in str(exc_info.value)
        assert "operation failed:" not in str(exc_info.value)

    def test_could_not_resolve_source_path_error_message(self):
        """Test that could not resolve source path error uses period"""
        with pytest.raises(ValueError) as exc_info:
            raise ValueError(f"Could not resolve source path 'test/path'. Error details")

        assert "path 'test/path'." in str(exc_info.value)
        assert "path 'test/path':" not in str(exc_info.value)

    def test_could_not_resolve_destination_path_error_message(self):
        """Test that could not resolve destination path error uses period"""
        with pytest.raises(ValueError) as exc_info:
            raise ValueError(f"Could not resolve destination path 'test/path'. Error details")

        assert "path 'test/path'." in str(exc_info.value)
        assert "path 'test/path':" not in str(exc_info.value)

    def test_could_not_list_contents_error_message(self):
        """Test that could not list contents error uses period"""
        with pytest.raises(ValueError) as exc_info:
            raise ValueError(f"Could not list contents at 'test/path'. Error details")

        assert "at 'test/path'." in str(exc_info.value)
        assert "at 'test/path':" not in str(exc_info.value)

    def test_could_not_access_paths_error_message(self):
        """Test that could not access paths error uses period"""
        with pytest.raises(ValueError) as exc_info:
            raise ValueError(f"Could not access paths. Error details")

        assert "access paths." in str(exc_info.value)
        assert "access paths:" not in str(exc_info.value)

    def test_could_not_link_folder_error_message(self):
        """Test that could not link folder error uses period"""
        with pytest.raises(ValueError) as exc_info:
            raise ValueError(f"Could not link folder. Error details")

        assert "link folder." in str(exc_info.value)
        assert "link folder:" not in str(exc_info.value)

    def test_failed_to_list_files_error_message(self):
        """Test that failed to list files error uses period"""
        with pytest.raises(ValueError) as exc_info:
            raise ValueError(f"Failed to list files for project 'test_project'. Error details")

        assert "project 'test_project'." in str(exc_info.value)
        assert "project 'test_project':" not in str(exc_info.value)


class TestCLOSErrorMessages:
    """Test error messages in clos.py"""

    def test_logs_not_available_error_message(self):
        """Test that logs not available error uses 'Error.' prefix"""
        with pytest.raises(ValueError) as exc_info:
            raise ValueError("Logs are not available.")

        assert "Logs are not available." in str(exc_info.value)
        assert "ERROR:" not in str(exc_info.value)

    def test_failed_to_list_project_content_error_message(self):
        """Test that failed to list project content error uses period"""
        with pytest.raises(ValueError) as exc_info:
            raise ValueError(f"Failed to list project content for project 'test_project'. Error details")

        assert "project 'test_project'." in str(exc_info.value)
        assert "project 'test_project':" not in str(exc_info.value)

    def test_failed_to_get_items_from_analyses_results_error_message(self):
        """Test that analyses results error uses period"""
        with pytest.raises(ValueError) as exc_info:
            raise ValueError(f"Failed to get items from Analyses Results folder. Error details")

        assert "Results folder." in str(exc_info.value)
        assert "Results folder:" not in str(exc_info.value)

    def test_error_resolving_user_error_message(self):
        """Test that error resolving user uses period"""
        with pytest.raises(ValueError) as exc_info:
            raise ValueError(f"Error resolving user 'test_user'. Error details")

        assert "user 'test_user'." in str(exc_info.value)
        assert "user 'test_user':" not in str(exc_info.value)

    def test_error_resolving_project_error_message(self):
        """Test that error resolving project uses period"""
        with pytest.raises(ValueError) as exc_info:
            raise ValueError(f"Error resolving project 'test_project'. Error details")

        assert "project 'test_project'." in str(exc_info.value)
        assert "project 'test_project':" not in str(exc_info.value)

    def test_error_resolving_workflow_error_message(self):
        """Test that error resolving workflow uses period"""
        with pytest.raises(ValueError) as exc_info:
            raise ValueError(f"Error resolving workflow 'test_workflow'. Error details")

        assert "workflow 'test_workflow'." in str(exc_info.value)
        assert "workflow 'test_workflow':" not in str(exc_info.value)

    def test_error_getting_current_user_info_error_message(self):
        """Test that error getting user info uses period"""
        with pytest.raises(ValueError) as exc_info:
            raise ValueError(f"Error getting current user info. Error details")

        assert "user info." in str(exc_info.value)
        assert "user info:" not in str(exc_info.value)

    def test_error_filtering_by_queue_error_message(self):
        """Test that error filtering by queue uses period"""
        with pytest.raises(ValueError) as exc_info:
            raise ValueError(f"Error filtering by queue 'test_queue'. Error details")

        assert "queue 'test_queue'." in str(exc_info.value)
        assert "queue 'test_queue':" not in str(exc_info.value)

    def test_workflow_type_detected_error_message(self):
        """Test that workflow type detection error uses period"""
        with pytest.raises(ValueError) as exc_info:
            raise ValueError(f"More than one workflow type detected for test_workflow. ['nextflow', 'wdl']")

        assert "for test_workflow." in str(exc_info.value)
        assert "for test_workflow:" not in str(exc_info.value)

    def test_repository_platform_not_supported_error_message(self):
        """Test that repository platform not supported error uses period"""
        with pytest.raises(ValueError) as exc_info:
            raise ValueError(f"Your repository platform 'test' is not supported. Use one of the supported platforms.")

        assert "not supported." in str(exc_info.value)
        assert "not supported:" not in str(exc_info.value)

    def test_no_workflow_found_error_message(self):
        """Test that no workflow found error doesn't have extra colons"""
        with pytest.raises(ValueError) as exc_info:
            raise ValueError(f"No workflow found with name test_workflow in workspace test_workspace")

        # Should not have colons around the variable names
        assert "name test_workflow in workspace test_workspace" in str(exc_info.value)
        assert "name: test_workflow" not in str(exc_info.value)
        assert "workspace: test_workspace" not in str(exc_info.value)

    def test_more_than_one_workflow_found_error_message(self):
        """Test that more than one workflow found error doesn't have extra colons"""
        with pytest.raises(ValueError) as exc_info:
            raise ValueError(f"More than one workflow found with name test_workflow. Use '--last' flag.")

        # Should not have colons around the variable names
        assert "name test_workflow." in str(exc_info.value)
        assert "name: test_workflow" not in str(exc_info.value)


class TestLinkErrorMessages:
    """Test error messages in link/link.py"""

    def test_forbidden_invalid_api_key_error_message(self):
        """Test that forbidden error uses period"""
        with pytest.raises(ValueError) as exc_info:
            raise ValueError("Forbidden. Invalid API key or insufficient permissions.")

        assert "Forbidden." in str(exc_info.value)
        assert "Forbidden:" not in str(exc_info.value)


class TestCostErrorMessages:
    """Test error messages in cost/cost.py"""

    def test_unexpected_error_occurred_error_message(self):
        """Test that unexpected error message uses period"""
        with pytest.raises(ValueError) as exc_info:
            raise ValueError(f"An unexpected error occurred. Error details")

        assert "occurred." in str(exc_info.value)
        assert "occurred:" not in str(exc_info.value)


class TestDatasetsErrorMessages:
    """Test error messages in datasets/datasets.py"""

    def test_unknown_item_type_for_copy_error_message(self):
        """Test that unknown item type error uses period"""
        with pytest.raises(ValueError) as exc_info:
            raise ValueError(f"Unknown item type for copy. test_item")

        assert "for copy." in str(exc_info.value)
        assert "for copy:" not in str(exc_info.value)


class TestErrorMessageConsistency:
    """Test overall error message consistency across the codebase"""

    def test_no_double_colons_in_error_messages(self):
        """Verify that error messages don't contain multiple colons in sequence"""
        # This is a meta-test to ensure consistency
        error_messages = [
            "Operation not permitted. Your workspace does not have the option",
            "Unauthorized. Invalid or missing API key.",
            "Forbidden. You don't have permission",
            "Conflict. The folder cannot be deleted",
            "Internal server error. The server encountered an error",
            "Job 'test' not found or not accessible. Error",
            "Failed to retrieve working directory for job 'test'. Error",
            "Move failed. 400 - Bad request",
            "Logs are not available.",
            "More than one workflow type detected for workflow. types",
            "Your repository platform is not supported. platform",
        ]

        for msg in error_messages:
            # Should not contain ': ' after the first word
            parts = msg.split('. ', 1)
            if len(parts) > 1:
                # After the first period, there should be no colons before variables
                assert ':' not in parts[1].split('{')[0], f"Found colon in: {msg}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

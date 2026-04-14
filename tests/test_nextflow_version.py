"""Tests for Nextflow version resolution utilities."""

import pytest
import rich_click as click
from unittest.mock import patch
from cloudos_cli.utils.nextflow_version import resolve_nextflow_version


class TestResolveNextflowVersion:
    """Test cases for resolve_nextflow_version function."""
    
    def test_default_azure_version(self):
        """Test that Azure always defaults to 22.11.1-edge."""
        result = resolve_nextflow_version(
            nextflow_version=None,
            execution_platform='azure',
            is_module=False
        )
        assert result == '22.11.1-edge'
    
    def test_default_hpc_version(self):
        """Test that HPC always defaults to 22.10.8."""
        result = resolve_nextflow_version(
            nextflow_version=None,
            execution_platform='hpc',
            is_module=False
        )
        assert result == '22.10.8'
    
    def test_default_aws_platform_workflow(self):
        """Test that AWS Platform workflows default to 22.10.8."""
        result = resolve_nextflow_version(
            nextflow_version=None,
            execution_platform='aws',
            is_module=True
        )
        assert result == '22.10.8'
    
    def test_default_aws_user_workflow(self):
        """Test that AWS user-imported workflows default to 24.04.4."""
        result = resolve_nextflow_version(
            nextflow_version=None,
            execution_platform='aws',
            is_module=False
        )
        assert result == '24.04.4'
    
    def test_latest_resolution_aws(self):
        """Test that 'latest' resolves to correct version for AWS."""
        result = resolve_nextflow_version(
            nextflow_version='latest',
            execution_platform='aws',
            is_module=False
        )
        assert result == '25.10.4'  # AWS_NEXTFLOW_LATEST
    
    def test_latest_resolution_azure(self):
        """Test that 'latest' resolves to correct version for Azure."""
        result = resolve_nextflow_version(
            nextflow_version='latest',
            execution_platform='azure',
            is_module=False
        )
        assert result == '22.11.1-edge'  # AZURE_NEXTFLOW_LATEST
    
    def test_latest_resolution_hpc(self):
        """Test that 'latest' resolves to correct version for HPC."""
        result = resolve_nextflow_version(
            nextflow_version='latest',
            execution_platform='hpc',
            is_module=False
        )
        assert result == '22.10.8'  # HPC_NEXTFLOW_LATEST
    
    def test_platform_workflow_forces_azure_version(self):
        """Test that Platform workflows on Azure are forced to 22.11.1-edge."""
        result = resolve_nextflow_version(
            nextflow_version='24.04.4',  # User tries different version
            execution_platform='azure',
            is_module=True,
            workflow_name='test-workflow'
        )
        assert result == '22.11.1-edge'
    
    def test_platform_workflow_forces_aws_version(self):
        """Test that Platform workflows on AWS are forced to 22.10.8."""
        result = resolve_nextflow_version(
            nextflow_version='24.04.4',  # User tries different version
            execution_platform='aws',
            is_module=True,
            workflow_name='test-workflow'
        )
        assert result == '22.10.8'
    
    def test_valid_aws_version_accepted(self):
        """Test that valid AWS versions are accepted."""
        for version in ['22.10.8', '24.04.4', '25.04.8', '25.10.4']:
            result = resolve_nextflow_version(
                nextflow_version=version,
                execution_platform='aws',
                is_module=False
            )
            assert result == version
    
    def test_invalid_aws_version_raises_error(self):
        """Test that invalid AWS version raises BadParameter."""
        with pytest.raises(click.BadParameter, match='Unsupported Nextflow version'):
            resolve_nextflow_version(
                nextflow_version='99.99.99',
                execution_platform='aws',
                is_module=False
            )
    
    def test_invalid_hpc_version_raises_error(self):
        """Test that invalid HPC version raises BadParameter."""
        with pytest.raises(click.BadParameter, match='Unsupported Nextflow version'):
            resolve_nextflow_version(
                nextflow_version='24.04.4',  # Not supported on HPC
                execution_platform='hpc',
                is_module=False
            )
    
    def test_azure_invalid_version_auto_corrects(self):
        """Test that Azure auto-corrects invalid versions with warning."""
        with patch('cloudos_cli.utils.nextflow_version.click.secho') as mock_secho:
            result = resolve_nextflow_version(
                nextflow_version='24.04.4',  # Not supported on Azure
                execution_platform='azure',
                is_module=False
            )
            assert result == '22.11.1-edge'
            # Verify warning was displayed
            mock_secho.assert_called_once()
            assert 'Warning' in mock_secho.call_args[0][0]
    
    def test_verbose_output(self, capsys):
        """Test that verbose flag produces output."""
        resolve_nextflow_version(
            nextflow_version=None,
            execution_platform='aws',
            is_module=True,
            verbose=True
        )
        captured = capsys.readouterr()
        assert 'Using default Nextflow version' in captured.out
    
    def test_dsl2_warning_for_new_versions(self):
        """Test that DSL2 warning is displayed for newer versions."""
        with patch('cloudos_cli.utils.nextflow_version.click.secho') as mock_secho:
            resolve_nextflow_version(
                nextflow_version='24.04.4',
                execution_platform='aws',
                is_module=False
            )
            # Should have warning about DSL2
            mock_secho.assert_called_once()
            assert 'DSL2' in mock_secho.call_args[0][0]
    
    def test_no_dsl2_warning_for_legacy_versions(self):
        """Test that no DSL2 warning for legacy versions."""
        with patch('cloudos_cli.utils.nextflow_version.click.secho') as mock_secho:
            resolve_nextflow_version(
                nextflow_version='22.10.8',
                execution_platform='aws',
                is_module=False
            )
            # Should not have any warnings
            mock_secho.assert_not_called()


# Example usage for mocking in integration tests
class TestJobSubmissionMocking:
    """Examples of how to mock the function in job submission tests."""
    
    @patch('cloudos_cli.jobs.cli.resolve_nextflow_version')
    def test_job_submission_with_mocked_version(self, mock_resolve):
        """Example: Mock the entire version resolution logic."""
        # Set up the mock to return a specific version
        mock_resolve.return_value = '24.04.4'
        
        # Now you can test the job submission without worrying about
        # all the complex version resolution logic
        # ... your job submission test code here ...
        
        assert mock_resolve.return_value == '24.04.4'

"""Tests for Nextflow version resolution utilities."""

import pytest
import rich_click as click
from unittest.mock import patch
from cloudos_cli.utils.nextflow_version import resolve_nextflow_version
from cloudos_cli.constants import (
    AWS_NEXTFLOW_LATEST,
    AZURE_NEXTFLOW_LATEST,
    HPC_NEXTFLOW_LATEST,
    PLATFORM_WORKFLOW_NEXTFLOW_VERSION,
    USER_WORKFLOW_NEXTFLOW_VERSION,
    AWS_NEXTFLOW_VERSIONS
)


class TestResolveNextflowVersion:
    """Test cases for resolve_nextflow_version function."""
    
    def test_default_azure_version(self):
        """Test that Azure always defaults to AZURE_NEXTFLOW_LATEST."""
        result = resolve_nextflow_version(
            nextflow_version=None,
            execution_platform='azure',
            is_module=False
        )
        assert result == AZURE_NEXTFLOW_LATEST
    
    def test_default_hpc_version(self):
        """Test that HPC always defaults to HPC_NEXTFLOW_LATEST."""
        result = resolve_nextflow_version(
            nextflow_version=None,
            execution_platform='hpc',
            is_module=False
        )
        assert result == HPC_NEXTFLOW_LATEST
    
    def test_default_aws_platform_workflow(self):
        """Test that AWS Platform workflows default to PLATFORM_WORKFLOW_NEXTFLOW_VERSION."""
        result = resolve_nextflow_version(
            nextflow_version=None,
            execution_platform='aws',
            is_module=True
        )
        assert result == PLATFORM_WORKFLOW_NEXTFLOW_VERSION
    
    def test_default_aws_user_workflow(self):
        """Test that AWS user-imported workflows default to USER_WORKFLOW_NEXTFLOW_VERSION."""
        result = resolve_nextflow_version(
            nextflow_version=None,
            execution_platform='aws',
            is_module=False
        )
        assert result == USER_WORKFLOW_NEXTFLOW_VERSION
    
    def test_latest_resolution_aws(self):
        """Test that 'latest' resolves to AWS_NEXTFLOW_LATEST."""
        result = resolve_nextflow_version(
            nextflow_version='latest',
            execution_platform='aws',
            is_module=False
        )
        assert result == AWS_NEXTFLOW_LATEST
    
    def test_latest_resolution_azure(self):
        """Test that 'latest' resolves to AZURE_NEXTFLOW_LATEST."""
        result = resolve_nextflow_version(
            nextflow_version='latest',
            execution_platform='azure',
            is_module=False
        )
        assert result == AZURE_NEXTFLOW_LATEST
    
    def test_latest_resolution_hpc(self):
        """Test that 'latest' resolves to HPC_NEXTFLOW_LATEST."""
        result = resolve_nextflow_version(
            nextflow_version='latest',
            execution_platform='hpc',
            is_module=False
        )
        assert result == HPC_NEXTFLOW_LATEST
    
    def test_platform_workflow_forces_azure_version(self):
        """Test that Platform workflows on Azure are forced to AZURE_NEXTFLOW_LATEST."""
        result = resolve_nextflow_version(
            nextflow_version='24.04.4',  # User tries different version
            execution_platform='azure',
            is_module=True,
            workflow_name='test-workflow'
        )
        assert result == AZURE_NEXTFLOW_LATEST
    
    def test_platform_workflow_forces_aws_version(self):
        """Test that Platform workflows on AWS are forced to PLATFORM_WORKFLOW_NEXTFLOW_VERSION."""
        result = resolve_nextflow_version(
            nextflow_version='24.04.4',  # User tries different version
            execution_platform='aws',
            is_module=True,
            workflow_name='test-workflow'
        )
        assert result == PLATFORM_WORKFLOW_NEXTFLOW_VERSION
    
    def test_valid_aws_version_accepted(self):
        """Test that valid AWS versions are accepted."""
        for version in AWS_NEXTFLOW_VERSIONS:
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
            assert result == AZURE_NEXTFLOW_LATEST
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
                nextflow_version=USER_WORKFLOW_NEXTFLOW_VERSION,
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
                nextflow_version=PLATFORM_WORKFLOW_NEXTFLOW_VERSION,
                execution_platform='aws',
                is_module=False
            )
            # Should not have any warnings
            mock_secho.assert_not_called()


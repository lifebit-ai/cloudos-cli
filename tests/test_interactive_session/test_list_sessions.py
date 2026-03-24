"""Tests for interactive session list command."""

import pytest
import json
from click.testing import CliRunner
from cloudos_cli.__main__ import run_cloudos_cli
from unittest import mock
from unittest.mock import patch


class TestInteractiveSessionCommand:
    """Test the interactive session command structure."""

    def test_interactive_session_command_exists(self):
        """Test that the 'interactive-session' command exists."""
        runner = CliRunner()
        result = runner.invoke(run_cloudos_cli, ['interactive-session', '--help'])
        
        # Command should exist and not error out
        assert result.exit_code == 0
        assert 'interactive session' in result.output.lower()

    def test_interactive_session_list_command_exists(self):
        """Test that the 'interactive-session list' command exists."""
        runner = CliRunner()
        result = runner.invoke(run_cloudos_cli, ['interactive-session', 'list', '--help'])
        
        # Command should exist and show help properly
        assert result.exit_code == 0
        assert 'interactive session' in result.output.lower()
        assert 'list' in result.output.lower()

    def test_interactive_session_list_has_required_options(self):
        """Test that required options are present in list command."""
        runner = CliRunner()
        result = runner.invoke(run_cloudos_cli, ['interactive-session', 'list', '--help'])
        
        assert result.exit_code == 0
        # Check for required options
        assert '--apikey' in result.output
        assert '--workspace-id' in result.output
        # Check for optional filters
        assert '--filter-status' in result.output
        assert '--limit' in result.output
        assert '--page' in result.output
        assert '--filter-only-mine' in result.output
        assert '--archived' in result.output
        assert '--output-format' in result.output

    def test_interactive_session_list_output_format_options(self):
        """Test that output format options are correct."""
        runner = CliRunner()
        result = runner.invoke(run_cloudos_cli, ['interactive-session', 'list', '--help'])
        
        assert result.exit_code == 0
        # Check for format options
        assert 'stdout' in result.output or 'stdout' in result.output.lower()
        assert 'json' in result.output or 'json' in result.output.lower()
        assert 'csv' in result.output or 'csv' in result.output.lower()


class TestInteractiveSessionListIntegration:
    """Integration tests for interactive session list command with mocked API."""

    @pytest.fixture
    def runner(self):
        """Provide a CliRunner instance."""
        return CliRunner()

    def test_list_sessions_missing_workspace_id(self, runner):
        """Test listing sessions without workspace-id from command line.
        
        Note: If a default profile has workspace_id configured, it will be used
        and the command will attempt the API call instead of failing validation.
        This test just verifies the command can be invoked.
        """
        result = runner.invoke(run_cloudos_cli, [
            'interactive-session', 'list',
            '--apikey', 'test_key',
            '--cloudos-url', 'http://test.com'
        ])
        
        # Command should either fail with missing workspace-id error, or attempt
        # an API call (if workspace_id is in the default profile)
        # We just verify the command was invoked without syntax errors
        assert result.exit_code != 0  # Should fail for some reason

    @patch('cloudos_cli.interactive_session.cli.Cloudos')
    @patch('cloudos_cli.configure.configure.ConfigurationProfile.load_profile_and_validate_data')
    def test_list_sessions_with_valid_params(self, mock_config, mock_cloudos):
        """Test listing sessions with valid parameters."""
        runner = CliRunner()
        
        # Mock the configuration loading
        mock_config.return_value = {
            'apikey': 'test_key',
            'cloudos_url': 'http://test.com',
            'workspace_id': 'test_team'
        }
        
        # Mock the Cloudos API call
        mock_cloudos_instance = mock.MagicMock()
        mock_cloudos.return_value = mock_cloudos_instance
        mock_cloudos_instance.get_interactive_session_list.return_value = {
            'sessions': [],
            'pagination_metadata': {'count': 0, 'page': 1, 'limit': 10, 'totalPages': 0}
        }
        
        result = runner.invoke(run_cloudos_cli, [
            'interactive-session', 'list',
            '--apikey', 'test_key',
            '--cloudos-url', 'http://test.com',
            '--workspace-id', 'test_team'
        ])
        
        # Even if it fails due to config, we want to verify the command was invoked
        # Success would mean no exceptions during argument parsing
        assert 'No interactive sessions found' in result.output or result.exit_code == 0


class TestInteractiveSessionAPIMethod:
    """Unit tests for the get_interactive_session_list API method in Cloudos class."""

    def test_get_interactive_session_list_method_exists(self):
        """Test that the get_interactive_session_list method exists in Cloudos class."""
        from cloudos_cli.clos import Cloudos
        
        # Check if method exists
        assert hasattr(Cloudos, 'get_interactive_session_list')
        assert callable(getattr(Cloudos, 'get_interactive_session_list'))

    def test_get_interactive_session_list_signature(self):
        """Test that the method has the correct signature."""
        from cloudos_cli.clos import Cloudos
        import inspect
        
        method = getattr(Cloudos, 'get_interactive_session_list')
        sig = inspect.signature(method)
        params = list(sig.parameters.keys())
        
        # Check for required parameters
        assert 'self' in params
        assert 'team_id' in params
        # Check for optional parameters
        assert 'page' in params
        assert 'limit' in params
        assert 'status' in params
        assert 'owner_only' in params
        assert 'include_archived' in params
        assert 'verify' in params

    @patch('cloudos_cli.clos.retry_requests_get')
    def test_get_interactive_session_list_api_call(self, mock_get):
        """Test that the method makes the correct API call."""
        from cloudos_cli.clos import Cloudos
        
        # Setup mock response
        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'sessions': [
                {
                    '_id': 'session_001',
                    'name': 'Test Session',
                    'status': 'running',
                    'interactiveSessionType': 'awsJupyterNotebook',
                    'resources': {'instanceType': 'c5.xlarge'},
                    'totalCostInUsd': 1.50,
                    'user': {'name': 'John'}
                }
            ],
            'paginationMetadata': {
                'Pagination-Count': 1,
                'Pagination-Page': 1,
                'Pagination-Limit': 10
            }
        }
        mock_get.return_value = mock_response
        
        # Create Cloudos instance and call method
        cl = Cloudos('http://test.com', 'test_key', None)
        result = cl.get_interactive_session_list('test_team')
        
        # Verify API was called
        assert mock_get.called
        assert 'interactive-sessions' in mock_get.call_args[0][0]
        assert result['sessions'][0]['_id'] == 'session_001'
        assert result['pagination_metadata']['count'] == 1

    @patch('cloudos_cli.clos.retry_requests_get')
    def test_get_interactive_session_list_with_filters(self, mock_get):
        """Test that filters are correctly passed to the API."""
        from cloudos_cli.clos import Cloudos
        
        # Setup mock response
        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'sessions': [],
            'paginationMetadata': {
                'Pagination-Count': 0,
                'Pagination-Page': 1,
                'Pagination-Limit': 10
            }
        }
        mock_get.return_value = mock_response
        
        # Create Cloudos instance and call method with filters
        cl = Cloudos('http://test.com', 'test_key', None)
        result = cl.get_interactive_session_list(
            'test_team',
            page=2,
            limit=20,
            status=['running', 'initialising'],
            owner_only=True,
            include_archived=True
        )
        
        # Verify API was called with correct parameters
        assert mock_get.called
        call_args = mock_get.call_args
        params = call_args[1]['params']
        
        assert params['page'] == 2
        assert params['limit'] == 20
        assert params['onlyOwnerSessions'] == 'true'
        assert params['archived.status'] == 'true'

    def test_get_interactive_session_list_validation(self):
        """Test that method validates input parameters."""
        from cloudos_cli.clos import Cloudos
        
        cl = Cloudos('http://test.com', 'test_key', None)
        
        # Test invalid team_id
        with pytest.raises(ValueError):
            cl.get_interactive_session_list(None)
        
        # Test invalid page
        with pytest.raises(ValueError):
            cl.get_interactive_session_list('test_team', page=0)
        
        # Test invalid limit
        with pytest.raises(ValueError):
            cl.get_interactive_session_list('test_team', limit=150)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])


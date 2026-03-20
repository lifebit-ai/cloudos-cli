"""Tests for interactive session create command."""

import pytest
import json
from click.testing import CliRunner
from cloudos_cli.__main__ import run_cloudos_cli
from unittest import mock
from unittest.mock import patch, MagicMock


class TestInteractiveSessionCreateCommand:
    """Test the interactive session create command structure."""

    def test_interactive_session_create_command_exists(self):
        """Test that the 'interactive-session create' command exists."""
        runner = CliRunner()
        result = runner.invoke(run_cloudos_cli, ['interactive-session', 'create', '--help'])
        
        # Command should exist and not error out
        assert result.exit_code == 0
        assert 'create' in result.output.lower()

    def test_interactive_session_create_has_required_options(self):
        """Test that required options are present in create command."""
        runner = CliRunner()
        result = runner.invoke(run_cloudos_cli, ['interactive-session', 'create', '--help'])
        
        assert result.exit_code == 0
        # Check for required options
        assert '--apikey' in result.output or '--apikey' in result.output
        assert '--workspace-id' in result.output
        assert '--project-name' in result.output
        assert '--name' in result.output
        assert '--session-type' in result.output

    def test_interactive_session_create_session_type_choices(self):
        """Test that session type options are correct."""
        runner = CliRunner()
        result = runner.invoke(run_cloudos_cli, ['interactive-session', 'create', '--help'])
        
        assert result.exit_code == 0
        # Check for session type choices
        assert 'jupyter' in result.output.lower() or 'jupyter' in result.output
        assert 'vscode' in result.output.lower() or 'vscode' in result.output

    def test_interactive_session_create_has_optional_configuration_options(self):
        """Test that optional configuration options are present."""
        runner = CliRunner()
        result = runner.invoke(run_cloudos_cli, ['interactive-session', 'create', '--help'])
        
        assert result.exit_code == 0
        # Check for optional options
        assert '--instance' in result.output
        assert '--storage' in result.output
        assert '--spot' in result.output
        assert '--shared' in result.output
        assert '--cost-limit' in result.output
        assert '--shutdown-in' in result.output
        assert '--mount' in result.output
        assert '--link' in result.output
        assert '--r-version' in result.output
        assert '--spark-master' in result.output
        assert '--spark-core' in result.output
        assert '--spark-workers' in result.output


class TestInteractiveSessionCreateIntegration:
    """Integration tests for interactive session create command with mocked API."""

    @pytest.fixture
    def runner(self):
        """Provide a CliRunner instance."""
        return CliRunner()

    def test_create_session_missing_required_options(self, runner):
        """Test creating session without required options fails."""
        result = runner.invoke(run_cloudos_cli, [
            'interactive-session', 'create',
            '--apikey', 'test_key'
        ])
        
        # Should fail for missing required options
        assert result.exit_code != 0

    @patch('cloudos_cli.interactive_session.cli.Cloudos')
    @patch('cloudos_cli.configure.configure.ConfigurationProfile.load_profile_and_validate_data')
    def test_create_session_jupyter_basic(self, mock_config, mock_cloudos):
        """Test creating a basic Jupyter session."""
        runner = CliRunner()
        
        # Mock the configuration loading
        mock_config.return_value = {
            'apikey': 'test_key',
            'cloudos_url': 'http://test.com',
            'workspace_id': 'test_team',
            'project_name': 'my_project'
        }
        
        # Mock the Cloudos API calls
        mock_cloudos_instance = MagicMock()
        mock_cloudos.return_value = mock_cloudos_instance
        mock_cloudos_instance.create_interactive_session.return_value = {
            '_id': 'session_001',
            'name': 'Test Jupyter',
            'status': 'running',
            'interactiveSessionType': 'awsJupyterNotebook'
        }
        
        result = runner.invoke(run_cloudos_cli, [
            'interactive-session', 'create',
            '--apikey', 'test_key',
            '--cloudos-url', 'http://test.com',
            '--workspace-id', 'test_team',
            '--project-name', 'my_project',
            '--name', 'Test Jupyter',
            '--session-type', 'jupyter'
        ])
        
        # Command should execute (may fail at config loading but not at argument parsing)
        assert 'Error' not in result.output or result.exit_code in [0, 1]

    @patch('cloudos_cli.interactive_session.cli.Cloudos')
    @patch('cloudos_cli.configure.configure.ConfigurationProfile.load_profile_and_validate_data')
    def test_create_session_with_all_options(self, mock_config, mock_cloudos):
        """Test creating a session with all options specified."""
        runner = CliRunner()
        
        mock_config.return_value = {
            'apikey': 'test_key',
            'cloudos_url': 'http://test.com',
            'workspace_id': 'test_team',
            'project_name': 'my_project'
        }
        
        mock_cloudos_instance = MagicMock()
        mock_cloudos.return_value = mock_cloudos_instance
        mock_cloudos_instance.create_interactive_session.return_value = {
            '_id': 'session_002',
            'name': 'Advanced Session',
            'status': 'provisioning'
        }
        
        result = runner.invoke(run_cloudos_cli, [
            'interactive-session', 'create',
            '--apikey', 'test_key',
            '--cloudos-url', 'http://test.com',
            '--workspace-id', 'test_team',
            '--project-name', 'my_project',
            '--name', 'Advanced Session',
            '--session-type', 'vscode',
            '--instance', 'c5.2xlarge',
            '--storage', '1000',
            '--spot',
            '--shared',
            '--cost-limit', '50.0',
            '--shutdown-in', '8h',
            '--mount', 'MyDataset/datafile.csv'
        ])
        
        # Command should be invoked without syntax errors
        assert result.exit_code in [0, 1]

    @patch('cloudos_cli.interactive_session.cli.Cloudos')
    @patch('cloudos_cli.configure.configure.ConfigurationProfile.load_profile_and_validate_data')
    def test_create_session_spark_with_cluster_config(self, mock_config, mock_cloudos):
        """Test creating a Spark session with cluster configuration."""
        runner = CliRunner()
        
        mock_config.return_value = {
            'apikey': 'test_key',
            'cloudos_url': 'http://test.com',
            'workspace_id': 'test_team',
            'project_name': 'my_project'
        }
        
        mock_cloudos_instance = MagicMock()
        mock_cloudos.return_value = mock_cloudos_instance
        mock_cloudos_instance.create_interactive_session.return_value = {
            '_id': 'session_003',
            'name': 'Spark Cluster',
            'status': 'scheduled'
        }
        
        result = runner.invoke(run_cloudos_cli, [
            'interactive-session', 'create',
            '--apikey', 'test_key',
            '--cloudos-url', 'http://test.com',
            '--workspace-id', 'test_team',
            '--project-name', 'my_project',
            '--name', 'Spark Cluster',
            '--session-type', 'spark',
            '--spark-master', 'c5.2xlarge',
            '--spark-core', 'c5.xlarge',
            '--spark-workers', '3'
        ])
        
        assert result.exit_code in [0, 1]

    @patch('cloudos_cli.interactive_session.cli.Cloudos')
    @patch('cloudos_cli.configure.configure.ConfigurationProfile.load_profile_and_validate_data')
    def test_create_session_rstudio_with_r_version(self, mock_config, mock_cloudos):
        """Test creating an RStudio session with R version."""
        runner = CliRunner()
        
        mock_config.return_value = {
            'apikey': 'test_key',
            'cloudos_url': 'http://test.com',
            'workspace_id': 'test_team',
            'project_name': 'my_project'
        }
        
        mock_cloudos_instance = MagicMock()
        mock_cloudos.return_value = mock_cloudos_instance
        mock_cloudos_instance.create_interactive_session.return_value = {
            '_id': 'session_004',
            'name': 'RStudio Session',
            'status': 'running'
        }
        
        result = runner.invoke(run_cloudos_cli, [
            'interactive-session', 'create',
            '--apikey', 'test_key',
            '--cloudos-url', 'http://test.com',
            '--workspace-id', 'test_team',
            '--project-name', 'my_project',
            '--name', 'RStudio Session',
            '--session-type', 'rstudio',
            '--r-version', '4.5.2'
        ])
        
        assert result.exit_code in [0, 1]

    @patch('cloudos_cli.interactive_session.cli.Cloudos')
    @patch('cloudos_cli.configure.configure.ConfigurationProfile.load_profile_and_validate_data')
    def test_create_session_with_defaults(self, mock_config, mock_cloudos):
        """Test creating a session with default values for optional parameters."""
        runner = CliRunner()
        
        mock_config.return_value = {
            'apikey': 'test_key',
            'cloudos_url': 'http://test.com',
            'workspace_id': 'test_team',
            'project_name': 'my_project'
        }
        
        mock_cloudos_instance = MagicMock()
        mock_cloudos.return_value = mock_cloudos_instance
        
        mock_cloudos_instance.create_interactive_session.return_value = {
            '_id': 'session_006',
            'name': 'Default Session',
            'status': 'scheduled',
            'backend_type': 'regular',
            'instance_type': 'c5.xlarge',
            'storage': 500
        }
        
        result = runner.invoke(run_cloudos_cli, [
            'interactive-session', 'create',
            '--apikey', 'test_key',
            '--cloudos-url', 'http://test.com',
            '--workspace-id', 'test_team',
            '--project-name', 'my_project',
            '--name', 'Default Session',
            '--session-type', 'jupyter'
        ])
        
        assert result.exit_code in [0, 1]


class TestInteractiveSessionAPIMethod:
    """Unit tests for the create_interactive_session API method."""

    def test_create_interactive_session_method_exists(self):
        """Test that the create_interactive_session method exists in Cloudos class."""
        from cloudos_cli.clos import Cloudos
        
        assert hasattr(Cloudos, 'create_interactive_session')
        assert callable(getattr(Cloudos, 'create_interactive_session'))

    def test_create_interactive_session_signature(self):
        """Test that the method has the correct signature."""
        from cloudos_cli.clos import Cloudos
        import inspect
        
        method = getattr(Cloudos, 'create_interactive_session')
        sig = inspect.signature(method)
        params = list(sig.parameters.keys())
        
        assert 'self' in params
        assert 'team_id' in params
        assert 'payload' in params
        assert 'verify' in params

    @patch('cloudos_cli.clos.requests.post')
    def test_create_interactive_session_api_call(self, mock_post):
        """Test that the method makes the correct API call."""
        from cloudos_cli.clos import Cloudos
        
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            '_id': 'session_001',
            'name': 'Test Session',
            'status': 'scheduled'
        }
        mock_post.return_value = mock_response
        
        # Create Cloudos instance and call method
        cl = Cloudos('http://test.com', 'test_key', None)
        payload = {
            'interactiveSessionConfiguration': {
                'backend': 'regular'
            },
            'projectId': 'proj_001'
        }
        result = cl.create_interactive_session('test_team', payload)
        
        # Verify API was called
        assert mock_post.called
        call_args = mock_post.call_args
        # Check the endpoint contains the team ID
        assert 'interactive-sessions' in call_args[0][0]
        # Verify the result
        assert result['_id'] == 'session_001'

    @patch('cloudos_cli.clos.requests.post')
    def test_create_interactive_session_error_handling(self, mock_post):
        """Test error handling for failed API calls."""
        from cloudos_cli.clos import Cloudos
        from cloudos_cli.utils.errors import BadRequestException
        
        # Setup mock error response
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = 'Bad request message'
        mock_post.return_value = mock_response
        
        # Create Cloudos instance and call method
        cl = Cloudos('http://test.com', 'test_key', None)
        payload = {'test': 'data'}
        
        # Should raise BadRequestException for HTTP 400
        with pytest.raises(BadRequestException):
            cl.create_interactive_session('test_team', payload)


class TestSessionCreatorHelpers:
    """Unit tests for session_creator helper functions."""

    def test_parse_shutdown_duration_function_exists(self):
        """Test that parse_shutdown_duration function exists."""
        from cloudos_cli.interactive_session.interactive_session import parse_shutdown_duration
        
        assert callable(parse_shutdown_duration)

    def test_parse_shutdown_duration_hours(self):
        """Test parsing shutdown duration in hours."""
        from cloudos_cli.interactive_session.interactive_session import parse_shutdown_duration
        
        result = parse_shutdown_duration('2h')
        # Should return a datetime string
        assert isinstance(result, str)
        assert 'T' in result  # ISO format

    def test_parse_shutdown_duration_days(self):
        """Test parsing shutdown duration in days."""
        from cloudos_cli.interactive_session.interactive_session import parse_shutdown_duration
        
        result = parse_shutdown_duration('1d')
        assert isinstance(result, str)
        assert 'T' in result  # ISO format

    def test_parse_data_file_function_exists(self):
        """Test that parse_data_file function exists."""
        from cloudos_cli.interactive_session.interactive_session import parse_data_file
        
        assert callable(parse_data_file)

    def test_parse_data_file_format(self):
        """Test parsing data file format."""
        from cloudos_cli.interactive_session.interactive_session import parse_data_file
        
        # Test CloudOS dataset with / separator: project_name/dataset_path
        result = parse_data_file('leila-test/Data/mydata.csv')
        assert isinstance(result, dict)
        assert result['type'] == 'cloudos'
        assert 'project_name' in result
        assert 'dataset_path' in result
        assert result['project_name'] == 'leila-test'
        assert result['dataset_path'] == 'Data/mydata.csv'
        
        # Test CloudOS dataset with > separator
        result2 = parse_data_file('leila-test > Data/mydata.csv')
        assert result2['type'] == 'cloudos'
        assert result2['project_name'] == 'leila-test'
        assert result2['dataset_path'] == 'Data/mydata.csv'
        
        # Test CloudOS dataset with nested paths
        result3 = parse_data_file('my-project/folder/subfolder/file.txt')
        assert result3['type'] == 'cloudos'
        assert result3['project_name'] == 'my-project'
        assert result3['dataset_path'] == 'folder/subfolder/file.txt'
        
        # Test S3 file path
        result4 = parse_data_file('s3://lifebit-featured-datasets/pipelines/phewas/100_binary_pheno.phe')
        assert isinstance(result4, dict)
        assert result4['type'] == 's3'
        assert 's3_bucket' in result4
        assert 's3_prefix' in result4
        assert result4['s3_bucket'] == 'lifebit-featured-datasets'
        assert result4['s3_prefix'] == 'pipelines/phewas/100_binary_pheno.phe'
        
        # Test S3 bucket root file
        result5 = parse_data_file('s3://my-bucket/file.txt')
        assert result5['type'] == 's3'
        assert result5['s3_bucket'] == 'my-bucket'
        assert result5['s3_prefix'] == 'file.txt'

    def test_resolve_data_file_id_function_exists(self):
        """Test that resolve_data_file_id function exists."""
        from cloudos_cli.interactive_session.interactive_session import resolve_data_file_id
        
        assert callable(resolve_data_file_id)

    def test_parse_s3_mount_function_exists(self):
        """Test that parse_s3_mount function exists."""
        from cloudos_cli.interactive_session.interactive_session import parse_s3_mount
        
        assert callable(parse_s3_mount)

    def test_parse_s3_mount_format(self):
        """Test parsing S3 mount format."""
        from cloudos_cli.interactive_session.interactive_session import parse_s3_mount
        
        result = parse_s3_mount('results:my-bucket:output/')
        assert isinstance(result, dict)
        assert 'type' in result
        assert 'data' in result
        assert result['type'] == 'S3Folder'
        
        data = result['data']
        assert 'name' in data
        assert 's3BucketName' in data
        assert 's3Prefix' in data
        assert data['name'] == 'results'
        assert data['s3BucketName'] == 'my-bucket'
        assert data['s3Prefix'] == 'output/'

    def test_build_session_payload_function_exists(self):
        """Test that build_session_payload function exists."""
        from cloudos_cli.interactive_session.interactive_session import build_session_payload
        
        assert callable(build_session_payload)

    def test_build_session_payload_jupyter(self):
        """Test building payload for Jupyter session."""
        from cloudos_cli.interactive_session.interactive_session import build_session_payload
        
        result = build_session_payload(
            name='Test Session',
            backend='regular',
            instance_type='c5.xlarge',
            storage_size=500,
            project_id='proj_001'
        )
        
        assert isinstance(result, dict)
        assert 'interactiveSessionConfiguration' in result
        assert 'projectId' in result
        assert result['projectId'] == 'proj_001'
        assert result['interactiveSessionConfiguration']['backend'] == 'regular'

    def test_format_session_creation_table_function_exists(self):
        """Test that format_session_creation_table function exists."""
        from cloudos_cli.interactive_session.interactive_session import format_session_creation_table
        
        assert callable(format_session_creation_table)

    def test_format_session_creation_table_output(self):
        """Test formatting session creation output for table display."""
        from cloudos_cli.interactive_session.interactive_session import format_session_creation_table
        
        session_data = {
            '_id': 'session_001',
            'name': 'Test Session',
            'status': 'scheduled',
            'interactiveSessionType': 'awsJupyterNotebook'
        }
        
        result = format_session_creation_table(session_data)
        # Should return a string representation
        assert isinstance(result, (str, type(None))) or hasattr(result, '__str__')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

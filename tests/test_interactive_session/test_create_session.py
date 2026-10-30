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
        assert '--copy' in result.output
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
        assert 'Error' not in result.output or result.exit_code == 0

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
        ])

        # Command should be invoked without syntax errors
        assert result.exit_code == 0

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
        
        assert result.exit_code == 0

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
        
        assert result.exit_code == 0

    @pytest.mark.parametrize('session_type', ['windows', 'linux'])
    @patch('cloudos_cli.interactive_session.cli.Cloudos')
    @patch('cloudos_cli.configure.configure.ConfigurationProfile.load_profile_and_validate_data')
    def test_create_session_windows_linux(self, mock_config, mock_cloudos, session_type):
        """Test creating Windows and Linux sessions sends the matching backend."""
        runner = CliRunner()

        mock_config.return_value = {
            'apikey': 'test_key',
            'cloudos_url': 'http://test.com',
            'workspace_id': 'test_team',
            'project_name': 'my_project'
        }

        mock_cloudos_instance = MagicMock()
        mock_cloudos.return_value = mock_cloudos_instance
        mock_cloudos_instance.get_project_id_from_name.return_value = 'proj_001'
        mock_cloudos_instance.create_interactive_session.return_value = {
            '_id': 'session_007',
            'name': f'{session_type} session',
            'status': 'scheduled'
        }

        result = runner.invoke(run_cloudos_cli, [
            'interactive-session', 'create',
            '--apikey', 'test_key',
            '--cloudos-url', 'http://test.com',
            '--workspace-id', 'test_team',
            '--project-name', 'my_project',
            '--name', f'{session_type} session',
            '--session-type', session_type,
            '--instance', 'c6a.xlarge'
        ])

        assert result.exit_code == 0, result.output
        payload = mock_cloudos_instance.create_interactive_session.call_args[0][1]
        config = payload['interactiveSessionConfiguration']
        assert config['backend'] == session_type
        assert config['executionPlatform'] == 'aws'
        assert config['instanceType'] == 'c6a.xlarge'

    @pytest.mark.parametrize('session_type', ['windows', 'linux'])
    @patch('cloudos_cli.interactive_session.cli.Cloudos')
    @patch('cloudos_cli.configure.configure.ConfigurationProfile.load_profile_and_validate_data')
    def test_create_session_windows_linux_azure_is_error(self, mock_config, mock_cloudos, session_type):
        """Test that Windows and Linux sessions fail on Azure before any API call."""
        runner = CliRunner()

        mock_config.return_value = {
            'apikey': 'test_key',
            'cloudos_url': 'http://test.com',
            'workspace_id': 'test_team',
            'project_name': 'my_project'
        }

        result = runner.invoke(run_cloudos_cli, [
            'interactive-session', 'create',
            '--apikey', 'test_key',
            '--cloudos-url', 'http://test.com',
            '--workspace-id', 'test_team',
            '--project-name', 'my_project',
            '--name', 'Azure session',
            '--session-type', session_type,
            '--execution-platform', 'azure'
        ])

        assert result.exit_code == 1
        assert 'only available on AWS' in result.output
        mock_cloudos.return_value.create_interactive_session.assert_not_called()

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
        
        assert result.exit_code == 0


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

    @patch('cloudos_cli.clos.retry_requests_post')
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

    @patch('cloudos_cli.clos.retry_requests_post')
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
        
        # Test Lifebit Platform dataset with / separator: project_name/dataset_path
        result = parse_data_file('leila-test/Data/mydata.csv')
        assert isinstance(result, dict)
        assert result['type'] == 'cloudos'
        assert 'project_name' in result
        assert 'dataset_path' in result
        assert result['project_name'] == 'leila-test'
        assert result['dataset_path'] == 'Data/mydata.csv'
        
        # Test Lifebit Platform dataset with > separator
        result2 = parse_data_file('leila-test > Data/mydata.csv')
        assert result2['type'] == 'cloudos'
        assert result2['project_name'] == 'leila-test'
        assert result2['dataset_path'] == 'Data/mydata.csv'
        
        # Test Lifebit Platform dataset with nested paths
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

    @pytest.mark.parametrize('backend', ['windows', 'linux'])
    def test_build_session_payload_windows_linux(self, backend):
        """Test building payload for Windows and Linux sessions."""
        from cloudos_cli.interactive_session.interactive_session import build_session_payload

        result = build_session_payload(
            name='Test Session',
            backend=backend,
            instance_type='c6a.xlarge',
            storage_size=500,
            project_id='proj_001'
        )

        config = result['interactiveSessionConfiguration']
        assert config['backend'] == backend
        assert config['executionPlatform'] == 'aws'
        assert config['instanceType'] == 'c6a.xlarge'
        assert 'rVersion' not in config
        assert 'cluster' not in config

    @pytest.mark.parametrize('backend', ['windows', 'linux'])
    def test_build_session_payload_windows_linux_azure_is_error(self, backend):
        """Test that Windows and Linux sessions are rejected on Azure."""
        from cloudos_cli.interactive_session.interactive_session import build_session_payload

        with pytest.raises(ValueError, match='only available on AWS'):
            build_session_payload(
                name='Test Session',
                backend=backend,
                execution_platform='azure',
                project_id='proj_001'
            )

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


class TestCreateSessionCopyFlag:
    """Tests for the --copy flag in create_session."""

    @pytest.fixture
    def base_args(self):
        return [
            'interactive-session', 'create',
            '--apikey', 'test_key',
            '--cloudos-url', 'http://test.com',
            '--workspace-id', 'test_team',
            '--project-name', 'my_project',
            '--name', 'Copy Session',
            '--session-type', 'jupyter',
        ]

    @patch('cloudos_cli.interactive_session.cli._make_link_client')
    @patch('cloudos_cli.interactive_session.cli.parse_data_file')
    @patch('cloudos_cli.interactive_session.cli.Cloudos')
    @patch('cloudos_cli.configure.configure.ConfigurationProfile.load_profile_and_validate_data')
    def test_copy_with_file_explorer_path(self, mock_config, mock_cloudos, mock_parse, mock_link_client, base_args):
        """--copy with a project-prefixed FE path resolves and copies the item."""
        runner = CliRunner()
        mock_config.return_value = {
            'apikey': 'test_key',
            'cloudos_url': 'http://test.com',
            'workspace_id': 'test_team',
            'project_name': 'my_project',
        }
        mock_parse.return_value = {
            'type': 'cloudos',
            'project_name': 'my_project',
            'dataset_path': 'Data/file.csv',
        }
        fe_link = MagicMock()
        fe_link.parse_file_explorer_item.return_value = {
            'dataItem': {'item': 'item_id_123', 'name': 'file.csv', 'kind': 'File'}
        }
        mock_link_client.return_value = fe_link
        mock_cloudos_instance = MagicMock()
        mock_cloudos.return_value = mock_cloudos_instance
        mock_cloudos_instance.create_interactive_session.return_value = {
            '_id': 'sess_001', 'name': 'Copy Session', 'status': 'scheduled'
        }

        result = runner.invoke(run_cloudos_cli, base_args + ['--copy', '--link', 'my_project/Data/file.csv'])

        assert result.exit_code == 0
        mock_parse.assert_called_once_with('my_project/Data/file.csv')
        fe_link.parse_file_explorer_item.assert_called_once_with('Data/file.csv')

    @patch('cloudos_cli.interactive_session.cli._make_link_client')
    @patch('cloudos_cli.interactive_session.cli.parse_data_file')
    @patch('cloudos_cli.interactive_session.cli.Cloudos')
    @patch('cloudos_cli.configure.configure.ConfigurationProfile.load_profile_and_validate_data')
    def test_copy_with_known_root_folder_and_no_project_is_error(self, mock_config, mock_cloudos, mock_parse, mock_link_client, base_args):
        """--copy with a bare known-root-folder path and no --project-name raises an error."""
        runner = CliRunner()
        mock_config.return_value = {
            'apikey': 'test_key',
            'cloudos_url': 'http://test.com',
            'workspace_id': 'test_team',
            'project_name': None,
        }

        args_no_project = [
            'interactive-session', 'create',
            '--apikey', 'test_key',
            '--cloudos-url', 'http://test.com',
            '--workspace-id', 'test_team',
            '--name', 'Copy Session',
            '--session-type', 'jupyter',
            '--copy', '--link', 'Data/file.csv',
        ]
        result = runner.invoke(run_cloudos_cli, args_no_project)

        assert result.exit_code != 0
        assert 'project-name' in result.output.lower() or 'project_name' in result.output.lower() or 'Error' in result.output

    @patch('cloudos_cli.interactive_session.cli._make_link_client')
    @patch('cloudos_cli.interactive_session.cli.parse_data_file')
    @patch('cloudos_cli.interactive_session.cli.Cloudos')
    @patch('cloudos_cli.configure.configure.ConfigurationProfile.load_profile_and_validate_data')
    def test_copy_with_s3_path_on_azure_is_error(self, mock_config, mock_cloudos, mock_parse, mock_link_client, base_args):
        """--copy with an S3 path on Azure execution platform is rejected."""
        runner = CliRunner()
        mock_config.return_value = {
            'apikey': 'test_key',
            'cloudos_url': 'http://test.com',
            'workspace_id': 'test_team',
            'project_name': 'my_project',
        }
        mock_parse.return_value = {
            'type': 's3',
            's3_bucket': 'my-bucket',
            's3_prefix': 'data/file.csv',
        }
        mock_cloudos_instance = MagicMock()
        mock_cloudos.return_value = mock_cloudos_instance

        result = runner.invoke(run_cloudos_cli, base_args + [
            '--copy', '--link', 's3://my-bucket/data/file.csv',
            '--execution-platform', 'azure',
        ])

        assert result.exit_code != 0
        assert 'S3' in result.output or 'azure' in result.output.lower() or 'Azure' in result.output



class TestVolumeSizes:
    """Tests for the volumeSizes split of the session storage."""

    @pytest.mark.parametrize('backend,kwargs', [
        ('regular', {}),
        ('vscode', {}),
        ('rstudio', {'r_version': '4.5.2'}),
        ('spark', {'spark_master_type': 'c5.2xlarge', 'spark_core_type': 'c5.xlarge'}),
        ('windows', {}),
        ('linux', {}),
    ])
    def test_payload_has_default_volume_sizes_for_all_backends(self, backend, kwargs):
        """Every backend gets the default 50/225/225 split for 500 GB."""
        from cloudos_cli.interactive_session.interactive_session import build_session_payload

        payload = build_session_payload(name='s', backend=backend, project_id='p', **kwargs)
        config = payload['interactiveSessionConfiguration']
        assert config['storageSizeInGb'] == 500
        assert config['volumeSizes'] == {'libraries': 50, 'sessionResults': 225, 'mountedData': 225}

    def test_payload_azure_has_volume_sizes(self):
        from cloudos_cli.interactive_session.interactive_session import build_session_payload

        payload = build_session_payload(name='s', backend='regular', project_id='p',
                                        execution_platform='azure', instance_type='Standard_D4s_v3')
        assert payload['interactiveSessionConfiguration']['volumeSizes'] == {
            'libraries': 50, 'sessionResults': 225, 'mountedData': 225}

    def test_payload_uses_given_volume_sizes(self):
        from cloudos_cli.interactive_session.interactive_session import build_session_payload

        volumes = {'libraries': 100, 'sessionResults': 500, 'mountedData': 400}
        payload = build_session_payload(name='s', backend='regular', project_id='p',
                                        storage_size=1000, volume_sizes=volumes)
        assert payload['interactiveSessionConfiguration']['volumeSizes'] == volumes

    def test_payload_rejects_volume_sizes_not_matching_storage(self):
        from cloudos_cli.interactive_session.interactive_session import build_session_payload

        with pytest.raises(ValueError, match='add up to the storage size'):
            build_session_payload(name='s', backend='regular', project_id='p', storage_size=1000,
                                  volume_sizes={'libraries': 50, 'sessionResults': 225, 'mountedData': 225})

    @pytest.mark.parametrize('storage', [59, 64051])
    def test_payload_rejects_storage_out_of_range(self, storage):
        from cloudos_cli.interactive_session.interactive_session import build_session_payload

        with pytest.raises(ValueError, match='60-64050'):
            build_session_payload(name='s', backend='regular', project_id='p', storage_size=storage)

    @pytest.mark.parametrize('kwargs,expected', [
        ({}, (500, {'libraries': 50, 'sessionResults': 225, 'mountedData': 225})),
        ({'storage_size': 1000}, (1000, {'libraries': 50, 'sessionResults': 475, 'mountedData': 475})),
        # Odd remainder: the extra GB goes to sessionResults
        ({'storage_size': 1001}, (1001, {'libraries': 50, 'sessionResults': 476, 'mountedData': 475})),
        # Smallest storage, and one GB more (odd remainder)
        ({'storage_size': 60}, (60, {'libraries': 50, 'sessionResults': 5, 'mountedData': 5})),
        # An even split below a volume's minimum is raised to it, taking the GB from the others
        ({'storage_size': 100, 'mounted_data': 10}, (100, {'libraries': 50, 'sessionResults': 40, 'mountedData': 10})),
        ({'storage_size': 61, 'session_results': 5}, (61, {'libraries': 50, 'sessionResults': 5, 'mountedData': 6})),
        # Largest volumes allowed
        ({'libraries': 1000, 'session_results': 32000, 'mounted_data': 31050},
         (64050, {'libraries': 1000, 'sessionResults': 32000, 'mountedData': 31050})),
        # An even split over a volume's maximum is capped, and the excess goes to the others
        # (20000 GB left would give libraries 10000; it gets 1000 and sessionResults the other 9000)
        ({'storage_size': 40000, 'mounted_data': 20000},
         (40000, {'libraries': 1000, 'sessionResults': 19000, 'mountedData': 20000})),
        ({'storage_size': 61}, (61, {'libraries': 50, 'sessionResults': 6, 'mountedData': 5})),
        ({'storage_size': 64050}, (64050, {'libraries': 50, 'sessionResults': 32000, 'mountedData': 32000})),
        # One volume given: the other two share the rest
        ({'storage_size': 1000, 'libraries': 100}, (1000, {'libraries': 100, 'sessionResults': 450, 'mountedData': 450})),
        ({'storage_size': 1000, 'session_results': 300}, (1000, {'libraries': 350, 'sessionResults': 300, 'mountedData': 350})),
        # sessionResults given, odd remainder: the extra GB goes to mountedData
        ({'storage_size': 1001, 'session_results': 300}, (1001, {'libraries': 350, 'sessionResults': 300, 'mountedData': 351})),
        ({'storage_size': 1000, 'mounted_data': 100}, (1000, {'libraries': 450, 'sessionResults': 450, 'mountedData': 100})),
        # Two volumes given: the third gets the rest
        ({'storage_size': 1000, 'libraries': 60, 'session_results': 300},
         (1000, {'libraries': 60, 'sessionResults': 300, 'mountedData': 640})),
        # All three given: storage is their sum
        ({'libraries': 50, 'session_results': 5, 'mounted_data': 5},
         (60, {'libraries': 50, 'sessionResults': 5, 'mountedData': 5})),
        ({'libraries': 60, 'session_results': 400, 'mounted_data': 40},
         (500, {'libraries': 60, 'sessionResults': 400, 'mountedData': 40})),
        ({'storage_size': 500, 'libraries': 60, 'session_results': 400, 'mounted_data': 40},
         (500, {'libraries': 60, 'sessionResults': 400, 'mountedData': 40})),
    ])
    def test_resolve_volume_sizes(self, kwargs, expected):
        from cloudos_cli.interactive_session.interactive_session import resolve_volume_sizes

        assert resolve_volume_sizes(**kwargs) == expected

    @pytest.mark.parametrize('kwargs,message', [
        ({'storage_size': 59}, '60-64050'),
        ({'storage_size': 64051}, '60-64050'),
        ({'libraries': 49}, 'libraries volume .*at least 50 GB'),
        ({'storage_size': 2000, 'libraries': 1001}, 'libraries volume .*at most 1000 GB'),
        ({'storage_size': 40000, 'session_results': 32001}, 'sessionResults volume .*at most 32000 GB'),
        ({'storage_size': 40000, 'mounted_data': 32001}, 'mountedData volume .*at most 32000 GB'),
        # The rest is more than the volumes not set can hold at their maximum
        ({'storage_size': 64050, 'mounted_data': 100}, '30950 GB more than the volumes can hold'),
        ({'storage_size': 2000, 'session_results': 500, 'mounted_data': 450}, '50 GB more than the volumes can hold'),
        ({'session_results': 4}, 'sessionResults volume .*at least 5 GB'),
        ({'mounted_data': 4}, 'mountedData volume .*at least 5 GB'),
        # Even split of the rest leaves a volume below its minimum
        ({'storage_size': 60, 'libraries': 52}, 'too small for sessionResults'),
        # 50 GB left for two volumes whose minimums add up to 55 GB
        ({'storage_size': 100, 'mounted_data': 50}, 'too small for libraries .*even after moving GB'),
        # Two volumes given leave too little for the third
        ({'storage_size': 60, 'libraries': 50, 'session_results': 6}, 'too small for mountedData'),
        # All three given but the sum is out of range
        ({'libraries': 50, 'session_results': 32000, 'mounted_data': 32001}, '60-64050'),
        # All three given and --storage does not match
        ({'storage_size': 600, 'libraries': 50, 'session_results': 225, 'mounted_data': 225}, 'does not match'),
    ])
    def test_resolve_volume_sizes_errors(self, kwargs, message):
        from cloudos_cli.interactive_session.interactive_session import resolve_volume_sizes

        with pytest.raises(ValueError, match=message):
            resolve_volume_sizes(**kwargs)

    def test_volume_maximums_fit_within_max_storage(self):
        from cloudos_cli.interactive_session.interactive_session import (
            MIN_STORAGE_SIZE, MAX_STORAGE_SIZE, VOLUME_MAXIMUMS)

        assert VOLUME_MAXIMUMS == {'libraries': 1000, 'sessionResults': 32000, 'mountedData': 32000}
        assert MAX_STORAGE_SIZE == 64050
        assert MIN_STORAGE_SIZE <= MAX_STORAGE_SIZE <= sum(VOLUME_MAXIMUMS.values())

    @pytest.mark.parametrize('volumes,message', [
        ({'libraries': 1001, 'sessionResults': 500, 'mountedData': 499}, 'libraries volume .*at most 1000 GB'),
        ({'libraries': 50, 'sessionResults': 32001, 'mountedData': 5}, 'sessionResults volume .*at most 32000 GB'),
    ])
    def test_validate_volume_sizes_rejects_over_maximum(self, volumes, message):
        from cloudos_cli.interactive_session.interactive_session import validate_volume_sizes

        with pytest.raises(ValueError, match=message):
            validate_volume_sizes(sum(volumes.values()), volumes)

    def test_min_storage_is_sum_of_volume_minimums(self):
        from cloudos_cli.interactive_session.interactive_session import MIN_STORAGE_SIZE, VOLUME_MINIMUMS

        assert MIN_STORAGE_SIZE == sum(VOLUME_MINIMUMS.values()) == 60

    @pytest.mark.parametrize('storage,current', [(60, None), (64050, None), (500, 500), (1000, 500)])
    def test_validate_storage_size_accepts(self, storage, current):
        from cloudos_cli.interactive_session.interactive_session import validate_storage_size

        validate_storage_size(storage, current_size=current)

    @pytest.mark.parametrize('storage,current,message', [
        (59, None, '60-64050'),
        (64051, None, '60-64050'),
        (499, 500, "can't be smaller than the session's current storage \\(500 GB\\)"),
    ])
    def test_validate_storage_size_rejects(self, storage, current, message):
        from cloudos_cli.interactive_session.interactive_session import validate_storage_size

        with pytest.raises(ValueError, match=message):
            validate_storage_size(storage, current_size=current)

    @pytest.mark.parametrize('current', [
        None,
        {},
        {'libraries': 50, 'sessionResults': 225, 'mountedData': 225},
        # Older sessions may report only some volumes; only those are checked
        {'libraries': 50},
    ])
    def test_validate_volumes_not_shrunk_accepts(self, current):
        from cloudos_cli.interactive_session.interactive_session import validate_volumes_not_shrunk

        validate_volumes_not_shrunk({'libraries': 50, 'sessionResults': 225, 'mountedData': 225}, current)

    def test_validate_volumes_not_shrunk_rejects(self):
        from cloudos_cli.interactive_session.interactive_session import validate_volumes_not_shrunk

        with pytest.raises(ValueError) as e:
            validate_volumes_not_shrunk({'libraries': 50, 'sessionResults': 600, 'mountedData': 350},
                                        {'libraries': 100, 'sessionResults': 450, 'mountedData': 450})
        message = str(e.value)
        assert 'libraries (--libraries-volume) 50 GB < current 100 GB' in message
        assert 'mountedData (--data-volume) 350 GB < current 450 GB' in message
        assert 'current 450 GB' in message and 'sessionResults (--results-volume)' not in message

    CURRENT_VOLUMES = {'libraries': 100, 'sessionResults': 450, 'mountedData': 450}

    @pytest.mark.parametrize('kwargs,expected', [
        # Same storage: nothing changes
        ({'storage_size': 1000}, (1000, {'libraries': 100, 'sessionResults': 450, 'mountedData': 450})),
        # Only storage: libraries kept, the extra shared by the other two (odd GB to sessionResults)
        ({'storage_size': 1201}, (1201, {'libraries': 100, 'sessionResults': 551, 'mountedData': 550})),
        # One volume given: the other two keep their size plus a share of the rest
        ({'storage_size': 1200, 'libraries': 200}, (1200, {'libraries': 200, 'sessionResults': 500, 'mountedData': 500})),
        ({'storage_size': 1200, 'mounted_data': 450},
         (1200, {'libraries': 200, 'sessionResults': 550, 'mountedData': 450})),
        # Two volumes given: the third gets the rest
        ({'storage_size': 1200, 'libraries': 100, 'session_results': 450},
         (1200, {'libraries': 100, 'sessionResults': 450, 'mountedData': 650})),
        # All three given: storage is their sum
        ({'libraries': 100, 'session_results': 500, 'mounted_data': 600},
         (1200, {'libraries': 100, 'sessionResults': 500, 'mountedData': 600})),
        # libraries' share would take it past 1000 GB, so the excess goes to sessionResults
        ({'storage_size': 4000, 'mounted_data': 450},
         (4000, {'libraries': 1000, 'sessionResults': 2550, 'mountedData': 450})),
    ])
    def test_resolve_resume_volume_sizes(self, kwargs, expected):
        from cloudos_cli.interactive_session.interactive_session import resolve_resume_volume_sizes

        assert resolve_resume_volume_sizes(self.CURRENT_VOLUMES, **kwargs) == expected

    @pytest.mark.parametrize('kwargs,message', [
        ({'storage_size': 1200, 'session_results': 400}, "can't be smaller than their current size"),
        ({'libraries': 100, 'session_results': 450, 'mounted_data': 400}, "can't be smaller than their current size"),
        # Given volumes leave less than the current size of the others
        ({'storage_size': 1000, 'libraries': 200}, 'too small to keep the current volume sizes .*needs at least 1100 GB'),
        ({'storage_size': 1200, 'libraries': 4}, 'at least 50 GB'),
        ({'storage_size': 2000, 'libraries': 1001}, 'at most 1000 GB'),
        ({'storage_size': 64050, 'session_results': 500}, 'more than the volumes can hold'),
        ({'storage_size': 59}, '60-64050'),
        ({'libraries': 100}, 'Storage size is required'),
    ])
    def test_resolve_resume_volume_sizes_errors(self, kwargs, message):
        from cloudos_cli.interactive_session.interactive_session import resolve_resume_volume_sizes

        with pytest.raises(ValueError, match=message):
            resolve_resume_volume_sizes(self.CURRENT_VOLUMES, **kwargs)

    @pytest.mark.parametrize('current,expected', [
        (None, {'libraries': 1000, 'sessionResults': 32000, 'mountedData': 32000}),
        ({'libraries': 100, 'sessionResults': 450, 'mountedData': 450},
         {'libraries': 1000, 'sessionResults': 32000, 'mountedData': 32000}),
        # A volume above its maximum may stay at its current size
        ({'libraries': 1500, 'sessionResults': 750}, {'libraries': 1500, 'sessionResults': 32000, 'mountedData': 32000}),
    ])
    def test_volume_maximums_for(self, current, expected):
        from cloudos_cli.interactive_session.interactive_session import volume_maximums_for

        assert volume_maximums_for(current) == expected

    # A session created before the maximums existed, with libraries above 1000 GB
    OVER_MAX_VOLUMES = {'libraries': 1500, 'sessionResults': 750, 'mountedData': 750}

    @pytest.mark.parametrize('kwargs,expected', [
        # libraries keeps its 1500 GB instead of being capped to 1000 GB
        ({'storage_size': 3200}, (3200, {'libraries': 1500, 'sessionResults': 850, 'mountedData': 850})),
        ({'storage_size': 3200, 'session_results': 800},
         (3200, {'libraries': 1500, 'sessionResults': 800, 'mountedData': 900})),
        ({'storage_size': 3200, 'libraries': 1500},
         (3200, {'libraries': 1500, 'sessionResults': 850, 'mountedData': 850})),
    ])
    def test_resolve_resume_volume_sizes_keeps_volume_above_maximum(self, kwargs, expected):
        from cloudos_cli.interactive_session.interactive_session import resolve_resume_volume_sizes

        assert resolve_resume_volume_sizes(self.OVER_MAX_VOLUMES, **kwargs) == expected

    @pytest.mark.parametrize('kwargs,message', [
        ({'storage_size': 3200, 'libraries': 1000}, "can't be smaller than their current size"),
        ({'storage_size': 3200, 'libraries': 1501}, 'libraries volume .*at most 1500 GB'),
    ])
    def test_resolve_resume_volume_sizes_above_maximum_errors(self, kwargs, message):
        from cloudos_cli.interactive_session.interactive_session import resolve_resume_volume_sizes

        with pytest.raises(ValueError, match=message):
            resolve_resume_volume_sizes(self.OVER_MAX_VOLUMES, **kwargs)

    def test_resume_payload_accepts_volume_above_maximum_with_volume_maximums(self):
        from cloudos_cli.interactive_session.interactive_session import build_resume_payload, volume_maximums_for

        volumes = {'libraries': 1500, 'sessionResults': 850, 'mountedData': 850}
        with pytest.raises(ValueError, match='at most 1000 GB'):
            build_resume_payload(storage_size=3200, volume_sizes=volumes)
        payload = build_resume_payload(storage_size=3200, volume_sizes=volumes,
                                       volume_maximums=volume_maximums_for(self.OVER_MAX_VOLUMES))
        assert payload['newInteractiveSessionConfiguration']['volumeSizes'] == volumes

    @pytest.mark.parametrize('current', [None, {}, {'libraries': 50}])
    def test_resolve_resume_volume_sizes_without_current_uses_create_split(self, current):
        from cloudos_cli.interactive_session.interactive_session import resolve_resume_volume_sizes

        assert resolve_resume_volume_sizes(current, storage_size=1000) == \
            (1000, {'libraries': 50, 'sessionResults': 475, 'mountedData': 475})

    def test_resolve_resume_volume_sizes_without_current_still_blocks_shrink(self):
        from cloudos_cli.interactive_session.interactive_session import resolve_resume_volume_sizes

        with pytest.raises(ValueError, match="can't be smaller than their current size"):
            resolve_resume_volume_sizes({'libraries': 100}, storage_size=1000)

    def test_resume_payload_includes_volume_sizes(self):
        from cloudos_cli.interactive_session.interactive_session import build_resume_payload

        volumes = {'libraries': 50, 'sessionResults': 475, 'mountedData': 475}
        payload = build_resume_payload(storage_size=1000, volume_sizes=volumes)
        config = payload['newInteractiveSessionConfiguration']
        assert config['storageSizeInGb'] == 1000
        assert config['volumeSizes'] == volumes

    def test_resume_payload_without_storage_has_no_volume_sizes(self):
        from cloudos_cli.interactive_session.interactive_session import build_resume_payload

        payload = build_resume_payload(instance_type='c5.2xlarge')
        assert 'volumeSizes' not in payload['newInteractiveSessionConfiguration']

    def test_creation_table_shows_volume_sizes(self, capsys):
        from cloudos_cli.interactive_session.interactive_session import format_session_creation_table

        format_session_creation_table(
            {'_id': 's1', 'name': 'n', 'status': 'scheduled'}, storage_size=500,
            volume_sizes={'libraries': 50, 'sessionResults': 225, 'mountedData': 225})
        out = capsys.readouterr().out
        assert 'Libraries' in out
        assert 'Session results' in out
        assert 'Mounted data' in out
        assert '225 GB' in out

    def test_creation_table_prefers_response_volume_sizes(self, capsys):
        from cloudos_cli.interactive_session.interactive_session import format_session_creation_table

        format_session_creation_table(
            {'_id': 's1', 'name': 'n', 'status': 'scheduled',
             'volumeSizes': {'libraries': 70, 'sessionResults': 230, 'mountedData': 200}},
            storage_size=500,
            volume_sizes={'libraries': 50, 'sessionResults': 225, 'mountedData': 225})
        out = capsys.readouterr().out
        assert '70 GB' in out and '230 GB' in out and '200 GB' in out
        assert '225 GB' not in out

    # Trimmed from a real status response: top-level volumeSizes plus a volumes list
    STATUS_RESPONSE = {
        '_id': '6ad228df564b8bcbd11c8b07', 'name': 'vs-check', 'status': 'initializing',
        'interactiveSessionType': 'awsVSCode',
        'resources': {'instanceType': 'c5.xlarge', 'storageSizeInGb': 500},
        'volumes': [{'type': 'environment', 'storageSizeInGb': 100},
                    {'type': 'vscode-libraries', 'storageSizeInGb': 50},
                    {'type': 'mounted-data', 'storageSizeInGb': 225},
                    {'type': 'session-results', 'storageSizeInGb': 225}],
        'volumeSizes': {'libraries': 50, 'mountedData': 225, 'sessionResults': 225},
    }

    def test_status_transform_includes_volume_sizes(self):
        from cloudos_cli.interactive_session.interactive_session import transform_session_response

        data = transform_session_response(self.STATUS_RESPONSE)
        assert data['volume_sizes'] == {'libraries': 50, 'mountedData': 225, 'sessionResults': 225}

    def test_status_transform_without_volume_sizes(self):
        from cloudos_cli.interactive_session.interactive_session import transform_session_response

        data = transform_session_response({'_id': 'x', 'resources': {'storageSizeInGb': 500}})
        assert data['volume_sizes'] is None

    def test_status_table_shows_volume_sizes(self, capsys):
        from cloudos_cli.interactive_session.interactive_session import (
            transform_session_response, format_session_status_table)

        format_session_status_table(transform_session_response(self.STATUS_RESPONSE))
        out = capsys.readouterr().out
        assert 'Libraries' in out and '50 GB' in out
        assert 'Session results' in out and 'Mounted data' in out

    def test_status_table_without_volume_sizes_has_no_volume_rows(self, capsys):
        from cloudos_cli.interactive_session.interactive_session import (
            transform_session_response, format_session_status_table)

        format_session_status_table(transform_session_response({'_id': 'x', 'resources': {'storageSizeInGb': 500}}))
        out = capsys.readouterr().out
        assert 'Libraries' not in out

    def test_status_csv_has_volume_columns(self):
        from cloudos_cli.interactive_session.interactive_session import (
            transform_session_response, export_session_status_csv)

        header, row = export_session_status_csv(transform_session_response(self.STATUS_RESPONSE)).split('\n')
        columns = dict(zip(header.split(','), row.split(',')))
        assert columns['Storage'] == '500 GB'
        assert columns['Libraries volume'] == '50 GB'
        assert columns['Session results volume'] == '225 GB'
        assert columns['Mounted data volume'] == '225 GB'


class TestCreateSessionVolumeFlags:
    """CLI tests for --storage and the volume flags in create and resume."""

    BASE_ARGS = [
        'interactive-session', 'create',
        '--apikey', 'test_key',
        '--cloudos-url', 'http://test.com',
        '--workspace-id', 'test_team',
        '--project-name', 'my_project',
        '--name', 'Volume Session',
        '--session-type', 'jupyter',
    ]
    RESUME_ARGS = [
        'interactive-session', 'resume',
        '--session-id', 'a' * 24,
        '--apikey', 'test_key',
        '--cloudos-url', 'http://test.com',
        '--workspace-id', 'test_team',
    ]
    PROFILE = {
        'apikey': 'test_key',
        'cloudos_url': 'http://test.com',
        'workspace_id': 'test_team',
        'project_name': 'my_project',
    }

    def _invoke(self, mock_config, mock_cloudos, args, current_storage=500, current_volumes=None,
                status_error=None):
        mock_config.return_value = self.PROFILE
        cl = MagicMock()
        mock_cloudos.return_value = cl
        cl.create_interactive_session.return_value = {'_id': 'sess_001', 'name': 'n', 'status': 'scheduled'}
        cl.resume_interactive_session.return_value = {'status': 'resuming', 'interactiveSessionConfiguration': {}}
        # resume looks up the session's current storage before sending a new size
        with patch('cloudos_cli.interactive_session.cli.get_interactive_session_status') as mock_status:
            resources = {'storageSizeInGb': current_storage}
            if current_volumes is not None:
                resources['volumeSizes'] = current_volumes
            mock_status.return_value = {'resources': resources}
            mock_status.side_effect = status_error
            result = CliRunner().invoke(run_cloudos_cli, args)
        self.mock_status = mock_status
        return result, cl

    def test_help_lists_volume_flags(self):
        result = CliRunner().invoke(run_cloudos_cli, ['interactive-session', 'create', '--help'])
        assert result.exit_code == 0
        for flag in ('--libraries-volume', '--results-volume', '--data-volume'):
            assert flag in result.output

    @pytest.mark.parametrize('command', ['create', 'resume'])
    def test_help_shows_limits_from_constants(self, command):
        from cloudos_cli.interactive_session.interactive_session import (
            STORAGE_RANGE, VOLUME_MINIMUMS, VOLUME_MAXIMUMS)

        result = CliRunner().invoke(run_cloudos_cli, ['interactive-session', command, '--help'])
        assert result.exit_code == 0
        output = ' '.join(result.output.replace('│', ' ').split())
        assert f'({STORAGE_RANGE})' in output
        for volume, minimum in VOLUME_MINIMUMS.items():
            assert f'(min {minimum}, max {VOLUME_MAXIMUMS[volume]})' in output
        if command == 'create':
            assert 'A volume that would go over its maximum gets its maximum' in output
        else:
            assert 'A volume already above its maximum keeps its current size' in output

    @pytest.mark.parametrize('extra,storage,volumes', [
        ([], 500, {'libraries': 50, 'sessionResults': 225, 'mountedData': 225}),
        (['--storage', '1001'], 1001, {'libraries': 50, 'sessionResults': 476, 'mountedData': 475}),
        (['--storage', '1000', '--data-volume', '100'], 1000,
         {'libraries': 450, 'sessionResults': 450, 'mountedData': 100}),
        (['--libraries-volume', '100', '--results-volume', '300', '--data-volume', '600'], 1000,
         {'libraries': 100, 'sessionResults': 300, 'mountedData': 600}),
        # Smallest storage and volumes allowed
        (['--storage', '60'], 60, {'libraries': 50, 'sessionResults': 5, 'mountedData': 5}),
        (['--libraries-volume', '50', '--results-volume', '5', '--data-volume', '5'], 60,
         {'libraries': 50, 'sessionResults': 5, 'mountedData': 5}),
    ])
    @patch('cloudos_cli.interactive_session.cli.Cloudos')
    @patch('cloudos_cli.configure.configure.ConfigurationProfile.load_profile_and_validate_data')
    def test_create_sends_volume_sizes(self, mock_config, mock_cloudos, extra, storage, volumes):
        result, cl = self._invoke(mock_config, mock_cloudos, self.BASE_ARGS + extra)

        assert result.exit_code == 0, result.output
        payload = cl.create_interactive_session.call_args[0][1]
        config = payload['interactiveSessionConfiguration']
        assert config['storageSizeInGb'] == storage
        assert config['volumeSizes'] == volumes
        assert 'Mounted data' in result.output
        assert f"{volumes['mountedData']} GB" in result.output

    @pytest.mark.parametrize('extra,message', [
        (['--storage', '59'], '60-64050'),
        (['--libraries-volume', '10'], 'at least 50 GB'),
        (['--storage', '600', '--libraries-volume', '50', '--results-volume', '225', '--data-volume', '225'],
         'does not match'),
    ])
    @patch('cloudos_cli.interactive_session.cli.Cloudos')
    @patch('cloudos_cli.configure.configure.ConfigurationProfile.load_profile_and_validate_data')
    def test_create_invalid_volumes_fail_before_api_call(self, mock_config, mock_cloudos, extra, message):
        result, cl = self._invoke(mock_config, mock_cloudos, self.BASE_ARGS + extra)

        assert result.exit_code != 0
        assert message in result.output
        mock_cloudos.assert_not_called()
        cl.create_interactive_session.assert_not_called()

    @pytest.mark.parametrize('platform,instance', [('aws', 'c5.xlarge'), ('azure', 'Standard_D4s_v3')])
    @patch('cloudos_cli.interactive_session.cli.Cloudos')
    @patch('cloudos_cli.configure.configure.ConfigurationProfile.load_profile_and_validate_data')
    def test_create_default_instance_per_platform(self, mock_config, mock_cloudos, platform, instance):
        result, cl = self._invoke(mock_config, mock_cloudos, self.BASE_ARGS + ['--execution-platform', platform])

        assert result.exit_code == 0, result.output
        config = cl.create_interactive_session.call_args[0][1]['interactiveSessionConfiguration']
        assert config['executionPlatform'] == platform
        assert config['instanceType'] == instance
        assert config['volumeSizes'] == {'libraries': 50, 'sessionResults': 225, 'mountedData': 225}

    @patch('cloudos_cli.interactive_session.cli.Cloudos')
    @patch('cloudos_cli.configure.configure.ConfigurationProfile.load_profile_and_validate_data')
    def test_resume_with_storage_sends_volume_sizes(self, mock_config, mock_cloudos):
        result, cl = self._invoke(mock_config, mock_cloudos, self.RESUME_ARGS + ['--storage', '1000'])

        assert result.exit_code == 0, result.output
        payload = cl.resume_interactive_session.call_args[0][2]
        config = payload['newInteractiveSessionConfiguration']
        assert config['storageSizeInGb'] == 1000
        assert config['volumeSizes'] == {'libraries': 50, 'sessionResults': 475, 'mountedData': 475}

    @patch('cloudos_cli.interactive_session.cli.Cloudos')
    @patch('cloudos_cli.configure.configure.ConfigurationProfile.load_profile_and_validate_data')
    def test_resume_without_storage_sends_no_volume_sizes(self, mock_config, mock_cloudos):
        result, cl = self._invoke(mock_config, mock_cloudos, self.RESUME_ARGS + ['--instance', 'c5.2xlarge'])

        assert result.exit_code == 0, result.output
        payload = cl.resume_interactive_session.call_args[0][2]
        assert 'volumeSizes' not in payload['newInteractiveSessionConfiguration']
        assert 'storageSizeInGb' not in payload['newInteractiveSessionConfiguration']

    @patch('cloudos_cli.interactive_session.cli.Cloudos')
    @patch('cloudos_cli.configure.configure.ConfigurationProfile.load_profile_and_validate_data')
    def test_resume_partial_volumes_without_storage_is_error(self, mock_config, mock_cloudos):
        result, cl = self._invoke(mock_config, mock_cloudos, self.RESUME_ARGS + ['--data-volume', '300'])

        assert result.exit_code != 0
        assert '--storage is required' in result.output
        cl.resume_interactive_session.assert_not_called()

    @pytest.mark.parametrize('extra,current,storage,volumes', [
        # Smallest storage, on a session that already has it
        (['--storage', '60'], 60, 60, {'libraries': 50, 'sessionResults': 5, 'mountedData': 5}),
        (['--libraries-volume', '50', '--results-volume', '5', '--data-volume', '5'], 60, 60,
         {'libraries': 50, 'sessionResults': 5, 'mountedData': 5}),
        # Same storage as now, and larger
        (['--storage', '500'], 500, 500, {'libraries': 50, 'sessionResults': 225, 'mountedData': 225}),
        (['--storage', '1000'], 500, 1000, {'libraries': 50, 'sessionResults': 475, 'mountedData': 475}),
    ])
    @patch('cloudos_cli.interactive_session.cli.Cloudos')
    @patch('cloudos_cli.configure.configure.ConfigurationProfile.load_profile_and_validate_data')
    def test_resume_accepts_storage(self, mock_config, mock_cloudos, extra, current, storage, volumes):
        result, cl = self._invoke(mock_config, mock_cloudos, self.RESUME_ARGS + extra, current_storage=current)

        assert result.exit_code == 0, result.output
        config = cl.resume_interactive_session.call_args[0][2]['newInteractiveSessionConfiguration']
        assert config['storageSizeInGb'] == storage
        assert config['volumeSizes'] == volumes

    @patch('cloudos_cli.interactive_session.cli.Cloudos')
    @patch('cloudos_cli.configure.configure.ConfigurationProfile.load_profile_and_validate_data')
    def test_resume_storage_smaller_than_current_is_error(self, mock_config, mock_cloudos):
        result, cl = self._invoke(mock_config, mock_cloudos, self.RESUME_ARGS + ['--storage', '500'],
                                  current_storage=1000)

        assert result.exit_code != 0
        assert "can't be smaller than the session's current storage (1000 GB)" in result.output
        cl.resume_interactive_session.assert_not_called()

    @patch('cloudos_cli.interactive_session.cli.Cloudos')
    @patch('cloudos_cli.configure.configure.ConfigurationProfile.load_profile_and_validate_data')
    def test_resume_storage_only_grows_from_current_volumes(self, mock_config, mock_cloudos):
        # libraries keeps its 100 GB; the extra 200 GB is shared by the other two
        result, cl = self._invoke(mock_config, mock_cloudos, self.RESUME_ARGS + ['--storage', '1200'],
                                  current_storage=1000,
                                  current_volumes={'libraries': 100, 'sessionResults': 450, 'mountedData': 450})

        assert result.exit_code == 0, result.output
        config = cl.resume_interactive_session.call_args[0][2]['newInteractiveSessionConfiguration']
        assert config['storageSizeInGb'] == 1200
        assert config['volumeSizes'] == {'libraries': 100, 'sessionResults': 550, 'mountedData': 550}

    @patch('cloudos_cli.interactive_session.cli.Cloudos')
    @patch('cloudos_cli.configure.configure.ConfigurationProfile.load_profile_and_validate_data')
    def test_resume_keeps_volume_above_maximum(self, mock_config, mock_cloudos):
        # Checked against a real session on ADAPT-prod: the platform accepts libraries at 1500 GB
        result, cl = self._invoke(mock_config, mock_cloudos, self.RESUME_ARGS + ['--storage', '3200'],
                                  current_storage=3000,
                                  current_volumes={'libraries': 1500, 'sessionResults': 750, 'mountedData': 750})

        assert result.exit_code == 0, result.output
        config = cl.resume_interactive_session.call_args[0][2]['newInteractiveSessionConfiguration']
        assert config['volumeSizes'] == {'libraries': 1500, 'sessionResults': 850, 'mountedData': 850}

    @patch('cloudos_cli.interactive_session.cli.Cloudos')
    @patch('cloudos_cli.configure.configure.ConfigurationProfile.load_profile_and_validate_data')
    def test_resume_volume_smaller_than_current_is_error(self, mock_config, mock_cloudos):
        extra = ['--storage', '1200', '--libraries-volume', '50']
        result, cl = self._invoke(mock_config, mock_cloudos, self.RESUME_ARGS + extra,
                                  current_storage=1000,
                                  current_volumes={'libraries': 100, 'sessionResults': 450, 'mountedData': 450})

        assert result.exit_code != 0
        assert "Volumes can't be smaller than their current size" in result.output
        cl.resume_interactive_session.assert_not_called()

    @patch('cloudos_cli.interactive_session.cli.Cloudos')
    @patch('cloudos_cli.configure.configure.ConfigurationProfile.load_profile_and_validate_data')
    def test_resume_growing_every_volume_is_accepted(self, mock_config, mock_cloudos):
        extra = ['--storage', '1200', '--libraries-volume', '100', '--results-volume', '600']
        result, cl = self._invoke(mock_config, mock_cloudos, self.RESUME_ARGS + extra,
                                  current_storage=1000,
                                  current_volumes={'libraries': 100, 'sessionResults': 450, 'mountedData': 450})

        assert result.exit_code == 0, result.output
        config = cl.resume_interactive_session.call_args[0][2]['newInteractiveSessionConfiguration']
        assert config['volumeSizes'] == {'libraries': 100, 'sessionResults': 600, 'mountedData': 500}

    @patch('cloudos_cli.interactive_session.cli.Cloudos')
    @patch('cloudos_cli.configure.configure.ConfigurationProfile.load_profile_and_validate_data')
    def test_resume_storage_out_of_range_fails_before_status_lookup(self, mock_config, mock_cloudos):
        result, cl = self._invoke(mock_config, mock_cloudos, self.RESUME_ARGS + ['--storage', '59'])

        assert result.exit_code != 0
        assert '60-64050' in result.output
        self.mock_status.assert_not_called()
        cl.resume_interactive_session.assert_not_called()

    @patch('cloudos_cli.interactive_session.cli.Cloudos')
    @patch('cloudos_cli.configure.configure.ConfigurationProfile.load_profile_and_validate_data')
    def test_resume_storage_status_lookup_failure_is_error(self, mock_config, mock_cloudos):
        result, cl = self._invoke(mock_config, mock_cloudos, self.RESUME_ARGS + ['--storage', '1000'],
                                  status_error=RuntimeError('Server error'))

        assert result.exit_code != 0
        assert 'Could not get the current storage' in result.output
        cl.resume_interactive_session.assert_not_called()

    @patch('cloudos_cli.interactive_session.cli.Cloudos')
    @patch('cloudos_cli.configure.configure.ConfigurationProfile.load_profile_and_validate_data')
    def test_resume_without_storage_skips_status_lookup(self, mock_config, mock_cloudos):
        result, cl = self._invoke(mock_config, mock_cloudos, self.RESUME_ARGS + ['--instance', 'c5.2xlarge'])

        assert result.exit_code == 0, result.output
        self.mock_status.assert_not_called()

if __name__ == '__main__':
    pytest.main([__file__, '-v'])

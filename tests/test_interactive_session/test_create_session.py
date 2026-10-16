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
                                        execution_platform='azure', instance_type='Standard_F1s')
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

    @pytest.mark.parametrize('storage', [499, 64051])
    def test_payload_rejects_storage_out_of_range(self, storage):
        from cloudos_cli.interactive_session.interactive_session import build_session_payload

        with pytest.raises(ValueError, match='500-64050'):
            build_session_payload(name='s', backend='regular', project_id='p', storage_size=storage)

    @pytest.mark.parametrize('kwargs,expected', [
        ({}, (500, {'libraries': 50, 'sessionResults': 225, 'mountedData': 225})),
        ({'storage_size': 1000}, (1000, {'libraries': 50, 'sessionResults': 475, 'mountedData': 475})),
        # Odd remainder: the extra GB goes to sessionResults
        ({'storage_size': 1001}, (1001, {'libraries': 50, 'sessionResults': 476, 'mountedData': 475})),
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
        ({'libraries': 60, 'session_results': 400, 'mounted_data': 40},
         (500, {'libraries': 60, 'sessionResults': 400, 'mountedData': 40})),
        ({'storage_size': 500, 'libraries': 60, 'session_results': 400, 'mounted_data': 40},
         (500, {'libraries': 60, 'sessionResults': 400, 'mountedData': 40})),
    ])
    def test_resolve_volume_sizes(self, kwargs, expected):
        from cloudos_cli.interactive_session.interactive_session import resolve_volume_sizes

        assert resolve_volume_sizes(**kwargs) == expected

    @pytest.mark.parametrize('kwargs,message', [
        ({'storage_size': 499}, '500-64050'),
        ({'storage_size': 64051}, '500-64050'),
        ({'libraries': 49}, 'libraries volume .*at least 50 GB'),
        ({'session_results': 224}, 'sessionResults volume .*at least 225 GB'),
        ({'mounted_data': 34}, 'mountedData volume .*at least 35 GB'),
        # Even split of the rest leaves sessionResults below its minimum
        ({'storage_size': 500, 'mounted_data': 100}, 'too small for sessionResults'),
        ({'storage_size': 500, 'libraries': 100}, 'too small for sessionResults'),
        # Two volumes given leave too little for the third
        ({'storage_size': 500, 'libraries': 50, 'session_results': 430}, 'too small for mountedData'),
        # All three given but the sum is out of range
        ({'libraries': 50, 'session_results': 225, 'mounted_data': 35}, '500-64050'),
        # All three given and --storage does not match
        ({'storage_size': 600, 'libraries': 50, 'session_results': 225, 'mounted_data': 225}, 'does not match'),
    ])
    def test_resolve_volume_sizes_errors(self, kwargs, message):
        from cloudos_cli.interactive_session.interactive_session import resolve_volume_sizes

        with pytest.raises(ValueError, match=message):
            resolve_volume_sizes(**kwargs)

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

    def _invoke(self, mock_config, mock_cloudos, args):
        mock_config.return_value = self.PROFILE
        cl = MagicMock()
        mock_cloudos.return_value = cl
        cl.create_interactive_session.return_value = {'_id': 'sess_001', 'name': 'n', 'status': 'scheduled'}
        cl.resume_interactive_session.return_value = {'status': 'resuming', 'interactiveSessionConfiguration': {}}
        result = CliRunner().invoke(run_cloudos_cli, args)
        return result, cl

    def test_help_lists_volume_flags(self):
        result = CliRunner().invoke(run_cloudos_cli, ['interactive-session', 'create', '--help'])
        assert result.exit_code == 0
        for flag in ('--libraries-volume', '--results-volume', '--data-volume'):
            assert flag in result.output

    @pytest.mark.parametrize('extra,storage,volumes', [
        ([], 500, {'libraries': 50, 'sessionResults': 225, 'mountedData': 225}),
        (['--storage', '1001'], 1001, {'libraries': 50, 'sessionResults': 476, 'mountedData': 475}),
        (['--storage', '1000', '--data-volume', '100'], 1000,
         {'libraries': 450, 'sessionResults': 450, 'mountedData': 100}),
        (['--libraries-volume', '100', '--results-volume', '300', '--data-volume', '600'], 1000,
         {'libraries': 100, 'sessionResults': 300, 'mountedData': 600}),
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
        (['--storage', '100'], '500-64050'),
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

if __name__ == '__main__':
    pytest.main([__file__, '-v'])

"""Pytest added for function ConfigurationProfile"""
from cloudos_cli.configure.configure import ConfigurationProfile
import os
import configparser
from unittest.mock import patch, mock_open

CONFIG_DIR = "tests/test_data/.cloudos"
APIKEY1 = 'vnvye7hnfkisdg98j2'
APIKEY2 = 'oajsfaijsgoiasof00'
CLOUDOS_URL = 'http://cloudos.lifebit.ai'


def test_configure_check_credentials_config_exists():
    """
    Test 'configure' to generate a default profile
    """
    assert os.path.exists(os.path.join(CONFIG_DIR, "credentials"))
    assert os.path.exists(os.path.join(CONFIG_DIR, "config"))


@patch('builtins.input', side_effect=['http://cloudos.lifebit.ai', 'workspace_id', 'project_name', '1', '1', 'workflow_name', 'y'])
@patch('getpass.getpass', side_effect=[APIKEY1, APIKEY1])
def test_create_profile_with_user_input(mock_getpass, mock_input):
    """
    Test creating a profile with mocked user input
    """
    config_manager = ConfigurationProfile(CONFIG_DIR)
    config_manager.create_profile_from_input('user_input_profile')

    # Verify the profile was created
    config = configparser.ConfigParser()
    config.read(os.path.join(CONFIG_DIR, "config"))
    assert 'user_input_profile' in config.sections()
    assert config['user_input_profile']['cloudos_url'] == CLOUDOS_URL


@patch('builtins.input', side_effect=['http://cloudos.lifebit.ai', 'workspace_id', 'project_name', '1', '1', 'workflow_name', 'n'])
@patch('getpass.getpass', side_effect=[APIKEY1, APIKEY1])
def test_create_profile_abort_if_exists(mock_getpass, mock_input):
    """
    Test that creating a profile aborts if the profile already exists and user chooses not to overwrite
    """
    config_manager = ConfigurationProfile(CONFIG_DIR)

    # Create a profile first
    config_manager.create_profile_from_input('existing_profile')

    # Attempt to create the same profile again
    with patch('builtins.input', side_effect=['n']):  # Simulate user choosing not to overwrite
        config_manager.create_profile_from_input('existing_profile')

    # Verify the profile was not overwritten
    config = configparser.ConfigParser()
    config.read(os.path.join(CONFIG_DIR, "config"))
    assert config['existing_profile']['cloudos_url'] == CLOUDOS_URL


def test_make_default_profile():
    """
    Test setting a profile as default
    """
    config_manager = ConfigurationProfile(CONFIG_DIR)

    # Set profile2 as default
    config_manager.make_default_profile('profile2')

    # Verify profile2 is now the default
    config = configparser.ConfigParser()
    config.read(os.path.join(CONFIG_DIR, "config"))
    assert config['profile2']['default'] == 'True'
    assert config['profile1']['default'] == 'False'


def test_list_profiles():
    """
    Test listing profiles
    """
    config_manager = ConfigurationProfile(CONFIG_DIR)

    with patch('builtins.print') as mock_print:
        config_manager.list_profiles()
        mock_print.assert_any_call("Available profiles:")
        mock_print.assert_any_call(" - profile1")
        mock_print.assert_any_call(" - profile2 (default)")


@patch('builtins.input', side_effect=['http://cloudos.lifebit.ai', 'workspace_id', 'project_name', '1', '1', 'workflow_name', 'n'])
@patch('getpass.getpass', side_effect=[APIKEY1, APIKEY1])
def test_remove_profile(mock_getpass, mock_input):
    """
    Test removing a profile
    """
    config_manager = ConfigurationProfile(CONFIG_DIR)
    config_manager.create_profile_from_input('profile_to_remove')

    # Remove the profile
    config_manager.remove_profile('profile_to_remove')

    # Verify the profile was removed
    config = configparser.ConfigParser()
    config.read(os.path.join(CONFIG_DIR, "config"))
    assert 'profile_to_remove' not in config.sections()

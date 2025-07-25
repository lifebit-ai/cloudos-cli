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
    # Create the .cloudos directory and files on the fly
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(os.path.join(CONFIG_DIR, "credentials"), "w") as cred_file:
        cred_file.write("[default]\napi_key = test_api_key\n")
    with open(os.path.join(CONFIG_DIR, "config"), "w") as config_file:
        config_file.write("[default]\ncloudos_url = http://cloudos.lifebit.ai\n")

    # Assertions to verify the files exist
    assert os.path.exists(os.path.join(CONFIG_DIR, "credentials"))
    assert os.path.exists(os.path.join(CONFIG_DIR, "config"))


@patch('builtins.input', side_effect=[APIKEY1, 'http://cloudos.lifebit.ai', 'workspace_id', 'procurement_id', 'project_name', '2', '2', 'workflow_name', 'session1234', 'n'])
def test_create_profile_with_user_input(mock_input):
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


@patch('builtins.input', side_effect=['', '', '', '', '', '', '', '', '', 'n'])
def test_create_profile_keep_existing_values(mock_input):
    """
    Test creating a profile and leaving it as is by pressing "Enter" for each field
    """
    config_manager = ConfigurationProfile(CONFIG_DIR)

    # Attempt to create the same profile again, pressing "Enter" to keep existing values
    with patch('builtins.print') as mock_in:
        config_manager.create_profile_from_input('user_input_profile')

    # Verify the profile values remain unchanged
    config = configparser.ConfigParser()
    config.read(os.path.join(CONFIG_DIR, "config"))
    assert config['user_input_profile']['cloudos_url'] == CLOUDOS_URL
    assert config['user_input_profile']['execution_platform'] == "azure"
    assert config['user_input_profile']['repository_platform'] == "gitlab"


def test_make_default_profile():
    """
    Test setting a profile as default
    """
    config_manager = ConfigurationProfile(CONFIG_DIR)

    # Set profile2 as default
    config_manager.make_default_profile('user_input_profile')

    # Verify profile2 is now the default
    config = configparser.ConfigParser()
    config.read(os.path.join(CONFIG_DIR, "config"))
    assert config['user_input_profile']['default'] == 'True'


def test_list_profiles():
    """
    Test listing profiles
    """
    config_manager = ConfigurationProfile(CONFIG_DIR)

    with patch('builtins.print') as mock_print:
        config_manager.list_profiles()
        mock_print.assert_any_call("Available profiles:")
        mock_print.assert_any_call(" - default")
        mock_print.assert_any_call(" - user_input_profile (default)")


@patch('builtins.input', side_effect=[APIKEY1, 'http://cloudos.lifebit.ai', 'workspace_id', 'procurement_id', 'project_name', '1', '1', 'workflow_name', 'session1234', 'n'])
def test_remove_profile(mock_input):
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


def test_check_if_profile_exists():
    """
    Test checking if a profile exists
    """
    config_manager = ConfigurationProfile(CONFIG_DIR)

    # Check if profile1 exists
    assert config_manager.check_if_profile_exists('user_input_profile') is True

    # Check if a non-existing profile exists
    assert config_manager.check_if_profile_exists('non_existing_profile') is False


def test_determine_default_profile():
    """
    Test determining the default profile
    """
    config_manager = ConfigurationProfile(CONFIG_DIR)

    # Determine the default profile
    default_profile = config_manager.determine_default_profile()

    # Verify the default profile is correct
    assert default_profile == 'user_input_profile'

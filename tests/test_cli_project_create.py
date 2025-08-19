import pytest
from click.testing import CliRunner
from cloudos_cli.__main__ import run_cloudos_cli


def test_project_create_command_exists():
    """
    Test that the 'project create' command exists and shows proper help
    """
    runner = CliRunner()
    
    # Test that project create command exists
    result = runner.invoke(run_cloudos_cli, ['project', 'create', '--help'])
    
    # Command should exist and not error out
    assert result.exit_code == 0
    
    # Check that the help text contains expected options
    assert 'Create a new project in CloudOS' in result.output
    assert '--new-project' in result.output
    assert '--workspace-id' in result.output
    assert '--apikey' in result.output
    assert '--cloudos-url' in result.output


def test_project_create_command_structure():
    """
    Test that the 'project create' command has the correct structure and options
    """
    runner = CliRunner()
    
    # Test that the command exists and can show help without making API calls
    result = runner.invoke(run_cloudos_cli, ['project', 'create', '--help'])
    
    # Command should exist and show help properly
    assert result.exit_code == 0
    assert 'Create a new project in CloudOS' in result.output
    assert '--new-project' in result.output
    assert 'required' in result.output  # Required arguments should be marked as such


def test_project_group_contains_create_command():
    """
    Test that the 'project' group contains the 'create' command
    """
    runner = CliRunner()
    
    # Test that project group shows create command
    result = runner.invoke(run_cloudos_cli, ['project', '--help'])
    
    assert result.exit_code == 0
    assert 'create' in result.output
    assert 'Create a new project in CloudOS' in result.output

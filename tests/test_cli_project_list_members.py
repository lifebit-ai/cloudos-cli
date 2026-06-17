import pytest
from click.testing import CliRunner
from cloudos_cli.__main__ import run_cloudos_cli


def test_project_list_members_command_exists():
    """Test that the 'project members' command exists and shows proper help."""
    runner = CliRunner()
    result = runner.invoke(run_cloudos_cli, ['project', 'members', '--help'])
    assert result.exit_code == 0
    assert 'Retrieve and display members of a Lifebit Platform project.' in result.output
    assert '--project-id' in result.output
    assert '--apikey' in result.output
    assert '--cloudos-url' in result.output


def test_project_group_contains_list_members_command():
    """Test that the 'project' group lists the 'members' command."""
    runner = CliRunner()
    result = runner.invoke(run_cloudos_cli, ['project', '--help'])
    assert result.exit_code == 0
    assert 'members' in result.output


def test_project_list_members_output_format_options():
    """Test that 'project members' exposes the expected output format choices."""
    runner = CliRunner()
    result = runner.invoke(run_cloudos_cli, ['project', 'members', '--help'])
    assert result.exit_code == 0
    assert '--output-format' in result.output
    assert 'stdout' in result.output
    assert 'json' in result.output

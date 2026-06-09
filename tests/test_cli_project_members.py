from click.testing import CliRunner
from cloudos_cli.__main__ import run_cloudos_cli


def test_project_members_command_exists():
    """
    Test that the 'project members' command exists and shows proper help
    """
    runner = CliRunner()
    result = runner.invoke(run_cloudos_cli, ['project', 'members', '--help'])

    assert result.exit_code == 0
    assert 'Collect and display all members from a Lifebit Platform project' in result.output
    assert '--project-id' in result.output
    assert '--apikey' in result.output
    assert '--cloudos-url' in result.output


def test_project_group_contains_members_command():
    """
    Test that the 'project' group contains the 'members' command
    """
    runner = CliRunner()
    result = runner.invoke(run_cloudos_cli, ['project', '--help'])

    assert result.exit_code == 0
    assert 'members' in result.output
    assert 'Collect and display all members from a Lifebit Platform project' in result.output

"""pytest tests for --accelerate-saving-results flag in job run command

This test file provides testing for the --accelerate-saving-results flag functionality
in the job run command of CloudOS CLI.
"""
import pytest
from click.testing import CliRunner
from cloudos_cli.jobs.cli import run


def test_run_accelerate_saving_results_flag_is_boolean():
    """
    Test that --accelerate-saving-results is properly defined as a boolean flag
    """
    from cloudos_cli.jobs.cli import run as run_command

    # Get the accelerate-saving-results option from the command
    accelerate_saving_results_option = None
    for param in run_command.params:
        if hasattr(param, 'name') and param.name == 'accelerate_saving_results':
            accelerate_saving_results_option = param
            break

    assert accelerate_saving_results_option is not None
    assert accelerate_saving_results_option.is_flag is True
    assert accelerate_saving_results_option.default is False


def test_run_accelerate_saving_results_help_text():
    """
    Test that --accelerate-saving-results appears in help text
    """
    runner = CliRunner()
    result = runner.invoke(run, ['--help'])

    # Check that the truncated flag appears in help text
    assert '--accelerate-' in result.output
    # Check that key words from the description appear
    assert 'saving results' in result.output.lower()


def test_run_accelerate_saving_results_flag_definition():
    """
    Test that the flag has the correct help text definition
    """
    from cloudos_cli.jobs.cli import run as run_command

    # Get the accelerate-saving-results option from the command
    accelerate_saving_results_option = None
    for param in run_command.params:
        if hasattr(param, 'name') and param.name == 'accelerate_saving_results':
            accelerate_saving_results_option = param
            break

    assert accelerate_saving_results_option is not None
    assert 'Enables saving results directly to cloud storage bypassing the master node' in accelerate_saving_results_option.help
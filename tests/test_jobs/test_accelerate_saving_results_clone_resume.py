"""pytest tests for --accelerate-saving-results flag in job resume command

This test file provides testing for the --accelerate-saving-results flag functionality
in the job resume command of CloudOS CLI.
"""
import pytest
from click import Command
from cloudos_cli.jobs.cli import clone_resume


@pytest.mark.parametrize("args, expected", [([], False), (["--accelerate-saving-results"], True)])
def test_resume_accelerate_saving_results_flag_is_boolean(args, expected):
    """
    Test that --accelerate-saving-results is properly defined as a boolean flag in resume command
    """

    # Get the accelerate-saving-results option from the command
    accelerate_saving_results_option = None
    for param in clone_resume.params:
        if hasattr(param, 'name') and param.name == 'accelerate_saving_results':
            accelerate_saving_results_option = param
            break

    assert accelerate_saving_results_option is not None
    assert accelerate_saving_results_option.is_flag is True
    # Parse the actual option: Click 8.5+ resolves implicit defaults lazily.
    command = Command("test", params=[accelerate_saving_results_option])
    with command.make_context("test", args) as ctx:
        assert ctx.params["accelerate_saving_results"] is expected


def test_resume_accelerate_saving_results_flag_definition():
    """
    Test that the flag has the correct help text definition in resume command
    """

    # Get the accelerate-saving-results option from the command
    accelerate_saving_results_option = None
    for param in clone_resume.params:
        if hasattr(param, 'name') and param.name == 'accelerate_saving_results':
            accelerate_saving_results_option = param
            break

    assert accelerate_saving_results_option is not None
    assert 'Enables saving results directly to cloud storage bypassing the master node' in accelerate_saving_results_option.help

#!/usr/bin/env python3

import rich_click as click
import sys
from ._version import __version__
from cloudos_cli.logging.logger import update_command_context_from_click
from cloudos_cli.configure.configure import (
    build_default_map_for_group,
    get_shared_config
)
from cloudos_cli.utils.cli_helpers import (
    custom_exception_handler,
    pass_debug_to_subcommands,
    setup_debug
)

# Import all command groups from their cli modules
from cloudos_cli.jobs.cli import job
from cloudos_cli.workflows.cli import workflow
from cloudos_cli.projects.cli import project
from cloudos_cli.cromwell.cli import cromwell
from cloudos_cli.queue.cli import queue
from cloudos_cli.bash.cli import bash
from cloudos_cli.procurement.cli import procurement
from cloudos_cli.datasets.cli import datasets
from cloudos_cli.configure.cli import configure
from cloudos_cli.link.cli import link


# Install the custom exception handler
sys.excepthook = custom_exception_handler


@click.group(cls=pass_debug_to_subcommands())
@click.option('--debug', is_flag=True, help='Show detailed error information and tracebacks', 
              is_eager=True, expose_value=False, callback=setup_debug)
@click.version_option(__version__)
@click.pass_context
def run_cloudos_cli(ctx):
    """CloudOS python package: a package for interacting with CloudOS."""
    update_command_context_from_click(ctx)
    ctx.ensure_object(dict)

    if ctx.invoked_subcommand not in ['datasets']:
        print(run_cloudos_cli.__doc__ + '\n')
        print('Version: ' + __version__ + '\n')
    
    # Load shared configuration (handles missing profiles and fields gracefully)
    shared_config = get_shared_config()
    
    # Automatically build default_map from registered commands
    ctx.default_map = build_default_map_for_group(run_cloudos_cli, shared_config)


# Register all command groups
run_cloudos_cli.add_command(job)
run_cloudos_cli.add_command(workflow)
run_cloudos_cli.add_command(project)
run_cloudos_cli.add_command(cromwell)
run_cloudos_cli.add_command(queue)
run_cloudos_cli.add_command(bash)
run_cloudos_cli.add_command(procurement)
run_cloudos_cli.add_command(datasets)
run_cloudos_cli.add_command(configure)
run_cloudos_cli.add_command(link)

if __name__ == '__main__':
    run_cloudos_cli()

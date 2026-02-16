"""CLI commands for CloudOS configuration management."""

import rich_click as click
from cloudos_cli.configure.configure import ConfigurationProfile
from cloudos_cli.logging.logger import update_command_context_from_click
from cloudos_cli.utils.cli_helpers import pass_debug_to_subcommands


# Create the configure group
@click.group(cls=pass_debug_to_subcommands(), invoke_without_command=True)
@click.option('--profile', help='Profile to use from the config file', default='default')
@click.option('--make-default',
              is_flag=True,
              help='Make the profile the default one.')
@click.pass_context
def configure(ctx, profile, make_default):
    """CloudOS configuration."""
    print(configure.__doc__ + '\n')
    update_command_context_from_click(ctx)
    profile = profile or ctx.obj['profile']
    config_manager = ConfigurationProfile()

    if ctx.invoked_subcommand is None and profile == "default" and not make_default:
        config_manager.create_profile_from_input(profile_name="default")

    if profile != "default" and not make_default:
        config_manager.create_profile_from_input(profile_name=profile)
    if make_default:
        config_manager.make_default_profile(profile_name=profile)


@configure.command('list-profiles')
def list_profiles():
    """List all available configuration profiles."""
    config_manager = ConfigurationProfile()
    config_manager.list_profiles()


@configure.command('remove-profile')
@click.option('--profile',
              help='Name of the profile. Not using this option will lead to profile named "deafults" being generated',
              required=True)
@click.pass_context
def remove_profile(ctx, profile):
    """Remove a configuration profile."""
    update_command_context_from_click(ctx)
    profile = profile or ctx.obj['profile']
    config_manager = ConfigurationProfile()
    config_manager.remove_profile(profile)

import os
from pathlib import Path
import configparser
import click
from cloudos_cli.logging.logger import update_command_context_from_click


class ConfigurationProfile:
    """Class to manage configuration profiles for the CloudOS CLI.
    This class provides methods to create, list, remove, and load profiles from
    configuration files. It also allows setting a profile as the default profile.
    Attributes:
        config_dir (str): Directory where the configuration files are stored.
        credentials_file (str): Path to the credentials file.
        config_file (str): Path to the config file.
    """

    def __init__(self, config_dir=None):
        """Initialize the ConfigurationProfile class.
        Args:
            config_dir (str): Directory where the configuration files are stored.
        """
        # Set the configuration directory to the user's home directory if not provided
        self.config_dir = config_dir or os.path.join(Path.home(), ".cloudos")
        self.credentials_file = os.path.join(self.config_dir, "credentials")
        self.config_file = os.path.join(self.config_dir, "config")

        # Ensure the configuration directory exists
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)

    def create_profile_from_input(self, profile_name):
        """Interactively create a profile in credentials and config files.
        Parameters:
        ----------
        profile_name : str
            The name of the profile to create or update. If the profile already exists,
            the user will be prompted to update its parameters.
        This method guides the user through an interactive process to input or update
        profile details such as API token, platform URL, workspace ID, project name,
        execution platform, repository provider, and workflow name. The profile can
        also be set as the default profile if desired.
        The API token is stored in the credentials file, while other settings are
        stored in the config file. If the profile already exists, existing values
        are pre-filled for convenience.
        """

        # Load or create configparser instances
        credentials = configparser.ConfigParser()
        config = configparser.ConfigParser()

        # If files exist, read them
        if os.path.exists(self.credentials_file):
            credentials.read(self.credentials_file)
        if os.path.exists(self.config_file):
            config.read(self.config_file)

        number_of_profiles = len(config.sections())

        shared_config = dict({})
        # Check if the profile already exists
        if profile_name in config.sections() and profile_name in credentials.sections():
            profile_data = self.load_profile(profile_name=profile_name)
            shared_config['apikey'] = profile_data.get('apikey', None)
            shared_config['cloudos_url'] = profile_data.get('cloudos_url', None)
            shared_config['workspace_id'] = profile_data.get('workspace_id', None)
            shared_config['procurement_id'] = profile_data.get('procurement_id', None)
            shared_config['project_name'] = profile_data.get('project_name', None)
            shared_config['workflow_name'] = profile_data.get('workflow_name', None)
            shared_config['repository_platform'] = profile_data.get('repository_platform', None)
            shared_config['execution_platform'] = profile_data.get('execution_platform', None)
            shared_config['session_id'] = profile_data.get('session_id', None)
            shared_config['profile'] = profile_name
            print(f"Profile '{profile_name}' already exists. You can update single parameters or all.")

        if shared_config.get('profile', None) is not None:
            print(f"Updating profile: {profile_name}")
        else:
            print(f"Creating new profile: {profile_name}")

        # Ask for user input
        # API token
        present_api_token = shared_config.get('apikey', None)
        if present_api_token is not None:
            # Mask the API token except for the last 4 characters, max 16 characters masked
            masked_api_token = '*' * max(0, min(len(present_api_token) - 4, 16)) + present_api_token[-4:]
            api_token = input(f"API token [{masked_api_token}]: ").strip()
        else:
            api_token = input(f"API token [{profile_name}]: ").strip()
        # If the user presses Enter, keep the existing value
        if api_token == "" and shared_config.get('apikey', None) is not None:
            api_token = shared_config['apikey']
        elif api_token == "":
            api_token = None
        else:
            api_token = api_token

        # Platform URL
        platform_url = input(f"Platform URL [{shared_config.get('cloudos_url', profile_name)}]: ").strip()
        # If the user presses Enter, keep the existing value
        if platform_url == "" and shared_config.get('cloudos_url', None) is not None:
            platform_url = shared_config['cloudos_url']
        elif platform_url == "":
            platform_url = None
        else:
            platform_url = platform_url

        # Workspace ID
        platform_workspace_id = input(
            f"Platform workspace ID [{shared_config.get('workspace_id', profile_name)}]: "
        ).strip()
        # If the user presses Enter, keep the existing value
        if platform_workspace_id == "" and shared_config.get('workspace_id', None) is not None:
            platform_workspace_id = shared_config['workspace_id']
        elif platform_workspace_id == "":
            platform_workspace_id = None
        else:
            platform_workspace_id = platform_workspace_id

        # Workspace ID
        platform_procurement_id = input(
            f"Platform procurement ID [{shared_config.get('procurement_id', profile_name)}]: "
        ).strip()
        # If the user presses Enter, keep the existing value
        if platform_procurement_id == "" and shared_config.get('procurement_id', None) is not None:
            platform_procurement_id = shared_config['procurement_id']
        elif platform_procurement_id == "":
            platform_procurement_id = None
        else:
            platform_procurement_id = platform_procurement_id

        # Project name
        project_name = input(f"Project name [{shared_config.get('project_name', profile_name)}]: ").strip()
        # If the user presses Enter, keep the existing value
        if project_name == "" and shared_config.get('project_name', None) is not None:
            project_name = shared_config['project_name']
        elif project_name == "":
            project_name = None
        else:
            project_name = project_name

        # Execution platform
        while True:
            platform_executor = input(
                f"Platform executor [{shared_config.get('execution_platform', profile_name)}]:\n" +
                "\t1. aws (default)\n" +
                "\t2. azure\n"
            ).strip()
            if platform_executor == "" and shared_config.get('execution_platform', None) is not None:
                platform_executor = shared_config['execution_platform']
                break
            elif platform_executor == "1" or platform_executor.lower() == "aws":
                platform_executor = "aws"
                break
            elif platform_executor == "2" or platform_executor.lower() == "azure":
                platform_executor = "azure"
                break
            elif platform_executor == "":
                platform_executor = "aws"
                break
            else:
                print("❌ Invalid choice. Please select either 1 (aws) or 2 (azure).")

        # Repository provider
        while True:
            repository_provider = input(
                f"Repository provider [{shared_config.get('repository_platform', profile_name)}]:\n" +
                "\t1. github (default)\n" +
                "\t2. gitlab\n" +
                "\t3. bitbucketServer\n"
            ).strip()
            if repository_provider == "" and shared_config.get('repository_platform', None) is not None:
                repository_provider = shared_config['repository_platform']
                break
            elif repository_provider == "1" or repository_provider.lower() == "github":
                repository_provider = "github"
                break
            elif repository_provider == "2" or repository_provider.lower() == "gitlab":
                repository_provider = "gitlab"
                break
            elif repository_provider == "3" or repository_provider.lower() == "bitbucketserver":
                repository_provider = "bitbucketServer"
                break
            elif repository_provider == "":
                repository_provider = "github"
                break
            else:
                print("❌ Invalid choice. Please select either 1 (github) or 2 (gitlab) or 3 (bitbucketServer).")

        # Workflow name
        workflow_name = input(f"Workflow name [{shared_config.get('workflow_name', profile_name)}]: ").strip()
        # If the user presses Enter, keep the existing value
        if workflow_name == "" and shared_config.get('workflow_name', None) is not None:
            workflow_name = shared_config['workflow_name']
        elif workflow_name == "":
            workflow_name = None
        else:
            workflow_name = workflow_name

        # Interactive Analysis ID
        session_id = input(
            f"Interactive Analysis ID [{shared_config.get('session_id', profile_name)}]: "
        ).strip()
        # If the user presses Enter, keep the existing value
        if session_id == "" and shared_config.get('session_id', None) is not None:
            session_id = shared_config['session_id']
        elif session_id == "":
            session_id = None
        else:
            session_id = session_id

        # Make the profile the default if it is the first one
        if number_of_profiles >= 1:
            default_profile = self.determine_default_profile()
            if default_profile is not None:
                if default_profile == profile_name:
                    print(f"Profile '{profile_name}' is already the default profile.")
                    default_profile = True
                else:
                    make_default = input(f"Make this profile the default? (y/n) [{profile_name}]: ").strip().lower()
                    if make_default == 'y':
                        default_profile = True
                        # Remove the default flag from any existing profiles
                        for section in config.sections():
                            if 'default' in config[section]:
                                if config[section]['default'].lower() == 'true':
                                    config[section]['default'] = 'False'
                    else:
                        default_profile = False
        else:
            default_profile = True

        # Save API token into credentials file
        credentials[profile_name] = {}
        if api_token is not None:
            credentials[profile_name]['apikey'] = api_token
        with open(self.credentials_file, 'w') as cred_file:
            credentials.write(cred_file)

        # Save other settings into config file
        config[profile_name] = {}
        if platform_url is not None:
            config[profile_name]['cloudos_url'] = platform_url
        if platform_workspace_id is not None:
            config[profile_name]['workspace_id'] = platform_workspace_id
        if platform_procurement_id is not None:
            config[profile_name]['procurement_id'] = platform_procurement_id
        if project_name is not None:
            config[profile_name]['project_name'] = project_name
        if platform_executor is not None:
            config[profile_name]['execution_platform'] = platform_executor
        if repository_provider is not None:
            config[profile_name]['repository_platform'] = repository_provider
        if workflow_name is not None:
            config[profile_name]['workflow_name'] = workflow_name
        if default_profile is not None:
            config[profile_name]['default'] = str(default_profile)
        if session_id is not None:
            config[profile_name]['session_id'] = session_id
        

        with open(self.config_file, 'w') as conf_file:
            config.write(conf_file)

        # if the profile existed, print message as updated
        if shared_config.get('profile', None) is not None:
            print(f"\n✅ Profile '{profile_name}' updated successfully!")
        else:
            # if the profile was created, print message as created
            print(f"\n✅ Profile '{profile_name}' created successfully!")

    def list_profiles(self):
        """Lists all available profiles."""
        config = configparser.ConfigParser()
        config.read(self.config_file)

        if not config.sections():
            print("No profiles found.")
            return

        print("Available profiles:")
        for profile in config.sections():
            # Check if the profile is the default one
            if config[profile].getboolean('default', fallback=False):
                print(f" - {profile} (default)")
            else:
                print(f" - {profile}")

    def remove_profile(self, profile):
        """Removes a profile from the config and credentials files.
        Parameters:
        ----------
        profile : str
            The name of the profile to remove.
        """
        # Load or create configparser instances
        credentials = configparser.ConfigParser()
        config = configparser.ConfigParser()

        # If files exist, read them
        if os.path.exists(self.credentials_file):
            credentials.read(self.credentials_file)
        if os.path.exists(self.config_file):
            config.read(self.config_file)

        if not config.sections():
            print("No profiles found.")
            return

        # Check if the section exists in the config file
        if config.has_section(profile) and credentials.has_section(profile):
            # check if this profile is the current default
            if config[profile].getboolean('default', fallback=False):
                # If it is, set the first profile as default
                for section in config.sections():
                    if section != profile:
                        config[section]['default'] = 'True'
                        break
                else:
                    print("No other profiles available to set as default.")
            config.remove_section(profile)
            credentials.remove_section(profile)
            with open(self.credentials_file, 'w') as credfile:
                credentials.write(credfile)
            with open(self.config_file, 'w') as configfile:
                config.write(configfile)
            print(f"Profile '{profile}' removed successfully.")
        else:
            print(f"No profile found with the name '{profile}'.")

    def make_default_profile(self, profile_name):
        """Set a profile as the default profile.
        Parameters:
        ----------
        profile_name : str
            The name of the profile to set as default.
        """
        config = configparser.ConfigParser()
        config.read(self.config_file)

        if not config.has_section(profile_name):
            print(f"No profile found with the name '{profile_name}'.")
            return

        # Check if the profile is already default
        if config[profile_name].getboolean('default', fallback=False):
            print(f"Profile '{profile_name}' is already the default profile.")
            return

        # Remove the default flag from any existing profiles
        for section in config.sections():
            if 'default' in config[section]:
                if config[section]['default'].lower() == 'true':
                    config[section]['default'] = 'False'

        # Set the new default profile
        config[profile_name]['default'] = 'True'
        with open(self.config_file, 'w') as conf_file:
            config.write(conf_file)
        print(f"Profile '{profile_name}' set as default.")

    def load_profile(self, profile_name):
        """Load a profile from the config and credentials files dynamically.
        
        This method now returns ALL parameters from the profile, not just predefined ones.
        This makes it extensible - you can add new parameters to profiles without modifying this method.
        
        Parameters:
        ----------
        profile_name : str
            The name of the profile to load.
        Returns:
        -------
        dict
            A dictionary containing all profile parameters. Returns all keys from both
            credentials and config files for the specified profile.
            
        Examples
        --------
        # If you add accelerate_saving_results to your profile config:
        config[profile_name]['accelerate_saving_results'] = 'true'
        
        # It will automatically be included in the returned dictionary:
        profile_data = load_profile('myprofile')
        # profile_data will contain 'accelerate_saving_results': 'true'
        """
        config = configparser.ConfigParser()
        credentials = configparser.ConfigParser()

        # If files exist, read them
        if os.path.exists(self.credentials_file):
            credentials.read(self.credentials_file)
        if os.path.exists(self.config_file):
            config.read(self.config_file)

        if not config.has_section(profile_name):
            raise ValueError(f'Profile "{profile_name}" does not exist. Please create it ' +
                             f'with "cloudos configure --profile {profile_name}".\n')

        # Dynamically load all parameters from the profile
        profile_data = {}
        
        # Load all items from credentials file
        if credentials.has_section(profile_name):
            for key, value in credentials[profile_name].items():
                profile_data[key] = value
        
        # Load all items from config file
        if config.has_section(profile_name):
            for key, value in config[profile_name].items():
                # Skip the 'default' flag as it's not a user parameter
                if key != 'default':
                    profile_data[key] = value
        
        return profile_data

    def check_if_profile_exists(self, profile_name):
        """Check if a profile exists in the config file.
        Parameters:
        ----------
        profile_name : str
            The name of the profile to check.
        Returns:
        -------
        bool
            True if the profile exists, False otherwise.
        """
        config = configparser.ConfigParser()
        config.read(self.config_file)

        if not config.has_section(profile_name):
            return False
        return True

    def determine_default_profile(self):
        """Determine the default profile from the config file.
        Returns:
        -------
        str
            The name of the default profile, or None if no default is set.
        """
        config = configparser.ConfigParser()
        config.read(self.config_file)

        if len(config.sections()) == 0:
            return None

        # prioritize profiles marked as default
        for section in config.sections():
            if 'default' in config[section]:
                if config[section]['default'].lower() == 'true':
                    return section

        # check if no "default" profile exists in the sections
        if 'default' not in config.sections():
            print("No default profile found. Making the first profile the default.")
            # Set the first profile as default
            first_profile = config.sections()[0]
            config[first_profile]['default'] = 'True'
            with open(self.config_file, 'w') as conf_file:
                config.write(conf_file)
            return first_profile
        else:
            # make "default" profile as default
            config["default"]["default"] = "True"
            with open(self.config_file, 'w') as conf_file:
                config.write(conf_file)
            return "default"

    @staticmethod
    def get_param_value(ctx, param_value, param_name, default_value, required=False, missing_required_params=None):
        source = ctx.get_parameter_source(param_name)
        result = default_value if source != click.core.ParameterSource.COMMANDLINE else param_value

        if required and result == "":
            if missing_required_params is not None:
                missing_required_params.append('--' + param_name.replace('_', '-'))
        return result

    def load_profile_and_validate_data(self, ctx, init_profile, cloudos_url_default, profile, required_dict, **cli_params):
        """
        Load profile data and validate required parameters dynamically.
        
        This method now accepts any parameters via **cli_params, making it extensible.
        You can add new parameters to profiles (like accelerate_saving_results) without
        modifying this method.

        Parameters
        ----------
        ctx : click.Context
            The Click context object.
        init_profile : str
            A default string to identify if any profile is available
        cloudos_url_default : str
            The default cloudos URL to compare with the one from the profile
        profile : str
            The profile name to load.
        required_dict : dict
            A dictionary with param name as key and whether is required or not (as bool) as value.
        **cli_params : dict
            All CLI parameters passed as keyword arguments. Any parameter can be passed here
            and will be resolved from the profile if available.
            
            Examples: apikey, cloudos_url, workspace_id, project_name, workflow_name, 
                     execution_platform, repository_platform, session_id, procurement_id,
                     accelerate_saving_results, etc.

        Returns
        -------
        dict
            A dictionary containing all loaded and validated parameters.
            
        Examples
        --------
        # Add a new parameter to profile without changing this method:
        # 1. Add to profile creation (create_profile_from_input)
        # 2. Add to load_profile method return dict
        # 3. Pass it in cli_params when calling this method
        # 4. It will automatically be resolved from profile!
        """
        missing = []
        resolved_params = {}

        if profile != init_profile:
            # Load profile data
            profile_data = self.load_profile(profile_name=profile)
            
            # Dynamically process all parameters passed in cli_params
            for param_name, cli_value in cli_params.items():
                profile_value = profile_data.get(param_name, "")
                is_required = required_dict.get(param_name, False)

                # Resolve the parameter value
                resolved_value = self.get_param_value(
                    ctx, 
                    cli_value, 
                    param_name, 
                    profile_value,
                    required=is_required, 
                    missing_required_params=missing
                )
                
                # Convert empty strings to None for optional parameters
                # This prevents issues with functions that expect None for unset values
                if resolved_value == "" and not is_required:
                    resolved_value = None
                resolved_params[param_name] = resolved_value
        else:
            # No profile used - check if user provided all required parameters
            for param_name, cli_value in cli_params.items():
                is_required = required_dict.get(param_name, False)

                # Resolve the parameter value
                resolved_value = self.get_param_value(
                    ctx,
                    cli_value,
                    param_name,
                    cli_value,  # Use CLI value as default when no profile
                    required=is_required,
                    missing_required_params=missing
                )
                # Convert empty strings to None for optional parameters
                # This prevents issues with functions that expect None for unset values
                if resolved_value == "" and not is_required:
                    resolved_value = None
                resolved_params[param_name] = resolved_value

        # Special handling for cloudos_url with fallback to default
        resolved_cloudos_url = resolved_params.get('cloudos_url', '')
        if not resolved_cloudos_url:
            click.secho(
                f"No CloudOS URL provided via CLI or profile. Falling back to default: {cloudos_url_default}",
                fg="yellow",
                bold=True
            )
            resolved_params['cloudos_url'] = cloudos_url_default
        else:
            resolved_params['cloudos_url'] = resolved_cloudos_url.rstrip('/')

        # Raise once, after all checks
        if missing:
            formatted = ', '.join(p for p in missing)
            raise click.UsageError(
                f"Missing required option/s: {formatted}\n"
                f"You can configure the following parameters persistently by running cloudos configure:\n"
                f"  --apikey, --cloudos-url, --workspace-id, --workflow-name,\n"
                f"  --repository-platform, --execution-platform, --project-name,\n"
                f"  --session-id, --procurement-id\n"
                f"For more information on the usage of the command, please run cloudos configure --help"
            )

        return resolved_params


# Not part of the class, but related to configuration
# Global constants for CloudOS CLI
CLOUDOS_URL = 'https://cloudos.lifebit.ai'
INIT_PROFILE = 'initialisingProfile'

# Define all standard configuration keys with their default empty values
# This is the single source of truth for configuration fields
STANDARD_CONFIG_KEYS = {
    'apikey': '',
    'cloudos_url': CLOUDOS_URL,
    'workspace_id': '',
    'procurement_id': '',
    'project_name': '',
    'workflow_name': '',
    'repository_platform': 'github',
    'execution_platform': 'aws',
    'profile': INIT_PROFILE,
    'session_id': '',
}


# Decorator to load profile configuration and validate required parameters
def with_profile_config(required_params=None):
    """
    Decorator to automatically handle profile configuration loading for commands.

    This decorator simplifies command functions by automatically loading configuration
    from profiles and validating required parameters. It eliminates the need to manually
    create required_dict and call load_profile_and_validate_data in each command.

    Parameters
    ----------
    required_params : list, optional
        List of parameter names that can currently be added in a profile. Common values:
        - 'apikey': CloudOS API key
        - 'workspace_id': CloudOS workspace ID
        - 'project_name': Project name
        - 'workflow_name': Workflow/pipeline name
        - 'session_id': Interactive session ID
        - 'procurement_id': Procurement ID
        This list can be updated as new parameters are added to profiles.

    Example
    -------
    @job.command('details')
    @click.option('--apikey', help='Your CloudOS API key', required=True)
    @click.option('--workspace-id', help='The specific CloudOS workspace id.', required=True)
    @click.option('--job-id', help='The job id in CloudOS to search for.', required=True)
    @click.option('--profile', help='Profile to use from the config file', default=None)
    @click.pass_context
    @with_profile_config(required_params=['apikey', 'workspace_id'])
    def job_details(ctx, apikey, workspace_id, job_id, ...):
        # apikey, cloudos_url, workspace_id are automatically available
        cl = Cloudos(cloudos_url, apikey, None)
        ...

    Returns
    -------
    function
        Decorated function with automatic profile configuration loading.
    """
    import functools

    if required_params is None:
        required_params = []

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            import inspect

            # Get context from args or kwargs
            ctx = kwargs.get('ctx') or (args[0] if args and isinstance(args[0], click.Context) else None)

            if ctx is None:
                raise ValueError("Context not found. Make sure @click.pass_context is used before this decorator.")

            # Update logging context
            update_command_context_from_click(ctx)

            # Get profile from kwargs
            profile = kwargs.get('profile')

            # Check if profile was explicitly provided on command line
            # If it was provided via CLI, use that; otherwise fall back to default_map
            profile_source = ctx.get_parameter_source('profile')

            if profile_source == click.core.ParameterSource.COMMANDLINE:
                # User explicitly specified --profile on command line, use it
                pass  # profile is already set from kwargs
            elif profile is None and ctx.default_map:
                # No profile specified on CLI, try to get from default_map
                try:
                    command_path = ctx.command_path.split()[1:]  # Skip the root command
                    profile_map = ctx.default_map
                    for cmd in command_path:
                        profile_map = profile_map.get(cmd, {})
                    profile = profile_map.get('profile')
                except (AttributeError, KeyError):
                    pass

            # Build required_dict dynamically from required_params
            # Only parameters in required_params will be validated as required
            required_dict = {param: param in required_params for param in required_params}

            # Create configuration manager and load profile
            config_manager = ConfigurationProfile()

            # Pass all kwargs dynamically to load_profile_and_validate_data
            # This allows any parameter to be loaded from profile without modifying the decorator
            # Remove 'profile' from kwargs since we're passing it explicitly
            cli_params = {k: v for k, v in kwargs.items() if k != 'profile'}

            user_options = config_manager.load_profile_and_validate_data(
                ctx,
                INIT_PROFILE,
                CLOUDOS_URL,
                profile=profile,
                required_dict=required_dict,
                **cli_params  # Pass all parameters dynamically (except 'profile')!
            )

            # Store user_options in context for easy access
            if ctx.obj is None:
                ctx.obj = {}
            ctx.obj.update(user_options)

            # Get function signature to determine which parameters it accepts
            sig = inspect.signature(func)
            func_params = set(sig.parameters.keys())

            # Only update kwargs with parameters that the function actually accepts
            # AND that were not explicitly provided by the user on the command line
            # AND that have a meaningful value from the profile (not None)
            import sys
            for key, value in user_options.items():
                if key in func_params and value is not None:
                    # Check if the parameter was provided via command line
                    param_source = ctx.get_parameter_source(key)
                    # Only override if NOT from command line (i.e., use profile/default values)
                    if param_source != click.core.ParameterSource.COMMANDLINE:
                        kwargs[key] = value

            # Call the original function
            return func(*args, **kwargs)

        return wrapper
    return decorator


def build_default_map_for_group(group, shared_config):
    """
    Recursively build a default_map dictionary for a Click group and all its subcommands.

    This function introspects a Click group to discover all registered commands and subcommands,
    then builds a default_map structure that applies the shared_config to all of them.
    This eliminates the need to manually maintain a list of commands in default_map.

    Parameters
    ----------
    group : click.Group
        The Click group to introspect
    shared_config : dict
        The configuration dictionary to apply to all commands

    Returns
    -------
    dict
        A dictionary mapping command names to their configurations

    Example
    -------
    # Instead of manually defining:
    default_map = {
        'job': {'status': shared_config, 'list': shared_config, ...},
        'workflow': {'list': shared_config, ...}
    }

    # Use:
    default_map = build_default_map_for_group(run_cloudos_cli, shared_config)
    """
    default_map = {}

    if not isinstance(group, click.Group):
        return default_map

    # Iterate through all commands in the group
    for cmd_name, cmd in group.commands.items():
        if isinstance(cmd, click.Group):
            # If it's a subgroup, recursively build its default_map
            default_map[cmd_name] = build_default_map_for_group(cmd, shared_config)
        else:
            # If it's a command, apply the shared config
            default_map[cmd_name] = shared_config

    return default_map


def get_shared_config():
    """
    Load shared configuration from the default profile with fallback to empty defaults.

    This function centralizes the logic for loading the shared configuration that will
    be used to populate the default_map for all commands. It handles missing profiles,
    incomplete profiles, and loading errors gracefully.

    The default profile is loaded without validation - just to provide default values.
    The with_profile_config decorator will handle validation when commands actually run.
    This allows the default profile to have missing fields when not actually used.

    Returns
    -------
    dict
        A dictionary containing the shared configuration with all standard fields.
        Missing fields are filled with empty strings to prevent KeyErrors.

    Example
    -------
    >>> shared_config = get_shared_config()
    >>> ctx.default_map = build_default_map_for_group(run_cloudos_cli, shared_config)
    """
    from rich.console import Console

    config_manager = ConfigurationProfile()
    profile_to_use = config_manager.determine_default_profile()

    if profile_to_use is None:
        console = Console()
        console.print(
            "[bold yellow]No profile found. Please create one with \"cloudos configure\"."
        )
        # Return default configuration when no profile exists
        return STANDARD_CONFIG_KEYS.copy()

    # Load default profile - just to provide defaults
    try:
        shared_config = config_manager.load_profile(profile_name=profile_to_use)
        # Ensure 'profile' key is always set to the profile name
        shared_config['profile'] = profile_to_use

        # Fill in any missing keys with default values to prevent KeyErrors
        for key, default_value in STANDARD_CONFIG_KEYS.items():
            if key not in shared_config:
                shared_config[key] = default_value

        return shared_config

    except Exception:
        # If loading the default profile fails, use empty defaults
        shared_config = STANDARD_CONFIG_KEYS.copy()
        shared_config['profile'] = profile_to_use
        return shared_config
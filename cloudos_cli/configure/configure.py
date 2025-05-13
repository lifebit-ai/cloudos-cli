import os
from pathlib import Path
import configparser
import getpass
import sys

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
            shared_config['project_name'] = profile_data.get('project_name', None)
            shared_config['workflow_name'] = profile_data.get('workflow_name', None)
            shared_config['repository_platform'] = profile_data.get('repository_platform', None)
            shared_config['execution_platform'] = profile_data.get('execution_platform', None)
            shared_config['profile'] = profile_name
            print(f"Profile '{profile_name}' already exists. You can update single parameters or all.")

        if shared_config.get('profile', None) is not None:
            print(f"Updating profile: {profile_name}")
        else:
            print(f"Creating new profile: {profile_name}")

        # Ask for user input
        ## API token
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

        ## Platform URL
        platform_url = input(f"Platform URL [{shared_config.get('cloudos_url', profile_name)}]: ").strip()
        # If the user presses Enter, keep the existing value
        if platform_url == "" and shared_config.get('cloudos_url', None) is not None:
            platform_url = shared_config['cloudos_url']
        elif platform_url == "":
            platform_url = None
        else:
            platform_url = platform_url

        ## Workspace ID
        platform_workspace_id = input(f"Platform workspace ID [{shared_config.get('workspace_id', profile_name)}]: ").strip()
        # If the user presses Enter, keep the existing value
        if platform_workspace_id == "" and shared_config.get('workspace_id', None) is not None:
            platform_workspace_id = shared_config['workspace_id']
        elif platform_workspace_id == "":
            platform_workspace_id = None
        else:
            platform_workspace_id = platform_workspace_id

        ## Project name
        project_name = input(f"Project name [{shared_config.get('project_name', profile_name)}]: ").strip()
        # If the user presses Enter, keep the existing value
        if project_name == "" and shared_config.get('project_name', None) is not None:
            project_name = shared_config['project_name']
        elif project_name == "":
            project_name = None
        else:
            project_name = project_name

        ## Execution platform
        while True:
            platform_executor = input(f"Platform executor [{shared_config.get('execution_platform', profile_name)}]:\n\t1. aws (default)\n\t2. azure\n ").strip()
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

        ## Repository provider
        while True:
            repository_provider = input(f"Repository provider [{shared_config.get('repository_platform', profile_name)}]:\n\t1. github (default)\n\t2. gitlab\n\t3. bitBucketServer\n").strip()
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

        ## Workflow name
        workflow_name = input(f"Workflow name [{shared_config.get('workflow_name', profile_name)}]: ").strip()
        # If the user presses Enter, keep the existing value
        if workflow_name == "" and shared_config.get('workflow_name', None) is not None:
            workflow_name = shared_config['workflow_name']
        elif workflow_name == "":
            workflow_name = None
        else:
            workflow_name = workflow_name

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
        """Load a profile from the config and credentials files.
        Parameters:
        ----------
        profile_name : str
            The name of the profile to load.
        Returns:
        -------
        dict
            A dictionary containing the profile details.
        """
        config = configparser.ConfigParser()
        credentials = configparser.ConfigParser()

        # If files exist, read them
        if os.path.exists(self.credentials_file):
            credentials.read(self.credentials_file)
        if os.path.exists(self.config_file):
            config.read(self.config_file)

        if not config.has_section(profile_name):
            print(f'[Error] Profile "{profile_name}" does not exist. Please create it with "cloudos configure --profile {profile_name}".\n')
            sys.exit(1)

        return {
            'apikey': credentials[profile_name].get('apikey', ""),
            'cloudos_url': config[profile_name].get('cloudos_url', ""),
            'workspace_id': config[profile_name].get('workspace_id', ""),
            'project_name': config[profile_name].get('project_name', ""),
            'workflow_name': config[profile_name].get('workflow_name', ""),
            'execution_platform': config[profile_name].get('execution_platform', ""),
            'repository_platform': config[profile_name].get('repository_platform', ""),
        }


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

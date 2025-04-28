import os
from pathlib import Path
import configparser
import getpass

class ConfigurationProfile:
    def __init__(self):
        self.config_dir = os.path.join(Path.home(), ".cloudos")
        self.credentials_file = os.path.join(self.config_dir, "credentials")
        self.config_file = os.path.join(self.config_dir, "config")

        # Ensure the configuration directory exists
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)

    def create_default_profile(self, api_key):
        """Creates a default profile in credentials and config files."""
        os.makedirs(self.config_dir, exist_ok=True)

        # Create and write credentials
        credentials = configparser.ConfigParser()
        credentials['default'] = {
            'api_key': api_key
        }
        with open(self.credentials_file, 'w') as cred_file:
            credentials.write(cred_file)

        # Create and write config
        config = configparser.ConfigParser()
        config['default'] = {
            'region': 'us-east-1',
            'timeout': '30',
            'retries': '5'
        }
        with open(self.config_file, 'w') as conf_file:
            config.write(conf_file)


    def read_and_print_profile(self):
        """Reads and prints variables from credentials and config files."""
        credentials = configparser.ConfigParser()
        config = configparser.ConfigParser()

        credentials.read(self.credentials_file)
        config.read(self.config_file)

        print("== Credentials ==")
        for key, value in credentials['default'].items():
            print(f"{key}: {value}")

        print("\n== Config ==")
        for key, value in config['default'].items():
            print(f"{key}: {value}")

    def create_profile_from_input(self, profile_name):
        """Interactively create a profile in credentials and config files."""

        # Load or create configparser instances
        credentials = configparser.ConfigParser()
        config = configparser.ConfigParser()

        # If files exist, read them
        if os.path.exists(self.credentials_file):
            credentials.read(self.credentials_file)
        if os.path.exists(self.config_file):
            config.read(self.config_file)

        number_of_profiles = len(config.sections())

        # Check if the profile already exists
        if profile_name in config.sections():
            answer = input(f"Profile '{profile_name}' already exists. Overwrite it? (y/n): ").strip().lower()
            if answer != 'y':
                print("Aborting without changes.")
                return

        print(f"Creating profile: {profile_name}")

        # Ask for user input
        # --- Double entry verification for the API token ---
        while True:
            api_token = getpass.getpass(f"API token [{profile_name}]: ").strip()
            api_token_confirm = getpass.getpass(f"Confirm API token [{profile_name}]: ").strip()

            if api_token == api_token_confirm:
                print("✅ API token confirmed.")
                break
            else:
                print("❌ Tokens do not match. Please try again.\n")
        platform_url = input(f"Platform URL [{profile_name}]: ").strip()
        platform_workspace_id = input(f"Platform workspace ID [{profile_name}]: ").strip()
        project_name = input(f"Project name [{profile_name}]: ").strip()
        platform_executor = input(f"Platform executor [{profile_name}]: ").strip()
        repository_provider = input(f"Repository provider [{profile_name}]: ").strip()
        if number_of_profiles >= 1:
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
        credentials[profile_name] = {
            'api_key': api_token
        }
        with open(self.credentials_file, 'w') as cred_file:
            credentials.write(cred_file)

        # Save other settings into config file
        config[profile_name] = {
            'platform_url': platform_url,
            'platform_workspace_id': platform_workspace_id,
            'project_name': project_name,
            'platform_executor': platform_executor,
            'repository_provider': repository_provider,
            'default': default_profile
        }

        with open(self.config_file, 'w') as conf_file:
            config.write(conf_file)

        print(f"\n✅ Profile '{profile_name}' created successfully!")

    # def create_profile(self, profile_name, api_key, url, project_name):
    #     """Creates a new profile with the given environmental variables."""
    #     self.config_file = os.path.join(self.config_dir, "credentials")
    #     self.config[profile_name] = {
    #         "api_key": api_key,
    #         "url": url,
    #         "project_name": project_name
    #     }

    #     with open(self.config_file, "w") as file:
    #         self.config.write(file)
    #     print(f"Profile '{profile_name}' created successfully at {self.config_file}.")

    # def load_profile(self, profile_name):
    #     """Loads an existing profile."""
    #     self.config_file = os.path.join(self.config_dir, f"{profile_name}.ini")
    #     if not os.path.exists(self.config_file):
    #         raise FileNotFoundError(f"Profile '{profile_name}' does not exist.")

    #     self.config.read(self.config_file)
    #     self.config.get()
    #     return self.config[profile_name]

    # def create_profile_interactively(self):
    #     """Creates a new profile by asking the user for input."""
    #     profile_name = input("Enter profile name: ").strip()
    #     api_key = input("Enter API key: ").strip()
    #     url = input("Enter URL: ").strip()
    #     project_name = input("Enter project name: ").strip()

    #     self.create_profile(profile_name, api_key, url, project_name)

    def check_if_profile_exists():
        pass

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
        """Removes a profile from the credentials and config files."""
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
        """Sets a profile as the default."""
        config = configparser.ConfigParser()
        config.read(self.config_file)

        if not config.has_section(profile_name):
            print(f"No profile found with the name '{profile_name}'.")
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

# Example usage
# if __name__ == "__main__":
#     config_manager = ConfigurationProfile()

#     print("1. Create a new profile interactively")
#     print("2. Load an existing profile")
#     choice = input("Choose an option (1/2): ").strip()

#     if choice == "1":
#         config_manager.create_profile_interactively()
#     elif choice == "2":
#         profile_name = input("Enter the profile name to load: ").strip()
#         try:
#             profile = config_manager.load_profile(profile_name)
#             print(f"Loaded profile '{profile_name}':")
#             for key, value in profile.items():
#                 print(f"{key}: {value}")
#         except FileNotFoundError as e:
#             print(e)
#     else:
#         print("Invalid choice.")
import re
import sys
from cloudos_cli.utils.errors import BadRequestException


def is_valid_regex(s):
    """
    Validates whether the given string is a valid regular expression.

    Parameters
    ----------
    s : str
        The string to be checked as a regular expression.

    Returns
    -------
    bool
        True if the string is a valid regular expression, False otherwise.
    """
    try:
        re.compile(s)
        return True
    except re.error:
        return False

def is_glob_pattern(s):
    """
    Check if a given string contains glob pattern characters.

    Glob patterns are commonly used for filename matching and include
    special characters such as '*', '?', and '['.

    Parameters
    ----------
    s : str
        The string to check for glob pattern characters.

    Returns
    -------
    bool
        True if the string contains any glob pattern characters, otherwise False.
    """
    return any(char in s for char in "*?[")

def is_probably_regex(s):
    """
    Determines if a given string is likely a regular expression.

    This function checks whether the input string matches common patterns
    that are indicative of regular expressions. It first validates the
    string using `is_valid_regex(s)` and then searches for specific regex
    indicators such as quantifiers, character classes, anchors, and
    alternation.

    Parameters
    ----------
    s : str
        The string to evaluate.

    Returns
    -------
    bool
        True if the string is likely a regular expression, False otherwise.

    Notes
    -----
    The function assumes the existence of `is_valid_regex(s)` which
        validates whether the input string is a valid regex.
    """
    if not is_valid_regex(s):
        return False

    # Patterns that usually indicate actual regex use (not just file names)
    regex_indicators = [
        r"\.\*", r"\.\+", r"\\[dws]", r"\[[^\]]+\]", r"\([^\)]+\)",
        r"\{\d+(,\d*)?\}", r"\^", r"\$", r"\|"
    ]
    return any(re.search(pat, s) for pat in regex_indicators)

def classify_pattern(s):
    """
    Classifies a given string pattern into one of three categories: "regex", "glob", or "exact".

    Parameters
    ----------
    s : str
        The string pattern to classify.

    Returns
    -------
    str: A string indicating the type of pattern:
        - "regex" if the pattern is likely a regular expression.
        - "glob" if the pattern matches glob-style syntax.
        - "exact" if the pattern does not match regex or glob syntax.
    """
    if is_probably_regex(s):
        return "regex"
    elif is_glob_pattern(s):
        return "glob"
    else:
        return "exact"

def generate_datasets_for_project(cloudos_url, apikey, workspace_id, project_name, verify_ssl):
    """
    Generate datasets for a specified project in a CloudOS workspace.

    This function initializes a `Datasets` object for the given project and handles
    potential errors such as missing project elements or unauthorized API calls.

    Parameters
    ----------
    cloudos_url : str
        The URL of the CloudOS instance.
    apikey : str
        The API key for authentication.
    workspace_id : str
        The ID of the workspace where the project resides.
    project_name : str
        The name of the project for which datasets are generated.
    verify_ssl : bool
        Whether to verify SSL certificates during API calls.

    Returns
    -------
    Datasets
        An instance of the `Datasets` class initialized for the specified project.

    Raises
    ------
    ValueError
        If the specified project is not found in the workspace.
    BadRequestException
        If the API call is unauthorized or encounters other issues.
    """

    # this avoids circular import error if import is added at the top
    from cloudos_cli.datasets import Datasets
    try:
        ds = Datasets(
            cloudos_url=cloudos_url,
            apikey=apikey,
            workspace_id=workspace_id,
            project_name=project_name,
            verify=verify_ssl,
            cromwell_token=None
        )
    except ValueError:
        print(f"[ERROR] No {project_name} element in projects was found")
        sys.exit(1)

    except BadRequestException as e:
        if 'Forbidden' in str(e):
            print('[Error] It seems your call is not authorised. Please check if ' +
                  'your workspace is restricted by Airlock and if your API key is valid.')
            sys.exit(1)
        else:
            raise e

    return ds

def get_file_or_folder_id(cloudos_url, apikey, workspace_id, project_name, verify_ssl, command_dir, command_name, is_file=True):
    """Retrieve the ID of a specific file or folder within a CloudOS workspace.

    Parameters
    ----------
    cloudos_url : str
        The base URL of the CloudOS API.
    apikey : str
        The API key for authenticating requests to the CloudOS API.
    workspace_id : str
        The ID of the workspace containing the project.
    project_name : str
        The name of the project within the workspace.
    verify_ssl : bool
        Whether to verify SSL certificates for the API requests.
    name : str
        The name of the file or folder whose ID is to be retrieved.
    is_file : bool, optional
        Whether to retrieve a file ID (True) or folder ID (False). Default is True.

    Returns
    -------
    str: The ID of the specified file or folder.

    Raises
    ------
    ValueError
        If the specified file or folder is not found.
    Exception
        If there is an error during the API interaction or data retrieval.

    Notes
    -----
    - This function uses the `generate_datasets_for_project` function to create a Datasets object for the specified project.
    - The `list_folder_content` method is used for files, and `list_project_content` is used for folders.
    - The function assumes that the IDs are stored in the `"_id"` field of the metadata.
    """
    # create a Datasets() class
    ds = generate_datasets_for_project(cloudos_url, apikey, workspace_id, project_name, verify_ssl)

    if is_file:
        # get all files from a folder
        content = ds.list_folder_content(command_dir)
        for file in content['files']:
            if file.get("name") == command_name:
                return file.get("_id", '')
        raise ValueError(f"File '{command_name}' not found in directory '{command_dir}'.")
    else:
        # get all folders from the project
        # check if the command_dir has a sub-folder
        if len(command_dir.split("/")) > 1:
            # get the first folder which is just below the project
            folders = ds.list_folder_content(command_dir.split("/")[0])
            # use the last folder as is listed in the first folder
            folder_to_search = command_dir.split("/")[-1]
        else:
            folders = ds.list_project_content()
            folder_to_search = command_dir

        for folder in folders['folders']:
            if folder.get("name") == folder_to_search:
                return folder.get("_id", '')
        raise ValueError(f"Folder '{folder_to_search}' not found in project.")

def extract_project(path):
    """
    Extracts the project name and the remaining path from a given file path.

    The function assumes that a "project" exists if the path contains at least three parts
    when split by slashes. If the path has fewer than three parts, the project name is
    considered empty, and the entire path is returned as the remaining path.

    Parameters
    ----------
    path : str
        The file path to process.

    Returns
    -------
    tuple: A tuple containing:
        - str: The project name (empty string if no project exists).
        - str: The remaining path after the project name.
    """
    # Strip slashes and split the path
    parts = path.strip("/").split("/")
    # A "project" exists only if there are at least 3 parts
    # globs needs more than 3 parts i.e. PROJECT/Data/Downloads/*.csv
    if (len(parts) >= 3 and not is_glob_pattern(path)) or \
       (len(parts) > 3 and is_glob_pattern(path)):
        # Return the first part as project name and the rest as remaining path
        return parts[0], "/".join(parts[1:])
    else:
        # project is empty, use the project_name of the function
        return "", "/".join(parts)
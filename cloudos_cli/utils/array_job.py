import re
from cloudos_cli.datasets import Datasets


def is_valid_regex(s):
    try:
        re.compile(s)
        return True
    except re.error:
        return False

def is_glob_pattern(s):
    return any(char in s for char in "*?[")

def is_probably_regex(s):
    if not is_valid_regex(s):
        return False

    # Patterns that usually indicate actual regex use (not just file names)
    regex_indicators = [
        r"\.\*", r"\.\+", r"\\[dws]", r"\[[^\]]+\]", r"\([^\)]+\)",
        r"\{\d+(,\d*)?\}", r"\^", r"\$", r"\|"
    ]
    return any(re.search(pat, s) for pat in regex_indicators)

def classify_pattern(s):
    if is_probably_regex(s):
        return "regex"
    elif is_glob_pattern(s):
        return "glob"
    else:
        return "exact"

def generate_datasets_for_project(cloudos_url, apikey, workspace_id, project_name, verify_ssl):
    
    return Datasets(
        cloudos_url=cloudos_url,
        apikey=apikey,
        workspace_id=workspace_id,
        project_name=project_name,
        verify=verify_ssl,
        cromwell_token=None
    )

def get_file_id(cloudos_url, apikey, workspace_id, project_name, verify_ssl, directory_name, file_name):
    """Retrieve the ID of a specific file and its parent folder ID within a CloudOS workspace.

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
    directory_name : str
        The name of the directory containing the file.
    file_name : str
        The name of the file whose ID is to be retrieved.

    Returns
    -------
    tuple: A tuple containing:
        - file_id (str): The ID of the specified file.
        - folder_id (str): The ID of the parent folder containing the file.

    Raises
    ------
    ValueError
        If the specified file is not found in the directory.
    Exception
        If there is an error during the API interaction or data retrieval.

    Notes
    -----
    - This function uses the `generate_datasets_for_project` function to create a Datasets object for the specified project.
    - The `list_folder_content` method of the Datasets object is used to retrieve the contents of the specified directory.
    - The function assumes that the file and folder IDs are stored in the `"_id"` field and the parent folder ID is stored in the `"parent"` field of the file metadata.
    """
    # create a Datasets() class
    ds = generate_datasets_for_project(cloudos_url, apikey, workspace_id, project_name, verify_ssl)

    # get all files from a folder
    content = ds.list_folder_content(directory_name)

    # get the ID only of the desired file or folder
    # "parent":{"kind":"Dataset","id":"681dc9f121cd5b935168d143"}
    for file in content['files']:
        if file.get("name") == file_name:
            file_id = file.get("_id")
            folder_id = file.get("parent").get("_id")
            return file_id, folder_id


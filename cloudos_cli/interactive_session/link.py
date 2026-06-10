"""
This is the main class for linking files to interactive sessions.
"""

import json
import time
from dataclasses import dataclass
from typing import Union, List, Dict
from urllib.parse import urlparse

import rich_click as click

from cloudos_cli.clos import Cloudos
from cloudos_cli.utils.requests import retry_requests_post, retry_requests_get
from cloudos_cli.utils.errors import JoBNotCompletedException
from cloudos_cli.utils.array_job import generate_datasets_for_project


@dataclass
class Link(Cloudos):
    """Class for linking folders/files to interactive sessions.

    Parameters
    ----------
    cloudos_url : string
        The Lifebit Platform service url.
    apikey : string
        Your Lifebit Platform API key.
    workspace_id : string
        The specific Cloudos workspace id.
    verify: [bool|string]
        Whether to use SSL verification or not. Alternatively, if
        a string is passed, it will be interpreted as the path to
        the SSL certificate file.
    """
    workspace_id: str
    project_name: str
    verify: Union[bool, str] = True

    def link_folder(self,
                    folder: str,
                    session_id: str) -> dict:
        """Link a folder (S3 or File Explorer) to an interactive session.

        Attempts to use API v2 first, with automatic fallback to v1 if v2 is not available.

        Parameters
        ----------
        folder : str
            The folder to link.
        session_id : str
            The interactive session ID.

        Raises
        ------
        ValueError
            If the URL already exists with 'mounted' status
            If the API key is invalid or permissions are insufficient
            If the URL is invalid or the session is not active.
        """
        # Use batch method for single folder (leverages v2 dataItems array)
        return self.link_folders_batch([folder], session_id)

    def link_folders_batch(self,
                          folders: list,
                          session_id: str,
                          committed_count: int = 0) -> bool:
        """Link multiple folders/files (S3 or File Explorer) to an interactive session in one request.

        Attempts to use API v2 (which supports multiple items per request) first,
        with automatic fallback to v1 (individual requests) if v2 is not available.

        Parameters
        ----------
        folders : list
            List of folder/file paths to link.
        session_id : str
            The interactive session ID.
        committed_count : int, optional
            Number of items already submitted in earlier batches during this CLI invocation
            but not yet visible in the session status. Added to the current count when
            enforcing the 100-item limit.

        Raises
        ------
        ValueError
            If any validation fails or API errors occur.
        """
        if not folders:
            raise ValueError("No paths provided")

        # Check 100-item limit against already-linked items plus any in-flight batches
        current_items = self.get_fuse_filesystems_status(session_id)
        current_count = len(current_items) + committed_count
        if current_count + len(folders) > 100:
            raise ValueError("Cannot link more than 100 items")

        # Check for duplicate names against already-mounted items
        existing_mount_names = {fs.get("mountName") for fs in current_items if fs.get("mountName")}

        # Parse and validate all items
        data_items, folder_info = self._parse_items_to_data_items(folders, existing_mount_names)

        # Try v2 API first (supports batch)
        status_code = self._try_mount_v2(data_items, session_id)

        if status_code is None:
            # v2 failed or not available, fall back to v1
            status_code = self._fallback_mount_v1(folder_info, session_id)

        # Verify mount completion for all items
        if status_code == 204:
            return self._verify_all_mounts(folder_info, session_id)
        return True

    def _parse_items_to_data_items(self, folders: list, existing_mount_names: set = None) -> tuple:
        """Parse and validate folders/files, extracting data items for API payload.

        Parameters
        ----------
        folders : list
            List of folder/file paths to parse.
        existing_mount_names : set, optional
            Set of mount names already linked to the session.

        Returns
        -------
        tuple
            (data_items, folder_info) where data_items is a list of parsed items
            and folder_info contains metadata for status reporting.

        Raises
        ------
        ValueError
            If any path is invalid or uses unsupported storage.
        """
        data_items = []
        folder_info = []
        mount_names_seen = dict.fromkeys(existing_mount_names or [], None)

        for folder in folders:
            # Block Azure Blob Storage URLs
            if folder.startswith('az://'):
                raise ValueError(
                    "Azure Blob Storage paths (az://) are not supported for linking. "
                    "Azure environments do not support linking to Interactive Analysis sessions."
                )

            if folder.startswith('s3://'):
                if self.is_s3_file_path(folder):
                    parsed = self.parse_s3_file_path(folder)
                else:
                    parsed = self.parse_s3_path(folder)
                mount_name = parsed["dataItem"]["data"]["name"]

                if mount_name in mount_names_seen:
                    existing = mount_names_seen[mount_name]
                    conflict = f" and '{folder}'" if existing else f" (already mounted in session)"
                    raise ValueError(
                        f"Duplicate mount name '{mount_name}' detected{conflict}. "
                        f"Items with the same name cannot be mounted together. "
                        f"Please use items with unique names."
                    )
                mount_names_seen[mount_name] = folder

                data_items.append(parsed["dataItem"])
                folder_info.append({"path": folder, "type": "S3", "data": parsed["dataItem"]})
            else:
                parsed = self._parse_file_explorer_item(folder)
                mount_name = parsed["dataItem"]["name"]

                if mount_name in mount_names_seen:
                    existing = mount_names_seen[mount_name]
                    conflict = f" and '{folder}'" if existing else f" (already mounted in session)"
                    raise ValueError(
                        f"Duplicate mount name '{mount_name}' detected{conflict}. "
                        f"Items with the same name cannot be mounted together. "
                        f"Please use items with unique names."
                    )
                mount_names_seen[mount_name] = folder

                data_items.append(parsed["dataItem"])
                folder_info.append({"path": folder, "type": "File Explorer", "data": parsed["dataItem"]})

        return data_items, folder_info

    def _try_mount_v2(self, data_items: list, session_id: str) -> int:
        """Attempt to mount folders using API v2.

        Parameters
        ----------
        data_items : list
            List of parsed data items for the v2 payload.
        session_id : str
            The interactive session ID.

        Returns
        -------
        int or None
            Status code if successful, None if v2 unavailable (triggering fallback).

        Raises
        ------
        ValueError
            If v2 fails for reasons other than unavailability.
        """
        v2_payload = {"dataItems": data_items}

        try:
            status_code = self.mount_fuse_filesystem_v2(
                session_id=session_id,
                team_id=self.workspace_id,
                payload=v2_payload,
                verify=self.verify
            )
            return status_code
        except Exception as v2_error:
            # Check if error indicates v2 endpoint not available (404 only, but not session-not-found)
            error_str = str(v2_error)
            # Only fall back to v1 if it's a genuine endpoint-not-available 404
            # Session-not-found errors should propagate immediately
            if "Session not found" in error_str:
                raise  # Re-raise session-not-found errors immediately

            should_fallback = (
                "404" in error_str or "Not Found" in error_str or "not found" in error_str.lower()
            )

            if should_fallback:
                return None  # Trigger v1 fallback
            else:
                # v2 failed for reasons other than not available
                self._handle_mount_error(v2_error, "folder")

    def _fallback_mount_v1(self, folder_info: list, session_id: str) -> int:
        """Fall back to v1 API, mounting folders one at a time.

        Parameters
        ----------
        folder_info : list
            List of folder metadata dictionaries.
        session_id : str
            The interactive session ID.

        Returns
        -------
        int
            Status code from the last successful mount (typically 204).

        Raises
        ------
        ValueError
            If any item is a file (v1 only supports folders), or if any folder
            fails to mount. Note: Earlier folders may have successfully mounted
            before the failure.
        """
        for f in folder_info:
            item_type = f['data'].get('type', '')
            item_kind = f['data'].get('kind', '')
            if item_type == 'S3File' or item_kind == 'File':
                raise ValueError(
                    f"File linking requires API v2, which is not available for this session. "
                    f"Only folder linking is supported via the v1 API fallback."
                )

        status_code = None
        mounted_folders = []

        for folder_data in folder_info:
            try:
                status_code = self._mount_single_folder_v1(folder_data, session_id)
                mounted_folders.append(folder_data['path'])
            except ValueError as e:
                # If we've already mounted some folders, inform the user
                if mounted_folders:
                    error_msg = f"{str(e)}\n\nNote: The following folders were successfully mounted before this error: {', '.join(mounted_folders)}"
                    raise ValueError(error_msg)
                else:
                    raise
        return status_code

    def _mount_single_folder_v1(self, folder_data: dict, session_id: str) -> int:
        """Mount a single folder using API v1.

        Parameters
        ----------
        folder_data : dict
            Folder metadata including type, path, and data.
        session_id : str
            The interactive session ID.

        Returns
        -------
        int
            Status code (typically 204 on success).

        Raises
        ------
        ValueError
            If the mount request fails.
        """
        v1_payload = {"dataItem": folder_data["data"]}

        url = (
            f"{self.cloudos_url}/api/v1/"
            f"interactive-sessions/{session_id}/fuse-filesystem/mount"
            f"?teamId={self.workspace_id}"
        )
        headers = {
            "Content-type": "application/json",
            "apikey": self.apikey
        }

        try:
            r = retry_requests_post(url, headers=headers, json=v1_payload, verify=self.verify)

            if r.status_code >= 400:
                # Handle v1 errors using consolidated error handling
                if r.status_code == 403:
                    raise ValueError(f"Provided {folder_data['type']} item already exists with 'mounted' status")
                elif r.status_code == 401:
                    raise ValueError(f"Forbidden. Invalid API key or insufficient permissions.")
                elif r.status_code == 400:
                    try:
                        r_content = json.loads(r.content)
                        if r_content.get("message") == "Invalid Supported DataItem folderType. Supported values are S3Folder":
                            raise ValueError(f"Invalid Supported DataItem '{folder_data['type']}' folderType. Virtual folders cannot be linked.")
                        elif r_content.get("message") == "Request failed with status code 403":
                            raise ValueError(f"Interactive Analysis session is not active")
                        else:
                            raise ValueError(f"Cannot link item")
                    except json.JSONDecodeError:
                        raise ValueError(f"Bad request (400): Unable to parse error response")
                else:
                    raise ValueError(f"Failed to mount item: HTTP {r.status_code}")

            return r.status_code

        except ValueError:
            # Re-raise ValueError as-is
            raise
        except Exception as v1_error:
            raise ValueError(f"Failed to mount {folder_data['type']} item: {str(v1_error)}")

    def _verify_all_mounts(self, folder_info: list, session_id: str):
        """Verify mount completion status for all items (files and folders).

        Parameters
        ----------
        folder_info : list
            List of item metadata dictionaries.
        session_id : str
            The interactive session ID.
        """
        all_succeeded = True
        for folder_data in folder_info:
            if folder_data["type"] == "S3":
                item_data = folder_data['data']['data']
                key = item_data.get('s3Prefix') or item_data.get('s3ObjectKey', '')
                full_path = f"s3://{item_data['s3BucketName']}/{key}"
                mount_name = item_data['name']
                item_kind = "file" if folder_data['data'].get('type') == 'S3File' else "folder"
            else:
                folder_path = folder_data["path"]
                full_path = f"{self.project_name}/{folder_path.lstrip('/')}" if self.project_name else folder_path
                mount_name = folder_data['data']['name']
                item_kind = "file" if folder_data['data'].get('kind') == 'File' else "folder"

            source_label = f"{folder_data['type']} {item_kind}"

            try:
                final_status = self.wait_for_mount_completion(session_id, mount_name)

                if final_status["status"] == "mounted":
                    click.secho(f"Successfully mounted {source_label}: {full_path}", fg='green', bold=True)
                elif final_status["status"] == "failed":
                    raw_error = final_status.get("errorMessage", "Unknown error")
                    error_msg = self._translate_mount_error(raw_error)
                    click.secho(f"Failed to mount {source_label}: {full_path}", fg='red', bold=True)
                    click.secho(f"  Error: {error_msg}", fg='red')
                    all_succeeded = False
                else:
                    click.secho(f"Mount status: {final_status['status']} for {source_label}: {full_path}", fg='yellow', bold=True)
                    all_succeeded = False

            except ValueError as e:
                click.secho(f"Warning: Could not verify mount status - {str(e)}", fg='yellow', bold=True)
                click.secho(f"  The linking request was submitted, but verification failed.", fg='yellow')
                all_succeeded = False

        return all_succeeded

    def _translate_mount_error(self, error_msg: str) -> str:
        """Translate raw API error messages into user-friendly explanations."""
        msg_lower = error_msg.lower()
        if "prefix does not exist" in msg_lower or "key does not exist" in msg_lower:
            return (
                f"{error_msg} "
                "The path may not exist, or the workspace may not have permission to access it. "
                "Verify the path is correct and that the workspace's cloud account has read access to this bucket."
            )
        if "access denied" in msg_lower or "forbidden" in msg_lower:
            return (
                f"{error_msg} "
                "The workspace does not have permission to access this path. "
                "Verify that the workspace's cloud account has read access to this bucket."
            )
        return error_msg

    def _handle_mount_error(self, error: Exception, type_folder: str):
        """Handle and convert mount errors to user-friendly messages.

        Parameters
        ----------
        error : Exception
            The exception that occurred during mounting.
        type_folder : str
            The type of item being mounted ("S3" or "File Explorer").

        Raises
        ------
        ValueError
            Always raises with a user-friendly error message.
        """
        error_str = str(error)
        error_lower = error_str.lower()

        error_patterns = {
            ('403', 'forbidden'): {
                'check': lambda: "already exists" in error_lower or "mounted" in error_lower,
                'message_if_true': f"Provided {type_folder} item already exists with 'mounted' status",
                'message_if_false': f"Interactive Analysis session is not active or access denied"
            },
            ('401', 'unauthorized'): {
                'message': f"Forbidden. Invalid API key or insufficient permissions."
            },
            ('400', 'bad request'): {
                'check': lambda: "invalid supported dataitem foldertype" in error_lower,
                'message_if_true': f"Invalid Supported DataItem '{type_folder}' folderType. Virtual folders cannot be linked.",
                'message_if_false': f"Cannot link item: {error_str}"
            },
            ('404', 'not found'): {
                'message': f"Session not found or endpoint not available"
            }
        }

        for patterns, config in error_patterns.items():
            if any(pattern in error_lower or pattern in error_str for pattern in patterns):
                if 'check' in config:
                    message = config['message_if_true'] if config['check']() else config['message_if_false']
                else:
                    message = config['message']
                raise ValueError(message)

        raise ValueError(f"Failed to mount {type_folder} item: {error_str}")

    def parse_s3_path(self, s3_url):
        """
        Parses an S3 URL and extracts the bucket name, prefix, and base name.

        Parameters
        ----------
        s3_url : str
            The S3 URL to parse. Must start with "s3://".

        Returns
        -------
        dict: A dictionary containing the parsed S3 information structured as:
                "dataItem": {
                    "type": "S3Folder",
                    "data": {
                        "name": str,          # The base name (last segment of the prefix).
                        "s3BucketName": str,  # The name of the S3 bucket.
                        "s3Prefix": str       # The full prefix path in the bucket.

        Raises
        ------
        ValueError
            If the S3 URL does not start with "s3://".
            If the S3 URL does not include a key after the bucket.
        """
        if not s3_url.startswith("s3://"):
            raise ValueError("Invalid S3 URL. Link must start with 's3://'")

        parsed = urlparse(s3_url)
        bucket = parsed.netloc
        prefix = parsed.path.lstrip('/') # Remove leading slash

        if not prefix:
            raise ValueError("S3 URL must include a key after the bucket")

        parts = prefix.rstrip('/').split('/')
        base = parts[-1] # Last segment (file or folder)
        return {
            "dataItem": {
                "type": "S3Folder",
                "data": {
                    "name": base,
                    "s3BucketName": bucket,
                    "s3Prefix": prefix
                }
            }
        }

    def is_s3_file_path(self, s3_url: str) -> bool:
        """Return True if the S3 URL points to a file rather than a folder.

        A path is treated as a file when the last segment contains a dot (.) and the
        URL does not end with a trailing slash.

        Parameters
        ----------
        s3_url : str
            An S3 URL starting with 's3://'.

        Returns
        -------
        bool
        """
        if s3_url.endswith('/'):
            return False
        parsed = urlparse(s3_url)
        prefix = parsed.path.lstrip('/')
        last_part = prefix.rstrip('/').split('/')[-1] if prefix else ''
        return '.' in last_part

    def parse_s3_file_path(self, s3_url: str) -> dict:
        """Parse an S3 URL that points to a file and return an S3File data item.

        Parameters
        ----------
        s3_url : str
            The S3 URL to parse. Must start with 's3://'.

        Returns
        -------
        dict
            {"dataItem": {"type": "S3File", "data": {"name": str, "s3BucketName": str, "s3ObjectKey": str}}}

        Raises
        ------
        ValueError
            If the URL is invalid.
        """
        if not s3_url.startswith("s3://"):
            raise ValueError("Invalid S3 URL. Link must start with 's3://'")

        parsed = urlparse(s3_url)
        bucket = parsed.netloc
        key = parsed.path.lstrip('/')

        if not key:
            raise ValueError("S3 URL must include a key after the bucket")

        name = key.split('/')[-1]
        return {
            "dataItem": {
                "type": "S3File",
                "data": {
                    "name": name,
                    "s3BucketName": bucket,
                    "s3ObjectKey": key
                }
            }
        }

    def _parse_file_explorer_item(self, path: str) -> dict:
        """Auto-detect whether a File Explorer path is a file or folder and return the data item.

        Performs a single API lookup to determine item type and resolve the ID.

        Parameters
        ----------
        path : str
            The path within the project (e.g., 'Data/results' or 'Data/file.csv').

        Returns
        -------
        dict
            {"dataItem": {"kind": "File"|"Folder", "item": str, "name": str}}

        Raises
        ------
        ValueError
            If the item is not found or is a virtual folder.
        """
        stripped = path.strip("/")
        parts = stripped.split("/")
        item_name = parts[-1]
        parent_path = "/".join(parts[:-1]) if len(parts) > 1 else ""

        ds = generate_datasets_for_project(
            self.cloudos_url, self.apikey, self.workspace_id, self.project_name, self.verify
        )
        contents = ds.list_folder_content(parent_path)

        for item in contents.get("folders", []):
            if item.get("name") == item_name:
                if item.get("folderType") == "VirtualFolder":
                    raise ValueError(
                        f"Virtual folders cannot be linked. Please use a regular folder or S3 path instead."
                    )
                return {
                    "dataItem": {
                        "kind": "Folder",
                        "item": item.get("_id", ""),
                        "name": item_name
                    }
                }

        for item in contents.get("files", []):
            if item.get("name") == item_name:
                return {
                    "dataItem": {
                        "kind": "File",
                        "item": item.get("_id", ""),
                        "name": item_name
                    }
                }

        raise ValueError(
            f"Item '{item_name}' not found in path '{parent_path or '[root]'}' "
            f"in project '{self.project_name}'. "
            f"Try using 'cloudos datasets ls' to explore your data structure."
        )

    def get_fuse_filesystems_status(self, session_id: str) -> List[Dict]:
        """Get the status of fuse filesystems for an interactive session.

        Parameters
        ----------
        session_id : str
            The interactive session ID.

        Returns
        -------
        List[Dict]
            List of fuse filesystem objects with their status information.

        Raises
        ------
        ValueError
            If the API request fails or returns an error.
        """
        url = (
            f"{self.cloudos_url}/api/v1/"
            f"interactive-sessions/{session_id}/fuse-filesystems"
            f"?teamId={self.workspace_id}"
        )
        headers = {
            "Content-type": "application/json",
            "apikey": self.apikey
        }

        r = retry_requests_get(url, headers=headers, verify=self.verify)

        if r.status_code == 401:
            raise ValueError("Forbidden. Invalid API key or insufficient permissions.")
        elif r.status_code == 404:
            raise ValueError(
                f"Interactive session {session_id} not found. "
                "The session may not exist, or your API key may not have access to it. "
                "Verify the session ID and that your API key belongs to a workspace member with access to this session."
            )
        elif r.status_code != 200:
            raise ValueError(f"Failed to get fuse filesystem status: HTTP {r.status_code}")

        response_data = json.loads(r.content)
        return response_data.get("fuseFileSystems", [])

    def wait_for_mount_completion(self, session_id: str, mount_name: str,
                                timeout: int = 360, check_interval: int = 2) -> Dict:
        """Wait for a specific mount to complete and return its final status.

        Parameters
        ----------
        session_id : str
            The interactive session ID.
        mount_name : str
            The name of the mount to check.
        timeout : int, optional
            Maximum time to wait in seconds (default: 360).
        check_interval : int, optional
            Time between status checks in seconds (default: 2).

        Returns
        -------
        Dict
            The final status object of the mount.

        Raises
        ------
        ValueError
            If the mount is not found or timeout is reached.
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            filesystems = self.get_fuse_filesystems_status(session_id)

            # Find the mount by name
            target_mount = None
            for fs in filesystems:
                if fs.get("mountName") == mount_name:
                    target_mount = fs
                    break

            if target_mount and target_mount.get("status") in ["mounted", "failed"]:
                return target_mount
            # If mount not found or still in progress, continue waiting

            time.sleep(check_interval)

        raise ValueError(f"Timeout waiting for mount '{mount_name}' to complete after {timeout} seconds")

    def link_job_results(self, job_id: str, workspace_id: str, session_id: str, verify_ssl, verbose: bool = False):
        """
        Link job results to an interactive session.

        Parameters
        ----------
        job_id : str
            The job ID to link results from
        workspace_id : str
            The workspace ID
        session_id : str
            The interactive session ID
        verify_ssl : Union[bool, str]
            SSL verification setting
        verbose : bool
            Whether to print verbose output

        Returns
        -------
        None
            Prints status messages to console
        """
        try:
            if verbose:
                print('\tFetching job results...')

            results_path = self.get_job_results(job_id, workspace_id, verify_ssl)

            if results_path:
                print('\tLinking results directory...')
                if verbose:
                    print(f'\t\tResults: {results_path}')
                self.link_folder(results_path, session_id)
            else:
                click.secho('\tNo results found to link.', fg='yellow')

        except JoBNotCompletedException as e:
            click.secho(f'\tCannot link results: {str(e)}', fg='red')
        except Exception as e:
            error_msg = str(e)
            if "Results are not available" in error_msg or "deleted" in error_msg.lower() or "removed" in error_msg.lower():
                click.secho(f'\tCannot link results: {error_msg}', fg='red')
            else:
                click.secho(f'\tFailed to link results: {error_msg}', fg='red')

    def link_job_workdir(self, job_id: str, workspace_id: str, session_id: str, verify_ssl, verbose: bool = False):
        """
        Link job working directory to an interactive session.

        Parameters
        ----------
        job_id : str
            The job ID to link workdir from
        workspace_id : str
            The workspace ID
        session_id : str
            The interactive session ID
        verify_ssl : Union[bool, str]
            SSL verification setting
        verbose : bool
            Whether to print verbose output

        Returns
        -------
        None
            Prints status messages to console
        """
        try:
            if verbose:
                print('\tFetching job working directory...')

            workdir_path = self.get_job_workdir(job_id, workspace_id, verify_ssl)

            if workdir_path:
                print('\tLinking working directory...')
                if verbose:
                    print(f'\t\tWorkdir: {workdir_path}')
                self.link_folder(workdir_path.strip(), session_id)
            else:
                click.secho('\tNo working directory found to link.', fg='yellow')

        except Exception as e:
            error_msg = str(e)
            if "not yet available" in error_msg.lower() or "initializing" in error_msg.lower() or "not available" in error_msg.lower() or "deleted" in error_msg.lower() or "removed" in error_msg.lower():
                click.secho(f'\tCannot link workdir: {error_msg}', fg='red')
            else:
                click.secho(f'\tFailed to link workdir: {error_msg}', fg='red')

    def link_job_logs(self, job_id: str, workspace_id: str, session_id: str, verify_ssl, verbose: bool = False):
        """
        Link job logs to an interactive session.

        Parameters
        ----------
        job_id : str
            The job ID to link logs from
        workspace_id : str
            The workspace ID
        session_id : str
            The interactive session ID
        verify_ssl : Union[bool, str]
            SSL verification setting
        verbose : bool
            Whether to print verbose output

        Returns
        -------
        None
            Prints status messages to console
        """
        try:
            if verbose:
                print('\tFetching job logs...')

            logs_dict = self.get_job_logs(job_id, workspace_id, verify_ssl)

            if logs_dict:
                # Extract the parent logs directory from any log file path
                first_log_path = next(iter(logs_dict.values()))
                logs_dir = '/'.join(first_log_path.split('/')[:-1])

                print('\tLinking logs directory...')
                if verbose:
                    print(f'\t\tLogs directory: {logs_dir}')
                self.link_folder(logs_dir, session_id)
            else:
                click.secho('\tNo logs found to link.', fg='yellow')

        except Exception as e:
            error_msg = str(e)
            if "not yet available" in error_msg.lower() or "initializing" in error_msg.lower() or "not available" in error_msg.lower() or "deleted" in error_msg.lower() or "removed" in error_msg.lower():
                click.secho(f'\tCannot link logs: {error_msg}', fg='red')
            else:
                click.secho(f'\tFailed to link logs: {error_msg}', fg='red')

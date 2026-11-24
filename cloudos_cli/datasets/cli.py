"""CLI commands for Lifebit Platform datasets management."""

import rich_click as click
import csv
import os
import sys
from cloudos_cli.datasets import Datasets
from cloudos_cli.utils.errors import BadRequestException
from cloudos_cli.utils.resources import ssl_selector, format_bytes
from cloudos_cli.configure.configure import with_profile_config, CLOUDOS_URL
from cloudos_cli.logging.logger import update_command_context_from_click
from rich.console import Console
from rich.table import Table
from rich.style import Style
from cloudos_cli.utils.cli_helpers import pass_debug_to_subcommands


def _airlock_hint(exc):
    """Error text for a BadRequestException, noting Airlock as a likely cause of a 401/403."""
    msg = str(exc)
    rv = getattr(exc, "rv", None)
    status = getattr(rv, "status_code", None)
    if status not in (401, 403):
        return msg
    # Airlock denials come back as short plain text, which BadRequestException drops.
    body = (getattr(rv, "text", "") or "").strip()
    if body and len(body) <= 300 and not body.startswith(("{", "<")):
        msg = f"{msg} ({body})"
    if "airlock" in body.lower():
        return msg
    return f"{msg}. This may be caused by this workspace's Airlock data-governance policy."


def _require_data_path(path, arg_name, allow_root=False):
    """Return PATH without surrounding slashes, or raise unless it is inside 'Data'."""
    clean = path.strip("/")
    if clean.startswith("Data/") or (allow_root and clean == "Data"):
        return clean
    if clean.lower().startswith("data/"):
        hint = f"Did you mean 'Data/{clean[5:]}'?"
    elif clean and clean != "Data":
        hint = f"Did you mean 'Data/{clean}'?"
    else:
        hint = "E.g.: 'Data/my-folder'."
    raise ValueError(
        f"{arg_name} must start with 'Data/', where all user-uploaded data lives. {hint}"
    )


def _virtual_path(project_name, path):
    """Path of an item as shown in the web UI's File Explorer."""
    return f"Projects/{project_name}/{path.strip('/')}"


def _storage_path(item):
    """The s3:// or az:// location backing a File Explorer item, or None."""
    if item.get("fileType") == "S3File" or item.get("folderType") == "S3Folder":
        bucket = item.get("s3BucketName")
        key = item.get("s3ObjectKey") or item.get("s3Prefix")
        return f"s3://{bucket}/{key}" if bucket and key else None
    if item.get("fileType") == "AzureBlobFile" or item.get("folderType") == "AzureBlobFolder":
        account = item.get("blobStorageAccountName")
        container = item.get("blobContainerName")
        key = item.get("blobName") if item.get("fileType") == "AzureBlobFile" else item.get("blobPrefix")
        if account and container and key:
            return f"az://{account}.blob.core.windows.net/{container}/{key}"
    return None


@click.group(cls=pass_debug_to_subcommands())
@click.pass_context
def datasets(ctx):
    """Lifebit Platform datasets functionality."""
    update_command_context_from_click(ctx)
    if ctx.args and ctx.args[0] != 'ls':
        print(datasets.__doc__ + '\n')


@datasets.command(name="ls")
@click.argument("path", required=False, nargs=1)
@click.option('-k',
              '--apikey',
              help='Your Lifebit Platform API key.',
              required=True)
@click.option('-c',
              '--cloudos-url',
              help=(f'The Lifebit Platform url you are trying to access to. Default={CLOUDOS_URL}.'),
              default=CLOUDOS_URL,
              required=True)
@click.option('--workspace-id',
              help='The specific Lifebit Platform workspace id.',
              required=True)
@click.option('--disable-ssl-verification',
              help=('Disable SSL certificate verification. Please, remember that this option is ' +
                    'not generally recommended for security reasons.'),
              is_flag=True)
@click.option('--ssl-cert',
              help='Path to your SSL certificate file.')
@click.option('--project-name',
              help='The name of a Lifebit Platform project.',
              required=True)
@click.option('--profile', help='Profile to use from the config file', default=None)
@click.option('--details',
              help=('When selected, it prints the details of the listed files. ' +
                    'Details contains "Type", "Owner", "Size", "Last Updated", ' +
                    '"Virtual Name", "Storage Path".'),
              is_flag=True)
@click.option('--output-format',
              help=('The desired display for the output, either directly in standard output or saved as file. ' +
                    'Default=stdout.'),
              type=click.Choice(['stdout', 'csv'], case_sensitive=False),
              default='stdout')
@click.option('--output-basename',
              help=('Output file base name to save jobs details. ' +
                    'Default=datasets_ls'),
              default='datasets_ls',
              required=False)
@click.pass_context
@with_profile_config(required_params=['apikey', 'workspace_id', 'project_name'])
def list_files(ctx,
               apikey,
               cloudos_url,
               workspace_id,
               disable_ssl_verification,
               ssl_cert,
               project_name,
               profile,
               path,
               details,
               output_format,
               output_basename):
    """List contents of a path within a Lifebit Platform workspace dataset."""
    verify_ssl = ssl_selector(disable_ssl_verification, ssl_cert)

    datasets = Datasets(
        cloudos_url=cloudos_url,
        apikey=apikey,
        workspace_id=workspace_id,
        project_name=project_name,
        verify=verify_ssl,
        cromwell_token=None
    )

    try:
        result = datasets.list_folder_content(path)
        contents = result.get("contents") or result.get("datasets", [])

        if not contents:
            contents = result.get("files", []) + result.get("folders", [])

        # Process items to extract data
        processed_items = []
        for item in contents:
            is_folder = "folderType" in item or item.get("isDir", False)
            type_ = "folder" if is_folder else "file"

            # Enhanced type information
            if is_folder:
                folder_type = item.get("folderType")
                if folder_type == "VirtualFolder":
                    type_ = "virtual folder"
                elif folder_type == "S3Folder":
                    type_ = "s3 folder"
                elif folder_type == "AzureBlobFolder":
                    type_ = "azure folder"
                else:
                    type_ = "folder"
            else:
                # Check if file is managed by Lifebit (user uploaded)
                is_managed_by_lifebit = item.get("isManagedByLifebit", False)
                if is_managed_by_lifebit:
                    type_ = "file (user uploaded)"
                else:
                    type_ = "file (virtual copy)"

            user = item.get("user", {})
            if isinstance(user, dict):
                name = user.get("name", "").strip()
                surname = user.get("surname", "").strip()
            else:
                name = surname = ""
            if name and surname:
                owner = f"{name} {surname}"
            elif name:
                owner = name
            elif surname:
                owner = surname
            else:
                owner = "-"

            raw_size = item.get("sizeInBytes", item.get("size"))
            size = format_bytes(raw_size) if not is_folder and raw_size is not None else "-"

            updated = item.get("updatedAt") or item.get("lastModified", "-")
            filepath = item.get("name", "-")

            storage_path = _storage_path(item) or "-"

            processed_items.append({
                'type': type_,
                'owner': owner,
                'size': size,
                'raw_size': raw_size,
                'updated': updated,
                'name': filepath,
                'storage_path': storage_path,
                'is_folder': is_folder
            })

        # Output handling
        if output_format == 'csv':
            csv_filename = f'{output_basename}.csv'

            if details:
                # CSV with all details
                with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
                    fieldnames = ['Type', 'Owner', 'Size', 'Size (bytes)', 'Last Updated', 'Virtual Name', 'Storage Path']
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()

                    for item in processed_items:
                        writer.writerow({
                            'Type': item['type'],
                            'Owner': item['owner'],
                            'Size': item['size'],
                            'Size (bytes)': item['raw_size'] if item['raw_size'] is not None else '',
                            'Last Updated': item['updated'],
                            'Virtual Name': item['name'],
                            'Storage Path': item['storage_path']
                        })
            else:
                # CSV with just names
                with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(['Name', 'Storage Path'])
                    for item in processed_items:
                        writer.writerow([item['name'], item['storage_path']])

            click.secho(f'\nDatasets list saved to: {csv_filename}', fg='green', bold=True)

        else:  # stdout
            if details:
                console = Console(width=None)
                table = Table(show_header=True, header_style="bold white")
                table.add_column("Type", style="cyan", no_wrap=True)
                table.add_column("Owner", style="white")
                table.add_column("Size", style="magenta")
                table.add_column("Last Updated", style="green")
                table.add_column("Virtual Name", style="bold", overflow="fold")
                table.add_column("Storage Path", style="dim", no_wrap=False, overflow="fold", ratio=2)

                for item in processed_items:
                    style = Style(color="blue", underline=True) if item['is_folder'] else None
                    table.add_row(
                        item['type'],
                        item['owner'],
                        item['size'],
                        item['updated'],
                        item['name'],
                        item['storage_path'],
                        style=style
                    )

                console.print(table)

            else:
                console = Console()
                for item in processed_items:
                    if item['is_folder']:
                        console.print(f"[blue underline]{item['name']}[/]")
                    else:
                        console.print(item['name'])

    except Exception as e:
        raise ValueError(f"Failed to list files for project '{project_name}'. {str(e)}")


@datasets.command(name="mv")
@click.argument("source_path", required=True)
@click.argument("destination_path", required=True)
@click.option('-k', '--apikey', required=True, help='Your Lifebit Platform API key.')
@click.option('-c', '--cloudos-url', default=CLOUDOS_URL, required=True, help='The Lifebit Platform URL.')
@click.option('--workspace-id', required=True, help='The Lifebit Platform workspace ID.')
@click.option('--project-name', required=True, help='The source project name.')
@click.option('--destination-project-name', required=False,
              help='The destination project name. Defaults to the source project.')
@click.option('--disable-ssl-verification', is_flag=True, help='Disable SSL certificate verification.')
@click.option('--ssl-cert', help='Path to your SSL certificate file.')
@click.option('--profile', default=None, help='Profile to use from the config file.')
@click.pass_context
@with_profile_config(required_params=['apikey', 'workspace_id', 'project_name'])
def move_files(ctx, source_path, destination_path, apikey, cloudos_url, workspace_id,
               project_name, destination_project_name,
               disable_ssl_verification, ssl_cert, profile):
    """
    Move a file or folder from a source path to a destination path within or across Lifebit Platform projects.

    SOURCE_PATH [path]: the full path to the file or folder to move. It must be a 'Data' folder path.
     E.g.: 'Data/folderA/file.txt'\n
    DESTINATION_PATH [path]: the full path to the destination folder. It must be a 'Data' folder path.
     E.g.: 'Data/folderB'
    """
    # Validate destination constraint
    _require_data_path(destination_path, "DESTINATION_PATH", allow_root=True)
    _require_data_path(source_path, "SOURCE_PATH", allow_root=True)

    verify_ssl = ssl_selector(disable_ssl_verification, ssl_cert)

    destination_project_name = destination_project_name or project_name
    # Initialize Datasets clients
    source_client = Datasets(
        cloudos_url=cloudos_url,
        apikey=apikey,
        workspace_id=workspace_id,
        project_name=project_name,
        verify=verify_ssl,
        cromwell_token=None
    )

    dest_client = Datasets(
        cloudos_url=cloudos_url,
        apikey=apikey,
        workspace_id=workspace_id,
        project_name=destination_project_name,
        verify=verify_ssl,
        cromwell_token=None
    )
    print('Checking source path')
    # === Resolve Source Item ===
    source_parts = source_path.strip("/").split("/")
    source_parent_path = "/".join(source_parts[:-1]) if len(source_parts) > 1 else None
    source_item_name = source_parts[-1]

    try:
        source_contents = source_client.list_folder_content(source_parent_path)
    except Exception as e:
        raise ValueError(f"Could not resolve source path '{source_path}'. {str(e)}")

    found_source = None
    for collection in ["files", "folders"]:
        for item in source_contents.get(collection, []):
            if item.get("name") == source_item_name:
                found_source = item
                break
        if found_source:
            break
    if not found_source:
        raise ValueError(f"Item '{source_item_name}' not found in '{source_parent_path or '[project root]'}'")

    source_id = found_source["_id"]
    source_kind = "Folder" if "folderType" in found_source else "File"
    print("Checking destination path")
    # === Resolve Destination Folder ===
    dest_parts = destination_path.strip("/").split("/")
    dest_folder_name = dest_parts[-1]
    dest_parent_path = "/".join(dest_parts[:-1]) if len(dest_parts) > 1 else None

    try:
        dest_contents = dest_client.list_folder_content(dest_parent_path)
        match = next((f for f in dest_contents.get("folders", []) if f.get("name") == dest_folder_name), None)
        if not match:
            raise ValueError(f"Could not resolve destination folder '{destination_path}'")

        target_id = match["_id"]
        folder_type = match.get("folderType")
        # Normalize kind: top-level datasets are kind=Dataset, all other folders are kind=Folder
        if folder_type in ("VirtualFolder", "Folder"):
            target_kind = "Folder"
        elif folder_type == "S3Folder":
            raise ValueError(f"Unable to move item '{source_item_name}' to '{destination_path}'. "
                             "The destination is an S3 folder, and only virtual folders can be selected as valid move destinations.")
        elif isinstance(folder_type, bool) and folder_type:  # legacy dataset structure
            target_kind = "Dataset"
        else:
            raise ValueError(f"Unrecognized folderType '{folder_type}' for destination '{destination_path}'")

    except Exception as e:
        raise ValueError(f"Could not resolve destination path '{destination_path}'. {str(e)}")
    print(f"Moving {source_kind} '{source_item_name}' to '{destination_path}' "
          f"in project '{destination_project_name} ...")
    # === Perform Move ===
    try:
        response = source_client.move_files_and_folders(
            source_id=source_id,
            source_kind=source_kind,
            target_id=target_id,
            target_kind=target_kind
        )
        if response.ok:
            click.secho(f"{source_kind} '{source_item_name}' moved to '{destination_path}' " +
                        f"in project '{destination_project_name}'.", fg="green", bold=True)
        else:
            raise ValueError(f"Move failed. {response.status_code} - {response.text}")
    except Exception as e:
        raise ValueError(f"Move operation failed. {str(e)}")


@datasets.command(name="rename")
@click.argument("source_path", required=True)
@click.argument("new_name", required=True)
@click.option('-k', '--apikey', required=True, help='Your Lifebit Platform API key.')
@click.option('-c', '--cloudos-url', default=CLOUDOS_URL, required=True, help='The Lifebit Platform URL.')
@click.option('--workspace-id', required=True, help='The Lifebit Platform workspace ID.')
@click.option('--project-name', required=True, help='The project name.')
@click.option('--disable-ssl-verification', is_flag=True, help='Disable SSL certificate verification.')
@click.option('--ssl-cert', help='Path to your SSL certificate file.')
@click.option('--profile', default=None, help='Profile to use from the config file.')
@click.pass_context
@with_profile_config(required_params=['apikey', 'workspace_id', 'project_name'])
def renaming_item(ctx,
                  source_path,
                  new_name,
                  apikey,
                  cloudos_url,
                  workspace_id,
                  project_name,
                  disable_ssl_verification,
                  ssl_cert,
                  profile):
    """
    Rename a file or folder in a Lifebit Platform project.

    SOURCE_PATH [path]: the full path to the file or folder to rename. It must be a 'Data' folder path.
     E.g.: 'Data/folderA/old_name.txt'\n
    NEW_NAME [name]: the new name to assign to the file or folder. E.g.: 'new_name.txt'
    """
    _require_data_path(source_path, "SOURCE_PATH")

    verify_ssl = ssl_selector(disable_ssl_verification, ssl_cert)
    client = Datasets(
        cloudos_url=cloudos_url,
        apikey=apikey,
        workspace_id=workspace_id,
        project_name=project_name,
        verify=verify_ssl,
        cromwell_token=None
    )

    parts = source_path.strip("/").split("/")

    parent_path = "/".join(parts[:-1])
    target_name = parts[-1]

    try:
        contents = client.list_folder_content(parent_path)
    except Exception as e:
        raise ValueError(f"Could not list contents at '{parent_path or '[project root]'}'. {str(e)}")

    # Search for file/folder
    found_item = None
    for category in ["files", "folders"]:
        for item in contents.get(category, []):
            if item.get("name") == target_name:
                found_item = item
                break
        if found_item:
            break

    if not found_item:
        raise ValueError(f"Item '{target_name}' not found in '{parent_path or '[project root]'}'")

    item_id = found_item["_id"]
    kind = "Folder" if "folderType" in found_item else "File"

    print(f"Renaming {kind} '{target_name}' to '{new_name}'...")
    try:
        response = client.rename_item(item_id=item_id, new_name=new_name, kind=kind)
        if response.ok:
            click.secho(
                f"{kind} '{target_name}' renamed to '{new_name}' in folder '{parent_path}'.",
                fg="green",
                bold=True
            )
        else:
            raise ValueError(f"Rename failed. {response.status_code} - {response.text}")
    except Exception as e:
        raise ValueError(f"Rename operation failed. {str(e)}")


@datasets.command(name="cp")
@click.argument("source_path", required=True)
@click.argument("destination_path", required=True)
@click.option('-k', '--apikey', required=True, help='Your Lifebit Platform API key.')
@click.option('-c', '--cloudos-url', default=CLOUDOS_URL, required=True, help='The Lifebit Platform URL.')
@click.option('--workspace-id', required=True, help='The Lifebit Platform workspace ID.')
@click.option('--project-name', required=True, help='The source project name.')
@click.option('--destination-project-name', required=False, help='The destination project name. Defaults to the source project.')
@click.option('--disable-ssl-verification', is_flag=True, help='Disable SSL certificate verification.')
@click.option('--ssl-cert', help='Path to your SSL certificate file.')
@click.option('--profile', default=None, help='Profile to use from the config file.')
@click.pass_context
@with_profile_config(required_params=['apikey', 'workspace_id', 'project_name'])
def copy_item_cli(ctx,
                  source_path,
                  destination_path,
                  apikey,
                  cloudos_url,
                  workspace_id,
                  project_name,
                  destination_project_name,
                  disable_ssl_verification,
                  ssl_cert,
                  profile):
    """
    Copy a file or folder (S3 or virtual) from SOURCE_PATH to DESTINATION_PATH.

    SOURCE_PATH [path]: the full path to the file or folder to copy.
     E.g.: AnalysesResults/my_analysis/results/my_plot.png\n
    DESTINATION_PATH [path]: the full path to the destination folder. It must be a 'Data' folder path.
     E.g.: Data/plots
    """
    destination_project_name = destination_project_name or project_name
    verify_ssl = ssl_selector(disable_ssl_verification, ssl_cert)
    # Initialize clients
    source_client = Datasets(
        cloudos_url=cloudos_url,
        apikey=apikey,
        workspace_id=workspace_id,
        project_name=project_name,
        verify=verify_ssl,
        cromwell_token=None
    )
    dest_client = Datasets(
        cloudos_url=cloudos_url,
        apikey=apikey,
        workspace_id=workspace_id,
        project_name=destination_project_name,
        verify=verify_ssl,
        cromwell_token=None
    )
    # Validate paths
    dest_parts = _require_data_path(destination_path, "DESTINATION_PATH", allow_root=True).split("/")
    # Parse source and destination
    source_parts = source_path.strip("/").split("/")
    source_parent = "/".join(source_parts[:-1]) if len(source_parts) > 1 else ""
    source_name = source_parts[-1]
    dest_folder_name = dest_parts[-1]
    dest_parent = "/".join(dest_parts[:-1]) if len(dest_parts) > 1 else ""
    try:
        source_content = source_client.list_folder_content(source_parent)
        dest_content = dest_client.list_folder_content(dest_parent)
    except Exception as e:
        raise ValueError(f"Could not access paths. {str(e)}")
    # Find the source item
    source_item = None
    for item in source_content.get('files', []) + source_content.get('folders', []):
        if item.get("name") == source_name:
            source_item = item
            break
    if not source_item:
        raise ValueError(f"Item '{source_name}' not found in '{source_parent or '[project root]'}'")
    # Find the destination folder
    destination_folder = None
    for folder in dest_content.get("folders", []):
        if folder.get("name") == dest_folder_name:
            destination_folder = folder
            break
    if not destination_folder:
        raise ValueError(f"Destination folder '{destination_path}' not found.")
    try:
        # Determine item type
        if "fileType" in source_item:
            item_type = "file"
        elif source_item.get("folderType") == "VirtualFolder":
            item_type = "virtual_folder"
        elif "s3BucketName" in source_item and source_item.get("folderType") == "S3Folder":
            item_type = "s3_folder"
        else:
            raise ValueError("Could not determine item type.")
        print(f"Copying {item_type.replace('_', ' ')} '{source_name}' to '{destination_path}'...")
        if destination_folder.get("folderType") is True and destination_folder.get("kind") in ("Data", "Cohorts", "AnalysesResults"):
            destination_kind = "Dataset"
        elif destination_folder.get("folderType") == "S3Folder":
            raise ValueError(f"Unable to copy item '{source_name}' to '{destination_path}'. The destination is an S3 folder, and only virtual folders can be selected as valid copy destinations.")
        else:
            destination_kind = "Folder"
        response = source_client.copy_item(
            item=source_item,
            destination_id=destination_folder["_id"],
            destination_kind=destination_kind
        )
        if response.ok:
            click.secho("Item copied successfully.", fg="green", bold=True)
        else:
            raise ValueError(f"Copy failed. {response.status_code} - {response.text}")
    except Exception as e:
        raise ValueError(f"Copy operation failed. {str(e)}")


@datasets.command(name="upload")
@click.argument("local_path", required=True, type=click.Path(exists=True, dir_okay=False, readable=True))
@click.argument("destination_path", required=True)
@click.option('-k', '--apikey', required=True, help='Your Lifebit Platform API key.')
@click.option('-c', '--cloudos-url', default=CLOUDOS_URL, required=True, help='The Lifebit Platform URL.')
@click.option('--workspace-id', required=True, help='The Lifebit Platform workspace ID.')
@click.option('--project-name', required=True, help='The project name.')
@click.option('--disable-ssl-verification', is_flag=True, help='Disable SSL certificate verification.')
@click.option('--ssl-cert', help='Path to your SSL certificate file.')
@click.option('--profile', default=None, help='Profile to use from the config file.')
@click.option('--show-storage-path', is_flag=True,
              help='Also print the s3:// location the file was stored at.')
@click.pass_context
@with_profile_config(required_params=['apikey', 'workspace_id', 'project_name'])
def upload_file_cli(ctx,
                    local_path,
                    destination_path,
                    apikey,
                    cloudos_url,
                    workspace_id,
                    project_name,
                    disable_ssl_verification,
                    ssl_cert,
                    profile,
                    show_storage_path):
    """
    Upload a local file to a Lifebit Platform project's File Explorer.

    LOCAL_PATH [path]: the path, on your local machine, to the file to upload.\n
    DESTINATION_PATH [path]: the File Explorer folder to upload into. It must be a 'Data'
     folder path. E.g.: 'Data/uploads'

    > [!NOTE]
    > Only AWS workspaces are supported. The command stops before uploading if the
    > workspace's Airlock policy blocks uploads from your computer.
    """
    destination_path = _require_data_path(destination_path, "DESTINATION_PATH", allow_root=True)
    client = Datasets(
        cloudos_url=cloudos_url,
        apikey=apikey,
        workspace_id=workspace_id,
        project_name=project_name,
        verify=ssl_selector(disable_ssl_verification, ssl_cert),
        cromwell_token=None
    )

    airlock_message = client.check_airlock_restriction('upload')
    if airlock_message:
        raise click.ClickException(airlock_message)
    try:
        cloud_config = client.get_cloud_aws_config()
    except BadRequestException as e:
        if e.rv.status_code == 404:
            raise click.ClickException("Uploading from your computer is only supported in AWS workspaces, "
                                       "and this one doesn't appear to be AWS-based (e.g. it uses Azure).")
        raise click.ClickException(f"Could not read this workspace's AWS configuration. {_airlock_hint(e)}")
    except Exception as e:
        raise click.ClickException(f"Could not read this workspace's AWS configuration. {e}")

    dest_parent, _, dest_folder_name = destination_path.rpartition("/")
    filename = os.path.basename(local_path)
    try:
        destination_folder = next((f for f in client.list_folder_content(dest_parent).get("folders", [])
                                   if f.get("name") == dest_folder_name), None)
        if not destination_folder:
            raise ValueError(f"Destination folder '{destination_path}' not found.")
        if destination_folder.get("folderType") in ("S3Folder", "AzureBlobFolder"):
            raise ValueError(f"Unable to upload to '{destination_path}': only virtual folders and "
                             "datasets can be upload destinations, not cloud storage folders.")
        # An existing file would share the S3 key, so its content would be replaced even
        # though the platform then rejects the duplicate name.
        existing = client.list_folder_content(destination_path)
    except BadRequestException as e:
        raise click.ClickException(f"Could not resolve destination path '{destination_path}'. {_airlock_hint(e)}")
    if any(i.get("name") == filename for i in existing.get("files", []) + existing.get("folders", [])):
        raise click.ClickException(
            f"'{filename}' already exists in '{destination_path}'. Remove or rename it first "
            "(e.g. 'cloudos datasets rm' or 'cloudos datasets rename'), or rename the local file."
        )
    destination_kind = "Dataset" if destination_folder.get("folderType") is True else "Folder"

    print(f"Uploading '{local_path}' to '{destination_path}/{filename}'...")
    try:
        client.upload_local_file(local_path=local_path, destination_folder_id=destination_folder["_id"],
                                 destination_parent_kind=destination_kind, cloud_config=cloud_config,
                                 destination_name=filename)
    except BadRequestException as e:
        raise click.ClickException(f"Upload to '{destination_path}' was rejected. {_airlock_hint(e)}")
    except Exception as e:
        raise ValueError(f"Upload operation failed. {e}")
    click.secho(f"File '{filename}' uploaded.", fg="green", bold=True)
    print(f"Virtual path: {_virtual_path(project_name, f'{destination_path}/{filename}')}")
    if show_storage_path:
        key = client.upload_object_key(cloud_config, destination_kind, destination_folder["_id"], filename)
        print(f"Storage path: s3://{cloud_config['lifebitBucketName']}/{key}")


@datasets.command(name="download")
@click.argument("source_path", required=True)
@click.argument("local_path", required=True, type=click.Path())
@click.option('-k', '--apikey', required=True, help='Your Lifebit Platform API key.')
@click.option('-c', '--cloudos-url', default=CLOUDOS_URL, required=True, help='The Lifebit Platform URL.')
@click.option('--workspace-id', required=True, help='The Lifebit Platform workspace ID.')
@click.option('--project-name', required=True, help='The project name.')
@click.option('--disable-ssl-verification', is_flag=True, help='Disable SSL certificate verification.')
@click.option('--ssl-cert', help='Path to your SSL certificate file.')
@click.option('--profile', default=None, help='Profile to use from the config file.')
@click.option('--show-storage-path', is_flag=True,
              help='Also print the s3:// or az:// location the file was read from.')
@click.option('-f', '--overwrite', is_flag=True,
              help='Overwrite LOCAL_PATH if it already exists as a file.')
@click.pass_context
@with_profile_config(required_params=['apikey', 'workspace_id', 'project_name'])
def download_file_cli(ctx,
                      source_path,
                      local_path,
                      apikey,
                      cloudos_url,
                      workspace_id,
                      project_name,
                      disable_ssl_verification,
                      ssl_cert,
                      profile,
                      show_storage_path,
                      overwrite):
    """
    Download a file from a Lifebit Platform project's File Explorer to local disk.

    SOURCE_PATH [path]: the File Explorer path of the file. E.g.: 'Data/results/my_plot.png'\n
    LOCAL_PATH [path]: where to save it. If LOCAL_PATH is an existing folder, the file keeps
     its name inside it. The folder is never created automatically.

    > [!NOTE]
    > An existing local file is only replaced with --overwrite/-f. The command stops before
    > downloading if Airlock is enabled for the workspace.
    """
    client = Datasets(
        cloudos_url=cloudos_url,
        apikey=apikey,
        workspace_id=workspace_id,
        project_name=project_name,
        verify=ssl_selector(disable_ssl_verification, ssl_cert),
        cromwell_token=None
    )

    airlock_message = client.check_airlock_restriction('download')
    if airlock_message:
        raise click.ClickException(airlock_message)

    source_parent, _, source_name = source_path.strip("/").rpartition("/")
    try:
        source_content = client.list_folder_content(source_parent)
    except BadRequestException as e:
        raise click.ClickException(f"Could not resolve source path '{source_path}'. {_airlock_hint(e)}")
    source_item = next((f for f in source_content.get("files", []) if f.get("name") == source_name), None)
    if not source_item:
        if any(f.get("name") == source_name for f in source_content.get("folders", [])):
            raise ValueError(f"'{source_path}' is a folder. 'cloudos datasets download' only downloads single files.")
        raise ValueError(f"File '{source_name}' not found in '{source_parent or '[project root]'}'")

    if local_path.endswith(tuple(s for s in (os.sep, os.altsep) if s)) and not os.path.isdir(local_path):
        raise ValueError(f"Local folder '{local_path}' does not exist. Create it first "
                         f"(e.g. 'mkdir -p {local_path}') or pass a full file path instead.")
    if os.path.isdir(local_path):
        # The name comes from the platform, so it must not be able to point outside local_path.
        if (os.path.basename(source_name) != source_name or source_name in (".", "..")
                or (os.name == "nt" and ":" in source_name)):
            raise ValueError(f"The remote file name '{source_name}' is not a safe local file name. "
                             "Pass a full LOCAL_PATH including the file name instead.")
        dest_file = os.path.join(local_path, source_name)
    else:
        dest_file = local_path
        parent_dir = os.path.dirname(os.path.abspath(dest_file))
        if not os.path.isdir(parent_dir):
            raise ValueError(f"Cannot save to '{dest_file}': folder '{parent_dir}' does not exist. "
                             "Create it first, e.g. with 'mkdir -p'.")
    if os.path.isdir(dest_file):
        raise ValueError(f"'{dest_file}' is a directory.")
    if os.path.lexists(dest_file) and not overwrite:
        raise ValueError(f"'{dest_file}' already exists. Use --overwrite/-f to overwrite it.")

    print(f"Downloading '{source_path}' to '{dest_file}'...")
    try:
        client.download_to_file(client.get_signed_download_url(source_item), dest_file, overwrite=overwrite,
                                expected_size=source_item.get("sizeInBytes"), progress=True)
    except BadRequestException as e:
        raise click.ClickException(f"Download of '{source_path}' was rejected. {_airlock_hint(e)}")
    except OSError as e:
        # Report the user's path, not the internal temporary file name.
        raise ValueError(f"Could not save to '{dest_file}': {e.strerror or e}")
    except Exception as e:
        raise ValueError(f"Download operation failed. {e}")
    click.secho(f"File '{source_name}' downloaded to '{dest_file}'.", fg="green", bold=True)
    if show_storage_path:
        print(f"Storage path: {_storage_path(source_item) or '-'}")


@datasets.command(name="mkdir")
@click.argument("new_folder_path", required=True)
@click.option('-k', '--apikey', required=True, help='Your Lifebit Platform API key.')
@click.option('-c', '--cloudos-url', default=CLOUDOS_URL, required=True, help='The Lifebit Platform URL.')
@click.option('--workspace-id', required=True, help='The Lifebit Platform workspace ID.')
@click.option('--project-name', required=True, help='The project name.')
@click.option('--disable-ssl-verification', is_flag=True, help='Disable SSL certificate verification.')
@click.option('--ssl-cert', help='Path to your SSL certificate file.')
@click.option('--profile', default=None, help='Profile to use from the config file.')
@click.pass_context
@with_profile_config(required_params=['apikey', 'workspace_id', 'project_name'])
def mkdir_item(ctx,
               new_folder_path,
               apikey,
               cloudos_url,
               workspace_id,
               project_name,
               disable_ssl_verification,
               ssl_cert,
               profile):
    """
    Create a virtual folder in a Lifebit Platform project.

    NEW_FOLDER_PATH [path]: Full path to the new folder including its name. Must start with 'Data'.
    """
    new_folder_path = _require_data_path(new_folder_path, "NEW_FOLDER_PATH")

    path_parts = new_folder_path.split("/")
    if len(path_parts) < 2:
        raise ValueError("NEW_FOLDER_PATH must include at least a parent folder and the new folder name.")

    parent_path = "/".join(path_parts[:-1])
    folder_name = path_parts[-1]

    verify_ssl = ssl_selector(disable_ssl_verification, ssl_cert)

    client = Datasets(
        cloudos_url=cloudos_url,
        apikey=apikey,
        workspace_id=workspace_id,
        project_name=project_name,
        verify=verify_ssl,
        cromwell_token=None
    )

    # Split parent path to get its parent + name
    parent_parts = parent_path.split("/")
    parent_name = parent_parts[-1]
    parent_of_parent_path = "/".join(parent_parts[:-1])

    # List the parent of the parent
    try:
        contents = client.list_folder_content(parent_of_parent_path)
    except Exception as e:
        raise ValueError(f"Could not list contents at '{parent_of_parent_path}'. {str(e)}")

    # Find the parent folder in the contents
    folder_info = next(
        (f for f in contents.get("folders", []) if f.get("name") == parent_name),
        None
    )

    if not folder_info:
        raise ValueError(f"Could not find folder '{parent_name}' in '{parent_of_parent_path}'.")

    parent_id = folder_info.get("_id")
    folder_type = folder_info.get("folderType")

    if folder_type is True:
        parent_kind = "Dataset"
    elif isinstance(folder_type, str):
        parent_kind = "Folder"
    else:
        raise ValueError(f"Unrecognized folderType for '{parent_path}'.")

    # Create the folder
    print(f"Creating folder '{folder_name}' under '{parent_path}' ({parent_kind})...")
    try:
        response = client.create_virtual_folder(name=folder_name, parent_id=parent_id, parent_kind=parent_kind)
        if response.ok:
            click.secho(f"Folder '{folder_name}' created.", fg="green", bold=True)
            print(f"Virtual path: {_virtual_path(project_name, new_folder_path)}")
        else:
            raise ValueError(f"Folder creation failed. {response.status_code} - {response.text}")
    except Exception as e:
        raise ValueError(f"Folder creation failed. {str(e)}")


@datasets.command(name="rm")
@click.argument("target_path", required=True)
@click.option('-k', '--apikey', required=True, help='Your Lifebit Platform API key.')
@click.option('-c', '--cloudos-url', default=CLOUDOS_URL, required=True, help='The Lifebit Platform URL.')
@click.option('--workspace-id', required=True, help='The Lifebit Platform workspace ID.')
@click.option('--project-name', required=True, help='The project name.')
@click.option('--disable-ssl-verification', is_flag=True, help='Disable SSL certificate verification.')
@click.option('--ssl-cert', help='Path to your SSL certificate file.')
@click.option('--profile', default=None, help='Profile to use from the config file.')
@click.option('--force', is_flag=True, help='Force delete files. Required when deleting user uploaded files. This may also delete the file from the cloud provider storage.')
@click.pass_context
@with_profile_config(required_params=['apikey', 'workspace_id', 'project_name'])
def rm_item(ctx,
            target_path,
            apikey,
            cloudos_url,
            workspace_id,
            project_name,
            disable_ssl_verification,
            ssl_cert,
            profile,
            force):
    """
    Delete a file or folder in a Lifebit Platform project.

    TARGET_PATH [path]: the full path to the file or folder to delete. Must start with 'Data'. \n
    E.g.: 'Data/folderA/file.txt' or 'Data/my_analysis/results/folderB'
    """
    _require_data_path(target_path, "TARGET_PATH")

    verify_ssl = ssl_selector(disable_ssl_verification, ssl_cert)

    client = Datasets(
        cloudos_url=cloudos_url,
        apikey=apikey,
        workspace_id=workspace_id,
        project_name=project_name,
        verify=verify_ssl,
        cromwell_token=None
    )

    parts = target_path.strip("/").split("/")
    parent_path = "/".join(parts[:-1])
    item_name = parts[-1]

    try:
        contents = client.list_folder_content(parent_path)
    except Exception as e:
        raise ValueError(f"Could not list contents at '{parent_path or '[project root]'}'. {str(e)}")

    found_item = None
    for item in contents.get('files', []) + contents.get('folders', []):
        if item.get("name") == item_name:
            found_item = item
            break

    if not found_item:
        raise ValueError(f"Item '{item_name}' not found in '{parent_path or '[project root]'}'")

    item_id = found_item.get("_id", '')
    kind = "Folder" if "folderType" in found_item else "File"
    if item_id == '':
        raise ValueError(f"Item '{item_name}' could not be removed as the parent folder is an s3 folder and their content cannot be modified.")
    # Check if the item is managed by Lifebit
    is_managed_by_lifebit = found_item.get("isManagedByLifebit", False)
    if is_managed_by_lifebit and not force:
        raise ValueError("By removing this file, it will be permanently deleted. If you want to go forward, please use the --force flag.")
    print(f"Removing {kind} '{item_name}' from '{parent_path or '[root]'}'...")
    try:
        response = client.delete_item(item_id=item_id, kind=kind)
        if response.ok:
            if is_managed_by_lifebit:
                click.secho(
                    f"{kind} '{item_name}' was permanently deleted from '{parent_path or '[root]'}'.",
                    fg="green", bold=True
                )
            else:
                click.secho(
                    f"{kind} '{item_name}' was removed from '{parent_path or '[root]'}'.",
                    fg="green", bold=True
                )
                click.secho("This item will still be available on your Cloud Provider.", fg="yellow")
        else:
            raise ValueError(f"Removal failed. {response.status_code} - {response.text}")
    except Exception as e:
        raise ValueError(f"Remove operation failed. {str(e)}")


@datasets.command(
    name="link",
    hidden=True,
    add_help_option=False,
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
@click.pass_context
def link_deprecated(ctx):
    raise click.ClickException(
        "'cloudos datasets link' has been removed.\n\n"
        "Use one of the supported alternatives:\n"
        "  cloudos interactive-session link <PATH> --session-id <SESSION_ID>\n"
        "  cloudos interactive-session create --link <PATH> [...]\n\n"
        "Add --profile <my_profile> to either command to use a saved profile."
    )

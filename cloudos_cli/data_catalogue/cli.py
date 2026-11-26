"""CLI commands for the Lifebit Platform data catalogue (Object Data Connect)."""

import csv
import json

import rich_click as click
from rich.console import Console
from rich.table import Table

from cloudos_cli.configure.configure import CLOUDOS_URL, with_profile_config
from cloudos_cli.data_catalogue.data_catalogue import (
    CLOUD_TYPES,
    DataCatalogue,
    build_item_metadata,
    metadata_from_meta_file,
    validate_item_metadata
)
from cloudos_cli.utils.cli_helpers import pass_debug_to_subcommands
from cloudos_cli.utils.resources import ssl_selector


BACKGROUND_NOTE = ('Access is applied in the background, so it can take a few moments '
                   'before the dataset is available in the workspaces.')


@click.group(cls=pass_debug_to_subcommands())
def data_catalogue():
    """Lifebit Platform data catalogue (Object Data Connect) functionality.

    Requires the API key of an organisation admin.
    """
    print(data_catalogue.__doc__.splitlines()[0] + '\n')


def connection_options(func):
    """Add the options shared by all data catalogue commands."""
    options = [
        click.option('-k', '--apikey', help='Your Lifebit Platform API key. It must belong to an organisation admin.',
                     required=True),
        click.option('-c', '--cloudos-url',
                     help=f'The Lifebit Platform url you are trying to access to. Default={CLOUDOS_URL}.',
                     default=CLOUDOS_URL, required=True),
        click.option('--organisation-id',
                     help=('The organisation that owns the data catalogue. If not given, it is taken from '
                           'the organisation of --workspace-id.')),
        click.option('--workspace-id',
                     help=('Any workspace of your organisation, only used to find the organisation when '
                           '--organisation-id is not given. Datasets are not shared with it.')),
        click.option('--disable-ssl-verification', is_flag=True,
                     help=('Disable SSL certificate verification. Please, remember that this option is '
                           'not generally recommended for security reasons.')),
        click.option('--ssl-cert', help='Path to your SSL certificate file.'),
        click.option('--profile', help='Profile to use from the config file', default=None),
    ]
    for option in reversed(options):
        func = option(func)
    return func


def _make_client(apikey, cloudos_url, organisation_id, workspace_id, disable_ssl_verification, ssl_cert):
    """Create a DataCatalogue client, finding the organisation from the workspace if needed."""
    client = DataCatalogue(
        cloudos_url=cloudos_url,
        apikey=apikey,
        cromwell_token=None,
        organisation_id=organisation_id,
        verify=ssl_selector(disable_ssl_verification, ssl_cert)
    )
    if not organisation_id:
        if not workspace_id:
            raise click.UsageError('Please provide --organisation-id, or --workspace-id (or a profile with a '
                                   'workspace ID) so the organisation can be found.')
        client.resolve_organisation_id(workspace_id)
    return client


def _shared_with(item):
    """Workspace names (or IDs if names are not available) an item is shared with."""
    workspaces = item.get('sharedWorkspaces')
    if workspaces:
        return [w.get('name') or w.get('id') for w in workspaces]
    return list(item.get('sharedWithTeamIds') or [])


def _items_table(items, title=None):
    table = Table(title=title)
    for column in ('Name', 'ID', 'Status', 'Cloud', 'Locations', 'Shared with'):
        table.add_column(column, overflow='fold')
    for item in items:
        status = item.get('status', '-')
        if item.get('statusReason'):
            status = f"{status} ({item['statusReason']})"
        table.add_row(
            item.get('name', '-'),
            item.get('_id', '-'),
            status,
            item.get('cloudProvider', '-'),
            '\n'.join(item.get('locations') or []) or '-',
            '\n'.join(_shared_with(item)) or '-'
        )
    return table


def with_items_options(func):
    """Options describing a single dataset, used by the import command."""
    options = [
        click.option('--name', help='The dataset name. It must be unique in the organisation.'),
        click.option('--description', help='The dataset description.'),
        click.option('--location', 'locations', multiple=True,
                     help=('A location URI of the dataset, e.g. s3://my-bucket/path/ or '
                           'az://account.blob.core.windows.net/container/path. Can be used several times.')),
        click.option('--cloud-provider', type=click.Choice(list(CLOUD_TYPES)), default='AWS', show_default=True,
                     help='The cloud provider hosting the dataset.'),
        click.option('--author', help='Optional. The dataset author.'),
        click.option('--release', help='Optional. The dataset release.'),
        click.option('--dataset-version', help='Optional. The dataset version.'),
        click.option('--trait', 'traits', multiple=True,
                     help='Optional. A disease or trait (ICD-10 code). Can be used several times.'),
        click.option('--ancestry', 'ancestries', multiple=True,
                     help='Optional. An ancestry of the participants. Can be used several times.'),
        click.option('--number-of-participants', type=click.IntRange(min=1),
                     help='Optional. The number of participants.'),
        click.option('--study-type', help='Optional. The study type, e.g. cohort.'),
        click.option('--from-file', 'from_files', multiple=True, type=click.Path(exists=True, dir_okay=False),
                     help=('Import datasets from Lifebit metadata (.meta) or JSON files instead of the options '
                           'above. Each file holds one dataset, or a list of datasets. Can be used several times.')),
    ]
    for option in reversed(options):
        func = option(func)
    return func


def _load_meta_files(paths):
    metadata = []
    for path in paths:
        try:
            with open(path) as f:
                content = json.load(f)
        except json.JSONDecodeError as e:
            raise click.BadParameter(f'{path} is not a valid JSON file: {e}', param_hint="'--from-file'")
        entries = content if isinstance(content, list) else [content]
        try:
            metadata.extend(metadata_from_meta_file(entry) for entry in entries)
        except ValueError as e:
            raise click.BadParameter(f'{path}: {e}', param_hint="'--from-file'")
    return metadata


@data_catalogue.command(name='import')
@connection_options
@with_items_options
@click.option('--share-with-workspace', 'share_with_workspaces', multiple=True,
              help='A workspace name or ID to share the dataset with. Can be used several times.')
@click.option('--share-with-all', is_flag=True,
              help='Share the dataset with all active workspaces of the same cloud provider.')
@click.pass_context
@with_profile_config(required_params=['apikey'])
def import_datasets(ctx, apikey, cloudos_url, organisation_id, workspace_id, disable_ssl_verification, ssl_cert,
                    profile, name, description, locations, cloud_provider, author, release, dataset_version,
                    traits, ancestries, number_of_participants, study_type, from_files, share_with_workspaces,
                    share_with_all):
    """Import datasets (location URIs) into the data catalogue and optionally share them with workspaces."""
    single_options = [name, description, locations, author, release, dataset_version, traits, ancestries,
                      number_of_participants, study_type]
    if from_files:
        if any(single_options):
            raise click.UsageError('--from-file cannot be combined with the options describing a single dataset '
                                   '(--name, --description, --location, ...).')
        all_metadata = _load_meta_files(from_files)
    else:
        if not name or not description or not locations:
            raise click.UsageError('Please provide --name, --description and at least one --location, '
                                   'or use --from-file.')
        all_metadata = [build_item_metadata(
            name=name, description=description, locations=locations, cloud_provider=cloud_provider,
            author=author, release=release, version=dataset_version, traits=traits, ancestry=ancestries,
            number_of_participants=number_of_participants, study_type=study_type
        )]
    if share_with_all and share_with_workspaces:
        raise click.UsageError('--share-with-all and --share-with-workspace cannot be used together.')

    for metadata in all_metadata:
        validate_item_metadata(metadata)
    names = [m['name'] for m in all_metadata]
    duplicated = sorted({n for n in names if names.count(n) > 1})
    if duplicated:
        raise ValueError(f"Dataset names must be unique, found repeated: {', '.join(duplicated)}.")
    cloud_providers = {m['cloudProvider'] for m in all_metadata}
    if len(cloud_providers) > 1:
        raise ValueError('All datasets imported together must have the same cloud provider.')

    client = _make_client(apikey, cloudos_url, organisation_id, workspace_id, disable_ssl_verification, ssl_cert)
    console = Console()
    workspaces = client.resolve_workspaces(share_with_workspaces, cloud_providers.pop(), share_with_all)
    if share_with_all and not workspaces:
        raise ValueError('There are no active workspaces of this cloud provider in the organisation.')
    team_ids = [w['_id'] for w in workspaces]

    created = client.create_items([{'metadata': m, 'sharedTeamIds': team_ids} for m in all_metadata])
    for item in created:
        item.setdefault('sharedWorkspaces', [{'id': w['_id'], 'name': w['name']} for w in workspaces])
    console.print(_items_table(created, title='Imported datasets'))
    if team_ids:
        console.print(f'[yellow]{BACKGROUND_NOTE}[/yellow]')


@data_catalogue.command(name='share')
@connection_options
@click.option('--item-id', required=True, help='The ID of the data catalogue item (dataset).')
@click.option('--share-with-workspace', 'share_with_workspaces', multiple=True,
              help='A workspace name or ID to give access to. Can be used several times.')
@click.option('--share-with-all', is_flag=True,
              help='Give access to all active workspaces of the same cloud provider.')
@click.option('--unshare-workspace', 'unshare_workspaces', multiple=True,
              help='A workspace name or ID to remove access from. Can be used several times.')
@click.option('--unshare-all', is_flag=True, help='Remove access from all workspaces.')
@click.option('-y', '--yes', is_flag=True, help='Do not ask for confirmation when removing access.')
@click.pass_context
@with_profile_config(required_params=['apikey'])
def share_dataset(ctx, apikey, cloudos_url, organisation_id, workspace_id, disable_ssl_verification, ssl_cert,
                  profile, item_id, share_with_workspaces, share_with_all, unshare_workspaces, unshare_all, yes):
    """Change the workspaces a data catalogue dataset is shared with.

    Workspaces are added to, or removed from, the current list. Workspaces that are not mentioned keep
    their access.
    """
    if not (share_with_workspaces or share_with_all or unshare_workspaces or unshare_all):
        raise click.UsageError('Please provide at least one of --share-with-workspace, --share-with-all, '
                               '--unshare-workspace or --unshare-all.')
    if share_with_all and share_with_workspaces:
        raise click.UsageError('--share-with-all and --share-with-workspace cannot be used together.')
    if unshare_all and (unshare_workspaces or share_with_workspaces or share_with_all):
        raise click.UsageError('--unshare-all cannot be combined with other sharing options.')

    client = _make_client(apikey, cloudos_url, organisation_id, workspace_id, disable_ssl_verification, ssl_cert)
    console = Console()
    item = client.get_item(item_id)
    current = list(item.get('sharedWithTeamIds') or [])
    names = {w.get('id'): w.get('name') for w in item.get('sharedWorkspaces') or []}

    new = [] if unshare_all else list(current)
    for workspace in client.resolve_workspaces(share_with_workspaces, item['cloudProvider'], share_with_all):
        names[workspace['_id']] = workspace['name']
        if workspace['_id'] not in new:
            new.append(workspace['_id'])
    unknown = []
    for ref in unshare_workspaces:
        matches = [i for i in current if i == ref or names.get(i) == ref]
        if not matches:
            unknown.append(ref)
        new = [i for i in new if i not in matches]
    if unknown:
        raise ValueError(f"The dataset is not shared with: {', '.join(unknown)}.")

    added = [i for i in new if i not in current]
    removed = [i for i in current if i not in new]
    label = item.get('name', item_id)
    if not added and not removed:
        console.print(f"Nothing to change, '{label}' is already shared with the requested workspaces.")
        return
    if removed and not yes:
        click.confirm(f"These workspaces will lose access to '{label}': "
                      f"{', '.join(names.get(i, i) for i in removed)}. Continue?", abort=True)

    client.update_shared_workspaces(item_id, new)
    for title, ids in (('Shared with', added), ('Removed access from', removed)):
        if ids:
            console.print(f"{title}: {', '.join(names.get(i, i) for i in ids)}")
    console.print(f"'{label}' is now shared with {len(new)} workspace(s).")
    console.print(f'[yellow]{BACKGROUND_NOTE}[/yellow]')


@data_catalogue.command(name='list')
@connection_options
@click.option('--search', help='Only show datasets matching this text.')
@click.option('--page', type=click.IntRange(min=1), default=1, show_default=True, help='The page to show.')
@click.option('--limit', type=click.IntRange(min=1, max=100), default=10, show_default=True,
              help='The number of datasets per page.')
@click.option('--output-format', type=click.Choice(['stdout', 'csv', 'json']), default='stdout',
              show_default=True, help='The output format. csv and json are written to a file.')
@click.option('--output-basename', default='data_catalogue_list', show_default=True,
              help='Output file base name, used with csv and json output formats.')
@click.pass_context
@with_profile_config(required_params=['apikey'])
def list_datasets(ctx, apikey, cloudos_url, organisation_id, workspace_id, disable_ssl_verification, ssl_cert,
                  profile, search, page, limit, output_format, output_basename):
    """List the datasets in the data catalogue of the organisation."""
    client = _make_client(apikey, cloudos_url, organisation_id, workspace_id, disable_ssl_verification, ssl_cert)
    content = client.list_items(page=page, per_page=limit, search=search)
    items = content.get('data', [])
    pagination = content.get('paginationMetadata', {})

    if output_format == 'json':
        outfile = f'{output_basename}.json'
        with open(outfile, 'w') as f:
            json.dump(items, f, indent=2)
        print(f'\tDataset list saved to {outfile}')
    elif output_format == 'csv':
        outfile = f'{output_basename}.csv'
        with open(outfile, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['name', 'id', 'status', 'cloud_provider', 'description', 'locations',
                             'shared_with', 'created_at'])
            for item in items:
                writer.writerow([item.get('name'), item.get('_id'), item.get('status'), item.get('cloudProvider'),
                                 item.get('description'), ';'.join(item.get('locations') or []),
                                 ';'.join(_shared_with(item)), item.get('createdAt')])
        print(f'\tDataset list saved to {outfile}')
    else:
        console = Console()
        if not items:
            console.print('No datasets found.')
            return
        console.print(_items_table(items))
        console.print(f"Page {pagination.get('currentPage', page)} of {pagination.get('totalPages', 1)} "
                      f"({pagination.get('totalCount', len(items))} datasets in total).")


@data_catalogue.command(name='info')
@connection_options
@click.option('--item-id', required=True, help='The ID of the data catalogue item (dataset).')
@click.pass_context
@with_profile_config(required_params=['apikey'])
def dataset_info(ctx, apikey, cloudos_url, organisation_id, workspace_id, disable_ssl_verification, ssl_cert,
                 profile, item_id):
    """Show a data catalogue dataset, the workspaces it is shared with and its metadata."""
    client = _make_client(apikey, cloudos_url, organisation_id, workspace_id, disable_ssl_verification, ssl_cert)
    item = client.get_item(item_id)
    metadata = client.get_item_metadata(item_id)
    console = Console()
    console.print(_items_table([item]))
    if metadata is None:
        console.print('[yellow]The dataset metadata is not available with an API key. '
                      'It can be seen in the Lifebit Platform.[/yellow]')
        return
    console.print('Metadata:')
    console.print_json(json.dumps(metadata))


@data_catalogue.command(name='rm')
@connection_options
@click.option('--item-id', required=True, help='The ID of the data catalogue item (dataset).')
@click.option('-y', '--yes', is_flag=True, help='Do not ask for confirmation.')
@click.pass_context
@with_profile_config(required_params=['apikey'])
def remove_dataset(ctx, apikey, cloudos_url, organisation_id, workspace_id, disable_ssl_verification, ssl_cert,
                   profile, item_id, yes):
    """Remove a dataset from the data catalogue. The data in the cloud storage is not deleted."""
    client = _make_client(apikey, cloudos_url, organisation_id, workspace_id, disable_ssl_verification, ssl_cert)
    item = client.get_item(item_id)
    label = item.get('name', item_id)
    if not yes:
        shared = _shared_with(item)
        extra = f" It is shared with {len(shared)} workspace(s), which will lose access." if shared else ''
        click.confirm(f"Remove '{label}' from the data catalogue?{extra}", abort=True)
    client.delete_item(item_id)
    Console().print(f"'{label}' was removed from the data catalogue. It may take a few moments to disappear "
                    'from the list.')

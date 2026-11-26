"""Tests for the data-catalogue CLI commands."""

import json

import pytest
import responses
from click.testing import CliRunner
from responses import matchers

from cloudos_cli.__main__ import run_cloudos_cli

APIKEY = 'vnoiweur89u2ongs'
CLOUDOS_URL = 'http://cloudos.lifebit.ai'
ORG_ID = 'org123'
ITEMS_URL = f'{CLOUDOS_URL}/api/v2/data-catalogue/items'
TEAMS_URL = f'{CLOUDOS_URL}/api/v1/organisations/{ORG_ID}/teams-metadata'
BASE_ARGS = ['--apikey', APIKEY, '--cloudos-url', CLOUDOS_URL, '--organisation-id', ORG_ID]

WORKSPACES = [
    {'_id': 'ws1', 'name': 'nf-core-tests', 'cloudType': 'AWSCloud'},
    {'_id': 'ws2', 'name': 'london-region-workspace', 'cloudType': 'AWSCloud'},
    {'_id': 'ws3', 'name': 'azure-workspace', 'cloudType': 'AzureCloud'},
]
ITEM = {
    '_id': 'item1', 'name': 'ds', 'status': 'active', 'cloudProvider': 'AWS',
    'description': 'desc', 'locations': ['s3://b/p/'],
    'sharedWithTeamIds': ['ws1'], 'sharedWorkspaces': [{'id': 'ws1', 'name': 'nf-core-tests'}]
}


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    """Do not read the profiles of the user running the tests."""
    monkeypatch.setenv('HOME', str(tmp_path))


def run(args, **kwargs):
    result = CliRunner().invoke(run_cloudos_cli, ['data-catalogue'] + args, **kwargs)
    return result


def mock_workspaces():
    responses.add(responses.GET, TEAMS_URL,
                  json={'teams': WORKSPACES, 'paginationMetadata': {'Pagination-Count': len(WORKSPACES)}})


def test_group_help_lists_commands():
    result = run(['--help'])
    assert result.exit_code == 0
    for command in ('import', 'share', 'list', 'info', 'rm'):
        assert command in result.output


@responses.activate
def test_import_single_dataset_shared_by_name():
    mock_workspaces()
    expected = [{'metadata': {'name': 'ds', 'description': 'desc', 'cloudProvider': 'AWS',
                              'locations': ['s3://b/p/', 's3://b/q/']},
                 'sharedTeamIds': ['ws1']}]
    responses.add(responses.POST, ITEMS_URL, status=201,
                  match=[matchers.json_params_matcher(expected)],
                  json=[{'_id': 'item1', 'name': 'ds', 'status': 'pending', 'cloudProvider': 'AWS',
                         'locations': ['s3://b/p/', 's3://b/q/']}])
    result = run(['import'] + BASE_ARGS + ['--name', 'ds', '--description', 'desc',
                                           '--location', 's3://b/p/', '--location', 's3://b/q/',
                                           '--share-with-workspace', 'nf-core-tests'])
    assert result.exit_code == 0, result.output
    assert 'item1' in result.output
    assert 'nf-core-tests' in result.output


@responses.activate
def test_import_share_with_all_uses_same_cloud_workspaces():
    mock_workspaces()
    responses.add(responses.POST, ITEMS_URL, status=201,
                  match=[matchers.json_params_matcher([{
                      'metadata': {'name': 'ds', 'description': 'desc', 'cloudProvider': 'AWS',
                                   'locations': ['s3://b/p/']},
                      'sharedTeamIds': ['ws1', 'ws2']}])],
                  json=[{'_id': 'item1', 'name': 'ds', 'status': 'pending'}])
    result = run(['import'] + BASE_ARGS + ['--name', 'ds', '--description', 'desc',
                                           '--location', 's3://b/p/', '--share-with-all'])
    assert result.exit_code == 0, result.output


@responses.activate
def test_import_from_meta_files(tmp_path):
    files = []
    for i in range(2):
        path = tmp_path / f'ds{i}.meta'
        path.write_text(json.dumps({'dataset_name': f'ds{i}', 'free_text_description': 'd',
                                    'location': f's3://b/{i}/', 'cloud_provider': 'AWS'}))
        files += ['--from-file', str(path)]
    responses.add(responses.POST, ITEMS_URL, status=201,
                  match=[matchers.json_params_matcher([
                      {'metadata': {'name': 'ds0', 'description': 'd', 'cloudProvider': 'AWS',
                                    'locations': ['s3://b/0/']}, 'sharedTeamIds': []},
                      {'metadata': {'name': 'ds1', 'description': 'd', 'cloudProvider': 'AWS',
                                    'locations': ['s3://b/1/']}, 'sharedTeamIds': []}])],
                  json=[{'_id': 'a', 'name': 'ds0'}, {'_id': 'b', 'name': 'ds1'}])
    result = run(['import'] + BASE_ARGS + files)
    assert result.exit_code == 0, result.output


@responses.activate
def test_import_rejects_invalid_location_before_calling_api():
    result = run(['import'] + BASE_ARGS + ['--name', 'ds', '--description', 'desc',
                                           '--location', 'gs://bucket/path'])
    assert result.exit_code != 0
    assert 'invalid AWS location' in str(result.exception)
    assert len(responses.calls) == 0


def test_import_requires_dataset_options():
    result = run(['import'] + BASE_ARGS + ['--name', 'ds'])
    assert result.exit_code == 2
    assert '--from-file' in result.output


def test_import_from_file_conflicts_with_name(tmp_path):
    path = tmp_path / 'ds.meta'
    path.write_text('{}')
    result = run(['import'] + BASE_ARGS + ['--from-file', str(path), '--name', 'ds'])
    assert result.exit_code == 2


def test_organisation_is_required():
    result = run(['list', '--apikey', APIKEY, '--cloudos-url', CLOUDOS_URL])
    assert result.exit_code == 2
    assert '--organisation-id' in result.output


@responses.activate
def test_organisation_is_resolved_from_workspace():
    responses.add(responses.GET, f'{CLOUDOS_URL}/api/v1/teams/ws1',
                  json={'team': {'organisation': {'id': ORG_ID}}})
    responses.add(responses.GET, ITEMS_URL, match=[matchers.query_param_matcher(
        {'organisationId': ORG_ID, 'page': '1', 'perPage': '10'})],
        json={'data': [ITEM], 'paginationMetadata': {'currentPage': 1, 'totalPages': 1, 'totalCount': 1}})
    result = run(['list', '--apikey', APIKEY, '--cloudos-url', CLOUDOS_URL, '--workspace-id', 'ws1'])
    assert result.exit_code == 0, result.output
    assert 'item1' in result.output


@responses.activate
def test_share_adds_to_current_workspaces():
    responses.add(responses.GET, f'{ITEMS_URL}/item1', json=ITEM)
    mock_workspaces()
    responses.add(responses.PUT, f'{ITEMS_URL}/item1',
                  match=[matchers.json_params_matcher({'sharedTeamIds': ['ws1', 'ws2']})], json={})
    result = run(['share'] + BASE_ARGS + ['--item-id', 'item1', '--share-with-workspace', 'london-region-workspace'])
    assert result.exit_code == 0, result.output
    assert 'Shared with: london-region-workspace' in result.output


@responses.activate
def test_share_removal_needs_confirmation():
    responses.add(responses.GET, f'{ITEMS_URL}/item1', json=ITEM)
    result = run(['share'] + BASE_ARGS + ['--item-id', 'item1', '--unshare-workspace', 'nf-core-tests'],
                 input='n\n')
    assert result.exit_code == 1
    assert 'will lose access' in result.output
    assert not any(c.request.method == 'PUT' for c in responses.calls)


@responses.activate
def test_unshare_all_with_yes():
    responses.add(responses.GET, f'{ITEMS_URL}/item1', json=ITEM)
    responses.add(responses.PUT, f'{ITEMS_URL}/item1',
                  match=[matchers.json_params_matcher({'sharedTeamIds': []})], json={})
    result = run(['share'] + BASE_ARGS + ['--item-id', 'item1', '--unshare-all', '--yes'])
    assert result.exit_code == 0, result.output
    assert 'Removed access from: nf-core-tests' in result.output


@responses.activate
def test_share_nothing_to_change():
    responses.add(responses.GET, f'{ITEMS_URL}/item1', json=ITEM)
    mock_workspaces()
    result = run(['share'] + BASE_ARGS + ['--item-id', 'item1', '--share-with-workspace', 'ws1'])
    assert result.exit_code == 0, result.output
    assert 'Nothing to change' in result.output


@responses.activate
def test_share_unknown_unshare_workspace():
    responses.add(responses.GET, f'{ITEMS_URL}/item1', json=ITEM)
    result = run(['share'] + BASE_ARGS + ['--item-id', 'item1', '--unshare-workspace', 'other'])
    assert result.exit_code == 1
    assert 'not shared with: other' in str(result.exception)


@responses.activate
def test_list_json_output(tmp_path):
    responses.add(responses.GET, ITEMS_URL, json={'data': [ITEM], 'paginationMetadata': {}})
    basename = str(tmp_path / 'out')
    result = run(['list'] + BASE_ARGS + ['--output-format', 'json', '--output-basename', basename])
    assert result.exit_code == 0, result.output
    with open(basename + '.json') as f:
        assert json.load(f) == [ITEM]


@responses.activate
def test_info_and_rm():
    responses.add(responses.GET, f'{ITEMS_URL}/item1', json=ITEM)
    responses.add(responses.GET, f'{ITEMS_URL}/item1/metadata', json={'name': 'ds', 'author': 'me'})
    responses.add(responses.DELETE, f'{ITEMS_URL}/item1', status=204)
    result = run(['info'] + BASE_ARGS + ['--item-id', 'item1'])
    assert result.exit_code == 0, result.output
    assert '"author": "me"' in result.output
    result = run(['rm'] + BASE_ARGS + ['--item-id', 'item1', '--yes'])
    assert result.exit_code == 0, result.output
    assert 'was removed from the data catalogue' in result.output

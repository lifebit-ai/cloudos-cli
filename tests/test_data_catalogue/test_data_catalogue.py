"""Tests for the DataCatalogue client and its helpers."""

import pytest
import responses
from responses import matchers

from cloudos_cli.data_catalogue import DataCatalogue
from cloudos_cli.data_catalogue.data_catalogue import (
    build_item_metadata,
    is_valid_location,
    metadata_from_meta_file,
    validate_item_metadata
)
from cloudos_cli.utils.errors import BadRequestException

APIKEY = 'vnoiweur89u2ongs'
CLOUDOS_URL = 'http://cloudos.lifebit.ai'
ORG_ID = 'org123'
ITEMS_URL = f'{CLOUDOS_URL}/api/v2/data-catalogue/items'
TEAMS_URL = f'{CLOUDOS_URL}/api/v1/organisations/{ORG_ID}/teams-metadata'

AWS_WS = {'_id': 'ws1', 'name': 'nf-core-tests', 'cloudType': 'AWSCloud'}
AWS_WS2 = {'_id': 'ws2', 'name': 'london-region-workspace', 'cloudType': 'AWSCloud'}
AZURE_WS = {'_id': 'ws3', 'name': 'azure-workspace', 'cloudType': 'AzureCloud'}


def client():
    return DataCatalogue(cloudos_url=CLOUDOS_URL, apikey=APIKEY, cromwell_token=None, organisation_id=ORG_ID)


@pytest.mark.parametrize('location,provider,expected', [
    ('s3://lifebit-featured-datasets/pipelines/', 'AWS', True),
    ('s3://bucket', 'AWS', True),
    ('s3://arn:aws:s3:eu-west-1:123456789012:accesspoint/my-ap/prefix', 'AWS', True),
    ('az://account.blob.core.windows.net/container/path', 'AWS', False),
    ('https://bucket.s3.amazonaws.com/path', 'AWS', False),
    ('s3:/bucket/path', 'AWS', False),
    ('az://account.blob.core.windows.net/container/path', 'Azure', True),
    ('az://account/container', 'Azure', True),
    ('s3://bucket/path', 'Azure', False),
    ('s3://bucket/path', 'GCP', False),
    ('', 'AWS', False),
])
def test_is_valid_location(location, provider, expected):
    assert is_valid_location(location, provider) is expected


def test_build_item_metadata_drops_empty_optional_fields():
    metadata = build_item_metadata('ds', 'desc', ('s3://b/p/',), author='', traits=(), number_of_participants=5)
    assert metadata == {
        'name': 'ds',
        'description': 'desc',
        'cloudProvider': 'AWS',
        'locations': ['s3://b/p/'],
        'numberOfParticipant': 5
    }


def test_metadata_from_meta_file_uses_ui_mapping():
    content = {
        'dataset_name': 'ds',
        'free_text_description': 'desc',
        'location': 's3://b/p/',
        'cloud_provider': 'AWS',
        'author': 'ignored',
        'metadata': {'traits': ['C50'], 'ancestry': ['EUR'], 'number_of_participant': 10, 'study_type': 'cohort'}
    }
    assert metadata_from_meta_file(content) == {
        'name': 'ds',
        'description': 'desc',
        'cloudProvider': 'AWS',
        'locations': ['s3://b/p/'],
        'traits': ['C50'],
        'ancestry': ['EUR'],
        'numberOfParticipant': 10,
        'studyType': 'cohort'
    }


def test_metadata_from_meta_file_accepts_location_list_and_defaults_to_aws():
    metadata = metadata_from_meta_file({'dataset_name': 'ds', 'free_text_description': 'd',
                                        'location': ['s3://a/', 's3://b/']})
    assert metadata['locations'] == ['s3://a/', 's3://b/']
    assert metadata['cloudProvider'] == 'AWS'


def test_validate_item_metadata_reports_all_problems():
    with pytest.raises(ValueError) as e:
        validate_item_metadata({'name': 'ds', 'description': '', 'cloudProvider': 'AWS',
                                'locations': ['gs://bucket/path']})
    assert 'a description is required' in str(e.value)
    assert 'invalid AWS location(s): gs://bucket/path' in str(e.value)


@responses.activate
def test_create_items_posts_a_list():
    items = [{'metadata': build_item_metadata('ds', 'desc', ['s3://b/p/']), 'sharedTeamIds': ['ws1']}]
    responses.add(
        responses.POST, ITEMS_URL,
        match=[matchers.query_param_matcher({'organisationId': ORG_ID}),
               matchers.header_matcher({'apikey': APIKEY}),
               matchers.json_params_matcher(items)],
        json=[{'_id': 'item1', 'name': 'ds', 'status': 'pending'}], status=201
    )
    created = client().create_items(items)
    assert created == [{'_id': 'item1', 'name': 'ds', 'status': 'pending'}]


@responses.activate
def test_update_shared_workspaces_puts_full_list():
    responses.add(
        responses.PUT, f'{ITEMS_URL}/item1',
        match=[matchers.query_param_matcher({'organisationId': ORG_ID}),
               matchers.json_params_matcher({'sharedTeamIds': ['ws1', 'ws2']})],
        json={'_id': 'item1'}, status=200
    )
    assert client().update_shared_workspaces('item1', ['ws1', 'ws2']) == {'_id': 'item1'}


@responses.activate
def test_list_and_delete_items():
    responses.add(
        responses.GET, ITEMS_URL,
        match=[matchers.query_param_matcher({'organisationId': ORG_ID, 'page': '2', 'perPage': '5',
                                             'search': 'gel'})],
        json={'data': [], 'paginationMetadata': {'totalCount': 0}}
    )
    responses.add(responses.DELETE, f'{ITEMS_URL}/item1',
                  match=[matchers.query_param_matcher({'organisationId': ORG_ID})], status=204)
    dc = client()
    assert dc.list_items(page=2, per_page=5, search='gel')['data'] == []
    dc.delete_item('item1')


@responses.activate
def test_duplicate_name_error_message():
    responses.add(responses.POST, ITEMS_URL, status=400, json={
        'statusCode': 400, 'code': 'BadRequest',
        'message': '[ds] The name ds is already taken for this Organisation'})
    with pytest.raises(BadRequestException, match='already taken for this Organisation'):
        client().create_items([{'metadata': {}, 'sharedTeamIds': []}])


@responses.activate
def test_schema_error_message():
    responses.add(responses.POST, ITEMS_URL, status=400, json={'errors': [{
        'instancePath': '/requestBody/0/metadata', 'keyword': 'required',
        'message': "must have required property 'description'"}]})
    with pytest.raises(BadRequestException, match="/requestBody/0/metadata: must have required property"):
        client().create_items([{'metadata': {}, 'sharedTeamIds': []}])


@responses.activate
def test_invalid_request_error_includes_details():
    responses.add(responses.GET, TEAMS_URL, status=400, json={
        'statusCode': 400, 'code': 'BadRequest', 'message': 'Invalid request',
        'data': [{'instancePath': '/query/limit', 'keyword': 'maximum', 'message': 'must be <= 25'}]})
    with pytest.raises(BadRequestException, match=r'Invalid request \(/query/limit: must be <= 25\)'):
        client().list_workspaces()


@responses.activate
def test_forbidden_error_mentions_admin():
    responses.add(responses.GET, ITEMS_URL, status=403, json={'message': 'Forbidden'})
    with pytest.raises(BadRequestException, match='organisation admin'):
        client().list_items()


@responses.activate
def test_resolve_organisation_id():
    responses.add(responses.GET, f'{CLOUDOS_URL}/api/v1/teams/ws1',
                  json={'team': {'_id': 'ws1', 'organisation': {'id': ORG_ID}}})
    dc = DataCatalogue(cloudos_url=CLOUDOS_URL, apikey=APIKEY, cromwell_token=None)
    assert dc.resolve_organisation_id('ws1') == ORG_ID
    assert dc.organisation_id == ORG_ID


@responses.activate
def test_list_workspaces_follows_pagination():
    responses.add(responses.GET, TEAMS_URL, match=[matchers.query_param_matcher(
        {'organisationId': ORG_ID, 'limit': '2', 'deactivated': 'false', 'page': '1'})],
        json={'teams': [AWS_WS, AWS_WS2], 'paginationMetadata': {'Pagination-Count': 3}})
    responses.add(responses.GET, TEAMS_URL, match=[matchers.query_param_matcher(
        {'organisationId': ORG_ID, 'limit': '2', 'deactivated': 'false', 'page': '2'})],
        json={'teams': [AZURE_WS], 'paginationMetadata': {'Pagination-Count': 3}})
    assert client().list_workspaces(page_size=2) == [AWS_WS, AWS_WS2, AZURE_WS]


def _mock_workspaces():
    responses.add(responses.GET, TEAMS_URL,
                  json={'teams': [AWS_WS, AWS_WS2, AZURE_WS], 'paginationMetadata': {'Pagination-Count': 3}})


@responses.activate
def test_resolve_workspaces_by_name_and_id():
    _mock_workspaces()
    assert client().resolve_workspaces(['nf-core-tests', 'ws2', 'ws1'], 'AWS') == [AWS_WS, AWS_WS2]


@responses.activate
def test_resolve_workspaces_all_filters_by_cloud():
    _mock_workspaces()
    assert client().resolve_workspaces([], 'Azure', share_with_all=True) == [AZURE_WS]


@responses.activate
def test_resolve_workspaces_errors():
    _mock_workspaces()
    with pytest.raises(ValueError) as e:
        client().resolve_workspaces(['missing', 'azure-workspace'], 'AWS')
    assert "workspace 'missing' was not found" in str(e.value)
    assert "workspace 'azure-workspace' runs on AzureCloud" in str(e.value)


def test_resolve_workspaces_without_references_makes_no_request():
    assert client().resolve_workspaces([], 'AWS') == []


@responses.activate
def test_get_item_falls_back_to_list_when_api_key_is_rejected():
    responses.add(responses.GET, f'{ITEMS_URL}/item2', status=401)
    responses.add(responses.GET, ITEMS_URL, match=[matchers.query_param_matcher(
        {'organisationId': ORG_ID, 'page': '1', 'perPage': '100'})],
        json={'data': [{'_id': 'item1'}], 'paginationMetadata': {'nextPage': 2}})
    responses.add(responses.GET, ITEMS_URL, match=[matchers.query_param_matcher(
        {'organisationId': ORG_ID, 'page': '2', 'perPage': '100'})],
        json={'data': [{'_id': 'item2', 'sharedWithTeamIds': ['ws1']}], 'paginationMetadata': {'nextPage': None}})
    assert client().get_item('item2') == {'_id': 'item2', 'sharedWithTeamIds': ['ws1']}


@responses.activate
def test_get_item_not_found_in_list():
    responses.add(responses.GET, f'{ITEMS_URL}/missing', status=401)
    responses.add(responses.GET, ITEMS_URL, json={'data': [], 'paginationMetadata': {'nextPage': None}})
    with pytest.raises(ValueError, match='was not found'):
        client().get_item('missing')


@responses.activate
def test_get_item_metadata_returns_none_when_api_key_is_rejected():
    responses.add(responses.GET, f'{ITEMS_URL}/item1/metadata', status=401)
    assert client().get_item_metadata('item1') is None

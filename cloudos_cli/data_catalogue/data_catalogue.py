"""
Client for the Lifebit Platform data catalogue (Object Data Connect).

Datasets in the data catalogue belong to an organisation and point to one or
more object-storage locations (S3 or Azure blob URIs). An organisation admin
can import them and share them with workspaces of the same cloud provider.
"""

import json
import re
from dataclasses import dataclass
from typing import Union

from cloudos_cli.clos import Cloudos
from cloudos_cli.utils.errors import BadRequestException
from cloudos_cli.utils.requests import (
    retry_requests_delete,
    retry_requests_get,
    retry_requests_post,
    retry_requests_put
)


# Cloud providers accepted by the data catalogue, mapped to the workspace cloudType
CLOUD_TYPES = {
    'AWS': 'AWSCloud',
    'Azure': 'AzureCloud'
}

# Location URI patterns, the same ones the Lifebit Platform UI validates against
_S3_URI_PATTERNS = [
    re.compile(r'^s3://[\w-]+(\.[\w-]+)*(/(?:[^?#]|%[0-9A-Fa-f]{2})*)*(\?[^#]*)?(#.*)?$'),
    re.compile(r'^s3://arn:aws:s3:[a-z0-9-]*:\d{12}:accesspoint/[\w-]+(/(?:[^?#]|%[0-9A-Fa-f]{2})*)*$'),
    re.compile(r'^s3://arn:aws:s3::\d{12}:accesspoint/[\w\-.]+(/(?:[^?#]|%[0-9A-Fa-f]{2})*)*$'),
    re.compile(r'^s3://arn:aws:s3-object-lambda:[a-z0-9-]*:\d{12}:accesspoint/[\w-]+'
               r'(/(?:[^?#]|%[0-9A-Fa-f]{2})*)*$'),
    re.compile(r'^s3://arn:aws:s3-outposts:[a-z0-9-]*:\d{12}:outpost/[\w-]+/accesspoint/[\w-]+'
               r'(/(?:[^?#]|%[0-9A-Fa-f]{2})*)*$'),
]
_AZURE_URI_PATTERN = re.compile(r'^az://[a-z0-9]{3,24}(\.[\w-]+)*/[a-z0-9][\w\-.]*(/[\w\-.]+)*$')

LOCATION_EXAMPLES = {
    'AWS': 's3://my-bucket/path/',
    'Azure': 'az://storageaccount.blob.core.windows.net/container/path'
}

ADMIN_HINT = ('Data catalogue operations require the API key of an organisation admin, '
              'and the organisation ID must be the one of your organisation.')


def is_valid_location(location, cloud_provider):
    """Check whether a location URI is valid for the given cloud provider.

    Parameters
    ----------
    location : str
        The location URI, e.g. s3://my-bucket/path/.
    cloud_provider : str
        One of the keys of CLOUD_TYPES.

    Returns
    -------
    bool
        True if the URI is valid for the cloud provider.
    """
    if not isinstance(location, str) or not location.strip():
        return False
    if cloud_provider == 'AWS':
        return any(p.match(location) for p in _S3_URI_PATTERNS)
    if cloud_provider == 'Azure':
        return bool(_AZURE_URI_PATTERN.match(location))
    return False


def build_item_metadata(name, description, locations, cloud_provider='AWS', author=None, release=None,
                        version=None, traits=None, ancestry=None, number_of_participants=None,
                        study_type=None):
    """Build the metadata of a data catalogue item, leaving out empty optional fields.

    Returns
    -------
    dict
        The item metadata, as expected by the data catalogue API.
    """
    metadata = {
        'name': name,
        'description': description,
        'cloudProvider': cloud_provider,
        'locations': list(locations or [])
    }
    optional = {
        'author': author,
        'release': release,
        'version': version,
        'traits': list(traits or []),
        'ancestry': list(ancestry or []),
        'numberOfParticipant': number_of_participants,
        'studyType': study_type
    }
    metadata.update({k: v for k, v in optional.items() if v not in (None, '', [])})
    return metadata


def metadata_from_meta_file(content):
    """Convert the content of a Lifebit metadata (.meta) file into item metadata.

    The mapping is the same one used by the Upload tab of the Lifebit Platform UI.

    Parameters
    ----------
    content : dict
        The parsed .meta / JSON file.

    Returns
    -------
    dict
        The item metadata, as expected by the data catalogue API.
    """
    if not isinstance(content, dict):
        raise ValueError('Each metadata file entry must be a JSON object.')
    location = content.get('location')
    if isinstance(location, list):
        locations = location
    else:
        locations = [location] if location else []
    extra = content.get('metadata') or {}
    if not isinstance(extra, dict):
        raise ValueError("The 'metadata' field of a metadata file must be a JSON object.")
    return build_item_metadata(
        name=content.get('dataset_name', ''),
        description=content.get('free_text_description', ''),
        locations=locations,
        cloud_provider=content.get('cloud_provider') or 'AWS',
        traits=extra.get('traits'),
        ancestry=extra.get('ancestry'),
        number_of_participants=extra.get('number_of_participant'),
        study_type=extra.get('study_type')
    )


def validate_item_metadata(metadata):
    """Validate item metadata before sending it, raising ValueError with all the problems found."""
    label = metadata.get('name') or '<unnamed>'
    problems = []
    if not metadata.get('name'):
        problems.append('a name is required')
    if not metadata.get('description'):
        problems.append('a description is required')
    cloud_provider = metadata.get('cloudProvider')
    if cloud_provider not in CLOUD_TYPES:
        problems.append(f"cloud provider '{cloud_provider}' is not supported "
                        f"(use one of: {', '.join(CLOUD_TYPES)})")
    locations = metadata.get('locations') or []
    if not locations:
        problems.append('at least one location is required')
    elif cloud_provider in CLOUD_TYPES:
        invalid = [loc for loc in locations if not is_valid_location(loc, cloud_provider)]
        if invalid:
            problems.append(f"invalid {cloud_provider} location(s): {', '.join(map(str, invalid))} "
                            f"(expected e.g. {LOCATION_EXAMPLES[cloud_provider]})")
    if problems:
        raise ValueError(f"Dataset '{label}': " + '; '.join(problems) + '.')


def _check_response(r):
    """Raise a BadRequestException for error responses, with a hint for permission errors."""
    if r.status_code >= 400:
        exc = BadRequestException(r)
        if r.status_code in (401, 403):
            exc.args = (f'{exc}. {ADMIN_HINT}',)
        raise exc


@dataclass
class DataCatalogue(Cloudos):
    """Client for the data catalogue items of an organisation.

    Parameters
    ----------
    cloudos_url : string
        The Lifebit Platform service url.
    apikey : string
        Your Lifebit Platform API key. It must belong to an organisation admin.
    cromwell_token : string
        Not used. Kept for compatibility with the Cloudos class.
    organisation_id : string
        The organisation that owns the data catalogue items.
    verify: [bool|string]
        Whether to use SSL verification or not. Alternatively, if
        a string is passed, it will be interpreted as the path to
        the SSL certificate file.
    """
    organisation_id: str = None
    verify: Union[bool, str] = True

    def _headers(self):
        return {
            'Content-type': 'application/json',
            'apikey': self.apikey
        }

    def _items_url(self, path=''):
        return f'{self.cloudos_url}/api/v2/data-catalogue/items{path}'

    def _require_organisation(self):
        if not self.organisation_id:
            raise ValueError('An organisation ID is required for data catalogue operations.')
        return {'organisationId': self.organisation_id}

    def resolve_organisation_id(self, workspace_id):
        """Find the organisation that a workspace belongs to.

        Parameters
        ----------
        workspace_id : str
            The Lifebit Platform workspace ID.

        Returns
        -------
        str
            The organisation ID. It is also stored in self.organisation_id.
        """
        r = retry_requests_get(f'{self.cloudos_url}/api/v1/teams/{workspace_id}',
                               headers=self._headers(), verify=self.verify)
        _check_response(r)
        team = r.json().get('team', {})
        organisation = team.get('organisation') or {}
        organisation_id = organisation.get('id') or organisation.get('_id')
        if not organisation_id:
            raise ValueError(f'Could not find the organisation of workspace {workspace_id}. '
                             'Please provide --organisation-id.')
        self.organisation_id = organisation_id
        return organisation_id

    def list_items(self, page=1, per_page=10, search=None):
        """List one page of data catalogue items.

        Returns
        -------
        dict
            {'data': [item, ...], 'paginationMetadata': {...}}
        """
        params = self._require_organisation()
        params.update({'page': page, 'perPage': per_page})
        if search:
            params['search'] = search
        r = retry_requests_get(self._items_url(), params=params,
                               headers=self._headers(), verify=self.verify)
        _check_response(r)
        return r.json()

    def get_item(self, item_id):
        """Get a data catalogue item, including the workspaces it is shared with.

        The platform does not accept API keys on GET /items/{id} (it answers 401 even for
        organisation admins), so in that case the item is looked up in the item list instead.
        """
        r = retry_requests_get(self._items_url(f'/{item_id}'), params=self._require_organisation(),
                               headers=self._headers(), verify=self.verify)
        if r.status_code in (401, 403):
            return self._find_item_in_list(item_id)
        _check_response(r)
        return r.json()

    def _find_item_in_list(self, item_id, per_page=100):
        page = 1
        while page:
            content = self.list_items(page=page, per_page=per_page)
            for item in content.get('data', []):
                if item.get('_id') == item_id:
                    return item
            page = content.get('paginationMetadata', {}).get('nextPage')
        raise ValueError(f'Dataset {item_id} was not found in the data catalogue of the organisation.')

    def get_item_metadata(self, item_id):
        """Get the metadata of a data catalogue item, as it was submitted.

        Returns None when the platform does not allow it with an API key (401/403).
        """
        r = retry_requests_get(self._items_url(f'/{item_id}/metadata'), params=self._require_organisation(),
                               headers=self._headers(), verify=self.verify)
        if r.status_code in (401, 403):
            return None
        _check_response(r)
        return r.json()

    def create_items(self, items):
        """Import one or more datasets into the data catalogue.

        Parameters
        ----------
        items : list of dict
            Each entry is {'metadata': {...}, 'sharedTeamIds': [...]}.

        Returns
        -------
        list
            The created items. Their status starts as 'pending'.
        """
        r = retry_requests_post(self._items_url(), params=self._require_organisation(),
                                headers=self._headers(), data=json.dumps(items), verify=self.verify)
        _check_response(r)
        created = r.json()
        return created if isinstance(created, list) else [created]

    def update_shared_workspaces(self, item_id, team_ids):
        """Set the full list of workspaces an item is shared with.

        Workspaces not in team_ids lose access to the item.
        """
        r = retry_requests_put(self._items_url(f'/{item_id}'), params=self._require_organisation(),
                               headers=self._headers(), data=json.dumps({'sharedTeamIds': list(team_ids)}),
                               verify=self.verify)
        _check_response(r)
        return r.json()

    def delete_item(self, item_id):
        """Delete a data catalogue item. The platform removes it in the background."""
        r = retry_requests_delete(self._items_url(f'/{item_id}'), params=self._require_organisation(),
                                  headers=self._headers(), verify=self.verify)
        _check_response(r)

    def list_workspaces(self, cloud_provider=None, page_size=25):
        """List the active workspaces of the organisation.

        Parameters
        ----------
        cloud_provider : str, optional
            When given, only workspaces of this cloud provider (AWS or Azure) are returned.

        Returns
        -------
        list of dict
            Workspaces, each with at least '_id', 'name' and 'cloudType'.
        """
        self._require_organisation()
        params = {
            'organisationId': self.organisation_id,
            'limit': page_size,
            'deactivated': 'false'
        }
        if cloud_provider:
            params['cloudType'] = CLOUD_TYPES[cloud_provider]
        url = f'{self.cloudos_url}/api/v1/organisations/{self.organisation_id}/teams-metadata'
        workspaces = []
        page = 1
        while True:
            params['page'] = page
            r = retry_requests_get(url, params=params, headers=self._headers(), verify=self.verify)
            _check_response(r)
            content = r.json()
            teams = content.get('teams', [])
            workspaces.extend(teams)
            total = content.get('paginationMetadata', {}).get('Pagination-Count', len(workspaces))
            if not teams or len(workspaces) >= total:
                return workspaces
            page += 1

    def resolve_workspaces(self, references, cloud_provider, share_with_all=False):
        """Turn workspace names or IDs into workspace IDs that an item can be shared with.

        Parameters
        ----------
        references : list of str
            Workspace names or IDs.
        cloud_provider : str
            The cloud provider of the item. Items can only be shared with workspaces of
            the same cloud provider.
        share_with_all : bool
            Return every active workspace of the organisation with the same cloud provider.

        Returns
        -------
        list of dict
            The matching workspaces, as returned by list_workspaces.
        """
        if not references and not share_with_all:
            return []
        workspaces = self.list_workspaces()
        cloud_type = CLOUD_TYPES[cloud_provider]
        if share_with_all:
            return [w for w in workspaces if w.get('cloudType') == cloud_type]

        by_id = {w['_id']: w for w in workspaces}
        resolved = []
        errors = []
        for ref in references:
            if ref in by_id:
                matches = [by_id[ref]]
            else:
                matches = [w for w in workspaces if w.get('name') == ref]
            if not matches:
                errors.append(f"workspace '{ref}' was not found among the active workspaces of the organisation")
            elif len(matches) > 1:
                ids = ', '.join(w['_id'] for w in matches)
                errors.append(f"workspace name '{ref}' is ambiguous, use one of these IDs instead: {ids}")
            elif matches[0].get('cloudType') != cloud_type:
                errors.append(f"workspace '{ref}' runs on {matches[0].get('cloudType')}, but the dataset is "
                              f"hosted on {cloud_provider}. Datasets can only be shared with workspaces "
                              'of the same cloud provider')
            elif matches[0] not in resolved:
                resolved.append(matches[0])
        if errors:
            raise ValueError('Cannot share the dataset: ' + '; '.join(errors) + '.')
        return resolved

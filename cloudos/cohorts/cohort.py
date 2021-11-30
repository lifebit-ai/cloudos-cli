"""
This is the main class for interacting with cohort browser cohorts.
"""

import requests
from cloudos.utils.errors import BadRequestException


class Cohort(object):
    """Class to store and operate cohorts.

    Parameters
    ----------
    apikey : string
        Your CloudOS API key.
    cloudos_url : string
        The CloudOS service url.
    workspace_id : string
        The specific Cloudos workspace id.
    cohort_id : string
        The ID of a Cohort Browser cohort (Optional).
    cohort_name : string
        The name of a Cohort Browser cohort - can be used instead of cohort_id (Optional).
    """
    def __init__(self, apikey, cloudos_url, workspace_id, cohort_id=None, cohort_name=None):
        self.apikey = apikey
        self.cloudos_url = cloudos_url
        self.workspace_id = workspace_id

        self.cohort_name = None
        self.num_participants = None
        self.query = None
        self.columns = None
        self.query_type = None

        if cohort_id is not None:
            self.cohort_id = cohort_id
        elif cohort_name is not None:
            self.cohort_id = self.fetch_cohort_id(cohort_name)
        else:
            raise ValueError('One of cohort_id or cohort_name must be set.')

        # Fill in cohort info from API
        self.update()

    @property
    def column_ids(self) -> list:
        return [ item['field']['id'] for item in self.columns ]

    def update(self):
        """Update the stored cohort information in the cohort object instance with
        the latest information from the Cohort Browser server."""

        headers = {"apikey": self.apikey,
                   "Accept": "application/json, text/plain, */*",
                   "Content-Type": "application/json;charset=UTF-8"}
        params = {"teamId": self.workspace_id}
        r = requests.get(f"{self.cloudos_url}/cohort-browser/v2/cohort/{self.cohort_id}",
                         params=params, headers=headers)
        if r.status_code >= 400:
            raise BadRequestException(r)
        r_json = r.json()
        self.cohort_name = r_json['name']
        self.cohort_desc = r_json.get('description')
        self.num_participants = r_json['numberOfParticipants']
        self.query = r_json.get('query')
        self.columns = r_json['columns']
        self.query_type = r_json['type']

    def fetch_cohort_id(self, name):
        return NotImplemented


def create_cohort(apikey, cloudos_url, workspace_id, cohort_name, cohort_desc=""):
    """Create a new cohort in the Cohort Browser.

    Parameters
    ----------
    apikey : string
        Your CloudOS API key.
    cloudos_url : string
        The CloudOS service url.
    workspace_id : string
        The specific Cloudos workspace id.
    cohort_name : string
        The name to assign to the new cohort.
    Cohort_desc : string
        The description to assign to the new cohort. (Optional)
    """

    headers = {"apikey": apikey,
               "Accept": "application/json, text/plain, */*",
               "Content-Type": "application/json;charset=UTF-8"}
    params = {"teamId": workspace_id}
    data = {"name": cohort_name,
            "description": cohort_desc}
    r = requests.post(f"{cloudos_url}/cohort-browser/v2/cohort",
                      params=params, headers=headers, json=data)
    if r.status_code >= 400:
        raise BadRequestException(r)
    r_json = r.json()
    cohort = Cohort(apikey, cloudos_url, workspace_id, cohort_id=r_json['_id'])
    return cohort

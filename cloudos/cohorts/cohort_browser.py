"""
This is the main class for interacting with a cohort browser instance.
"""
import requests
from dataclasses import dataclass
from cloudos.cohorts import Cohort
from cloudos.utils.errors import BadRequestException


@dataclass
class CohortBrowser:
    """A simple class to contain the required connection information.

    Parameters
    ----------
    apikey : string
        Your CloudOS API key.
    cloudos_url : string
        The CloudOS service url.
    workspace_id : string
        The specific Cloudos workspace id.
    """
    apikey: str
    cloudos_url: str
    workspace_id: str

    def load_cohort(self, cohort_id=None, cohort_name=None):
        """Load an existing cohort using its ID.

        Parameters
        ----------
        cohort_id : string
            The ID of a Cohort Browser cohort (Optional).
        cohort_name : string
            The name of a Cohort Browser cohort - can be used instead of cohort_id (Optional).

        Returns
        -------
        Cohort
        """
        return Cohort.load(self.apikey, self.cloudos_url, self.workspace_id,
                           cohort_id=cohort_id, cohort_name=cohort_name)

    def create_cohort(self, cohort_name, cohort_desc=""):
        """Create a new cohort in the Cohort Browser.

        Parameters
        ----------
        cohort_name : string
            The name to assign to the new cohort.
        cohort_desc : string
            The description to assign to the new cohort. (Optional)

        Returns
        -------
        Cohort
        """
        return Cohort.create(self.apikey, self.cloudos_url, self.workspace_id,
                             cohort_name, cohort_desc=cohort_desc)

    def get_phenotype_metadata(self, pheno_id):
        """Get metadata on a phenotype.

        Parameters
        ----------
        pheno_id : int
            The id of the phenotype of interest.

        Returns
        -------
        Dict
        """
        headers = {"apikey": self.apikey,
                   "Accept": "application/json, text/plain, */*",
                   "Content-Type": "application/json;charset=UTF-8"}
        params = {"teamId": self.workspace_id}
        r = requests.get(f"{self.cloudos_url}/cohort-browser/v2/cohort/filter/{pheno_id}/metadata",
                         params=params, headers=headers)
        if r.status_code >= 400:
            raise BadRequestException(r)
        r_json = r.json()
        r_json.pop('_id', None)
        return r_json

    def list_cohorts(self, size=10):
        """List all cohorts on the first page of Cohort browser.

        Parameters
        ----------
        term : int
            Number of cohorts to list on the first page.

        Returns
        -------
        Dict
        """
        headers = {"apikey": self.apikey,
                   "Accept": "application/json, text/plain, */*",
                   "Content-Type": "application/json;charset=UTF-8"}
        params = {"teamId": self.workspace_id,
                  "pageNumber": 0,
                  "pageSize": size}
        r = requests.get(f"{self.cloudos_url}/cohort-browser/v2/cohort",
                         params=params, headers=headers)
        if r.status_code >= 400:
            raise BadRequestException(r)
        r_json = r.json()
        if size == 10:
            print(f"""Total number of cohorts found: {r_json['total']}. 
            Showing {size} by default. Change 'size' parameter to return more.
            """.strip().replace("            ", ""))
        values_to_take = ["name", "description", "numberOfParticipants",
                          "numberOfFilters", "createdAt", "updatedAt"]
        cohort_dict = {}
        for i in range(len(r_json['cohorts'])):
            r_json['cohorts'][i]['numberOfFilters'] = len(r_json['cohorts'][i]['phenotypeFilters'])
            temp_dict = {x: r_json['cohorts'][i][x] for x in r_json['cohorts'][i]
                         if x in values_to_take}
            cohort_dict[i] = temp_dict
        return cohort_dict
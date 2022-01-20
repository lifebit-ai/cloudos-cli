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
        """List all cohorts from the first page of Cohort browser.
        Parameters
        ----------
        term : int or String "all"
            Number of cohorts to list from the first page.
        Returns
        -------
        Dict
        """
        headers = {"apikey": self.apikey,
                   "Accept": "application/json, text/plain, */*",
                   "Content-Type": "application/json;charset=UTF-8"}
        if size == "all":
            size = 0
            params = {"teamId": self.workspace_id,
                      "pageNumber": 0,
                      "pageSize": size}
            r = requests.get(f"{self.cloudos_url}/cohort-browser/v2/cohort",
                             params=params, headers=headers)
            if r.status_code >= 400:
                raise BadRequestException(r)
            r_json = r.json()
            size = r_json['total']
        params = {"teamId": self.workspace_id,
                  "pageNumber": 0,
                  "pageSize": size}
        r = requests.get(f"{self.cloudos_url}/cohort-browser/v2/cohort",
                            params=params, headers=headers)
        if r.status_code >= 400:
            raise BadRequestException(r)
        r_json = r.json()
        if size > r_json['total']:
            size = r_json['total']
        if size == 10:
            print(f"""Total number of cohorts found: {r_json['total']}.
            Showing {size} by default. Change 'size' parameter to return more.
            """.strip().replace("            ", ""))
        else:
            print(f"Total number of cohorts found: {r_json['total']}. Showing: {size}.")
        values_to_take = ["name", "_id", "description", "numberOfParticipants",
                          "numberOfFilters", "createdAt", "updatedAt"]
        cohort_list = []
        for cohort in r_json['cohorts']:
            temp_item = {k: v for k, v in cohort.items() if k in values_to_take}
            temp_item['numberOfFilters'] = len(cohort['phenotypeFilters'])
            cohort_list.append(temp_item)
        return cohort_list

    def search_phenotypes(self, term='', all_metadata=False):
        """Search for phenotypes with 'term' in their name.

        Parameters
        ----------
        term : string. Default=''
            The string with which to search for phenotypes. Empty string will return
            all phenotypes.
        all_metadata: boolean. Default=False
            Set to True to return all metadata for each returned phenotype.
        Returns
        -------
        Dict
        """
        headers = {"apikey": self.apikey,
                   "Accept": "application/json, text/plain, */*",
                   "Content-Type": "application/json;charset=UTF-8"}
        params = {"term": term,
                  "teamId": self.workspace_id}
        r = requests.get(f"{self.cloudos_url}/cohort-browser/v2/cohort/fields_search",
                         params=params, headers=headers)
        if r.status_code >= 400:
            raise BadRequestException(r)
        r_json = r.json()
        print(f"Total number of phenotypes found - {len(r_json['filters'])}")
        if all_metadata is True:
            return r_json['filters']
        else:
            values_to_take = ["id", "categoryPathLevel1", "categoryPathLevel2",
                              "categoryPathLevel3", "name", "description",
                              "type", "valueType", "units", "display",
                              "possibleValues", "min", "max", "recruiterDescription",
                              "group", "clinicalForm", "parent", "instances", "array",
                              "Sorting", "coding", "descriptionParticipantsNo",
                              "link", "descriptionCategoryID", "descriptionItemType",
                              "descriptionStrata", "descriptionSexed"]
            phenotypes_list = []
            for i, item in enumerate(r_json['filters']):
                temp_item = {item: r_json['filters'][i][item] for item in r_json['filters'][i]
                             if item in values_to_take}
                phenotypes_list.append(temp_item)
            return phenotypes_list
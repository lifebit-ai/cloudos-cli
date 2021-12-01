"""
This is the main class for interacting with a cohort browser instance.
"""

from dataclasses import dataclass
from cloudos.cohorts import Cohort


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

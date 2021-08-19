"""
This is the main class of the package.
"""

import requests
from dataclasses import dataclass
from cloudos.utils.errors import BadRequestException


@dataclass
class Cloudos:
    """A simple class to contain the required connection information.

    Parameters
    ----------
    apikey : string
        Your CloudOS API key.
    cloudos_url : string
        The CloudOS service url.
    """
    apikey: str
    cloudos_url: str

    def get_job_status(self, j_id):
        """Get job status from CloudOS.

        Parameters
        ----------
        j_id : string
            The CloudOS job id of the job just launched.

        Returns
        -------
        j_status : string
            The collected job status.
        """
        cloudos_url = self.cloudos_url
        apikey = self.apikey
        headers = {
            "Content-type": "application/json",
            "apikey": apikey
        }
        r = requests.get("{}/api/v1/jobs/{}".format(cloudos_url,
                                                    j_id),
                         headers=headers)
        if r.status_code >= 400:
            raise BadRequestException(r)
        return r

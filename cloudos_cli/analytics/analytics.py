"""
This is the main class for analytics operations.
"""

import requests
import json
from dataclasses import dataclass
from typing import Union, Optional
from cloudos_cli.clos import Cloudos
from cloudos_cli.utils.errors import BadRequestException


@dataclass
class Analytics(Cloudos):
    """Class to store and operate analytics data.

    Parameters
    ----------
    cloudos_url : string
        The Lifebit Platform service url.
    apikey : string
        Your Lifebit Platform API key.
    cromwell_token : string
        Cromwell server token.
    verify: [bool|string]
        Whether to use SSL verification or not. Alternatively, if
        a string is passed, it will be interpreted as the path to
        the SSL certificate file.
    """
    verify: Union[bool, str] = True

    def get_team_summary(self,
                         team_id: str,
                         start_date: Optional[str] = None,
                         end_date: Optional[str] = None,
                         granularity: Optional[str] = None):
        """Get aggregated team usage analytics over a date range.

        Parameters
        ----------
        team_id : str
            The Lifebit Platform team (workspace) id.
        start_date : str, optional
            The start date for the analytics range (e.g. '2024-01-01').
        end_date : str, optional
            The end date for the analytics range (e.g. '2024-12-31').
        granularity : str, optional
            The time granularity for the analytics (e.g. 'daily', 'weekly', 'monthly').

        Returns
        -------
        r : dict
            A dict containing aggregated team usage analytics (compute hours,
            job counts, spend) over the requested date range.
        """
        headers = {"apikey": self.apikey}
        params = {"teamId": team_id}
        if start_date is not None:
            params["startDate"] = start_date
        if end_date is not None:
            params["endDate"] = end_date
        if granularity is not None:
            params["granularity"] = granularity
        r = requests.get(
            "{}/api/v1/analytics/team/summary".format(self.cloudos_url),
            headers=headers,
            params=params,
            verify=self.verify
        )
        if r.status_code >= 400:
            raise BadRequestException(r)
        return json.loads(r.content)

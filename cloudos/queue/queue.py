"""
This is the main class to create job queues.
"""

import requests
import json
import pandas as pd
from dataclasses import dataclass
from typing import Union
from cloudos.clos import Cloudos
from cloudos.utils.errors import BadRequestException


@dataclass
class Queue(Cloudos):
    """Class to store and operate job queues.

    Parameters
    ----------
    cloudos_url : string
        The CloudOS service url.
    apikey : string
        Your CloudOS API key.
    cromwell_token : string
        Cromwell server token.
    workspace_id : string
        The specific Cloudos workspace id.
    verify: [bool|string]
        Whether to use SSL verification or not. Alternatively, if
        a string is passed, it will be interpreted as the path to
        the SSL certificate file.
    """
    workspace_id: str
    verify: Union[bool, str] = True

    def get_job_queues(self):
        """Get all the job queues from a CloudOS workspace.

        Returns
        -------
        r : list
            A list of dicts, each corresponding to a job queue.
        """
        data = {"apikey": self.apikey}
        r = requests.get("{}/api/v1/teams/aws/v2/job-queues?teamId={}".format(self.cloudos_url,
                                                                              self.workspace_id),
                         params=data, verify=self.verify)
        if r.status_code >= 400:
            raise BadRequestException(r)
        return json.loads(r.content)

    @staticmethod
    def process_queue_list(r, all_fields=False):
        """Process a job list from a self.get_job_list call.

        Parameters
        ----------
        r : list
            A list of dicts, each corresponding to a job queue.
        all_fields : bool. Default=False
            Whether to return a reduced version of the DataFrame containing
            only the selected columns or the full DataFrame.

        Returns
        -------
        df : pandas.DataFrame
            A DataFrame with the requested columns from the job queues.
        """
        COLUMNS = ['id',
                   'name',
                   'label',
                   'description',
                   'resourceType',
                   'executor',
                   'status'
                   ]
        df_full = pd.json_normalize(r)
        if all_fields:
            df = df_full
        else:
            df = df_full.loc[:, COLUMNS]
        return df

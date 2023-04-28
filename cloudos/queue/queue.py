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
        headers = {"apikey": self.apikey}
        r = requests.get("{}/api/v1/teams/aws/v2/job-queues?teamId={}".format(self.cloudos_url,
                                                                              self.workspace_id),
                         headers=headers, verify=self.verify)
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

    def fetch_job_queue_id(self, workflow_type, batch=False, job_queue=None):
        """Fetches CloudOS ID for a given job queue.

        When batch=True and isinstance(job_queue_name, str) this method will try to find the
        corresponding CloudOS ID for the job_queue_name in a given workspace. If
        job_queue_name=None, this method will select the newest "ready" job queue
        for the selected workflow type.

        Parameters
        ----------
        workflow_type : str ['wdl'|'cromwell'|'nextflow']
            The type of workflow to run.
        batch: bool
            Whether to create a batch job instead of the default ignite.
        job_queue : str or None
            The name of the job queue to search. If None, a default one will be selected.

        Returns
        -------
        job_queue_id : str or None
            The CloudOS ID for the selected job queue, or None if batch=False.
        """
        if not batch:
            return None
        if workflow_type == 'wdl':
            workflow_type = 'cromwell'
        if workflow_type not in ['cromwell', 'nextflow']:
            raise ValueError('[ERROR] Only nextflow or cromwell workflows are allowed when ' +
                             'running using AWS batch.')
        job_queues = self.get_job_queues()
        available_queues = [q for q in job_queues if q['status'] == 'Ready' and
                            q['executor'] == workflow_type]
        if len(available_queues) == 0:
            raise Exception(f'[ERROR] There are no available job queues for {workflow_type} ' +
                            'workflows. Consider creating one using CloudOS UI.')
        default_queue_id = available_queues[-1]['id']
        default_queue_name = available_queues[-1]['label']
        if job_queue is None:
            print('\tNo job_queue was specified, using the most recent suitable one: ' +
                  f'{default_queue_name}.')
            return default_queue_id
        selected_queue = [q for q in available_queues if q['label'] == job_queue]
        if len(selected_queue) == 0:
            print(f'\tQueue \'{job_queue}\' you specified was not found, using the most recent ' +
                  f'suitable one instead: {default_queue_name}.')
            return default_queue_id
        return selected_queue[0]['id']

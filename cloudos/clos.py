"""
This is the main class of the package.
"""

import requests
import json
from dataclasses import dataclass
from cloudos.utils.errors import BadRequestException
import pandas as pd


@dataclass
class Cloudos:
    """A simple class to contain the required connection information.

    Parameters
    ----------
    cloudos_url : string
        The CloudOS service url.
    apikey : string
        Your CloudOS API key.
    cromwell_token : string
        Cromwell server token.
    """
    cloudos_url: str
    apikey: str
    cromwell_token: str

    def get_job_status(self, j_id, verify=True):
        """Get job status from CloudOS.

        Parameters
        ----------
        j_id : string
            The CloudOS job id of the job just launched.
        verify: [bool|string]
            Whether to use SSL verification or not. Alternatively, if
            a string is passed, it will be interpreted as the path to
            the SSL certificate file.

        Returns
        -------
        r : requests.models.Response
            The server response
        """
        cloudos_url = self.cloudos_url
        apikey = self.apikey
        headers = {
            "Content-type": "application/json",
            "apikey": apikey
        }
        r = requests.get("{}/api/v1/jobs/{}".format(cloudos_url,
                                                    j_id),
                         headers=headers, verify=verify)
        if r.status_code >= 400:
            raise BadRequestException(r)
        return r

    def get_cromwell_status(self, workspace_id, verify=True):
        """Get Cromwell server status from CloudOS.

        Parameters
        ----------
        workspace_id : string
            The CloudOS workspace id from to check the Cromwell status.
        verify: [bool|string]
            Whether to use SSL verification or not. Alternatively, if
            a string is passed, it will be interpreted as the path to
            the SSL certificate file.

        Returns
        -------
        r : requests.models.Response
            The server response
        """
        cloudos_url = self.cloudos_url
        token = f'Bearer {self.cromwell_token}'
        headers = {
            "Accept": "application/json",
            "Authorization": token
        }
        r = requests.get("{}/api/v1/cromwell?teamId={}".format(cloudos_url,
                                                               workspace_id),
                         headers=headers, verify=verify)
        if r.status_code >= 400:
            raise BadRequestException(r)
        return r

    def cromwell_switch(self, workspace_id, action, verify=True):
        """Restart Cromwell server.

        Parameters
        ----------
        workspace_id : string
            The CloudOS workspace id in which restart/stop Cromwell status.
        action : string [restart|stop]
            The action to perform.
        verify: [bool|string]
            Whether to use SSL verification or not. Alternatively, if
            a string is passed, it will be interpreted as the path to
            the SSL certificate file.

        Returns
        -------
        r : requests.models.Response
            The server response
        """
        cloudos_url = self.cloudos_url
        token = f'Bearer {self.cromwell_token}'
        headers = {
            "Accept": "application/json",
            "Authorization": token
        }
        r = requests.put("{}/api/v1/cromwell/{}?teamId={}".format(cloudos_url,
                                                                  action,
                                                                  workspace_id),
                         headers=headers, verify=verify)
        if r.status_code >= 400:
            raise BadRequestException(r)
        return r

    def get_job_list(self, workspace_id, verify=True):
        """Get all the jobs from a CloudOS workspace.

        Parameters
        ----------
        workspace_id : string
            The CloudOS workspace id from to collect the jobs.
        verify: [bool|string]
            Whether to use SSL verification or not. Alternatively, if
            a string is passed, it will be interpreted as the path to
            the SSL certificate file.

        Returns
        -------
        r : requests.models.Response
            The server response
        """
        data = {"apikey": self.apikey}
        r = requests.get("{}/api/v1/jobs?teamId={}".format(self.cloudos_url,
                                                           workspace_id),
                         params=data, verify=verify)
        if r.status_code >= 400:
            raise BadRequestException(r)
        return r

    @staticmethod
    def process_job_list(r, all_fields=False):
        """Process a server response from a self.get_job_list call.

        Parameters
        ----------
        r : requests.models.Response
            The server response. It should contain a field named 'jobs' and
            the required columns (hard-coded in the function).
        all_fields : bool. Default=False
            Whether to return a reduced version of the DataFrame containing
            only the selected columns or the full DataFrame.

        Returns
        -------
        df : pandas.DataFrame
            A DataFrame with the requested columns from the jobs.
        """
        COLUMNS = ['_id',
                   'team',
                   'name',
                   'parameters',
                   'status',
                   'startTime',
                   'endTime',
                   'createdAt',
                   'updatedAt',
                   'computeCostSpent',
                   'masterInstanceStorageCost',
                   'resumeWorkDir',
                   'user.id',
                   'workflow._id',
                   'workflow.name',
                   'workflow.description',
                   'workflow.createdAt',
                   'workflow.updatedAt',
                   'workflow.workflowType',
                   'project._id',
                   'project.name',
                   'project.user',
                   'project.team',
                   'project.createdAt',
                   'project.updatedAt',
                   'masterInstance.usedInstance.type',
                   'spotInstances.usedInstance.asSpot'
                   ]
        my_jobs = json.loads(r.content)
        df_full = pd.json_normalize(my_jobs['jobs'])
        if all_fields:
            df = df_full
        else:
            df = df_full.loc[:, COLUMNS]
        return df

    def get_workflow_list(self, workspace_id, verify=True):
        """Get all the workflows from a CloudOS workspace.

        Parameters
        ----------
        workspace_id : string
            The CloudOS workspace id from to collect the workflows.
        verify: [bool|string]
            Whether to use SSL verification or not. Alternatively, if
            a string is passed, it will be interpreted as the path to
            the SSL certificate file.

        Returns
        -------
        r : requests.models.Response
            The server response
        """
        data = {"apikey": self.apikey}
        r = requests.get("{}/api/v1/workflows?teamId={}".format(self.cloudos_url,
                                                                workspace_id),
                         params=data, verify=verify)
        if r.status_code >= 400:
            raise BadRequestException(r)
        return r

    @staticmethod
    def process_workflow_list(r, all_fields=False):
        """Process a server response from a self.get_workflow_list call.

        Parameters
        ----------
        r : requests.models.Response
            The server response. It should contain a field named 'workflows' and
            the required columns (hard-coded in the function).
        all_fields : bool. Default=False
            Whether to return a reduced version of the DataFrame containing
            only the selected columns or the full DataFrame.

        Returns
        -------
        df : pandas.DataFrame
            A DataFrame with the requested columns from the workflows.
        """
        COLUMNS = ['_id',
                   'name',
                   'archived.status',
                   'mainFile',
                   'workflowType',
                   'repository.name',
                   'repository.platform',
                   'repository.url',
                   'repository.isPrivate'
                   ]
        my_workflows = json.loads(r.content)
        df_full = pd.json_normalize(my_workflows)
        if all_fields:
            df = df_full
        else:
            df = df_full.loc[:, COLUMNS]
        return df

    def detect_workflow(self, workflow_name, workspace_id, verify=True):
        """Detects workflow type: nextflow or wdl.

        Parameters
        ----------
        workflow_name : string
            Name of the workflow.
        workspace_id : string
            The CloudOS workspace id from to collect the workflows.
        verify: [bool|string]
            Whether to use SSL verification or not. Alternatively, if
            a string is passed, it will be interpreted as the path to
            the SSL certificate file.

        Returns
        -------
        wt : string ['nextflow'|'wdl']
            The workflow type detected
        """
        my_workflows_r = self.get_workflow_list(workspace_id, verify=verify)
        my_workflows = self.process_workflow_list(my_workflows_r)
        wt_all = my_workflows.loc[my_workflows['name'] == workflow_name, 'workflowType']
        if len(wt_all) == 0:
            raise ValueError(f'No workflow found with name: {workflow_name}')
        wt = wt_all.unique()
        if len(wt) > 1:
            raise ValueError(f'More than one workflow type detected for {workflow_name}: {wt}')
        return str(wt[0])

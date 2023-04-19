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
        Cromwell server token. If None, apikey will be used instead.
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

    def _create_cromwell_header(self):
        """Generates cromwell header.

        This methods is responsible for using personal API key instead of
        specific Cromwell API when the later is not provided.

        Returns
        -------
        headers : dict
            The correct headers based on using cromwell specific token or
            personal API key.
        """
        if self.cromwell_token is None:
            headers = {
                "Accept": "application/json",
                "apikey": self.apikey
            }
        else:
            headers = {
                "Accept": "application/json",
                "Authorization": f'Bearer {self.cromwell_token}'
            }
        return headers

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
        headers = self._create_cromwell_header()
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
        headers = self._create_cromwell_header()
        r = requests.put("{}/api/v1/cromwell/{}?teamId={}".format(cloudos_url,
                                                                  action,
                                                                  workspace_id),
                         headers=headers, verify=verify)
        if r.status_code >= 400:
            raise BadRequestException(r)
        return r

    def get_job_list(self, workspace_id, last_n_jobs=30, page=1, verify=True):
        """Get jobs from a CloudOS workspace.

        Parameters
        ----------
        workspace_id : string
            The CloudOS workspace id from to collect the jobs.
        last_n_jobs : [int | 'all']
            How many of the last jobs from the user to retrieve. You can specify a
            very large int or 'all' to get all user's jobs.
        page : int
            Response page to get.
        verify: [bool|string]
            Whether to use SSL verification or not. Alternatively, if
            a string is passed, it will be interpreted as the path to
            the SSL certificate file.

        Returns
        -------
        r : list
            A list of dicts, each corresponding to a jobs from the user and the workspace.
        """
        data = {"apikey": self.apikey}
        r = requests.get("{}/api/v1/jobs?teamId={}&page={}".format(self.cloudos_url,
                                                                   workspace_id, page),
                         params=data, verify=verify)
        if r.status_code >= 400:
            raise BadRequestException(r)
        content = json.loads(r.content)
        n_jobs = len(content['jobs'])
        if last_n_jobs == 'all':
            jobs_to_get = n_jobs
        elif last_n_jobs > 0:
            jobs_to_get = last_n_jobs - n_jobs
        else:
            raise TypeError("[ERROR] Please select an int > 0 or 'all' for 'last_n_jobs'")
        if jobs_to_get == 0 or n_jobs == 0:
            return content['jobs']
        if jobs_to_get > 0:
            if last_n_jobs == 'all':
                next_to_get = 'all'
            else:
                next_to_get = jobs_to_get
            return content['jobs'] + self.get_job_list(workspace_id, last_n_jobs=next_to_get,
                                                       page=page+1, verify=verify)
        if jobs_to_get < 0:
            return content['jobs'][:jobs_to_get]

    @staticmethod
    def process_job_list(r, all_fields=False):
        """Process a job list from a self.get_job_list call.

        Parameters
        ----------
        r : list
            A list of dicts, each corresponding to a job from the user and the workspace.
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
                   'user.id',
                   'workflow._id',
                   'workflow.name',
                   'workflow.description',
                   'workflow.createdAt',
                   'workflow.updatedAt',
                   'workflow.workflowType',
                   'project._id',
                   'project.name',
                   'project.createdAt',
                   'project.updatedAt',
                   'masterInstance.usedInstance.type',
                   'spotInstances.usedInstance.asSpot'
                   ]
        df_full = pd.json_normalize(r)
        if all_fields:
            df = df_full
        else:
            df = df_full.loc[:, COLUMNS]
        return df

    def get_curated_workflow_list(self, workspace_id, get_all=True, page=1, verify=True):
        """Get all the curated workflows from a CloudOS workspace.

        Parameters
        ----------
        workspace_id : string
            The CloudOS workspace id from to collect the workflows.
        get_all : bool
            Whether to get all available curated workflows or just the indicated page.
        page : int
            The page number to retrieve, from the paginated response.
        verify: [bool|string]
            Whether to use SSL verification or not. Alternatively, if
            a string is passed, it will be interpreted as the path to
            the SSL certificate file.

        Returns
        -------
        r : list
            A list of dicts, each corresponding to a workflow.
        """
        data = {"apikey": self.apikey,
                "search": "",
                "page": page,
                "filters": [
                    [
                        {
                            "isPredefined": True,
                            "isCurated": True,
                            "isFeatured": False,
                            "isModule": False
                        },
                        {
                            "isPredefined": True,
                            "isCurated": False,
                            "isFeatured": False,
                            "isModule": False
                        },
                        {
                            "isPredefined": True,
                            "isCurated": True,
                            "isFeatured": True,
                            "isModule": False
                        }
                    ]
                 ]
                }
        r = requests.post("{}/api/v1/workflows/getByType?teamId={}".format(self.cloudos_url,
                                                                           workspace_id),
                          json=data, verify=verify)
        if r.status_code >= 400:
            raise BadRequestException(r)
        content = json.loads(r.content)
        if get_all:
            workflows_collected = len(content['pipelines'])
            workflows_to_get = content['total']
            if workflows_to_get <= workflows_collected or workflows_collected == 0:
                return content['pipelines']
            if workflows_to_get > workflows_collected:
                return content['pipelines'] + self.get_curated_workflow_list(workspace_id,
                                                                             get_all=True,
                                                                             page=page+1,
                                                                             verify=verify)
        else:
            return content['pipelines']

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
        r : list
            A list of dicts, each corresponding to a workflow.
        """
        data = {"apikey": self.apikey}
        r = requests.get("{}/api/v1/workflows?teamId={}".format(self.cloudos_url,
                                                                workspace_id),
                         params=data, verify=verify)
        if r.status_code >= 400:
            raise BadRequestException(r)
        return json.loads(r.content)

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
                   'parameters',
                   'repository.name',
                   'repository.platform',
                   'repository.url',
                   'repository.isPrivate'
                   ]
        df_full = pd.json_normalize(r)
        if all_fields:
            df = df_full
        else:
            present_columns = []
            for column in COLUMNS:
                if column in df_full.columns:
                    present_columns.append(column)
            df = df_full.loc[:, present_columns]
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

    def get_project_list(self, workspace_id, verify=True):
        """Get all the project from a CloudOS workspace.

        Parameters
        ----------
        workspace_id : string
            The CloudOS workspace id from to collect the projects.
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
        r = requests.get("{}/api/v1/projects?teamId={}".format(self.cloudos_url, workspace_id),
                         params=data, verify=verify)
        if r.status_code >= 400:
            raise BadRequestException(r)
        return r

    @staticmethod
    def process_project_list(r, all_fields=False):
        """Process a server response from a self.get_project_list call.

        Parameters
        ----------
        r : requests.models.Response
        The server response. There are two types of responses:
            - A list with 2 elements: 'total' and 'projects', being 'projects' a list of dicts,
              one for each project.
            - A list of dicts, one for each project.
        all_fields : bool. Default=False
            Whether to return a reduced version of the DataFrame containing
            only the selected columns or the full DataFrame.

        Returns
        -------
        df : pandas.DataFrame
            A DataFrame with the requested columns from the projects.
        """
        COLUMNS = ['_id',
                   'name',
                   'user.id',
                   'user.name',
                   'user.surname',
                   'user.email',
                   'createdAt',
                   'updatedAt',
                   'workflowCount',
                   'jobCount',
                   'notebookSessionCount'
                   ]
        my_projects = json.loads(r.content)
        if 'projects' in my_projects:
            my_projects = my_projects['projects']
        df_full = pd.json_normalize(my_projects)
        if all_fields:
            df = df_full
        else:
            df = df_full.loc[:, COLUMNS]
        return df

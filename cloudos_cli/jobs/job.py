"""
This is the main class to create jobs.
"""

import base64
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from sqlite3.dbapi2 import paramstyle
from typing import Union

from cloudos_cli.global_vars import (CLOUDOS_URL, JOB_COMPLETED, AWS_NEXTFLOW_LATEST,
                                  AZURE_NEXTFLOW_LATEST, HPC_NEXTFLOW_LATEST, AWS_NEXTFLOW_VERSIONS,
                                  AZURE_NEXTFLOW_VERSIONS, HPC_NEXTFLOW_VERSIONS
)
from cloudos_cli.clos import Cloudos
from cloudos_cli.queue.queue import Queue
from cloudos_cli.utils.array_job import classify_pattern, get_file_or_folder_id, extract_project
from cloudos_cli.utils.errors import (
    BadRequestException,
    cloud_os_request_error,
    CantResumeNonResumableJob,
    CantResumeRunningJob,
)
from cloudos_cli.utils.requests import retry_requests_post, retry_requests_get
from cloudos_cli.utils.resources import ssl_selector


@dataclass
class Job(Cloudos):
    """Class to store and operate jobs.

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
    project_name : string
        The name of a CloudOS project.
    workflow_name : string
        The name of a CloudOS workflow or pipeline.
    verify: [bool|string]
        Whether to use SSL verification or not. Alternatively, if
        a string is passed, it will be interpreted as the path to
        the SSL certificate file.
    mainfile : string
        The name of the mainFile used by the workflow. Required for WDL pipelines as different
        mainFiles could be loaded for a single pipeline.
    importsfile : string
        The name of the importsFile used by the workflow. Optional and only used for WDL pipelines
        as different importsFiles could be loaded for a single pipeline.
    repository_platform : string
        The name of the repository platform of the workflow.
    project_id : string
        The CloudOS project id for a given project name.
    workflow_id : string
        The CloudOS workflow id for a given workflow_name.
    """
    workspace_id: str
    project_name: str
    workflow_name: str
    verify: Union[bool, str] = True
    mainfile: str = None
    importsfile: str = None
    repository_platform: str = 'github'
    project_id: str = None
    workflow_id: str = None

    @property
    def project_id(self) -> str:
        return self._project_id

    @project_id.setter
    def project_id(self, v) -> None:
        if isinstance(v, property):
            # Fetch the value as not defined by user.
            self._project_id = self.fetch_cloudos_id(
                self.apikey,
                self.cloudos_url,
                'projects',
                self.workspace_id,
                self.project_name,
                verify=self.verify)
        else:
            # Let the user define the value.
            self._project_id = v

    @property
    def workflow_id(self) -> str:
        return self._workflow_id

    @workflow_id.setter
    def workflow_id(self, v) -> None:
        if isinstance(v, property):
            # Fetch the value as not defined by user.
            self._workflow_id = self.fetch_cloudos_id(
                self.apikey,
                self.cloudos_url,
                'workflows',
                self.workspace_id,
                self.workflow_name,
                self.mainfile,
                self.importsfile,
                self.repository_platform,
                self.verify)
        else:
            # Let the user define the value.
            self._workflow_id = v

    def fetch_cloudos_id(self,
                         apikey,
                         cloudos_url,
                         resource,
                         workspace_id,
                         name,
                         mainfile=None,
                         importsfile=None,
                         repository_platform='github',
                         verify=True):
        """Fetch the cloudos id for a given name.

        Parameters
        ----------
        apikey : string
            Your CloudOS API key
        cloudos_url : string
            The CloudOS service url.
        resource : string
            The resource you want to fetch from. E.g.: projects.
        workspace_id : string
            The specific Cloudos workspace id.
        name : string
            The name of a CloudOS resource element.
        mainfile : string
            The name of the mainFile used by the workflow. Only used when resource == 'workflows'.
            Required for WDL pipelines as different mainFiles could be loaded for a single
            pipeline.
        importsfile : string
            The name of the importsFile used by the workflow. Optional and only used for WDL pipelines
            as different importsFiles could be loaded for a single pipeline.
        repository_platform : string
            The name of the repository platform of the workflow resides.
        verify: [bool|string]
            Whether to use SSL verification or not. Alternatively, if
            a string is passed, it will be interpreted as the path to
            the SSL certificate file.

        Returns
        -------
        project_id : string
            The CloudOS project id for a given project name.
        """
        allowed_resources = ['projects', 'workflows']
        if resource not in allowed_resources:
            raise ValueError('Your specified resource is not supported. ' +
                             f'Use one of the following: {allowed_resources}')
        if resource == 'workflows':
            content = self.get_workflow_list(workspace_id, verify=verify)
            for element in content:
                # from the API, workflow names are coming with newline characters
                element_name = element["name"].strip()
                if (element_name == name and element["workflowType"] == "docker" and
                        not element["archived"]["status"]):
                    return element["_id"]  # no mainfile or importsfile
                if (element_name == name and
                        element["repository"]["platform"] == repository_platform and
                        not element["archived"]["status"]):
                    if mainfile is None:
                        return element["_id"]
                    elif element["mainFile"] == mainfile:
                        if importsfile is None and "importsFile" not in element.keys():
                            return element["_id"]
                        elif "importsFile" in element.keys() and element["importsFile"] == importsfile:
                            return element["_id"]
        elif resource == 'projects':
            content = self.get_project_list(workspace_id, verify=verify)
            # New API projects endpoint spec
            from pprint import pprint
            for element in content:
                if element["name"] == name:
                    return element["_id"]
        if mainfile is not None:
            raise ValueError(f'[ERROR] A workflow named \'{name}\' with a mainFile \'{mainfile}\'' +
                             f' and an importsFile \'{importsfile}\' was not found')
        else:
            raise ValueError(f'[ERROR] No {name} element in {resource} was found')

    def convert_nextflow_to_json(self,
                                 job_config,
                                 parameter,
                                 array_parameter,
                                 array_file_header,
                                 is_module,
                                 example_parameters,
                                 git_commit,
                                 git_tag,
                                 git_branch,
                                 project_id,
                                 workflow_id,
                                 job_name,
                                 resumable,
                                 save_logs,
                                 batch,
                                 job_queue_id,
                                 nextflow_profile,
                                 nextflow_version,
                                 instance_type,
                                 instance_disk,
                                 storage_mode,
                                 lustre_size,
                                 execution_platform,
                                 hpc_id,
                                 workflow_type,
                                 cromwell_id,
                                 azure_worker_instance_type,
                                 azure_worker_instance_disk,
                                 azure_worker_instance_spot,
                                 cost_limit,
                                 use_mountpoints,
                                 docker_login,
                                 command,
                                 cpus,
                                 memory,
                                 resume_dir=None):
        """Converts a nextflow.config file into a json formatted dict.

        Parameters
        ----------
        job_config : string
            Path to a nextflow.config file with parameters scope.
        parameter : tuple
            Tuple of strings indicating the parameters to pass to the pipeline call.
            They are in the following form: ('param1=param1val', 'param2=param2val', ...)
        array_parameter : tuple
            Tuple of strings indicating the parameters to pass to the pipeline call
            for array jobs. They are in the following form: ('param1=param1val', 'param2=param2val', ...)
        array_file_header : string
            The header of the file containing the array parameters. It is used to
            add the necessary column index for array file columns.
        is_module : bool
            Whether the job is a module or not. If True, the job will be
            submitted as a module.
        example_parameters : list
            A list of dicts, with the parameters required for the API request in JSON format.
            It is typically used to run curated pipelines using the already available
            example parameters.
        git_commit : string
            The git commit hash of the pipeline to use. Equivalent to -r
            option in Nextflow. If not specified, the last commit of the
            default branch will be used.
        git_tag : string
            The tag of the pipeline to use. If not specified, the last
            commit of the default branch will be used.
        git_branch : string
            The branch of the pipeline to use. If not specified, the last
            commit of the default branch will be used.
        project_id : string
            The CloudOS project id for a given project name.
        workflow_id : string
            The CloudOS workflow id for a given workflow_name.
        job_name : string.
            The name to assign to the job.
        resumable: bool
            Whether to create a resumable job or not.
        save_logs : bool
            Whether to save job logs or not.
        batch: bool
            Whether to create an AWS batch job or not.
        job_queue_id : string
            Job queue Id to use in the batch job.
        nextflow_profile: string
            A comma separated string with the profiles to be used.
        nextflow_version: string
            Nextflow version to use when executing the workflow in CloudOS.
        instance_type : string
            Name of the instance type to be used for the job master node, for example for AWS EC2 c5.xlarge
        instance_disk : int
            The disk space of the master node instance, in GB.
        storage_mode : string
            Either 'lustre' or 'regular'. Indicates if the user wants to select regular
            or lustre storage.
        lustre_size : int
            The lustre storage to be used when --storage-mode=lustre, in GB. It should be 1200 or
            a multiple of it.
        execution_platform : string ['aws'|'azure'|'hpc']
            The execution platform implemented in your CloudOS.
        hpc_id : string
            The ID of your HPC in CloudOS.
        workflow_type : str
            The type of workflow to run. It could be 'nextflow', 'wdl' or 'docker'.
        cromwell_id : str
            Cromwell server ID.
        azure_worker_instance_type: str
            The worker node instance type to be used in azure.
        azure_worker_instance_disk: int
            The disk size in GB for the worker node to be used in azure.
        azure_worker_instance_spot: bool
            Whether the azure worker nodes have to be spot instances or not.
        cost_limit : float
            Job cost limit. -1 means no cost limit.
        use_mountpoints : bool
            Whether to use or not AWS S3 mountpoint for quicker file staging.
        docker_login : bool
            Whether to use private docker images, provided the users have linked their docker.io accounts.
        command : string
            The command to run in bash jobs.
        cpus : int
            The number of CPUs to use for the bash jobs task's master node.
        memory : int
            The amount of memory, in GB, to use for the bash job task's master node.
        resume_dir : str
            If specified, the job will be resumed using this argument as working directory.


        Returns
        -------
        params : dict
            A JSON formatted dict.
        """
        workflow_params = []
        if workflow_type == 'wdl':
            # This is required as non-resumable jobs fails always using WDL workflows.
            resumable = True
        if (
            nextflow_profile is None and
            job_config is None and
            len(parameter) == 0 and
            len(example_parameters) == 0
        ):
            raise ValueError('No --job-config, --nextflow_profile, --parameter or ' +
                             '--example_parameters were specified,' +
                             '  please use at least one of these options.')
        if workflow_type == 'wdl' and job_config is None and len(parameter) == 0:
            raise ValueError('No --job-config or --parameter were provided. At least one of ' +
                             'these are required for WDL workflows.')
        if workflow_type == 'docker' and len(parameter) == 0:
            raise ValueError('No --parameter were provided. At least one of ' +
                             'these are required for bash workflows.')
        if job_config is not None:
            with open(job_config, 'r') as p:
                reading = False
                for p_l in p:
                    if 'params' in p_l.lower():
                        reading = True
                    else:
                        if reading:
                            if workflow_type == 'wdl':
                                p_l_strip = p_l.strip().replace(
                                    ' ', '')
                            else:
                                p_l_strip = p_l.strip().replace(
                                    ' ', '').replace('\"', '').replace('\'', '')
                            if len(p_l_strip) == 0:
                                continue
                            elif p_l_strip[0] == '/' or p_l_strip[0] == '#':
                                continue
                            elif p_l_strip == '}':
                                reading = False
                            else:
                                p_list = p_l_strip.split('=')
                                p_name = p_list[0]
                                p_value = '='.join(p_list[1:])
                                if len(p_list) < 2:
                                    raise ValueError('Please, specify your ' +
                                                     'parameters in ' +
                                                     f'{job_config} using ' +
                                                     'the \'=\' as spacer. ' +
                                                     'E.g: name = my_name')
                                elif workflow_type == 'wdl':
                                    param = {"prefix": "",
                                             "name": p_name,
                                             "parameterKind": "textValue",
                                             "textValue": p_value}
                                    workflow_params.append(param)
                                else:
                                    param = {"prefix": "--",
                                             "name": p_name,
                                             "parameterKind": "textValue",
                                             "textValue": p_value}
                                    workflow_params.append(param)
            if len(workflow_params) == 0:
                raise ValueError(f'The {job_config} file did not contain any ' +
                                 'valid parameter')

        # array file specific parameters (from --array-parameter)
        if array_parameter is not None and len(array_parameter) > 0:
            ap_param = Job.split_array_file_params(array_parameter, workflow_type, array_file_header)
            workflow_params.append(ap_param)

        # general parameters (from --parameter)
        if len(parameter) > 0:
            for p in parameter:
                p_split = p.split('=')
                if len(p_split) < 2:
                    raise ValueError('Please, specify -p / --parameter using a single \'=\' ' +
                                     'as spacer. E.g: input=value')
                p_name = p_split[0]
                p_value = '='.join(p_split[1:])
                if workflow_type == 'docker':
                    # will differentiate between text, data items and glob patterns
                    workflow_params.append(self.docker_workflow_param_processing(p, self.project_name))
                elif workflow_type == 'wdl':
                    param = {"prefix": "",
                             "name": p_name,
                             "parameterKind": "textValue",
                             "textValue": p_value}
                    workflow_params.append(param)
                else:
                    param = {"prefix": "--",
                             "name": p_name,
                             "parameterKind": "textValue",
                             "textValue": p_value}
                    workflow_params.append(param)
            if len(workflow_params) == 0:
                raise ValueError(f'The provided parameters are not valid: {parameter}')
        if len(example_parameters) > 0:
            for example_param in example_parameters:
                workflow_params.append(example_param)
        if storage_mode == "lustre":
            print('\n[WARNING] Lustre storage has been selected. Please, be sure that this kind of ' +
                  'storage is available in your CloudOS workspace.\n')
            if lustre_size % 1200:
                raise ValueError('Please, specify a lustre storage size of 1200 or a multiple of it. ' +
                                 f'{lustre_size} is not a valid number.')
        if storage_mode not in ['lustre', 'regular']:
            raise ValueError('Please, use either \'lustre\' or \'regular\' for --storage-mode ' +
                             f'{storage_mode} is not allowed')
        params = {
            "parameters": workflow_params,
            "project": project_id,
            "workflow": workflow_id,
            "name": job_name,
            "resumable": resumable,
            "saveProcessLogs": save_logs,
            "executionPlatform": execution_platform,
            "hpc": hpc_id,
            "storageSizeInGb": instance_disk,
            "execution": {
                "computeCostLimit": cost_limit,
                "optim": "test"
            },
            "lusterFsxStorageSizeInGb": lustre_size,
            "storageMode": storage_mode,
            "instanceType": instance_type,
            "usesFusionFileSystem": use_mountpoints
        }
        if workflow_type != 'docker':
            params["nextflowVersion"] = nextflow_version
        if execution_platform != 'hpc':
            params['masterInstance'] = {
                "requestedInstance": {
                    "type": instance_type
                }
            }
            params['batch'] = {
                "enabled": batch
            }
        if job_queue_id is not None:
            params['batch'] = {
                "dockerLogin": docker_login,
                "enabled": batch,
                "jobQueue": job_queue_id
            }
        if execution_platform == 'azure' and not is_module:
            params['azureBatch'] = {
                "vmType": azure_worker_instance_type,
                "spot": azure_worker_instance_spot,
                "diskSizeInGb": azure_worker_instance_disk
            }
        if workflow_type == 'docker':
            params = params | command  # add command to params as dict (python 3.9+)
            params["resourceRequirements"] = {
                "cpu": cpus,
                "ram": memory
            }
        if workflow_type == 'wdl':
            params['cromwellCloudResources'] = cromwell_id
        git_flag = [x is not None for x in [git_tag, git_commit, git_branch]]
        if sum(git_flag) > 1:
            raise ValueError('Please, specify none or only one of --git-tag, ' +
                             '--git-branch or --git-commit options.')
        elif sum(git_flag) == 1:
            revision_type = 'tag' if git_tag is not None else 'commit' if git_commit is not None else 'branch'
            params['revision'] = {
                "revisionType": revision_type,
                "tag": git_tag,
                "commit": git_commit,
                "branch": git_branch
            }
        if nextflow_profile is not None:
            params['profile'] = nextflow_profile
        if resume_dir:
            params["resumeWorkDir"] = resume_dir
        return params

    def send_job(self,
                 job_config=None,
                 project_id='',
                 parameter=(),
                 array_parameter=(),
                 array_file_header=None,
                 is_module=False,
                 example_parameters=[],
                 git_commit=None,
                 git_tag=None,
                 git_branch=None,
                 job_name='new_job',
                 resumable=False,
                 save_logs=True,
                 batch=True,
                 job_queue_id=None,
                 nextflow_profile=None,
                 nextflow_version='22.10.8',
                 instance_type='c5.xlarge',
                 instance_disk=500,
                 storage_mode='regular',
                 lustre_size=1200,
                 execution_platform='aws',
                 hpc_id=None,
                 workflow_type='nextflow',
                 cromwell_id=None,
                 azure_worker_instance_type='Standard_D4as_v4',
                 azure_worker_instance_disk=100,
                 azure_worker_instance_spot=False,
                 cost_limit=30.0,
                 use_mountpoints=False,
                 docker_login=False,
                 verify=True,
                 command=None,
                 cpus=1,
                 memory=4,
                 resume_job_work_dir=''):
        """Send a job to CloudOS.

        Parameters
        ----------
        job_config : string
            Path to a nextflow.config file with parameters scope.
        project_id : str
            Project ID where the job will be launched.
        parameter : tuple
            Tuple of strings indicating the parameters to pass to the pipeline call.
            They are in the following form: ('param1=param1val', 'param2=param2val', ...)
        array_parameter : tuple
            Tuple of strings indicating the parameters to pass to the pipeline call
            for array jobs. They are in the following form: ('param1=param1val', 'param2=param2val', ...)
        array_file_header : string
            The header of the file containing the array parameters. It is used to
            add the necessary column index for array file columns.
        example_parameters : list
            A list of dicts, with the parameters required for the API request in JSON format.
            It is typically used to run curated pipelines using the already available
            example parameters.
        git_commit : string
            The git commit hash of the pipeline to use. Equivalent to -r
            option in Nextflow. If not specified, the last commit of the
            default branch will be used.
        git_tag : string
            The tag of the pipeline to use. If not specified, the last
            commit of the default branch will be used.
        git_branch : string
            The branch of the pipeline to use. If not specified, the last
            commit of the default branch will be used.
        job_name : string
            The name to assign to the job.
        resumable : bool
            Whether to create a resumable job or not.
        save_logs : bool
            Whether to save job logs or not.
        batch: bool
            Whether to create an AWS batch job or not.
        job_queue_id : string
            Job queue Id to use in the batch job.
        nextflow_profile: string
            A comma separated string with the profiles to be used.
        nextflow_version: string
            Nextflow version to use when executing the workflow in CloudOS.
        instance_type : string
            Name of the instance type to be used for the job master node, for example for AWS EC2 c5.xlarge
        instance_disk : int
            The disk space of the master node instance, in GB.
        storage_mode : string
            Either 'lustre' or 'regular'. Indicates if the user wants to select regular
            or lustre storage.
        lustre_size : int
            The lustre storage to be used when --storage-mode=lustre, in GB. It should be 1200 or
            a multiple of it.
        execution_platform : string ['aws'|'azure'|'hpc']
            The execution platform implemented in your CloudOS.
        hpc_id : string
            The ID of your HPC in CloudOS.
        workflow_type : str
            The type of workflow to run. It could be 'nextflow', 'wdl' or 'docker'.
        cromwell_id : str
            Cromwell server ID.
        azure_worker_instance_type: str
            The worker node instance type to be used in azure.
        azure_worker_instance_disk: int
            The disk size in GB for the worker node to be used in azure.
        azure_worker_instance_spot: bool
            Whether the azure worker nodes have to be spot instances or not.
        cost_limit : float
            Job cost limit. -1 means no cost limit.
        use_mountpoints : bool
            Whether to use or not AWS S3 mountpoint for quicker file staging.
        docker_login : bool
            Whether to use private docker images, provided the users have linked their docker.io accounts.
        verify : [bool|string]
            Whether to use SSL verification or not. Alternatively, if
            a string is passed, it will be interpreted as the path to
            the SSL certificate file.
        command : string
            The command to run in bash jobs.
        cpus : int
            The number of CPUs to use for the bash jobs task's master node.
        memory : int
            The amount of memory, in GB, to use for the bash job task's master node.
        resume_job_work_dir : str
            In case sending a resumed job, this is the resume work directory.

        Returns
        -------
        j_id : string
            The CloudOS job id of the job just launched.
        """
        apikey = self.apikey
        cloudos_url = self.cloudos_url
        workspace_id = self.workspace_id
        workflow_id = self.workflow_id
        project_id = project_id or self.project_id
        # Prepare api request for CloudOS to run a job
        headers = {
            "Content-type": "application/json",
            "apikey": apikey
        }
        params = self.convert_nextflow_to_json(job_config,
                                               parameter,
                                               array_parameter,
                                               array_file_header,
                                               is_module,
                                               example_parameters,
                                               git_commit,
                                               git_tag,
                                               git_branch,
                                               project_id,
                                               workflow_id,
                                               job_name,
                                               resumable,
                                               save_logs,
                                               batch,
                                               job_queue_id,
                                               nextflow_profile,
                                               nextflow_version,
                                               instance_type,
                                               instance_disk,
                                               storage_mode,
                                               lustre_size,
                                               execution_platform,
                                               hpc_id,
                                               workflow_type,
                                               cromwell_id,
                                               azure_worker_instance_type,
                                               azure_worker_instance_disk,
                                               azure_worker_instance_spot,
                                               cost_limit,
                                               use_mountpoints,
                                               docker_login,
                                               command=command,
                                               cpus=cpus,
                                               memory=memory,
                                               resume_dir=resume_job_work_dir)

        r = retry_requests_post("{}/api/v2/jobs?teamId={}".format(cloudos_url,
                                                                  workspace_id),
                                data=json.dumps(params), headers=headers, verify=verify)
        if r.status_code >= 400:
            raise BadRequestException(r)
        j_id = json.loads(r.content)["jobId"]
        print('\tJob successfully launched to CloudOS, please check the ' +
              f'following link: {cloudos_url}/app/advanced-analytics/analyses/{j_id}')
        return j_id

    def check_branch(
        self,
        workspace_id,
        git_platform,
        repository_id,
        repository_owner,
        workflow_owner_id,
        branch,
        verify,
    ):
        """
        Checks if a given branch exists in a target repository.
        :param workspace_id: CloudOS workspace ID.
        :param git_platform: Repository platform (Github, Gitlab).
        :param repository ID: Repository ID.
        :param repository owner: Owner of repository.
        :param workflow_owner_id: Workflow owner ID.
        :param branch: Branch to check.
        :param verify: SSL verification option.
        :return: bool
        """
        params = {
            "teamId": workspace_id,
            "repositoryIdentifier": repository_id,
            "owner": repository_owner,
            "workflowOwnerId": workflow_owner_id,
            "branchName": branch,
        }
        headers = {"Content-type": "application/json", "apikey": self.apikey}
        branches_url = f"{self.cloudos_url}/api/v1/git/{git_platform}/getBranches/"
        branches_r = retry_requests_get(
            branches_url, headers=headers, params=params, verify=verify
        )

        cloud_os_request_error(branches_r)
        branches_d = branches_r.json()

        return bool(branches_d["branches"])

    def check_commit(
        self,
        workspace_id,
        git_platform,
        repository_id,
        repository_owner,
        workflow_owner_id,
        commit,
        verify,
    ):
        """
        Checks if a given commit exists in a repository.
        :param workspace_id: Workspace ID.
        :param git_platform: Git platform (Github, Gitlab).
        :param repository_owner: Repository owner.
        :param workflow_owner_id: Workflow owner ID.
        :param commit: Commit to be checked.
        :verify: SSL verification option.
        """
        params = {
            "teamId": workspace_id,
            "repositoryIdentifier": repository_id,
            "owner": repository_owner,
            "workflowOwnerId": workflow_owner_id,
            "commitName": commit,
        }
        headers = {"Content-type": "application/json", "apikey": self.apikey}
        commits_url = f"{self.cloudos_url}/api/v1/git/{git_platform}/getCommits/"
        commits_r = retry_requests_get(
            commits_url, headers=headers, params=params, verify=verify
        )

        cloud_os_request_error(commits_r)
        commits_d = commits_r.json()
        n_commits = len(commits_d["commits"])
        if n_commits > 1:
            raise ValueError(
                f"Provided commit {commit} matched more than one commit in the repository. Please provide a longer commit string."
            )
        return bool(commits_d["commits"])

    def check_profile(self, workflow_id, commit, workspace_id, profile, verify):
        """
        Checks if a Nextflow profile exists in a Workflow repository.
        :param workflow_id: Workflow ID.
        :param commit: Current commit of the repository.
        :param workspace_id: Workspace ID.
        :param profile: Profile to be checked.
        :param verify: SSL verification option.
        :return bool:
        """
        headers = {"apikey": self.apikey}
        params = {
            "teamId": workspace_id,
            "workflowId": workflow_id,
            "revisionHash": commit,
        }
        profile_url = f"{self.cloudos_url}/api/v2/workflows/parsers/nf-config-profiles"
        profile_r = retry_requests_get(
            profile_url, params=params, headers=headers, verify=verify
        )

        cloud_os_request_error(profile_r)
        profile_d = profile_r.json()

        return profile in profile_d

    def check_project(self, workspace_id, project, verify):
        """
        Check if a CloudOS project exists.
        :param workspace_id: Workspace ID.
        :param project: Project name.
        :verify: SSL verification option.
        """
        headers = {"apikey": self.apikey}
        params = {"teamId": workspace_id, "search": project}
        project_url = f"{self.cloudos_url}/api/v2/projects"
        project_r = retry_requests_get(
            project_url, params=params, headers=headers, verify=verify
        )

        cloud_os_request_error(project_r)
        project_d = project_r.json()
        if project_d["total"] == 1:
            return True, project_d["projects"][0]["_id"]
        if project_d["total"] > 1:
            raise ValueError(
                f"Project {project} is not unique. Please provide a unique project name."
            )
        return False, None

    def clone_or_resume_job(
        self,
        job_id,
        job_config=None,
        branch="",
        commit="",
        git_tag=None,
        profile="",
        name="",
        parameters=None,
        is_module=False,
        example_parameters=[],
        cost_limit=0.0,
        project="",
        instance_type="",
        resumable=None,
        save_logs=None,
        batch=None,
        job_queue_id=None,
        use_mountpoints=None,
        nextflow_version="",
        execution_platform=None,
        instance_disk=0,
        storage_mode="",
        lustre_size=1200,
        hpc_id=None,
        workflow_type="nextflow",
        cromwell_id=None,
        azure_worker_instance_type="Standard_D4as_v4",
        azure_worker_instance_disk=100,
        azure_worker_instance_spot=False,
        docker_login=False,
        verify=True,
        cpus=1,
        memory=4,
        resume_job=False,
    ):
        headers = {"apikey": self.apikey}

        params = {"teamId": self.workspace_id}
        job_payload_url = f"{self.cloudos_url}/api/v1/jobs/{job_id}/request-payload"
        job_payload_r = retry_requests_get(
            job_payload_url, headers=headers, params=params, verify=verify
        )
        # if request-payload is not available, use the raw job response
        # Some further parsing is required
        if job_payload_r.status_code == 404:
            job_info_url = f"{self.cloudos_url}/api/v1/jobs/{job_id}"
            job_info_r  = retry_requests_get(job_info_url, params=params, headers=headers)
            cloud_os_request_error(job_info_r)
            job_payload_d = job_info_r.json()
            job_payload_d["resumable"] = "resumeWorkDir" in job_payload_r
            job_payload_d["executionPlatform"] = execution_platform
            used_revision_type = job_payload_d["revision"]["revisionType"]
            for rev_type in [x for x in ("branch", "tag", "commit")]:
                if rev_type != used_revision_type:
                    job_payload_d["revision"][rev_type] = None
        else:
            cloud_os_request_error(job_payload_r)
            job_payload_d = job_payload_r.json()

        job_data_url = f"{self.cloudos_url}/api/v1/jobs/{job_id}"
        job_data_r = retry_requests_get(
            job_data_url, headers=headers, params=params, verify=verify
        )
        cloud_os_request_error(job_data_r)
        job_data_d = job_data_r.json()
        self.workflow_name = job_data_d["name"]
        # This if statement is the only difference between the
        # clone and resume funcionality
        if resume_job:
            if not job_payload_d["resumable"]:
                raise CantResumeNonResumableJob(job_id)
            status = job_data_d["status"]
            if status == "running":
                raise CantResumeRunningJob(job_id)
            new_resume_work_dir = job_data_d["resumeWorkDir"]
        else:
            new_resume_work_dir = ""
        specified_revision = sum([bool(x) for x in [commit, branch, git_tag]])
        if specified_revision > 1:
            raise ValueError("Only one of commit, branch, or tag should be specified")
        if not job_payload_d["revision"]:
            job_payload_d["revision"] = job_data_d["revision"]

        new_branch = (
            job_payload_d["revision"]["branch"] if not any([git_tag, commit]) else None
        )
        repository_data = job_data_d["workflow"]["repository"]
        repository_id = repository_data["repositoryId"]
        repository_owner_data = repository_data["owner"]
        repository_owner = repository_owner_data["login"]
        worflow_owner_id = repository_owner_data["id"]
        repository_platform = repository_data["platform"]
        new_commit = None
        if branch:
            branch_exists = self.check_branch(
                self.workspace_id,
                repository_platform,
                repository_id,
                repository_owner,
                worflow_owner_id,
                branch,
                verify=verify,
            )
            if not branch_exists:
                raise ValueError(f"Branch {branch} does not exist in the repository.")
        if commit:
            commit_exists = self.check_commit(
                self.workspace_id,
                repository_platform,
                repository_id,
                repository_owner,
                worflow_owner_id,
                commit,
                verify=verify,
            )
            if not commit_exists:
                raise ValueError(f"Commit {commit} does not exist in the repository.")
            new_commit = commit
        if git_tag and not any([commit, branch]):
            new_git_tag = git_tag
        else:
            new_git_tag = job_payload_d["revision"].get("tag", None)
        # commits, tags and branches can come as "" from the payload, but they need to be None
        new_git_tag = None if new_git_tag == "" else new_git_tag
        new_commit = None if new_commit == "" else new_commit
        new_branch = None if new_branch == "" else new_branch
        new_profile = job_payload_d.get("profile", None)
        if profile:
            workflow_id = job_payload_d["workflow"]
            profile_exists = self.check_profile(
                workflow_id, new_commit, self.workspace_id, profile, verify=verify
            )
            if not profile_exists:
                raise ValueError(
                    f"the profile {profile} does not exist in the commit {new_commit} of the workflow."
                )
            new_profile = profile

        new_project = job_payload_d["project"]
        if project:
            project_exists, new_project = self.check_project(
                self.workspace_id, project, verify=verify
            )
            if not project_exists:
                raise ValueError(f"The project {project} does not exist.")

        new_parameters = [
            f"{x['name']}={x['textValue']}" for x in job_payload_d["parameters"]
        ]
        if parameters:
            old_params_names = [x.split("=")[0] for x in new_parameters]
            for new_param in parameters:
                if new_param.split("=")[0] not in old_params_names:
                    new_parameters.append(new_param)

        new_save_logs = (
            job_payload_d["saveProcessLogs"] if save_logs is None else save_logs
        )
        new_use_mountpoints = (
            job_payload_d["usesFusionFileSystem"]
            if use_mountpoints is None
            else use_mountpoints
        )
        # Assemble payload for cloning
        new_name = name or job_payload_d["name"]
        new_is_module = is_module
        new_example_parameters = example_parameters
        new_instance_type = (
            instance_type
            or job_payload_d["masterInstance"]["requestedInstance"]["type"]
        )
        if not cost_limit:
            cost_limit = -1
        new_cost_limit = cost_limit or job_payload_d["execution"]["computeCostLimit"]
        new_resumable = resumable or job_payload_d["resumable"]
        new_job_config = job_config
        new_batch = batch or job_payload_d["batch"]["enabled"]
        new_job_queue_id = job_queue_id
        new_nextflow_version = nextflow_version or job_payload_d["nextflowVersion"]
        new_instance_disk = instance_disk or job_payload_d["storageSizeInGb"]
        new_storage_mode = storage_mode or job_payload_d["storageMode"]
        new_lustre_size = lustre_size
        new_execution_platform = job_payload_d["executionPlatform"]
        new_hpc_id = hpc_id
        new_workflow_type = workflow_type
        new_cromwell_id = cromwell_id
        new_azure_worker_instance_type = azure_worker_instance_type
        new_azure_worker_instance_disk = azure_worker_instance_disk
        new_azure_worker_instance_spot = azure_worker_instance_spot
        new_docker_login = docker_login
        new_cpus = cpus
        new_memory = memory
        new_job_id = self.send_job(
            job_config=new_job_config,
            project_id=new_project,
            parameter=new_parameters,
            is_module=new_is_module,
            example_parameters=new_example_parameters,
            git_commit=new_commit,
            git_tag=new_git_tag,
            git_branch=new_branch,
            job_name=new_name,
            resumable=new_resumable,
            save_logs=new_save_logs,
            batch=new_batch,
            job_queue_id=new_job_queue_id,
            nextflow_profile=new_profile,
            nextflow_version=new_nextflow_version,
            instance_type=new_instance_type,
            instance_disk=new_instance_disk,
            storage_mode=new_storage_mode,
            lustre_size=new_lustre_size,
            execution_platform=new_execution_platform,
            hpc_id=new_hpc_id,
            workflow_type=new_workflow_type,
            cromwell_id=new_cromwell_id,
            azure_worker_instance_type=new_azure_worker_instance_type,
            azure_worker_instance_disk=new_azure_worker_instance_disk,
            azure_worker_instance_spot=new_azure_worker_instance_spot,
            cost_limit=new_cost_limit,
            use_mountpoints=new_use_mountpoints,
            docker_login=new_docker_login,
            verify=verify,
            cpus=new_cpus,
            memory=new_memory,
            resume_job_work_dir=new_resume_work_dir,
        )
        return new_job_id

    def retrieve_cols_from_array_file(self, array_file, ds, separator, verify_ssl):
        """
        Retrieve metadata for columns from an array file stored in a directory.

        This method fetches the metadata of an array file by interacting with a directory service
        and making an API call to retrieve the file's metadata.

        Parameters
        ----------
        array_file : str
            The path to the array file whose metadata is to be retrieved.
        ds : object
            The directory service object used to list folder content.
        separator : str
            The separator used in the array file.
        verify_ssl : bool
            Whether to verify SSL certificates during the API request.

        Raises
        ------
        ValueError
            If the specified file is not found in the directory.
        BadRequestException
            If the API request to retrieve metadata fails with a status code >= 400.

        Returns
        -------
        Response
            The HTTP response object containing the metadata of the array file.
        """
        # Split the array_file path to get the directory and file name
        p = Path(array_file)
        directory = str(p.parent)
        file_name = p.name

        # fetch the content of the directory
        result = ds.list_folder_content(directory)

        # retrieve the S3 bucket name and object key for the specified file
        for file in result['files']:
            if file.get("name") == file_name:
                self.array_file_id = file.get("_id")
                s3_bucket_name = file.get("s3BucketName")
                s3_object_key = file.get("s3ObjectKey")
                s3_object_key_b64 = base64.b64encode(s3_object_key.encode()).decode()
                break
        else:
            raise ValueError(
                f'File "{file_name}" not found in the "{directory}" folder of the project "{self.project_name}".'
            )

        # retrieve the metadata of the array file
        headers = {
            "Content-type": "application/json",
            "apikey": self.apikey
        }
        url = (
            f"{self.cloudos_url}/api/v1/jobs/array-file/metadata"
            f"?separator={separator}"
            f"&s3BucketName={s3_bucket_name}"
            f"&s3ObjectKey={s3_object_key_b64}"
            f"&teamId={self.workspace_id}"
        )
        r = retry_requests_get(url, headers=headers, verify=verify_ssl)
        if r.status_code >= 400:
            raise BadRequestException(r)

        return r

    def setup_params_array_file(self, custom_script_path, ds_custom, command, separator):
        """
        Sets up a dictionary representing command parameters, including support for custom scripts
        and array files, to be used in job execution.

        Parameters
        ----------
        custom_script_path : str
            Path to the custom script file. If None, the command is treated as text.
        ds_custom : object
            An object providing access to folder content listing functionality.
        command : str
            The command to be executed, either as text or the name of a custom script.
        separator : str
            The separator to be used for the array file.

        Returns
        -------
        dict
            A dictionary containing the command parameters, including:
                - "command": The command name or text.
                - "customScriptFile" (optional): Details of the custom script file if provided.
                - "arrayFile": Details of the array file and its separator.
        """
        if custom_script_path is not None:
            command_path = Path(custom_script_path)
            command_dir = str(command_path.parent)
            command_name = command_path.name
            result_script = ds_custom.list_folder_content(command_dir)
            for file in result_script['files']:
                if file.get("name") == command_name:
                    custom_script_item = file.get("_id")
                    break
            # use this in case the command is in a custom script
            cmd = {
                "command": f"{command_name}",
                "customScriptFile": {
                    "dataItem": {
                        "kind": "File",
                        "item": f"{custom_script_item}"
                    }
                }
            }
        else:
            # use this for text commands
            cmd = {"command": command}

        # add array-file
        cmd = cmd | {
            "arrayFile": {
                "dataItem": {"kind": "File", "item": f"{self.array_file_id}"},
                "separator": f"{separator}"
            }
        }

        return cmd

    @staticmethod
    def split_array_file_params(array_parameter, workflow_type, array_file_header):
        """
        Splits and processes array parameters for a given workflow type and array file header.

        Parameters
        ----------
        array_parameter :   list
            A list of strings representing array parameters in the format "key=value".
        workflow_type : str
            The type of workflow, e.g., 'docker'.
        array_file_header : list
            A list of dictionaries representing the header of the array file.
            Each dictionary should contain "name" and "index" keys.

        Returns
        -------
        dict
            A dictionary containing processed parameter details, including:
                - prefix (str): The prefix for the parameter (e.g., "--" or "-").
                - name (str): The name of the parameter with leading dashes stripped.
                - parameterKind (str): The kind of parameter, set to "arrayFileColumn".
                - columnName (str): The name of the column derived from the parameter value.
                - columnIndex (int): The index of the column in the array file header.

        Raises
        ------
        ValueError
            If an array parameter does not contain a '=' character or is improperly formatted.
        """
        ap_param = dict()
        for ap in array_parameter:
            ap_split = ap.split('=')
            if len(ap_split) < 2:
                raise ValueError('Please, specify -a / --array-parameter using a single \'=\' ' +
                                'as spacer. E.g: input=value')
            ap_name = ap_split[0]
            ap_value = '='.join(ap_split[1:])
            if workflow_type == 'docker':
                ap_prefix = "--" if ap_name.startswith('--') else ("-" if ap_name.startswith('-') else '')
                ap_param = {
                    "prefix": ap_prefix,
                    "name": ap_name.lstrip('-'),
                    "parameterKind": "arrayFileColumn",
                    "columnName": ap_value,
                    "columnIndex": next((item["index"] for item in array_file_header if item["name"] == "id"), 0)
                }

        return ap_param

    def docker_workflow_param_processing(self, param, project_name):
        """
        Processes a Docker workflow parameter and determines its type and associated metadata.

        Parameters
        ----------
        param : str
            The parameter string in the format '--param_name=value'.
            It can represent a file path, a glob pattern, or a simple text value.
        project_name : str
            The name of the current project to use if no specific project is extracted from the parameter.

        Returns:
            dict: A dictionary containing the processed parameter details. The structure of the dictionary depends on the type of the parameter:
            - For glob patterns:
                {
                "name": str,          # Parameter name without leading dashes.
                "prefix": str,        # Prefix ('--' or '-') based on the parameter format.
                "globPattern": str,   # The glob pattern extracted from the parameter.
                "parameterKind": str, # Always "globPattern".
                "folder": str         # Folder ID associated with the glob pattern.
            - For file paths:
                {
                "name": str,          # Parameter name without leading dashes.
                "prefix": str,        # Prefix ('--' or '-') based on the parameter format.
                "parameterKind": str, # Always "dataItem".
                "dataItem": {
                    "kind": str,      # Always "File".
                    "item": str       # File ID associated with the file path.
            - For text values:
                {
                "name": str,          # Parameter name without leading dashes.
                "prefix": str,        # Prefix ('--' or '-') based on the parameter format.
                "parameterKind": str, # Always "textValue".
                "textValue": str      # The text value extracted from the parameter.

        Notes
        -----
        - The function uses helper methods `extract_project`, `classify_pattern`, and `get_file_or_folder_id` to process the parameter.
        - If the parameter represents a file path or glob pattern, the function retrieves the corresponding file or folder ID from the cloud workspace.
        - If the parameter does not match any specific pattern or file extension, it is treated as a simple text value.
        """

        # split '--param_name=example_test'
        # name -> '--param_name'
        # rest -> 'example_test'
        name, rest = param.split('=', 1)

        # e.g. "/Project/Subproject/file.csv", project is "Project"
        # e.g "Data/input.csv", project is '', leaving the global project name
        # e.g "-p --test=value", project is ''
        project, file_path = extract_project(rest)
        current_project = project if project != '' else project_name

        # e.g. "/Project/Subproject/file.csv"
        command_path = Path(file_path)
        command_dir = str(command_path.parent)
        command_name = command_path.name
        _, ext = os.path.splitext(command_name)
        prefix = "--" if name.startswith('--') else ("-" if name.startswith('-') else "")
        if classify_pattern(rest) in ["regex", "glob"]:
            if not (file_path.startswith('/Data') or file_path.startswith('Data')):
                raise ValueError("[ERROR] The file path inside the project must start with '/Data' or 'Data'. ")

            folder = get_file_or_folder_id(self.cloudos_url, self.apikey, self.workspace_id, current_project, self.verify, command_dir, command_name, is_file=False)
            return {
                "name": f"{name.lstrip('-')}",
                "prefix": f"{prefix}",
                'globPattern': command_name,
                "parameterKind": "globPattern",
                "folder": f"{folder}"
            }
        elif ext:
            if not (file_path.startswith('/Data') or file_path.startswith('Data')):
                raise ValueError("[ERROR] The file path inside the project must start with '/Data' or 'Data'. ")

            file = get_file_or_folder_id(self.cloudos_url, self.apikey, self.workspace_id, current_project, self.verify, command_dir, command_name, is_file=True)
            return {
                "name": f"{name.lstrip('-')}",
                "prefix": f"{prefix}",
                "parameterKind": "dataItem",
                "dataItem": {
                    "kind": "File",
                    "item": f"{file}"
                }
            }
        else:
            return {
                "name": f"{name.lstrip('-')}",
                "prefix": f"{prefix}",
                "parameterKind": "textValue",
                "textValue": f"{rest}"
            }


class JobSetup:
    def __init__(
        self,
        apikey,
        workspace_id,
        project_name,
        execution_platform="aws",
        hpc_id="",
        wdl_mainfile="",
        wdl_importsfile="",
        storage_mode="regular",
        accelerate_file_staging=False,
        repository_platform="github",
        do_not_save_logs=False,
        use_private_docker_repository=False,
        cromwell_token=None,
        disable_ssl_verification=False,
        ssl_cert=None,
        nextflow_version="22.10.8",
        cloudos_url=CLOUDOS_URL,
        workflow_name="",
        job_id="",
        job_queue=None,
        job_config=None,
        branch=None,
        commit=None,
        git_tag=None,
        nextflow_profile=None,
        name="new_job",
        parameters=None,
        cost_limit=30.0,
        resumable=False,
        instance_disk=500,
        lustre_size=1200,
        instance_type="NONE_SELECTED",
        azure_worker_instance_type="Standard_D4as_v4",
        azure_worker_instance_disk=100,
        azure_worker_instance_spot=False,
        cpus=1,
        memory=4,
        wait_completion=False,
        wait_time=3600,
        request_interval=30,
        verbose=False,
        run_type="",
    ) -> None:
        self.REQUEST_INTERVAL_CROMWELL = 30

        self.job_completed = JOB_COMPLETED
        self.aws_nextflow_latest = AWS_NEXTFLOW_LATEST
        self.azure_nextflow_latest = AZURE_NEXTFLOW_LATEST
        self.hpc_nextflow_latest = HPC_NEXTFLOW_LATEST
        self.aws_nextflow_versions = AWS_NEXTFLOW_VERSIONS
        self.azure_nextflow_versions = AZURE_NEXTFLOW_VERSIONS
        self.hpc_nextflow_versions = HPC_NEXTFLOW_VERSIONS
        self.headers = {"apikey": apikey}
        self.request_params = {"teamId": workspace_id}

        self.cloudos_url = cloudos_url
        self.apikey = apikey
        self._workflow_name = workflow_name
        self.job_config = job_config
        self.job_id = job_id
        self.branch = branch
        self.commit = commit
        self.git_tag = git_tag
        self.nextflow_profile = nextflow_profile
        self.nextflow_version = nextflow_version
        self.name = name
        self.parameters = parameters
        self.cost_limit = cost_limit
        self.resumable = resumable
        self.use_private_docker_repository = use_private_docker_repository
        self._instance_type = instance_type
        self.instance_disk = instance_disk
        self.lustre_size = lustre_size
        self.accelerate_file_staging = accelerate_file_staging
        self.azure_worker_instance_type = azure_worker_instance_type
        self.azure_worker_instance_disk = azure_worker_instance_disk
        self.azure_worker_instance_spot = azure_worker_instance_spot
        self.cpus = cpus
        self.memory = memory
        self.workspace_id = workspace_id
        self.project_name = project_name
        self.repository_platform = repository_platform
        self.cromwell_token = cromwell_token
        self.disable_ssl_verification = disable_ssl_verification
        self.ssl_cert = ssl_cert
        self.save_logs = not do_not_save_logs
        self.verify_ssl = ssl_selector(self.disable_ssl_verification, self.ssl_cert)
        self.execution_platform = (
            execution_platform if run_type == "run" else self.get_exec_platform()
        )
        self.job_queue = job_queue
        self.verbose = verbose
        self.wait_completion = wait_completion
        self.wait_time = wait_time
        self.request_interval = request_interval
        self.batch = not execution_platform == "azure" or execution_platform == "hpc"
        self.wdl_mainfile = wdl_mainfile
        self.wdl_importsfile = wdl_importsfile
        self.storage_mode = storage_mode
        self.hpc_id = hpc_id
        self.check_hpc_args()

        self.cl = Cloudos(self.cloudos_url, self.apikey, self.cromwell_token)

        if run_type != "run":
            workflow_attrs = self.get_workflow_attrs(self.job_id)
            self._workflow_name = workflow_attrs["name"]
            self.is_module = workflow_attrs["isModule"]
            self.workflow_type = workflow_attrs["workflowType"]
            self.repository_platform = self.get_repo_platform()
        else:
            self.workflow_type = self.cl.detect_workflow(
                self.workflow_name, self.workspace_id, self.verify_ssl
            )

            self.is_module = self.cl.is_module(
                self.workflow_name, self.workspace_id, self.verify_ssl
            )
        self.fix_nextflow_versions()
        self.check_module()

        if self.verbose:
            print("\t...Detecting workflow type")

        self.cromwell_id = self.cromwell_checks()

        if self.verbose:
            print("\t...Preparing objects")
        self.job = Job(
            cloudos_url=self.cloudos_url,
            apikey=self.apikey,
            cromwell_token=cromwell_token,
            workspace_id=self.workspace_id,
            project_name=self.project_name,
            workflow_name=self.workflow_name,
            repository_platform=self.repository_platform,
            verify=self.verify_ssl,
        )
        if self.verbose:
            print("\tThe following Job object was created")
            print(f"\t{str(self.job)}")
            print("\t...Sending job to CloudOS")

    @property
    def instance_type(self):
        if self._instance_type == "NONE_SELECTED":
            if self.execution_platform == "aws":
                return "c4.xlarge"
            elif self.execution_platform == "azure":
                return "Standard_D4as_v4"
            else:
                return None
        else:
            return self._instance_type

    @property
    def use_mountpoints(self):
        if self.accelerate_file_staging:
            if self.execution_platform != "aws":
                print(
                    "[Message] You have selected accelerate file staging, but this function is "
                    + "only available when execution platform is AWS. The accelerate file staging "
                    + "will not be applied"
                )
                return False
            else:
                print(
                    "[Message] Enabling AWS S3 mountpoint for accelerated file staging. "
                    + "Please, take into consideration the following:\n"
                    + "\t- It significantly reduces runtime and compute costs but may increase network costs.\n"
                    + "\t- Requires extra memory. Adjust process memory or optimise resource usage if necessary.\n"
                    + "\t- This is still a CloudOS BETA feature.\n"
                )
                return True
        else:
            return False

    @property
    def docker_login(self):
        if self.use_private_docker_repository:
            if self.is_module:
                print(
                    f'[Message] Workflow "{self.workflow_name}" is a CloudOS module. '
                    + "Option --use-private-docker-repository will be ignored."
                )
                return False
            else:
                me = self.job.get_user_info(verify=self.verify_ssl)[
                    "dockerRegistriesCredentials"
                ]
                if len(me) == 0:
                    raise Exception(
                        "User private Docker repository has been selected but your user "
                        + "credentials have not been configured yet. Please, link your "
                        + "Docker account to CloudOS before using "
                        + "--use-private-docker-repository option."
                    )
                print(
                    "[Message] Use private Docker repository has been selected. A custom job "
                    + "queue to support private Docker containers and/or Lustre FSx will be created for "
                    + "your job. The selected job queue will serve as a template."
                )
                return True
        else:
            return False

    @property
    def workflow_name(self):
        if self._workflow_name:
            return self._workflow_name
        if self.job_id:
            return self.get_workflow_attrs(self.job_id)["name"]
        else:
            raise ValueError("Workflow name or Job ID should be provided")

    def get_exec_platform(self):
        for cloud in ("aws", "azure", "gcp"):
            cloud_url = f"{self.cloudos_url}/api/v1/cloud/{cloud}"
            cloud_r = retry_requests_get(cloud_url, params=self.request_params, headers=self.headers)
            cloud_os_request_error(cloud_r)
            cloud_d = cloud_r.json()
            if cloud_d:
                return cloud
        raise ValueError("Workspace is not associated with any supported cloud provider")

    def get_repo_platform(self):
        job_url = f"{self.cloudos_url}/api/v1/jobs/{self.job_id}"
        job_r = retry_requests_get(job_url, params=self.request_params, headers=self.headers)
        cloud_os_request_error(job_r)
        job_d = job_r.json()
        return job_d["workflow"]["repository"]["platform"]

    def check_hpc_args(self):
        if self.execution_platform == "hpc":
            print("\n[Message] HPC execution platform selected")
            if self.hpc_id is None:
                raise ValueError("Please, specify your HPC ID using --hpc parameter")
            print(
                "[Message] Please, take into account that HPC execution do not support "
                + "the following parameters and all of them will be ignored:\n"
                + "\t--job-queue\n"
                + "\t--resumable | --do-not-save-logs\n"
                + "\t--instance-type | --instance-disk | --cost-limit\n"
                + "\t--storage-mode | --lustre-size\n"
                + "\t--wdl-mainfile | --wdl-importsfile | --cromwell-token\n"
            )
            self.wdl_mainfile = None
            self.wdl_importsfile = None
            self.storage_mode = "regular"
            self.save_logs = False

    def cromwell_checks(self):
        if self.execution_platform == "hpc" and self.workflow_type == "wdl":
            raise ValueError(
                f"The workflow {self.workflow_name} is a WDL workflow. "
                + "WDL is not supported on HPC execution platform."
            )
        if self.workflow_type == "wdl":
            print("[Message] WDL workflow detected")
            if self.wdl_mainfile is None:
                raise ValueError(
                    "Please, specify WDL mainFile using --wdl-mainfile <mainFile>."
                )
            c_status = self.cl.get_cromwell_status(self.workspace_id, self.verify_ssl)
            c_status_h = json.loads(c_status.content)["status"]
            print(f"\tCurrent Cromwell server status is: {c_status_h}\n")
            if c_status_h == "Stopped":
                print("\tStarting Cromwell server...\n")
                self.cl.cromwell_switch(self.workspace_id, "restart", self.verify_ssl)
                elapsed = 0
                while elapsed < 300 and c_status_h != "Running":
                    c_status_old = c_status_h
                    time.sleep(self.REQUEST_INTERVAL_CROMWELL)
                    elapsed += self.REQUEST_INTERVAL_CROMWELL
                    c_status = self.cl.get_cromwell_status(
                        self.workspace_id, self.verify_ssl
                    )
                    c_status_h = json.loads(c_status.content)["status"]
                    if c_status_h != c_status_old:
                        print(f"\tCurrent Cromwell server status is: {c_status_h}\n")
            if c_status_h != "Running":
                raise Exception("Cromwell server did not restarted properly.")
            cromwell_id = json.loads(c_status.content)["_id"]
            print(
                "\t"
                + ("*" * 80)
                + "\n"
                + "\t[WARNING] Cromwell server is now running. Please, remember to stop it when "
                + "your\n"
                + "\tjob finishes. You can use the following command:\n"
                + "\tcloudos cromwell stop \\\n"
                + "\t\t--cromwell-token $CROMWELL_TOKEN \\\n"
                + f"\t\t--cloudos-url {self.cloudos_url} \\\n"
                + f"\t\t--workspace-id {self.workspace_id}\n"
                + "\t"
                + ("*" * 80)
                + "\n"
            )
        else:
            cromwell_id = None
        return cromwell_id

    def check_module(self):
        if self.is_module:
            if self.job_queue is not None:
                print(
                    f'[Message] Ignoring job queue "{self.job_queue}" for '
                    + f'Platform Workflow "{self.workflow_name}". Platform Workflows '
                    + "use their own predetermined queues."
                )
            self.job_queue_id = None
            if self.nextflow_version != "22.10.8" and self.execution_platform != "azure":
                print(
                    f"[Message] The selected worflow '{self.workflow_name}' "
                    + "is a CloudOS module. CloudOS modules only work with "
                    + "Nextflow version 22.10.8. Switching to use 22.10.8"
                )
            self.nextflow_version = "22.10.8"
            if self.execution_platform == "azure":
                print(
                    f"[Message] The selected worflow '{self.workflow_name}' "
                    + "is a CloudOS module. For these workflows, worker nodes "
                    + "are managed internally. For this reason, the options "
                    + "azure-worker-instance-type, azure-worker-instance-disk and "
                    + "azure-worker-instance-spot are not taking effect."
                )
                self.nextflow_version = "22.11.1-edge"
        else:
            queue = Queue(
                cloudos_url=self.cloudos_url,
                apikey=self.apikey,
                cromwell_token=self.cromwell_token,
                workspace_id=self.workspace_id,
                verify=self.verify_ssl,
            )
            self.job_queue_id = queue.fetch_job_queue_id(
                workflow_type=self.workflow_type,
                batch=self.batch,
                job_queue=self.job_queue,
            )

    def fix_nextflow_versions(self):
        if self.nextflow_version == "latest":
            if self.execution_platform == "aws":
                self.nextflow_version = self.aws_nextflow_latest
            elif self.execution_platform == "azure":
                self.nextflow_version = self.azure_nextflow_latest
            else:
                self.nextflow_version = self.hpc_nextflow_latest
            print(
                "[Message] You have specified Nextflow version 'latest' for execution platform "
                + f"'{self.execution_platform}'. The workflow will use the "
                + f"latest version available on CloudOS: {self.nextflow_version}."
            )
        if self.execution_platform == "aws":
            if self.nextflow_version not in self.aws_nextflow_versions:
                print(
                    "[Message] For execution platform 'aws', the workflow will use the default "
                    + "'22.10.8' version on CloudOS."
                )
                self.nextflow_version = "22.10.8"
        if self.execution_platform == "azure":
            if self.nextflow_version not in self.azure_nextflow_versions:
                print(
                    "[Message] For execution platform 'azure', the workflow will use the '22.11.1-edge' "
                    + "version on CloudOS."
                )
                self.nextflow_version = "22.11.1-edge"
        if self.execution_platform == "hpc":
            if self.nextflow_version not in self.hpc_nextflow_versions:
                print(
                    "[Message] For execution platform 'hpc', the workflow will use the '22.10.8' version on CloudOS."
                )
                self.nextflow_version = "22.10.8"
        if (
            self.nextflow_version != "22.10.8"
            and self.nextflow_version != "22.11.1-edge"
        ):
            print(
                f"[Warning] You have specified Nextflow version {self.nextflow_version}. This version requires the pipeline "
                + "to be written in DSL2 and does not support DSL1."
            )

    def get_workflow_attrs(self, job_id):
        job_url = f"{self.cloudos_url}/api/v1/jobs/{job_id}"
        job_req = retry_requests_get(
            job_url, headers=self.headers, params=self.request_params
        )
        cloud_os_request_error(job_req)
        job_d = job_req.json()
        return job_d["workflow"]

    def run(self):
        if self.job_id:
            raise ValueError("Job ID should only be specified when resuming jobs.")

        j_id = self.job.send_job(
            job_config=self.job_config,
            parameter=self.parameters,
            is_module=self.is_module,
            git_commit=self.commit,
            git_tag=self.git_tag,
            git_branch=self.branch,
            job_name=self.name,
            resumable=self.resumable,
            save_logs=self.save_logs,
            batch=self.batch,
            job_queue_id=self.job_queue_id,
            nextflow_profile=self.nextflow_profile,
            nextflow_version=self.nextflow_version,
            instance_type=self.instance_type,
            instance_disk=self.instance_disk,
            storage_mode=self.storage_mode,
            lustre_size=self.lustre_size,
            execution_platform=self.execution_platform,
            hpc_id=self.hpc_id,
            workflow_type=self.workflow_type,
            cromwell_id=self.cromwell_id,
            azure_worker_instance_type=self.azure_worker_instance_type,
            azure_worker_instance_disk=self.azure_worker_instance_disk,
            azure_worker_instance_spot=self.azure_worker_instance_spot,
            cost_limit=self.cost_limit,
            use_mountpoints=self.use_mountpoints,
            docker_login=self.docker_login,
            verify=self.verify_ssl,
        )
        print(f"\tYour assigned job id is: {j_id}\n")
        self.job_id = j_id
        self.wait()

    def run_again(self, resume=False):
        job_id = self.job.clone_or_resume_job(
            job_id=self.job_id,
            job_config=self.job_config,
            branch=self.branch,
            commit=self.commit,
            git_tag=self.git_tag,
            profile=self.nextflow_profile,
            name=self.name,
            parameters=self.parameters,
            is_module=self.is_module,
            cost_limit=self.cost_limit,
            project=self.project_name,
            instance_type=self.instance_type,
            resumable=self.resumable,
            save_logs=self.save_logs,
            batch=self.batch,
            job_queue_id=self.job_queue_id,
            use_mountpoints=self.use_mountpoints,
            nextflow_version=self.nextflow_version,
            execution_platform=self.execution_platform,
            instance_disk=self.instance_disk,
            storage_mode=self.storage_mode,
            lustre_size=self.lustre_size,
            hpc_id=self.hpc_id,
            workflow_type=self.workflow_type,
            cromwell_id=self.cromwell_id,
            azure_worker_instance_type=self.azure_worker_instance_type,
            azure_worker_instance_disk=self.azure_worker_instance_disk,
            azure_worker_instance_spot=self.azure_worker_instance_spot,
            docker_login=self.docker_login,
            verify=self.verify_ssl,
            cpus=self.cpus,
            memory=self.memory,
            resume_job=resume,
        )
        print(f"\tYour assigned job id is: {job_id}\n")
        self.job_id = job_id
        self.wait()

    def wait(self):
        j_url = f"{self.cloudos_url}/app/advanced-analytics/analyses/{self.job_id}"
        if self.wait_completion:
            print(
                "\tPlease, wait until job completion (max wait time of "
                + f"{self.wait_time} seconds).\n"
            )
            j_status = self.job.wait_job_completion(
                job_id=self.job_id,
                wait_time=self.wait_time,
                request_interval=self.request_interval,
                verbose=self.verbose,
                verify=self.verify_ssl,
            )
            j_name = j_status["name"]
            j_final_s = j_status["status"]
            if j_final_s == self.job_completed:
                print(
                    f'\nJob status for job "{j_name}" (ID: {self.job_id}): {j_final_s}'
                )
                sys.exit(0)
            else:
                print(
                    f'\nJob status for job "{j_name}" (ID: {self.job_id}): {j_final_s}'
                )

                sys.exit(1)
        else:
            j_status = self.job.get_job_status(self.job_id, self.verify_ssl)
            j_status_h = json.loads(j_status.content)["status"]
            print(f"\tYour current job status is: {j_status_h}")
            print(
                "\tTo further check your job status you can either go to "
                + f"{j_url} or use the following command:\n"
                + "\tcloudos job status \\\n"
                + "\t\t--apikey $MY_API_KEY \\\n"
                + f"\t\t--cloudos-url {self.cloudos_url} \\\n"
                + f"\t\t--job-id {self.job_id}\n"
            )

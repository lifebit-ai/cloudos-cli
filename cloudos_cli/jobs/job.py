"""
This is the main class to create jobs.
"""

from dataclasses import dataclass
from typing import Union
import json
from cloudos_cli.clos import Cloudos
from cloudos_cli.utils.errors import BadRequestException
from cloudos_cli.utils.requests import retry_requests_post, retry_requests_get, retry_requests_delete
from pathlib import Path
import base64
from cloudos_cli.utils.array_job import classify_pattern, get_file_or_folder_id, extract_project
import os
import click
from datetime import datetime


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
    last: bool = False
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
            content = self.get_workflow_content(workspace_id, name, verify=verify, last=self.last)
            for element in content["workflows"]:
                if (element["name"] == name and element["workflowType"] == "docker" and
                        not element["archived"]["status"]):
                    return element["_id"]  # no mainfile or importsfile
                if (element["name"] == name and
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
            return self.get_project_id_from_name(workspace_id, self.project_name, verify=verify)
        if mainfile is not None:
            raise ValueError(f'A workflow named \'{name}\' with a mainFile \'{mainfile}\'' +
                             f' and an importsFile \'{importsfile}\' was not found')
        else:
            raise ValueError(f'No {name} element in {resource} was found')

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
                                 accelerate_saving_results,
                                 docker_login,
                                 command,
                                 cpus,
                                 memory):
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
        accelerate_saving_results : bool
            Whether to save results directly to cloud storage bypassing the master node.
        docker_login : bool
            Whether to use private docker images, provided the users have linked their docker.io accounts.
        command : string
            The command to run in bash jobs.
        cpus : int
            The number of CPUs to use for the bash jobs task's master node.
        memory : int
            The amount of memory, in GB, to use for the bash job task's master node.


        Returns
        -------
        params : dict
            A JSON formatted dict.
        """
        workflow_params = []
        if workflow_type == 'wdl':
            # This is required as non-resumable jobs fails always using WDL workflows.
            resumable = True
        if workflow_type == 'wdl' and job_config is None and len(parameter) == 0:
            raise ValueError('No --job-config or --parameter were provided. At least one of ' +
                             'these are required for WDL workflows.')
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
        elif array_file_header is not None and (array_parameter is None or len(array_parameter) == 0):
            raise ValueError('At least one array file column must be added to the parameters')

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
                raise ValueError(f'The provided parameters "{parameter}" are not valid. ')
        if len(example_parameters) > 0:
            for example_param in example_parameters:
                workflow_params.append(example_param)
        if storage_mode == "lustre":
            click.secho('\nLustre storage has been selected. Please, be sure that this kind of ' +
                  'storage is available in your CloudOS workspace.\n', fg='yellow', bold=True)
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
            "usesFusionFileSystem": use_mountpoints,
            "accelerateSavingResults": accelerate_saving_results
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
        return params

    def send_job(self,
                 job_config=None,
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
                 accelerate_saving_results=False,
                 docker_login=False,
                 verify=True,
                 command=None,
                 cpus=1,
                 memory=4):
        """Send a job to CloudOS.

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
        accelerate_saving_results : bool
            Whether to save results directly to cloud storage bypassing the master node.
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

        Returns
        -------
        j_id : string
            The CloudOS job id of the job just launched.
        """
        apikey = self.apikey
        cloudos_url = self.cloudos_url
        workspace_id = self.workspace_id
        workflow_id = self.workflow_id
        project_id = self.project_id
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
                                               accelerate_saving_results,
                                               docker_login,
                                               command=command,
                                               cpus=cpus,
                                               memory=memory)
        r = retry_requests_post("{}/api/v2/jobs?teamId={}".format(cloudos_url,
                                                                  workspace_id),
                                data=json.dumps(params), headers=headers, verify=verify)
        if r.status_code >= 400:
            raise BadRequestException(r)
        j_id = json.loads(r.content)["jobId"]
        print('\tJob successfully launched to CloudOS, please check the ' +
              f'following link: {cloudos_url}/app/advanced-analytics/analyses/{j_id}')
        return j_id

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
            raise ValueError(f'File "{file_name}" not found in the "{directory}" folder of the project "{self.project_name}".')

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
                raise ValueError("The file path inside the project must start with '/Data' or 'Data'. ")

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
                raise ValueError("The file path inside the project must start with '/Data' or 'Data'. ")

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

    def get_job_request_payload(self, job_id, verify=True):
        """Get the original request payload for a job.
        
        Parameters
        ----------
        job_id : str
            The CloudOS job ID to get the payload for.
        verify : [bool|string]
            Whether to use SSL verification or not. Alternatively, if
            a string is passed, it will be interpreted as the path to
            the SSL certificate file.
            
        Returns
        -------
        dict
            The original job request payload.
        """
        headers = {
            "Content-type": "application/json",
            "apikey": self.apikey
        }
        url = f"{self.cloudos_url}/api/v1/jobs/{job_id}/request-payload?teamId={self.workspace_id}"
        r = retry_requests_get(url, headers=headers, verify=verify)

        if r.status_code >= 400:
            raise BadRequestException(r)

        return json.loads(r.content)

    def update_parameter_value(self, parameters, param_name, new_value):
        """Update a parameter value in the parameters list.
        
        Parameters
        ----------
        parameters : list
            List of parameter dictionaries.
        param_name : str
            Name of the parameter to update.
        new_value : str
            New value for the parameter.
            
        Returns
        -------
        bool
            True if parameter was found and updated, False otherwise.
        """
        for param in parameters:
            if param.get('name') == param_name:
                # Handle different parameter kinds
                if param.get('parameterKind') == 'textValue':
                    param['textValue'] = new_value
                elif param.get('parameterKind') == 'dataItem':
                    # For data items, we need to process the value to get file/folder ID
                    # This is a simplified version - in practice you'd need more logic
                    if new_value.startswith('s3://') or new_value.startswith('az://'):
                        param['textValue'] = new_value
                        param['parameterKind'] = 'textValue'
                    else:
                        # Try to process as file/data item
                        processed_param = self.docker_workflow_param_processing(f"--{param_name}={new_value}", self.project_name)
                        param.update(processed_param)
                return True
        return False

    def get_field_from_jobs_endpoint(self, job_id, field=None, verify=True):
        """Get the resume work directory id for a job.

        Parameters
        ----------
        job_id : str
            The CloudOS job ID to get the resume work directory for.
        verify : [bool|string]
            Whether to use SSL verification or not. Alternatively, if
            a string is passed, it will be interpreted as the path to
            the SSL certificate file.

        Returns
        -------
        str
            The resume work directory id.
        """
        headers = {
            "Content-type": "application/json",
            "apikey": self.apikey
        }
        url = f"{self.cloudos_url}/api/v1/jobs/{job_id}?teamId={self.workspace_id}"
        r = retry_requests_get(url, headers=headers, verify=verify)
        if r.status_code >= 400:
            raise BadRequestException(r)
        if field in json.loads(r.content).keys():
            return json.loads(r.content)[field]
        else:
            raise ValueError(f"Field '{field}' not found in endpoint 'jobs'.")

    def clone_or_resume_job(self, 
                  source_job_id,
                  queue_name=None,
                  cost_limit=None,
                  master_instance=None,
                  job_name=None,
                  nextflow_version=None,
                  branch=None,
                  repository_platform='github',
                  profile=None,
                  do_not_save_logs=None,
                  use_fusion=None,
                  accelerate_saving_results=False,
                  resumable=None,
                  project_name=None,
                  parameters=None,
                  verify=True,
                  mode=None):
        """Clone or resume an existing job with optional parameter overrides.
        
        Parameters
        ----------
        source_job_id : str
            The CloudOS job ID to clone/resume from.
        queue_name : str, optional
            Name of the job queue to use.
        cost_limit : float, optional
            Job cost limit override.
        master_instance : str, optional
            Master instance type override.
        job_name : str, optional
            New job name.
        nextflow_version : str, optional
            Nextflow version override.
        branch : str, optional
            Git branch override.
        repository_platform : str, optional
            Repository platform override.
        profile : str, optional
            Nextflow profile override.
        do_not_save_logs : bool, optional
            Whether to save logs override.
        use_fusion : bool, optional
            Whether to use fusion filesystem override.
        accelerate_saving_results : bool, optional
            Whether to accelerate saving results override.
        resumable : bool, optional
            Whether to make the job resumable or not.
        project_name : str, optional
            Project name override (will look up new project ID).
        parameters : list, optional
            List of parameter overrides in format ['param1=value1', 'param2=value2'].
        verify : [bool|string]
            Whether to use SSL verification or not. Alternatively, if
            a string is passed, it will be interpreted as the path to
            the SSL certificate file.
        mode : str, optional
            The mode to use for the job (e.g. "clone", "resume").

        Returns
        -------
        str
            The CloudOS job ID of the cloned/resumed job.
        """

        # Get the original job payload
        original_payload = self.get_job_request_payload(source_job_id, verify=verify)

        # Create a copy of the payload for modification
        cloned_payload = json.loads(json.dumps(original_payload))

        # remove unwanted fields
        del cloned_payload['_id']
        del cloned_payload['resourceId']


        if mode == "resume":
            try:
                cloned_payload["resumeWorkDir"] = self.get_field_from_jobs_endpoint(
                    source_job_id, field="resumeWorkDir", verify=verify
                )
            except Exception:
                raise ValueError("The job was not set as resumable when originally run")

            try:
                status = self.get_field_from_jobs_endpoint(
                    source_job_id, field="status", verify=verify
                )
            except Exception as e:
                raise ValueError(f"The job status cannot be retrieved. {e}")

            allowed_statuses = {"completed", "aborted", "failed"}
            if status not in allowed_statuses:
                raise ValueError(
                    f"Only jobs with status {', '.join(allowed_statuses)} can be resumed. "
                    f"Current job status is '{status}'"
                )

        # Override job name if provided
        if job_name:
            cloned_payload['name'] = job_name

        # Override cost limit if provided
        if cost_limit is not None:
            if 'execution' not in cloned_payload:
                cloned_payload['execution'] = {}
            cloned_payload['execution']['computeCostLimit'] = cost_limit

        # Override master instance if provided
        if master_instance:
            if 'masterInstance' not in cloned_payload:
                cloned_payload['masterInstance'] = {'requestedInstance': {}}
            cloned_payload['masterInstance']['requestedInstance']['type'] = master_instance

        # Override nextflow version if provided (only for non-docker workflows)
        if nextflow_version and 'nextflowVersion' in cloned_payload:
            cloned_payload['nextflowVersion'] = nextflow_version
        elif nextflow_version and cloned_payload['executionPlatform'] == 'azure' and\
            nextflow_version not in ['22.11.1-edge', 'latest']:
            print("Azure workspace only uses Nextflow version 22.11.1-edge, option '--nextflow-version' is ignored.\n")

        # Override branch if provided
        # sometimes revision is missing from the 'request-payload' API, make sure is present
        if 'revision' not in cloned_payload or not cloned_payload.get('revision'):
            revision = self.get_field_from_jobs_endpoint(source_job_id, field="revision", verify=verify)
            cloned_payload['revision'] = revision
            # Ensure revisionType is present; if missing or empty, infer from available non-empty values
            # Note: The API should provide revisionType, but we handle missing cases
            if not cloned_payload['revision'].get('revisionType'):
                if cloned_payload['revision'].get('digest'):
                    cloned_payload['revision']['revisionType'] = 'digest'
                elif cloned_payload['revision'].get('tag'):
                    cloned_payload['revision']['revisionType'] = 'tag'
                elif cloned_payload['revision'].get('branch'):
                    cloned_payload['revision']['revisionType'] = 'branch'
                elif cloned_payload['revision'].get('commit'):
                    cloned_payload['revision']['revisionType'] = 'commit'

        if branch:
            workflow = self.get_field_from_jobs_endpoint(source_job_id, field="workflow", verify=verify)
            branches = self.get_branches(
                repository_identifier=workflow["repository"]["repositoryId"],
                owner=workflow["repository"]["owner"]["login"],
                workflow_owner_id=workflow["owner"]["id"],
                strategy=repository_platform,
                verify=verify
            )
            if branch not in [b.get('name') for b in branches.get('branches', [])]:
                raise ValueError(f"Branch '{branch}' not found in repository. Available branches: {[b.get('name') for b in branches.get('branches', [])]}")

            cloned_payload['revision']['branch'] = branch
            cloned_payload['revision']['revisionType'] = 'branch'
            # Clear other revision types when setting a branch
            cloned_payload['revision'].pop('tag', None)
            cloned_payload['revision'].pop('commit', None)

        # Override profile if provided
        if profile:
            cloned_payload['profile'] = profile

        # Override save logs if provided
        if do_not_save_logs:
            cloned_payload['saveProcessLogs'] = do_not_save_logs

        # Override use fusion if provided
        if use_fusion and cloned_payload['executionPlatform'] != 'azure':
            cloned_payload['usesFusionFileSystem'] = use_fusion
        elif use_fusion and cloned_payload['executionPlatform'] == 'azure':
            print("Azure workspace does not use fusion filesystem, option '--accelerate-file-staging' is ignored.\n")

        # Override accelerate saving results if provided
        if accelerate_saving_results:
            cloned_payload['accelerateSavingResults'] = accelerate_saving_results

        # Override resumable if provided
        if resumable and mode == "clone":
            cloned_payload['resumable'] = resumable
        elif resumable and mode == "resume":
            print("'resumable' option is only applicable when resuming a job, ignoring '--resumable' flag.\n")

        if 'command' in cloned_payload:
            cloned_payload['batch'] = {"enabled": False}
            if resumable:
                print("'resumable' option is not applicable when resuming a bash job, ignoring '--resumable' flag.\n")

        # Handle job queue override
        if queue_name:
            if cloned_payload['executionPlatform'] != 'azure':
                try:
                    from cloudos_cli.queue.queue import Queue
                    queue_api = Queue(self.cloudos_url, self.apikey, self.cromwell_token, self.workspace_id, verify)
                    queues = queue_api.get_job_queues()

                    queue_id = None
                    for queue in queues:
                        if queue.get("label") == queue_name or queue.get("name") == queue_name:
                            queue_id = queue.get("id") or queue.get("_id")
                            break
                    cloned_payload['batch']['jobQueue'] = queue_id
                    if not queue_id:
                        raise ValueError(f"Queue with name '{queue_name}' not found in workspace '{self.workspace_id}'")
                except Exception as e:
                    raise ValueError(f"Error filtering by queue '{queue_name}'. {str(e)}")
            else:
                print("Azure workspace does not use job queues, option '--job-queue' is ignored.\n")

        # Handle parameter overrides
        # The columnIndex is retrieved from request-payload as string, but needs to be int
        for param in cloned_payload.get('parameters', []):
            if param.get('parameterKind') == 'arrayFileColumn' and isinstance(param.get('columnIndex'), str):
                try:
                    param['columnIndex'] = int(param['columnIndex'])
                except ValueError:
                    raise ValueError(f"Invalid columnIndex value '{param['columnIndex']}' for parameter '{param.get('name')}'")

        if parameters:
            cloned_parameters = cloned_payload.get('parameters', [])
            for param_override in parameters:
                param_name, param_value = param_override.split('=', 1)
                param_name = param_name.lstrip('-') # Remove leading dashes
                if not self.update_parameter_value(cloned_parameters, param_name, param_value):
                    # Parameter not found, add as new parameter
                    # Determine workflow type to set proper prefix and format
                    prefix = "--" if param_override.startswith('--') else ("-" if param_override.startswith('-') else "")
                    new_param = {
                        "prefix": prefix,
                        "name": param_name,
                        "parameterKind": "textValue",
                        "textValue": param_value
                    }
                    cloned_parameters.append(new_param)
            cloned_payload['parameters'] = cloned_parameters

        # setup project name
        if project_name:
            # get project ID
            project_id = self.get_project_id_from_name(self.workspace_id, project_name, verify=verify)
            cloned_payload['project'] = project_id

        # Send the cloned job
        headers = {
            "Content-type": "application/json",
            "apikey": self.apikey
        }
        clean_payload = self.fix_boolean_strings(cloned_payload)

        r = retry_requests_post(f"{self.cloudos_url}/api/v2/jobs?teamId={self.workspace_id}",
                                data=json.dumps(clean_payload),
                                headers=headers,
                                verify=verify)

        if r.status_code >= 400:
            raise BadRequestException(r)

        j_id = json.loads(r.content)["jobId"]
        print(f'\tJob successfully {mode}d and launched to CloudOS, please check the ' +
              f"following link: {self.cloudos_url}/app/advanced-analytics/analyses/{j_id}\n")
        return j_id

    def fix_boolean_strings(self, obj):
        """
        Recursively convert string booleans ('True', 'False') into real booleans
        inside dicts, lists, or nested structures.
        """
        if isinstance(obj, dict):
            return {k: self.fix_boolean_strings(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self.fix_boolean_strings(v) for v in obj]
        elif isinstance(obj, str):
            if obj.lower() == "true":
                return True
            elif obj.lower() == "false":
                return False
            else:
                return obj
        else:
            return obj

    def get_job_relatedness(self, workspace_id, workdir_folder_id, limit=100, verify=True):
        """Get ALL related jobs that share the same working directory folder.

        This method retrieves all jobs sharing the same working directory folder,
        using pagination internally to fetch all results from the API.

        Parameters
        ----------
        workspace_id : str
            The CloudOS workspace ID.
        workdir_folder_id : str
            The working directory folder ID to filter jobs by.
        limit : int
            Batch size for API requests (default: 100). This parameter is kept
            for backwards compatibility but fetches all jobs regardless.
        verify : [bool | str], optional
            Whether to use SSL verification or not. Alternatively, if
            a string is passed, it will be interpreted as the path to
            the SSL certificate file. Default is True.

        Returns
        -------
        dict
            A dictionary where keys are job IDs and values are dictionaries
            containing job details: status, name, user name, user surname,
            _id, createdAt, runTime, and computeCostSpent.

        Raises
        ------
        BadRequestException
            If the request fails with a status code indicating an error.
        """
        headers = {
            "Content-type": "application/json",
            "apikey": self.apikey
        }

        # Fetch ALL related jobs using pagination
        all_jobs = []
        current_page = 1
        batch_size = limit  # API request batch size

        while True:
            params = {
                "limit": batch_size,
                "page": current_page,
                "sort": "-createdAt",
                "archived.status": "false",
                "workDirectory.folderId": workdir_folder_id,
                "teamId": workspace_id
            }

            url = f"{self.cloudos_url}/api/v2/jobs"
            response = retry_requests_get(url, params=params, headers=headers, verify=verify)

            if response.status_code >= 400:
                raise BadRequestException(response)

            content = json.loads(response.content)
            jobs = content.get("jobs", [])

            if not jobs:
                break  # No more jobs to fetch

            all_jobs.extend(jobs)

            if len(jobs) < batch_size:
                break  # Last page reached (fewer jobs than batch size)

            current_page += 1

        # Create final content with all fetched jobs
        content = {"jobs": all_jobs}

        # Process the jobs and extract the required fields
        related_jobs = {}

        for job in content.get("jobs", []):
            job_id = job.get("_id")
            if job_id:
                # Calculate runtime if both startTime and endTime exist
                run_time = None
                start_time = job.get("startTime")
                end_time = job.get("endTime")
                if start_time and end_time:
                    try:
                        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                        end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                        run_time = (end_dt - start_dt).total_seconds()
                    except (ValueError, AttributeError):
                        run_time = None

                # Extract user information
                user_info = job.get("user", {})

                related_jobs[job_id] = {
                    "_id": job_id,
                    "status": job.get("status"),
                    "name": job.get("name"),
                    "user_name": user_info.get("name"),
                    "user_surname": user_info.get("surname"),
                    "createdAt": job.get("createdAt"),
                    "runTime": run_time,
                    "computeCostSpent": job.get("computeCostSpent")
                }

        return related_jobs

    def get_parent_job(self, workspace_id, folder_id, verify=True):
        """Get the parent job of a given folder.

        Parameters
        ----------
        workspace_id : str
            The CloudOS workspace ID.
        folder_id : str
            The ID of the folder whose parent job is to be retrieved.
        verify : [bool | str], optional
            Whether to use SSL verification or not. Alternatively, if
            a string is passed, it will be interpreted as the path to
            the SSL certificate file. Default is True.

        Returns
        -------
        dict
            A dictionary containing details of the parent job.

        Raises
        ------
        BadRequestException
            If the request fails with a status code indicating an error.
        """
        headers = {
            "Content-type": "application/json",
            "apikey": self.apikey
        }

        params = {
            "id": folder_id,
            "status": "ready",
            "teamId": workspace_id
        }

        url = f"{self.cloudos_url}/api/v1/folders/"
        response = retry_requests_get(url, params=params, headers=headers, verify=verify)

        if response.status_code >= 400:
            raise BadRequestException(response)

        content = json.loads(response.content)

        # The API returns a list of folders; we need to extract the parent job ID from the first item (if present)
        if isinstance(content, list) and content:
            parent_job_id = content[0].get("parent", {}).get("id")
        else:
            parent_job_id = None

        if not parent_job_id:
            return None
        else:
            return parent_job_id

    def delete_job_results(self, job_id, mode, verify=True):
        """Delete job results folder.

        Parameters
        ----------
        job_id : str
            The CloudOS job ID whose results folder is to be deleted.
        mode : str
            The mode to use for deletion (e.g., "analysisResults" or "workDirectory").
        verify : [bool|string]
            Whether to use SSL verification or not. Alternatively, if
            a string is passed, it will be interpreted as the path to
            the SSL certificate file. Default is True.

        Returns
        -------
        dict
            A dictionary containing the deletion response from the API.

        Raises
        ------
        BadRequestException
            If the request fails with a status code indicating an error.
        ValueError
            If the folder ID is invalid or the folder does not exist.
        """
        if mode not in ["analysisResults", "workDirectory"]:
            raise ValueError(f"Invalid mode '{mode}'. Supported modes are 'analysisResults' and 'workDirectory'.")

        headers = {
            "Content-type": "application/json",
            "apikey": self.apikey
        }
        url = f"{self.cloudos_url}/api/v1/jobs/{job_id}/data?properties[]={mode}&teamId={self.workspace_id}"
        response = retry_requests_delete(url, headers=headers, verify=verify)

        # Handle specific status codes according to API specification
        if response.status_code == 204:
            # NoContent - successful deletion
            return {"message": "Results deleted successfully", "status": "deleted"}
        elif response.status_code == 400:
            raise ValueError(f"Operation not permitted. Your workspace does not have the option to delete {'results' if mode == 'analysisResults' else 'intermediate'} folders enabled. Please consult with the organisation owner to enable this feature.")
        elif response.status_code == 401:
            raise ValueError("Unauthorized. Invalid or missing API key.")
        elif response.status_code == 403:
            raise ValueError("Forbidden. You don't have permission to delete this folder.")
        elif response.status_code == 404:
            if response.content:
                try:
                    error_message = json.loads(response.content).get('message', f"Job with ID '{job_id}' not found or data does not exist.")
                except (json.JSONDecodeError, KeyError):
                    error_message = f"Job with ID '{job_id}' not found or data does not exist."
            else:
                error_message = f"Job with ID '{job_id}' not found or data does not exist."
            raise ValueError(error_message)
        elif response.status_code == 409:
            raise ValueError("Conflict. The folder cannot be deleted due to a conflict (e.g., folder is not empty or has dependencies).")
        elif response.status_code == 500:
            raise ValueError("Internal server error. The server encountered an error while processing the deletion request.")
        elif response.status_code >= 400:
            raise BadRequestException(response)

        # For any other successful response, parse content if available
        if response.content:
            return json.loads(response.content)
        return {"message": f"'{mode}' deleted successfully"}

    def get_branches(self, repository_identifier, owner, workflow_owner_id,
                     strategy='github', branch_name='', page=1, limit=100, verify=True):
        """Get branches from a GitHub repository with pagination support.

        Parameters
        ----------
        repository_identifier : str
            The GitHub repository identifier (repository ID).
        owner : str
            The owner of the repository (e.g., 'lifebit-ai').
        workflow_owner_id : str
            The workflow owner ID in CloudOS.
        strategy : str, optional
            The repository strategy/platform (default is 'github').
        branch_name : str, optional
            Filter branches by name. Default is '' (empty string to get all branches).
        page : int, optional
            Page number for pagination. Default is 1.
        limit : int, optional
            Number of results per page. Default is 100.
        verify : [bool|string], optional
            Whether to use SSL verification or not. Alternatively, if
            a string is passed, it will be interpreted as the path to
            the SSL certificate file. Default is True.

        Returns
        -------
        dict
            A dictionary containing all branches information from the API.
            Structure: {"branches": [...], "total": <total_count>}

        Raises
        ------
        BadRequestException
            If the request fails with a status code indicating an error.
        """
        headers = {
            "Content-type": "application/json",
            "apikey": self.apikey
        }

        all_branches = []
        current_page = 1
        total = None

        while True:
            params = {
                "repositoryIdentifier": repository_identifier,
                "owner": owner,
                "workflowOwnerId": workflow_owner_id,
                "branchName": branch_name,
                "page": current_page,
                "limit": limit,
                "teamId": self.workspace_id
            }

            url = f"{self.cloudos_url}/api/v1/git/{strategy}/getBranches"
            response = retry_requests_get(url, params=params, headers=headers, verify=verify)

            if response.status_code >= 400:
                raise BadRequestException(response)

            content = json.loads(response.content)
            branches = content.get("branches", [])

            if total is None:
                total = content.get("total")

            if not branches:
                break  # No more branches to fetch

            all_branches.extend(branches)

            # Check if we've fetched all branches (only if total is provided)
            if total is not None and len(all_branches) >= total:
                break

            current_page += 1

        return {"branches": all_branches, "total": total or len(all_branches)}


"""
This is the main class to create jobs.
"""

from dataclasses import dataclass
from typing import Union
import json
from cloudos_cli.clos import Cloudos
from cloudos_cli.utils.errors import (
    BadRequestException,
    cloud_os_request_error,
    CantResumeNonResumableJob,
    CantResumeRunningJob,
)
from cloudos_cli.utils.requests import retry_requests_post, retry_requests_get


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
    repository_platform: str = "github"
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
                "projects",
                self.workspace_id,
                self.project_name,
                verify=self.verify,
            )
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
                "workflows",
                self.workspace_id,
                self.workflow_name,
                self.mainfile,
                self.importsfile,
                self.repository_platform,
                self.verify,
            )
        else:
            # Let the user define the value.
            self._workflow_id = v

    def fetch_cloudos_id(
        self,
        apikey,
        cloudos_url,
        resource,
        workspace_id,
        name,
        mainfile=None,
        importsfile=None,
        repository_platform="github",
        verify=True,
    ):
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
        allowed_resources = ["projects", "workflows"]
        if resource not in allowed_resources:
            raise ValueError(
                "Your specified resource is not supported. "
                + f"Use one of the following: {allowed_resources}"
            )
        if resource == "workflows":
            content = self.get_workflow_list(workspace_id, verify=verify)
            for element in content:
                if (
                    element["name"] == name
                    and element["workflowType"] == "docker"
                    and not element["archived"]["status"]
                ):
                    return element["_id"]  # no mainfile or importsfile
                if (
                    element["name"] == name
                    and element["repository"]["platform"] == repository_platform
                    and not element["archived"]["status"]
                ):
                    if mainfile is None:
                        return element["_id"]
                    elif element["mainFile"] == mainfile:
                        if importsfile is None and "importsFile" not in element.keys():
                            return element["_id"]
                        elif (
                            "importsFile" in element.keys()
                            and element["importsFile"] == importsfile
                        ):
                            return element["_id"]
        elif resource == "projects":
            content = self.get_project_list(workspace_id, verify=verify)
            # New API projects endpoint spec
            for element in content:
                if element["name"] == name:
                    return element["_id"]
        if mainfile is not None:
            raise ValueError(
                f"[ERROR] A workflow named '{name}' with a mainFile '{mainfile}'"
                + f" and an importsFile '{importsfile}' was not found"
            )
        else:
            raise ValueError(f"[ERROR] No {name} element in {resource} was found")

    def convert_nextflow_to_json(
        self,
        job_config,
        parameter,
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
    ):
        """Converts a nextflow.config fie into a json formatted dict.

        Parameters
        ----------
        job_config : string
            Path to a nextflow.config file with parameters scope.
        parameter : tuple
            Tuple of strings indicating the parameters to pass to the pipeline call.
            They are in the following form: ('param1=param1val', 'param2=param2val', ...)
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


        Returns
        -------
        params : dict
            A JSON formatted dict.
        """
        workflow_params = []
        if workflow_type == "wdl":
            # This is required as non-resumable jobs fails always using WDL workflows.
            resumable = True
        if (
            nextflow_profile is None
            and job_config is None
            and len(parameter) == 0
            and len(example_parameters) == 0
        ):
            raise ValueError(
                "No --job-config, --nextflow_profile, --parameter or "
                + "--example_parameters were specified,"
                + "  please use at least one of these options."
            )
        if workflow_type == "wdl" and job_config is None and len(parameter) == 0:
            raise ValueError(
                "No --job-config or --parameter were provided. At least one of "
                + "these are required for WDL workflows."
            )
        if workflow_type == "docker" and len(parameter) == 0:
            raise ValueError(
                "No --parameter were provided. At least one of "
                + "these are required for bash workflows."
            )
        if job_config is not None:
            with open(job_config, "r") as p:
                reading = False
                for p_l in p:
                    if "params" in p_l.lower():
                        reading = True
                    else:
                        if reading:
                            if workflow_type == "wdl":
                                p_l_strip = p_l.strip().replace(" ", "")
                            else:
                                p_l_strip = (
                                    p_l.strip()
                                    .replace(" ", "")
                                    .replace('"', "")
                                    .replace("'", "")
                                )
                            if len(p_l_strip) == 0:
                                continue
                            elif p_l_strip[0] == "/" or p_l_strip[0] == "#":
                                continue
                            elif p_l_strip == "}":
                                reading = False
                            else:
                                p_list = p_l_strip.split("=")
                                p_name = p_list[0]
                                p_value = "=".join(p_list[1:])
                                if len(p_list) < 2:
                                    raise ValueError(
                                        "Please, specify your "
                                        + "parameters in "
                                        + f"{job_config} using "
                                        + "the '=' as spacer. "
                                        + "E.g: name = my_name"
                                    )
                                elif workflow_type == "wdl":
                                    param = {
                                        "prefix": "",
                                        "name": p_name,
                                        "parameterKind": "textValue",
                                        "textValue": p_value,
                                    }
                                    workflow_params.append(param)
                                else:
                                    param = {
                                        "prefix": "--",
                                        "name": p_name,
                                        "parameterKind": "textValue",
                                        "textValue": p_value,
                                    }
                                    workflow_params.append(param)
            if len(workflow_params) == 0:
                raise ValueError(
                    f"The {job_config} file did not contain any " + "valid parameter"
                )
        if len(parameter) > 0:
            for p in parameter:
                p_split = p.split("=")
                if len(p_split) < 2:
                    raise ValueError(
                        "Please, specify -p / --parameter using a single '=' "
                        + "as spacer. E.g: input=value"
                    )
                p_name = p_split[0]
                p_value = "=".join(p_split[1:])
                if workflow_type == "docker":
                    prefix = (
                        "--"
                        if p_name.startswith("--")
                        else ("-" if p_name.startswith("-") else "")
                    )
                    # leave defined for adding files later
                    parameter_kind = "textValue"
                    param = {
                        "prefix": prefix,
                        "name": p_name.lstrip("-"),
                        "parameterKind": parameter_kind,
                        "textValue": p_value,
                    }
                    workflow_params.append(param)
                elif workflow_type == "wdl":
                    param = {
                        "prefix": "",
                        "name": p_name,
                        "parameterKind": "textValue",
                        "textValue": p_value,
                    }
                    workflow_params.append(param)
                else:
                    param = {
                        "prefix": "--",
                        "name": p_name,
                        "parameterKind": "textValue",
                        "textValue": p_value,
                    }
                    workflow_params.append(param)
            if len(workflow_params) == 0:
                raise ValueError(f"The provided parameters are not valid: {parameter}")
        if len(example_parameters) > 0:
            for example_param in example_parameters:
                workflow_params.append(example_param)
        if storage_mode == "lustre":
            print(
                "\n[WARNING] Lustre storage has been selected. Please, be sure that this kind of "
                + "storage is available in your CloudOS workspace.\n"
            )
            if lustre_size % 1200:
                raise ValueError(
                    "Please, specify a lustre storage size of 1200 or a multiple of it. "
                    + f"{lustre_size} is not a valid number."
                )
        if storage_mode not in ["lustre", "regular"]:
            raise ValueError(
                "Please, use either 'lustre' or 'regular' for --storage-mode "
                + f"{storage_mode} is not allowed"
            )
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
            "execution": {"computeCostLimit": cost_limit, "optim": "test"},
            "lusterFsxStorageSizeInGb": lustre_size,
            "storageMode": storage_mode,
            "instanceType": instance_type,
            "usesFusionFileSystem": use_mountpoints,
        }
        if workflow_type != "docker":
            params["nextflowVersion"] = nextflow_version
        if execution_platform != "hpc":
            params["masterInstance"] = {"requestedInstance": {"type": instance_type}}
            params["batch"] = {"enabled": batch}
        if job_queue_id is not None:
            params["batch"] = {
                "dockerLogin": docker_login,
                "enabled": batch,
                "jobQueue": job_queue_id,
            }
        if execution_platform == "azure" and not is_module:
            params["azureBatch"] = {
                "vmType": azure_worker_instance_type,
                "spot": azure_worker_instance_spot,
                "diskSizeInGb": azure_worker_instance_disk,
            }
        if workflow_type == "docker":
            params["command"] = command
            params["resourceRequirements"] = {"cpu": cpus, "ram": memory}
        if workflow_type == "wdl":
            params["cromwellCloudResources"] = cromwell_id
        git_flag = [1 for x in [git_tag, git_commit, git_branch] if x]
        if sum(git_flag) > 1:
            raise ValueError(
                "Please, specify none or only one of --git-tag, "
                + "--git-branch or --git-commit options."
            )
        elif sum(git_flag) == 1:
            revision_type = (
                "tag"
                if git_tag is not None
                else "commit"
                if git_commit is not None
                else "branch"
            )
            params["revision"] = {
                "revisionType": revision_type,
                "tag": git_tag,
                "commit": git_commit,
                "branch": git_branch,
            }
        if nextflow_profile is not None:
            params["profile"] = nextflow_profile
        return params

    def send_job(
        self,
        job_config=None,
        project_id="",
        parameter=(),
        is_module=False,
        example_parameters=[],
        git_commit=None,
        git_tag=None,
        git_branch=None,
        job_name="new_job",
        resumable=False,
        save_logs=True,
        batch=True,
        job_queue_id=None,
        nextflow_profile=None,
        nextflow_version="22.10.8",
        instance_type="c5.xlarge",
        instance_disk=500,
        storage_mode="regular",
        lustre_size=1200,
        execution_platform="aws",
        hpc_id=None,
        workflow_type="nextflow",
        cromwell_id=None,
        azure_worker_instance_type="Standard_D4as_v4",
        azure_worker_instance_disk=100,
        azure_worker_instance_spot=False,
        cost_limit=30.0,
        use_mountpoints=False,
        docker_login=False,
        verify=True,
        command=None,
        cpus=1,
        memory=4,
        resume_job_work_dir="",
    ):
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
        project_id = self.project_id
        # Prepare api request for CloudOS to run a job
        headers = {"Content-type": "application/json", "apikey": apikey}
        params = self.convert_nextflow_to_json(
            job_config,
            parameter,
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
        )
        if project_id:
            params["project"] = project_id
        # specifying the resumeWorkDir slot, makes the job resumed.
        if resume_job_work_dir:
            params["resumeWorkDir"] = resume_job_work_dir
        from pprint import pprint
        r = retry_requests_post(
            "{}/api/v2/jobs?teamId={}".format(cloudos_url, workspace_id),
            data=json.dumps(params),
            headers=headers,
            verify=verify,
        )
        if r.status_code >= 400:
            raise BadRequestException(r)
        j_id = json.loads(r.content)["jobId"]
        print(
            "\tJob successfully launched to CloudOS, please check the "
            + f"following link: {cloudos_url}/app/advanced-analytics/analyses/{j_id}"
        )
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
        :param workspace_id: CloudOS workkspace ID.
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


        new_profile = job_payload_d["profile"]
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

        new_resumable = job_payload_d["resumable"] if resumable is None else resumable
        new_save_logs = (
            job_payload_d["saveProcessLogs"] if save_logs is None else save_logs
        )
        new_use_mountpoints = (
            job_payload_d["usesFusionFileSystem"]
            if use_mountpoints is None
            else use_mountpoints
        )
        ## Assemble payload for cloning
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

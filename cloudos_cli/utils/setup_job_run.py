from cloudos_cli.clos import Cloudos
from cloudos_cli.jobs import Job
from cloudos_cli.queue.queue import Queue
from cloudos_cli.utils.errors import cloud_os_request_error
from cloudos_cli.utils.requests import retry_requests_get
from cloudos_cli.utils.resources import ssl_selector
import json
import time
import sys

CLOUDOS_URL = "https://cloudos.lifebit.ai"


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
        ssl_cert="",
        nextflow_version="22.10.8",
        cloudos_url=CLOUDOS_URL,
        workflow_name="",
        job_id="",
        job_queue=None,
        job_config="",
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

        self.JOB_COMPLETED = "completed"
        self.AWS_NEXTFLOW_LATEST = "24.04.4"
        self.AZURE_NEXTFLOW_LATEST = "22.11.1-edge"
        self.HPC_NEXTFLOW_LATEST = "22.10.8"
        self.AWS_NEXTFLOW_VERSIONS = ["22.10.8", "24.04.4"]
        self.AZURE_NEXTFLOW_VERSIONS = ["22.11.1-edge"]
        self.HPC_NEXTFLOW_VERSIONS = ["22.10.8"]
        self.headers = {"apikey": apikey, "Content-type": "application/json"}
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

        if run_type == "run":
            wf_name = self.workflow_name
        else:
            wf_name = self.get_workflow_name(self.job_id)

        self.workflow_type = self.cl.detect_workflow(
            wf_name, self.workspace_id, self.verify_ssl
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
            return self.get_workflow_name(self.job_id)
        else:
            raise ValueError("Workflow name or Job ID should be provided")

    def get_exec_platform(self):
        job_url = f"{self.cloudos_url}/api/v1/jobs/{self.job_id}/request-payload"
        job_r = retry_requests_get(
            job_url, params=self.request_params, headers=self.headers
        )
        cloud_os_request_error(job_r)
        job_d = job_r.json()
        return job_d["executionPlatform"]

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
            if self.nextflow_version != "22.10.8":
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
                self.nextflow_version = self.AWS_NEXTFLOW_LATEST
            elif self.execution_platform == "azure":
                self.nextflow_version = self.AZURE_NEXTFLOW_LATEST
            else:
                self.nextflow_version = self.HPC_NEXTFLOW_LATEST
            print(
                "[Message] You have specified Nextflow version 'latest' for execution platform "
                + f"'{self.execution_platform}'. The workflow will use the "
                + f"latest version available on CloudOS: {self.nextflow_version}."
            )
        if self.execution_platform == "aws":
            if self.nextflow_version not in self.AWS_NEXTFLOW_VERSIONS:
                print(
                    "[Message] For execution platform 'aws', the workflow will use the default "
                    + "'22.10.8' version on CloudOS."
                )
                self.nextflow_version = "22.10.8"
        if self.execution_platform == "azure":
            if self.nextflow_version not in self.AZURE_NEXTFLOW_VERSIONS:
                print(
                    "[Message] For execution platform 'azure', the workflow will use the '22.11.1-edge' "
                    + "version on CloudOS."
                )
                self.nextflow_version = "22.11.1-edge"
        if self.execution_platform == "hpc":
            if self.nextflow_version not in self.HPC_NEXTFLOW_VERSIONS:
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

    def get_workflow_name(self, job_id):
        job_url = f"{self.cloudos_url}/api/v1/jobs/{job_id}"
        job_req = retry_requests_get(
            job_url, headers=self.headers, params=self.request_params
        )
        cloud_os_request_error(job_req)
        job_d = job_req.json()
        return job_d["workflow"]["name"]

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
            if j_final_s == self.JOB_COMPLETED:
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

"""
This is the main class to create job queues.
"""

import json
import copy
import pandas as pd
from dataclasses import dataclass
from typing import Union
from cloudos_cli.clos import Cloudos
from cloudos_cli.utils.errors import (
    BadRequestException,
    NoJobQueuesAvailableException,
)
from cloudos_cli.utils.requests import retry_requests_get, retry_requests_post


# ---------------------------------------------------------------------------
# Preset templates (match the CloudOS Platform UI presets exactly)
# ---------------------------------------------------------------------------

_STANDARD_INSTANCE_TYPES = [
    "optimal",
    "c4.2xlarge", "c4.4xlarge", "c4.8xlarge",
    "c5.xlarge", "c5.2xlarge", "c5.4xlarge", "c5.9xlarge",
    "c5.12xlarge", "c5.18xlarge", "c5.24xlarge", "c5.metal",
    "m4.xlarge", "m4.2xlarge", "m4.4xlarge", "m4.10xlarge", "m4.16xlarge",
    "m5.xlarge", "m5.2xlarge", "m5.4xlarge", "m5.8xlarge",
    "m5.12xlarge", "m5.16xlarge", "m5.24xlarge", "m5.metal",
    "r4.xlarge", "r4.2xlarge", "r4.4xlarge", "r4.8xlarge", "r4.16xlarge",
    "r5.xlarge", "r5.2xlarge", "r5.4xlarge", "r5.8xlarge",
    "r5.12xlarge", "r5.16xlarge", "r5.24xlarge", "r5.metal",
]

_GPU_INSTANCE_TYPES = [
    "optimal",
    "c4.2xlarge", "c4.4xlarge", "c4.8xlarge",
    "c5.xlarge", "c5.2xlarge", "c5.4xlarge", "c5.9xlarge",
    "c5.12xlarge", "c5.18xlarge", "c5.24xlarge", "c5.metal",
    "g4dn.xlarge", "g4dn.2xlarge", "g4dn.4xlarge", "g4dn.8xlarge",
    "g4dn.12xlarge", "g4dn.16xlarge", "g4dn.metal",
    "m4.xlarge", "m4.2xlarge", "m4.4xlarge", "m4.10xlarge", "m4.16xlarge",
    "m5.xlarge", "m5.2xlarge", "m5.4xlarge", "m5.8xlarge",
    "m5.12xlarge", "m5.16xlarge", "m5.24xlarge", "m5.metal",
    "p3.2xlarge", "p3.8xlarge", "p3.16xlarge",
    "r4.xlarge", "r4.2xlarge", "r4.4xlarge", "r4.8xlarge", "r4.16xlarge",
    "r5.xlarge", "r5.2xlarge", "r5.4xlarge", "r5.8xlarge",
    "r5.12xlarge", "r5.16xlarge", "r5.24xlarge", "r5.metal",
]

# ---------------------------------------------------------------------------
# Additional instance types accepted for custom (from-scratch) queues.
#
# The preset lists above intentionally mirror the CloudOS Platform UI presets,
# so they are left untouched. Custom queues may use any instance type AWS Batch
# supports, so the validation set (``ALL_INSTANCE_TYPES``) is widened with the
# current-generation Intel families below: compute-optimised (c6i/c7i),
# general-purpose (m6i/m7i) and memory-optimised (r6i/r7i) for standard
# workloads, plus g5/g6/p4d/p5 for GPU workloads. Sizes follow the AWS EC2
# instance type catalogue.
# https://aws.amazon.com/ec2/instance-types/
# https://aws.amazon.com/ec2/instance-types/accelerated-computing/
# ---------------------------------------------------------------------------

_STANDARD_INSTANCE_TYPES_EXTRA = [
    # Compute optimised
    "c6i.large", "c6i.xlarge", "c6i.2xlarge", "c6i.4xlarge", "c6i.8xlarge",
    "c6i.12xlarge", "c6i.16xlarge", "c6i.24xlarge", "c6i.32xlarge", "c6i.metal",
    "c7i.large", "c7i.xlarge", "c7i.2xlarge", "c7i.4xlarge", "c7i.8xlarge",
    "c7i.12xlarge", "c7i.16xlarge", "c7i.24xlarge", "c7i.48xlarge",
    "c7i.metal-24xl", "c7i.metal-48xl",
    # General purpose
    "m6i.large", "m6i.xlarge", "m6i.2xlarge", "m6i.4xlarge", "m6i.8xlarge",
    "m6i.12xlarge", "m6i.16xlarge", "m6i.24xlarge", "m6i.32xlarge", "m6i.metal",
    "m7i.large", "m7i.xlarge", "m7i.2xlarge", "m7i.4xlarge", "m7i.8xlarge",
    "m7i.12xlarge", "m7i.16xlarge", "m7i.24xlarge", "m7i.48xlarge",
    "m7i.metal-24xl", "m7i.metal-48xl",
    # Memory optimised
    "r6i.large", "r6i.xlarge", "r6i.2xlarge", "r6i.4xlarge", "r6i.8xlarge",
    "r6i.12xlarge", "r6i.16xlarge", "r6i.24xlarge", "r6i.32xlarge", "r6i.metal",
    "r7i.large", "r7i.xlarge", "r7i.2xlarge", "r7i.4xlarge", "r7i.8xlarge",
    "r7i.12xlarge", "r7i.16xlarge", "r7i.24xlarge", "r7i.48xlarge",
    "r7i.metal-24xl", "r7i.metal-48xl",
]

_GPU_INSTANCE_TYPES_EXTRA = [
    "g5.xlarge", "g5.2xlarge", "g5.4xlarge", "g5.8xlarge",
    "g5.12xlarge", "g5.16xlarge", "g5.24xlarge", "g5.48xlarge",
    "g6.xlarge", "g6.2xlarge", "g6.4xlarge", "g6.8xlarge",
    "g6.12xlarge", "g6.16xlarge", "g6.24xlarge", "g6.48xlarge",
    "p4d.24xlarge",
    "p5.48xlarge",
]

# Union of every selectable instance type (preset standard + GPU families plus
# the current-generation families above), used to validate user-supplied
# instance types for custom (from-scratch) queues.
ALL_INSTANCE_TYPES = sorted(
    set(_STANDARD_INSTANCE_TYPES)
    | set(_GPU_INSTANCE_TYPES)
    | set(_STANDARD_INSTANCE_TYPES_EXTRA)
    | set(_GPU_INSTANCE_TYPES_EXTRA)
)

QUEUE_PRESETS = {
    "standard-stable": {
        "computeEnvironmentName": "OnDemandStandard",
        "computeResources": {
            "allocationStrategy": "BEST_FIT_PROGRESSIVE",
            "instanceTypes": _STANDARD_INSTANCE_TYPES,
            "maxvCpus": 512,
            "type": "EC2",
            "minvCpus": 0,
        },
        "templateName": "Standard stable",
        "templateDescription": (
            "Standard stable (on-demand) instances of all resource types from "
            "c5, r5, m5, c4, r4, m4 instance families."
        ),
    },
    "standard-cost-saving": {
        "computeEnvironmentName": "OnDemandSpot",
        "computeResources": {
            "allocationStrategy": "SPOT_CAPACITY_OPTIMIZED",
            "instanceTypes": _STANDARD_INSTANCE_TYPES,
            "maxvCpus": 512,
            "type": "SPOT",
            "minvCpus": 0,
            "bidPercentage": 100,
        },
        "templateName": "Standard cost-saving",
        "templateDescription": (
            "Standard cost-saving (spot) instances of all resource types from "
            "c5, r5, m5, c4, r4, m4 instance families. Spot instances allow to "
            "save up to 80% cost compared to on-demand stable instances at a risk "
            "of being prematurely terminated. Useful for short-running processes. "
            "It is advised to use retry error strategy in the workflow for this job queue."
        ),
    },
    "read-write-optimised": {
        "computeEnvironmentName": "OnDemandStandardHighDiskThroughput",
        "computeResources": {
            "allocationStrategy": "BEST_FIT_PROGRESSIVE",
            "instanceTypes": _STANDARD_INSTANCE_TYPES,
            "maxvCpus": 512,
            "type": "EC2",
            "minvCpus": 0,
            "volume": {
                "type": "gp3",
                "size": {"usageQuantity": 1000, "usageUnit": "Gb"},
                "iops": 5000,
                "throughput": 500,
                "deviceName": "/dev/xvda",
                "deleteOnTermination": False,
                "encrypted": False,
            },
        },
        "templateName": "Read/write optimised",
        "templateDescription": (
            "Standard stable (on-demand) instances of all resource types from "
            "c5, r5, m5, c4, r4, m4 instance families and increased disk I/O "
            "performance. Useful for the jobs that require significant file read "
            "and write activity. May increase the job cost."
        ),
    },
    "standard-gpu": {
        "computeEnvironmentName": "OnDemandStandardGPUs",
        "computeResources": {
            "allocationStrategy": "BEST_FIT_PROGRESSIVE",
            "instanceTypes": _GPU_INSTANCE_TYPES,
            "maxvCpus": 512,
            "type": "EC2",
            "minvCpus": 0,
        },
        "templateName": "Standard with GPUs",
        "templateDescription": (
            "Standard stable (on-demand) instances as well as GPU instances of "
            "p3 and/or g4dn families. On-demand GPU machines typically incur higher costs."
        ),
    },
}


# ---------------------------------------------------------------------------
# Custom ("from scratch") queue creation options
# ---------------------------------------------------------------------------

# Provisioning type -> AWS Batch compute environment resource type.
PROVISIONING_TYPES = {
    "on-demand": "EC2",
    "spot": "SPOT",
}

# Allocation strategies allowed for each provisioning type.
ALLOCATION_STRATEGIES = {
    "on-demand": ["BEST_FIT", "BEST_FIT_PROGRESSIVE"],
    "spot": ["BEST_FIT", "BEST_FIT_PROGRESSIVE", "SPOT_CAPACITY_OPTIMIZED"],
}

# vCPU bounds.
MAX_VCPUS_LIMIT = 20000
DEFAULT_MAX_VCPUS = 512
DEFAULT_MIN_VCPUS = 0

# Volume types and their size/IOPS/throughput specifications. Each spec stores
# (default, minimum, maximum). ``throughput`` is ``None`` when not applicable.
VOLUME_SPECS = {
    "gp3": {
        "size": (1000, 50, 16384),
        "iops": (3000, 3000, 16000),
        "throughput": (125, 125, 1000),
    },
    "io2": {
        "size": (1000, 50, 16384),
        "iops": (3000, 100, 64000),
        "throughput": None,
    },
}

# Maximum number of compute environments a workspace can hold across all queues.
MAX_WORKSPACE_COMPUTE_ENVS = 10

# Message shown once a workspace reaches the compute environment limit.
WORKSPACE_CE_LIMIT_REACHED_MESSAGE = (
    "You have reached the limit for compute environments in your workspace. "
    f"Workspaces can have up to {MAX_WORKSPACE_COMPUTE_ENVS} compute environments."
)


@dataclass
class Queue(Cloudos):
    """Class to store and operate job queues.

    Parameters
    ----------
    cloudos_url : string
        The Lifebit Platform service url.
    apikey : string
        Your Lifebit Platform API key.
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

    def get_job_queues(self, exclude_system_queues=False):
        """Get all the job queues from a Lifebit Platform workspace.

        Parameters
        ----------
        exclude_system_queues : bool, default=False
            Whether to exclude system job queues from the result.

        Returns
        -------
        r : list
            A list of dicts, each corresponding to a job queue.
        """
        headers = {"apikey": self.apikey}
        r = retry_requests_get("{}/api/v1/teams/aws/v2/job-queues?teamId={}".format(self.cloudos_url,
                                                                                    self.workspace_id),
                               headers=headers, verify=self.verify)
        if r.status_code >= 400:
            raise BadRequestException(r)
        queues = json.loads(r.content)
        # By default, include system queues unless excluded
        if not exclude_system_queues:
            system_queues = self.get_system_job_queues()
            queues.extend(system_queues)
        
        return queues

    def get_system_job_queues(self):
        """Get all the system job queues from Lifebit Platform.

        Returns
        -------
        r : list
            A list of dicts, each corresponding to a system job queue.
        """
        headers = {"apikey": self.apikey}
        r = retry_requests_get("{}/api/v1/teams/aws/v2/system-job-queues?teamId={}".format(self.cloudos_url,
                                                                                            self.workspace_id),
                               headers=headers, verify=self.verify)
        if r.status_code >= 400:
            raise BadRequestException(r)
        return json.loads(r.content)

    @staticmethod
    def process_queue_list(r, all_fields=False):
        """Process a queue list from a self.get_job_queues call.

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
                   'isDefault',
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

    def fetch_job_queue_id(self, workflow_type, batch=True, job_queue=None):
        """Fetches Lifebit Platform ID for a given job queue.

        This method will try to find the
        corresponding Lifebit Platform ID for the job_queue in a given workspace. If
        job_queue=None, this method will select the available default queue in
        the workspace, or the newest "ready" job queue if no default queues are
        available.

        Parameters
        ----------
        workflow_type : str ['wdl'|'cromwell'|'nextflow']
            The type of workflow to run.
        batch: bool
            Whether to create a batch job or an ignite one.
        job_queue : str or None
            The name of the job queue to search. If None, a default one will be selected.

        Returns
        -------
        job_queue_id : str or None
            The Lifebit Platform ID for the selected job queue, or None if batch=False.
        """
        if not batch:
            return None
        if workflow_type == 'wdl':
            workflow_type = 'cromwell'
        if workflow_type not in ['cromwell', 'nextflow']:
            raise ValueError('Only nextflow or cromwell workflows are allowed when ' +
                             'running using AWS batch.')
        job_queues = self.get_job_queues()
        available_queues = [q for q in job_queues if q['status'] == 'Ready' and
                            q['executor'] == workflow_type]
        if len(available_queues) == 0:
            raise NoJobQueuesAvailableException(workflow_type)
        default_queue = [q for q in available_queues if q.get('isDefault', False)]
        if len(default_queue) > 0:
            default_queue_id = default_queue[0]['id']
            default_queue_name = default_queue[0]['label']
            queue_as_default = 'Lifebit Platform default'
        else:
            default_queue_id = available_queues[-1]['id']
            default_queue_name = available_queues[-1]['label']
            queue_as_default = 'most recent suitable'
        if job_queue is None:
            print(f'No job queue was specified, using the {queue_as_default} queue: ' +
                  f'{default_queue_name}.')
            return default_queue_id
        selected_queue = [q for q in available_queues if q['label'] == job_queue]
        if len(selected_queue) == 0:
            print(f'Queue \'{job_queue}\' you specified was not found, using the {queue_as_default} ' +
                  f'queue instead: {default_queue_name}.')
            return default_queue_id
        return selected_queue[0]['id']

    @staticmethod
    def get_preset_template(preset_name):
        """Return the environment and template fields for a given preset name.

        Parameters
        ----------
        preset_name : str
            One of: 'standard-stable', 'standard-cost-saving',
            'read-write-optimised', 'standard-gpu'.

        Returns
        -------
        template : dict
            A dict with keys 'computeEnvironmentName', 'computeResources',
            'templateName', and 'templateDescription'.

        Raises
        ------
        ValueError
            If ``preset_name`` is not a recognised preset.
        """
        if preset_name not in QUEUE_PRESETS:
            valid = ', '.join(QUEUE_PRESETS.keys())
            raise ValueError(
                f"Unknown preset '{preset_name}'. Valid presets are: {valid}"
            )
        return copy.deepcopy(QUEUE_PRESETS[preset_name])

    def create_job_queue(self, label, description, preset_name, executor="nextflow",
                         is_default=False):
        """Create a new job queue in the workspace using a preset template.

        Parameters
        ----------
        label : str
            Human-readable name for the queue.
        description : str
            Short description of the queue's purpose.
        preset_name : str
            One of the supported preset keys (see ``QUEUE_PRESETS``).
        executor : str, optional
            Workflow executor.  Defaults to ``'nextflow'``.
        is_default : bool, optional
            Whether to set the queue as the workspace default. Defaults to
            ``False``.

        Returns
        -------
        queue_id : str
            The Lifebit Platform ID assigned to the newly created queue.

        Raises
        ------
        BadRequestException
            If the API returns a 4xx or 5xx response.
        """
        preset = self.get_preset_template(preset_name)
        payload = {
            "id": "",
            "label": label,
            "description": description,
            "executor": executor,
            "status": "ToCreate",
            "environment": {
                "computeEnvironmentName": preset["computeEnvironmentName"],
                "computeResources": preset["computeResources"],
            },
            "templateName": preset["templateName"],
            "templateDescription": preset["templateDescription"],
            "isDefault": is_default,
        }
        return self._post_job_queue(payload)

    def _post_job_queue(self, payload):
        """POST a job queue payload to the Lifebit Platform and return its ID.

        Parameters
        ----------
        payload : dict
            The fully-built job queue creation payload.

        Returns
        -------
        queue_id : str
            The Lifebit Platform ID assigned to the newly created queue.

        Raises
        ------
        BadRequestException
            If the API returns a 4xx or 5xx response.
        """
        headers = {
            "Content-Type": "application/json",
            "apikey": self.apikey,
        }
        r = retry_requests_post(
            "{}/api/v1/teams/aws/v2/job-queue?teamId={}".format(
                self.cloudos_url, self.workspace_id
            ),
            headers=headers,
            json=payload,
            verify=self.verify,
        )
        if r.status_code >= 400:
            raise BadRequestException(r)
        response_data = json.loads(r.content)
        queue_id = response_data.get("id") or response_data.get("_id")
        if not queue_id:
            raise RuntimeError(
                "Job queue creation succeeded but the server response did not "
                "include a queue ID."
            )
        return queue_id

    def create_job_queue_from_scratch(self,
                                      label,
                                      description,
                                      provisioning_type,
                                      allocation_strategy,
                                      max_vcpus,
                                      min_vcpus,
                                      instance_types,
                                      volume_type,
                                      size,
                                      iops,
                                      throughput=None,
                                      executor="nextflow",
                                      is_default=False):
        """Create a custom job queue without using a preset template.

        Parameters
        ----------
        label : str
            Human-readable name for the queue. Also used as the compute
            environment name.
        description : str
            Short description of the queue's purpose.
        provisioning_type : str
            One of ``'on-demand'`` or ``'spot'``.
        allocation_strategy : str
            AWS Batch allocation strategy. Must be valid for the chosen
            ``provisioning_type`` (see ``ALLOCATION_STRATEGIES``).
        max_vcpus : int
            Maximum number of vCPUs for the compute environment.
        min_vcpus : int
            Minimum number of vCPUs for the compute environment.
        instance_types : list[str]
            Instance types to allow (e.g. ``['optimal']`` or a list from
            ``_STANDARD_INSTANCE_TYPES``).
        volume_type : str
            One of ``'gp3'`` or ``'io2'``.
        size : int
            Volume size in GiB.
        iops : int
            Provisioned IOPS for the volume.
        throughput : int or None, optional
            Volume throughput in MB/s. Only applicable to ``gp3`` volumes.
        executor : str, optional
            Workflow executor. Defaults to ``'nextflow'``.
        is_default : bool, optional
            Whether to set the queue as the workspace default. Defaults to
            ``False``.

        Returns
        -------
        queue_id : str
            The Lifebit Platform ID assigned to the newly created queue.

        Raises
        ------
        ValueError
            If the provisioning type, allocation strategy or volume type are
            not recognised, or the allocation strategy is incompatible with
            the provisioning type.
        BadRequestException
            If the API returns a 4xx or 5xx response.
        """
        compute_resources = self._build_compute_resources(
            provisioning_type=provisioning_type,
            allocation_strategy=allocation_strategy,
            max_vcpus=max_vcpus,
            min_vcpus=min_vcpus,
            instance_types=instance_types,
            volume_type=volume_type,
            size=size,
            iops=iops,
            throughput=throughput,
        )
        payload = {
            "id": "",
            "label": label,
            "description": description,
            "executor": executor,
            "status": "ToCreate",
            "environment": {
                "computeEnvironmentName": label,
                "computeResources": compute_resources,
            },
            "templateName": "",
            "templateDescription": "",
            "isDefault": is_default,
        }
        return self._post_job_queue(payload)

    @staticmethod
    def _build_compute_resources(provisioning_type,
                                 allocation_strategy,
                                 max_vcpus,
                                 min_vcpus,
                                 instance_types,
                                 volume_type,
                                 size,
                                 iops,
                                 throughput=None):
        """Validate inputs and build an AWS Batch ``computeResources`` dict.

        Parameters
        ----------
        provisioning_type : str
            One of ``'on-demand'`` or ``'spot'``.
        allocation_strategy : str
            AWS Batch allocation strategy. Must be valid for the chosen
            ``provisioning_type`` (see ``ALLOCATION_STRATEGIES``).
        max_vcpus : int
            Maximum number of vCPUs.
        min_vcpus : int
            Minimum number of vCPUs.
        instance_types : list[str]
            Instance types to allow.
        volume_type : str
            One of ``'gp3'`` or ``'io2'``.
        size : int
            Volume size in GiB.
        iops : int
            Provisioned IOPS for the volume.
        throughput : int or None, optional
            Volume throughput in MB/s. Only applicable to ``gp3`` volumes.

        Returns
        -------
        compute_resources : dict
            The assembled ``computeResources`` dict.

        Raises
        ------
        ValueError
            If the provisioning type, allocation strategy or volume type are
            not recognised, or the allocation strategy is incompatible with
            the provisioning type.
        """
        if provisioning_type not in PROVISIONING_TYPES:
            valid = ', '.join(PROVISIONING_TYPES.keys())
            raise ValueError(
                f"Unknown provisioning type '{provisioning_type}'. "
                f"Valid options are: {valid}"
            )
        allowed_strategies = ALLOCATION_STRATEGIES[provisioning_type]
        if allocation_strategy not in allowed_strategies:
            valid = ', '.join(allowed_strategies)
            raise ValueError(
                f"Allocation strategy '{allocation_strategy}' is not valid for "
                f"'{provisioning_type}' provisioning. Valid options are: {valid}"
            )
        if volume_type not in VOLUME_SPECS:
            valid = ', '.join(VOLUME_SPECS.keys())
            raise ValueError(
                f"Unknown volume type '{volume_type}'. Valid options are: {valid}"
            )
        if max_vcpus < 0 or max_vcpus > MAX_VCPUS_LIMIT:
            raise ValueError(
                f"max_vcpus ({max_vcpus}) must be between 0 and {MAX_VCPUS_LIMIT}."
            )
        if min_vcpus < 0 or min_vcpus > MAX_VCPUS_LIMIT:
            raise ValueError(
                f"min_vcpus ({min_vcpus}) must be between 0 and {MAX_VCPUS_LIMIT}."
            )
        if min_vcpus > max_vcpus:
            raise ValueError(
                f"min_vcpus ({min_vcpus}) cannot be greater than max_vcpus ({max_vcpus})."
            )
        if not instance_types:
            raise ValueError("At least one instance type is required.")
        invalid = [t for t in instance_types if t not in ALL_INSTANCE_TYPES]
        if invalid:
            raise ValueError(
                f"Invalid instance type(s): {', '.join(invalid)}. "
                "Allowed values are 'optimal' or standard/GPU instance types."
            )
        spec = VOLUME_SPECS[volume_type]
        for field, value in (("size", size), ("iops", iops)):
            _, minimum, maximum = spec[field]
            if value < minimum or value > maximum:
                raise ValueError(
                    f"{field} ({value}) must be between {minimum} and {maximum} for volume type '{volume_type}'."
                )
        if spec["throughput"] is not None and throughput is not None:
            _, minimum, maximum = spec["throughput"]
            if throughput < minimum or throughput > maximum:
                raise ValueError(
                    f"throughput ({throughput}) must be between {minimum} and {maximum} for volume type '{volume_type}'."
                )

        resource_type = PROVISIONING_TYPES[provisioning_type]
        volume = {
            "type": volume_type,
            "size": {"usageQuantity": size, "usageUnit": "Gb"},
            "iops": iops,
            "deviceName": "/dev/xvda",
            "deleteOnTermination": False,
            "encrypted": False,
        }
        if volume_type == "gp3" and throughput is not None:
            volume["throughput"] = throughput

        compute_resources = {
            "allocationStrategy": allocation_strategy,
            "instanceTypes": instance_types,
            "maxvCpus": max_vcpus,
            "type": resource_type,
            "minvCpus": min_vcpus,
            "volume": volume,
        }
        if provisioning_type == "spot":
            compute_resources["bidPercentage"] = 100
        return compute_resources

    def count_workspace_compute_environments(self, queues=None):
        """Count the total compute environments across all queues in the workspace.

        System job queues are not counted towards the workspace limit.

        Parameters
        ----------
        queues : list or None, optional
            A list of (non-system) job queue dicts as returned by
            ``get_job_queues(exclude_system_queues=True)``. If ``None``, the
            queues are fetched, excluding system queues.

        Returns
        -------
        count : int
            The total number of compute environments in the workspace.
        """
        if queues is None:
            queues = self.get_job_queues(exclude_system_queues=True)
        return sum(len(q.get('computeEnvironments', [])) for q in queues)

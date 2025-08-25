# cloudos-cli

[![CI_tests](https://github.com/lifebit-ai/cloudos-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/lifebit-ai/cloudos-cli/actions/workflows/ci.yml)

Python package for interacting with CloudOS

---

## Table of Contents

- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
  - [Configure Default Profile](#configure-default-profile)
  - [Configure Named Profile](#configure-named-profile)
  - [Change the Default Profile](#change-the-default-profile)
  - [List Profiles](#list-profiles)
  - [Remove Profile](#remove-profile)
- [Usage](#usage)
  - [Command Line Interface](#command-line-interface)
- [Commands](#commands)
  - [Configure](#configure)
  - [Job](#job)
    - [Submit a Job](#submit-a-job)
    - [Submit a Bash Job](#submit-a-bash-job)
    - [Submit a Bash Array Job](#submit-a-bash-array-job)
    - [Check Job Status](#check-job-status)
    - [Check Job Details](#check-job-details)
    - [List Jobs](#list-jobs)
    - [Abort Jobs](#abort-jobs)
    - [Get Job Logs and Results](#get-job-logs-and-results)
    - [Executor Support](#executor-support)
  - [Workflow](#workflow)
    - [List Workflows](#list-workflows)
    - [Import Workflow](#import-workflow)
  - [Project](#project)
    - [List Projects](#list-projects)
    - [Create Project](#create-project)
  - [Queue](#queue)
    - [List Job Queues](#list-job-queues)
  - [Datasets](#datasets)
    - [List Files](#list-files)
    - [Move Files](#move-files)
    - [Rename Files](#rename-files)
    - [Copy Files](#copy-files)
    - [Link S3 or File Explorer Folders](#link-s3-or-file-explorer-folders)
    - [Create Folder](#create-folder)
    - [Remove Files or Folders](#remove-files-or-folders)
  - [Procurement](#procurement)
    - [List Procurement Images](#list-procurement-images)
    - [Set Procurement Organization Image](#set-procurement-organization-image)
    - [Reset Procurement Organization Image](#reset-procurement-organization-image)
  - [Cromwell](#cromwell)
    - [Manage Cromwell Server](#manage-cromwell-server)
    - [Run WDL Workflows](#run-wdl-workflows)
- [Python API Usage](#python-api-usage)
- [Unit Testing](#unit-testing)

---

## Requirements

CloudOS CLI requires Python 3.9 or higher and several key dependencies for API communication, data processing, and user interface functionality.

The package requires Python >= 3.9 and the following python packages:

```
click>=8.0.1
pandas>=1.3.4
numpy>=1.26.4
requests>=2.26.0
rich_click>=1.8.2
```

---

## Installation

CloudOS CLI can be installed in multiple ways depending on your needs and environment. Choose the method that best fits your workflow.

### Docker image

It is recommended to install it as a docker image using the `Dockerfile` and the `environment.yml` files provided.

To run the existing docker image at `quay.io`:

```bash
docker run --rm -it quay.io/lifebitaiorg/cloudos-cli:latest
```

### From PyPI

The repository is also available from [PyPI](https://pypi.org/project/cloudos-cli/):

```bash
pip install cloudos-cli
```

### From Github

You will need Python >= 3.9 and pip installed.

Clone the repo and install it using pip:

```bash
git clone https://github.com/lifebit-ai/cloudos-cli
cd cloudos-cli
pip install -r requirements.txt
pip install .
```

> NOTE: To be able to call the `cloudos` executable, ensure that the local clone of the `cloudos-cli` folder is included in the `PATH` variable, using for example the command `export PATH="/absolute/path/to/cloudos-cli:$PATH"`.

---

## Configuration

CloudOS CLI uses a profile-based configuration system to store your credentials and settings securely. This eliminates the need to provide authentication details with every command and allows you to work with multiple CloudOS environments.

Configuration will be saved in the $HOME path folder regardless of operating system. Here, a new folder named `.cloudos` will be created, with files `credentials` and `config` also being created. The structure will look like:

```console
$HOME
  └── .cloudos
        ├── credentials     <-- holds API keys
        └── config          <-- holds all other parameters
```

### Configure Default Profile

To facilitate the reuse of required parameters, profiles can be created. 

In order to generate a profile called `default`, the following command can be used:

```console
cloudos configure
```

This will bring in prompts for API, platform URL, project name, platform executor, repository provider, workflow name (if any) and session ID for interactive analysis. This will be the default profile if no other was explicitly set. The default profile allows running all subcommands without adding `--profile` option in the command line.

### Configure Named Profile

In order to generate a named profile, the following command can be used:

```console
cloudos configure --profile {profile-name}
```

The same prompts as before will appear. If there is already a profile with the same name, the set parameters will appear in square brackets, where they can be overwritten or left unmodified by pressing Enter/Return.

> [!NOTE]
> When there is already at least 1 previous profile defined, a new question will appear asking to make the current profile as default

### Change the Default Profile

This can be achieved with:

```console
cloudos configure --profile {other-profile} --make-default
```

### List Profiles

At any time it can be seen how many profiles are present and which is the default:

```console
cloudos configure list-profiles
```

The response will look like:

```console
Available profiles:
 - default (default)
 - third-profile
```

### Remove Profile

Any profile can be remove with:

```console
cloudos configure remove-profile --profile second-profile
```

---

## Usage

CloudOS CLI can be used both as a command-line interface tool for interactive work and as a Python package for scripting and automation.

### Command Line Interface

To get general information about the tool:

```bash
cloudos --help
```
```console
Usage: cloudos [OPTIONS] COMMAND [ARGS]...                                     
                                                                                
 CloudOS python package: a package for interacting with CloudOS.                
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --version      Show the version and exit.                                    │
│ --help         Show this message and exit.                                   │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ bash         CloudOS bash functionality.                                     │
│ configure    CloudOS configuration.                                          │
│ cromwell     Cromwell server functionality: check status, start and stop.    │
│ datasets     CloudOS datasets functionality.                                 │
│ job          CloudOS job functionality: run, check and abort jobs in         │
│              CloudOS.                                                        │
│ procurement  CloudOS procurement functionality.                              │
│ project      CloudOS project functionality: list and create projects in      │
│              CloudOS.                                                        │
│ queue        CloudOS job queue functionality.                                │
│ workflow     CloudOS workflow functionality: list and import workflows.      │
╰──────────────────────────────────────────────────────────────────────────────╯
``` 


This will tell you the implemented commands. Each implemented command has its own subcommands with its own `--help`:

```bash
cloudos job run --help
```
```console
Usage: cloudos job run [OPTIONS]                                                                                       
                                                                                                                        
 Submit a job to CloudOS.                                                                                               
                                                                                                                        
╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ *  --apikey                         -k  TEXT                                   Your CloudOS API key [required]       │
│ *  --cloudos-url                    -c  TEXT                                   The CloudOS url you are trying to     │
│                                                                                access to.                            │
│                                                                                Default=https://cloudos.lifebit.ai.   │
│                                                                                [required]                            │
│ *  --workspace-id                       TEXT                                   The specific CloudOS workspace id.    │
│                                                                                [required]                            │
│ *  --project-name                       TEXT                                   The name of a CloudOS project.        │
│                                                                                [required]                            │
│ *  --workflow-name                      TEXT                                   The name of a CloudOS workflow or     │
│                                                                                pipeline.                             │
│                                                                                [required]                            │
│    --last                                                                      When the workflows are duplicated,    │
│                                                                                use the latest imported workflow (by  │
│                                                                                date).                                │
│    --job-config                         TEXT                                   A config file similar to a            │
│                                                                                nextflow.config file, but only with   │
│                                                                                the parameters to use with your job.  │
│    --parameter                      -p  TEXT                                   A single parameter to pass to the job │
│                                                                                call. It should be in the following   │
│                                                                                form: parameter_name=parameter_value. │
│                                                                                E.g.: -p input=s3://path_to_my_file.  │
│                                                                                You can use this option as many times │
│                                                                                as parameters you want to include.    │
│    --nextflow-profile                   TEXT                                   A comma separated string indicating   │
│                                                                                the nextflow profile/s to use with    │
│                                                                                your job.                             │
│    --nextflow-version                   [22.10.8|24.04.4|22.11.1-edge|latest]  Nextflow version to use when          │
│                                                                                executing the workflow in CloudOS.    │
│                                                                                Default=22.10.8.                      │
│    --git-commit                         TEXT                                   The git commit hash to run for the    │
│                                                                                selected pipeline. If not specified   │
│                                                                                it defaults to the last commit of the │
│                                                                                default branch.                       │
│    --git-tag                            TEXT                                   The tag to run for the selected       │
│                                                                                pipeline. If not specified it         │
│                                                                                defaults to the last commit of the    │
│                                                                                default branch.                       │
│    --git-branch                         TEXT                                   The branch to run for the selected    │
│                                                                                pipeline. If not specified it         │
│                                                                                defaults to the last commit of the    │
│                                                                                default branch.                       │
│    --job-name                           TEXT                                   The name of the job. Default=new_job. │
│    --resumable                                                                 Whether to make the job able to be    │
│                                                                                resumed or not.                       │
│    --do-not-save-logs                                                          Avoids process log saving. If you     │
│                                                                                select this option, your job process  │
│                                                                                logs will not be stored.              │
│    --job-queue                          TEXT                                   Name of the job queue to use with a   │
│                                                                                batch job.                            │
│    --instance-type                      TEXT                                   The type of compute instance to use   │
│                                                                                as master node.                       │
│                                                                                Default=c5.xlarge(aws)|Standard_D4as… │
│    --instance-disk                      INTEGER                                The disk space of the master node     │
│                                                                                instance, in GB. Default=500.         │
│    --storage-mode                       TEXT                                   Either 'lustre' or 'regular'.         │
│                                                                                Indicates if the user wants to select │
│                                                                                regular or lustre storage.            │
│                                                                                Default=regular.                      │
│    --lustre-size                        INTEGER                                The lustre storage to be used when    │
│                                                                                --storage-mode=lustre, in GB. It      │
│                                                                                should be 1200 or a multiple of it.   │
│                                                                                Default=1200.                         │
│    --wait-completion                                                           Whether to wait to job completion and │
│                                                                                report final job status.              │
│    --wait-time                          INTEGER                                Max time to wait (in seconds) to job  │
│                                                                                completion. Default=3600.             │
│    --wdl-mainfile                       TEXT                                   For WDL workflows, which mainFile     │
│                                                                                (.wdl) is configured to use.          │
│    --wdl-importsfile                    TEXT                                   For WDL workflows, which importsFile  │
│                                                                                (.zip) is configured to use.          │
│    --cromwell-token                 -t  TEXT                                   Specific Cromwell server              │
│                                                                                authentication token. Currently, not  │
│                                                                                necessary as apikey can be used       │
│                                                                                instead, but maintained for backwards │
│                                                                                compatibility.                        │
│    --repository-platform                [github|gitlab|bitbucketServer]        Name of the repository platform of    │
│                                                                                the workflow. Default=github.         │
│    --execution-platform                 [aws|azure|hpc]                        Name of the execution platform        │
│                                                                                implemented in your CloudOS.          │
│                                                                                Default=aws.                          │
│    --hpc-id                             TEXT                                   ID of your HPC, only applicable when  │
│                                                                                --execution-platform=hpc.             │
│                                                                                Default=660fae20f93358ad61e0104b      │
│    --azure-worker-instance-type         TEXT                                   The worker node instance type to be   │
│                                                                                used in azure.                        │
│                                                                                Default=Standard_D4as_v4              │
│    --azure-worker-instance-disk         INTEGER                                The disk size in GB for the worker    │
│                                                                                node to be used in azure. Default=100 │
│    --azure-worker-instance-spot                                                Whether the azure worker nodes have   │
│                                                                                to be spot instances or not.          │
│    --cost-limit                         FLOAT                                  Add a cost limit to your job.         │
│                                                                                Default=30.0 (For no cost limit       │
│                                                                                please use -1).                       │
│    --accelerate-file-staging                                                   Enables AWS S3 mountpoint for quicker │
│                                                                                file staging.                         │
│    --use-private-docker-repository                                             Allows to use private docker          │
│                                                                                repository for running jobs. The      │
│                                                                                Docker user account has to be already │
│                                                                                linked to CloudOS.                    │
│    --verbose                                                                   Whether to print information messages │
│                                                                                or not.                               │
│    --request-interval                   INTEGER                                Time interval to request (in seconds) │
│                                                                                the job status. For large jobs is     │
│                                                                                important to use a high number to     │
│                                                                                make fewer requests so that is not    │
│                                                                                considered spamming by the API.       │
│                                                                                Default=30.                           │
│    --disable-ssl-verification                                                  Disable SSL certificate verification. │
│                                                                                Please, remember that this option is  │
│                                                                                not generally recommended for         │
│                                                                                security reasons.                     │
│    --ssl-cert                           TEXT                                   Path to your SSL certificate file.    │
│    --profile                            TEXT                                   Profile to use from the config file   │
│    --help                                                                      Show this message and exit.           │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

```

---

## Commands

### Configure

See [Configuration](#configuration) section above for detailed information on setting up profiles and managing your CloudOS CLI configuration.

---

### Job

The job commands allow you to submit, monitor, and manage computational workflows on CloudOS. This includes both Nextflow pipelines and bash scripts, with support for various execution platforms.

#### Submit a Job

You can submit Nextflow workflows to CloudOS using either configuration files or command-line parameters. Jobs can be configured with specific compute resources, execution platforms, parameter etc..

First, configure your local environment to ease parameters input. We will try to submit a small toy example already available.

```bash
WORKFLOW_NAME="rnatoy"
JOB_PARAMS="cloudos_cli/examples/rnatoy.config"
```

As you can see, a file with the job parameters is used to configure the job. This file could be a regular `nextflow.config` file or any file with the following structure:

```
params {
    reads   = s3://lifebit-featured-datasets/pipelines/rnatoy-data
    genome  = s3://lifebit-featured-datasets/pipelines/rnatoy-data/ggal_1_48850000_49020000.Ggal71.500bpflank.fa
    annot   = s3://lifebit-featured-datasets/pipelines/rnatoy-data/ggal_1_48850000_49020000.bed.gff
}
```

To submit our job:

```bash
cloudos job run \
    --workflow-name $WORKFLOW_NAME \
    --job-config $JOB_PARAMS \
    --profile <my_profile> \
    --resumable
```

In addition, parameters can also be specified using the command-line `-p` or `--parameter`. For instance, the previous command is equivalent to:

```bash
cloudos job run \
    --workflow-name $WORKFLOW_NAME \
    --job-config $JOB_PARAMS \
    --profile <my_profile> \
    --parameter reads=s3://lifebit-featured-datasets/pipelines/rnatoy-data \
    --parameter genome=s3://lifebit-featured-datasets/pipelines/rnatoy-data/ggal_1_48850000_49020000.Ggal71.500bpflank.fa \
    --parameter annot=s3://lifebit-featured-datasets/pipelines/rnatoy-data/ggal_1_48850000_49020000.bed.gff \
    --resumable
```

> NOTE: options `--job-config` and `--parameter` are completely compatible and complementary, so you can use a `--job-config` and adding additional parameters using `--parameter` in the same call.

#### Submit a Bash Job

Execute bash scripts on CloudOS for custom processing workflows. Bash jobs allow you to run shell commands with custom parameters and are ideal for data preprocessing or simple computational tasks.

A bash job can be sent to CloudOS using the command `bash` and the subcommand `job`. In this case, the `--workflow-name` must be a bash job already present in the platform. Bash jobs are identified by bash icon (unlike Nextflow jobs, which are identified with Nextflow icon).

```bash
WORKFLOW_NAME="ubuntu"  # This should be a bash workflow
cloudos bash job \
    --cloudos-url $CLOUDOS \
    --profile my_profile \
    --workflow-name $WORKFLOW_NAME \
    --parameter -test_variable=value \
    --parameter --flag=activate \
    --parameter send="yes" \
    --job-name $JOB_NAME \
    --command "echo 'send' > new_file.txt" \
    --resumable
```

#### Submit a Bash Array Job

Run parallel bash jobs across multiple samples or datasets using array files. This is particularly useful for processing large datasets where each row represents a separate computational task.

When running a bash array job, you can specify an array file containing sample information and process each row in parallel. The CLI validates column names and provides flexible parameter mapping.

```bash
cloudos bash array-job \
    --profile my_profile \
    --workflow-name $WORKFLOW_NAME \
    --array-file <ARRAY_FILE> \
    --separator comma \
    --array-parameter file=bgen \
    --command "echo {file}"
```

See `cloudos bash array-job --help` for all available options and advanced configuration.

#### Check Job Status

Monitor the current status of your submitted jobs to track progress and identify any issues. Job status updates in real-time as your workflow progresses through different execution stages.

```bash
cloudos job status \
    --profile my_profile \
    --job-id <JOB_ID>
```

#### Check Job Details

Retrieve comprehensive information about a specific job, including parameters, resources, and execution details. This is useful for debugging, auditing, or recreating job configurations.

```bash
cloudos job details \
    --apikey $MY_API_KEY \
    --job-id <JOB_ID>
```

Or with a profile:

```bash
cloudos job details --profile <PROFILE> --job-id <JOB_ID>
```

#### List Jobs

Get an overview of all jobs in your workspace with filtering and export options. You can export job lists as CSV or JSON for further analysis and reporting.

```bash
cloudos job list \
    --profile my_profile \
    --output-format csv \
    --all-fields
```

#### Abort Jobs

Stop running or queued jobs when needed. This is useful for canceling long-running jobs or stopping jobs that are no longer needed.

```bash
cloudos job abort \
    --profile my_profile \
    --job-ids "<JOB_ID_1>,<JOB_ID_2>"
```

#### Get Job Logs and Results

Access job execution logs and output files for debugging and result retrieval. Logs provide detailed information about job execution, while results contain the output files generated by your workflows.

```bash
cloudos job logs \
    --profile my_profile \
    --job-id <JOB_ID>
```

#### Executor Support

CloudOS supports multiple execution platforms including AWS Batch, Azure, and HPC systems. Choose the appropriate executor based on your computational needs and available infrastructure.

AWS Batch is the default executor. Use `--job-queue` to specify a queue, or let CloudOS select one.

To use Azure:

```bash
cloudos job run ... --execution-platform azure
```

To use HPC:

```bash
cloudos job run ... --execution-platform hpc --hpc-id <HPC_ID>
```

---

### Workflow

Manage and organize your computational pipelines within CloudOS. The workflow commands allow you to browse available pipelines and import new ones from external repositories.

#### List Workflows

Browse all available workflows in your CloudOS workspace. This helps you discover existing pipelines and understand what computational tools are available for your projects.

```bash
cloudos workflow list \
    --profile my_profile \
    --output-format csv \
    --all-fields
```

#### Import Workflow

Add new Nextflow workflows to your CloudOS workspace from GitHub, GitLab, or Bitbucket repositories. This allows you to expand your available computational tools and share workflows across teams.

```bash
cloudos workflow import \
    --profile my_profile \
    --workflow-url <WORKFLOW_URL> \
    --workflow-name <NEW_NAME> \
    --repository-platform github
```

---

### Project

Organize your work and data within CloudOS using projects. Projects provide logical separation of datasets, workflows, and results, making it easier to manage complex research initiatives.

#### List Projects

View all projects available in your CloudOS workspace to understand your organizational structure and access permissions.

```bash
cloudos project list \
    --profile my_profile \
    --output-format csv \
    --all-fields
```

#### Create Project

Establish new projects for organizing your research work. Projects serve as containers for datasets, analysis results, and collaborative work.

```bash
cloudos project create \
    --profile my_profile \
    --new-project "My New Project"
```

---

### Queue

Monitor and manage computational resources and job queues within your CloudOS workspace. Understanding available queues helps optimize job scheduling and resource utilization.

#### List Job Queues

View available computational queues and their configurations. This information is essential for understanding available resources and optimizing job submissions.

```bash
cloudos queue list \
    --profile my_profile \
    --output-format json \
    --output-basename "available_queues"
```

---

### Datasets

Manage files and folders within your CloudOS File Explorer programmatically. These commands provide comprehensive file management capabilities for organizing research data and results.

#### List Files

Browse files and folders within your CloudOS projects. Use the `--details` flag to get comprehensive information about file ownership, sizes, and modification dates.

```bash
cloudos datasets ls <path> --profile <profile>
```

#### Move Files

Relocate files and folders within the same project or across different projects. This is useful for reorganizing data and moving results to appropriate locations.

Within the same project:

```bash
cloudos datasets mv <source_path> <destination_path> --profile <profile>
```

Across projects:

```bash
cloudos datasets mv <source_path> <destination_path> --profile <profile> --destination-project-name <project>
```

#### Rename Files

Change file and folder names while keeping them in the same location. This helps maintain organized file structures and clear naming conventions.

```bash
cloudos datasets rename <path> <new_name> --profile my_profile 
```

#### Copy Files

Create copies of files and folders for backup purposes or to share data across projects without moving the original files.

Within the same project:

```bash
cloudos datasets cp <source_path> <destination_path> --profile <profile>
```

Across projects:

```bash
cloudos datasets cp <source_path> <destination_path> --profile <profile> --destination-project-name <project>
```

#### Link S3 or File Explorer Folders

Connect external S3 buckets or internal File Explorer folders to your interactive analysis sessions. This provides direct access to data without needing to copy files.

```bash
cloudos datasets link <S3_OR_FILE_EXPLORER_PATH> --profile <profile> [--session-id <SESSION_ID>]
```

#### Create Folder

Create new organizational folders within your projects to maintain structured data hierarchies.

```bash
cloudos datasets mkdir <new_folder_path> --profile my_profile 
```

#### Remove Files or Folders

Delete unnecessary files or empty folders from your File Explorer. Note that this removes files from CloudOS but not from underlying cloud storage.

```bash
cloudos datasets rm <path> --profile my_profile
```

---

### Procurement

Manage container images and computational resources at the organizational level within CloudOS. These commands are primarily used by administrators to configure custom compute environments.

#### List Procurement Images

View available container images across organizations within your procurement. This helps understand what computational environments are available for different teams.

```bash
cloudos procurement images ls \
    --cloudos-url $CLOUDOS \
    --apikey $MY_API_KEY \
    --procurement-id <PROCUREMENT_ID>
```

#### Set Procurement Organization Image

Configure custom container images for specific organizations. This allows teams to use specialized computational environments tailored to their needs.

```bash
cloudos procurement images set \
    --cloudos-url $CLOUDOS \
    --apikey $MY_API_KEY \
    --procurement-id <PROCUREMENT_ID> \
    --organisation-id <ORG_ID> \
    --image-type "JobDefault" \
    --provider "aws" \
    --region "us-east-1" \
    --image-id "ami-0123456789abcdef0" \
    --image-name "custom-image-name"
```

#### Reset Procurement Organization Image

Restore default CloudOS container images for an organization, removing any custom configurations.

```bash
cloudos procurement images reset \
    --cloudos-url $CLOUDOS \
    --apikey $MY_API_KEY \
    --procurement-id <PROCUREMENT_ID> \
    --organisation-id <ORG_ID> \
    --image-type "JobDefault" \
    --provider "aws" \
    --region "us-east-1"
```

---

<!-- ### Cromwell

Manage Cromwell servers for running WDL (Workflow Description Language) pipelines. Cromwell is required for executing WDL workflows and needs to be running before submitting WDL jobs.

#### Manage Cromwell Server

Control the Cromwell server lifecycle within your CloudOS workspace. The server must be running to execute WDL workflows and should be stopped when not in use to conserve resources.

Check status:

```bash
cloudos cromwell status --cloudos-url <CLOUDOS_URL> --apikey <API_KEY> --workspace-id <WORKSPACE_ID>
```

Start:

```bash
cloudos cromwell start --cloudos-url <CLOUDOS_URL> --apikey <API_KEY> --workspace-id <WORKSPACE_ID>
```

Stop:

```bash
cloudos cromwell stop --cloudos-url <CLOUDOS_URL> --apikey <API_KEY> --workspace-id <WORKSPACE_ID>
```

#### Run WDL Workflows

Execute WDL (Workflow Description Language) pipelines using the Cromwell server. WDL workflows require different configuration parameters compared to Nextflow pipelines.

Add `--wdl-mainfile` and optionally `--wdl-importsfile` to `cloudos job run`:

```bash
cloudos job run \
  --cloudos-url <CLOUDOS_URL> \
  --apikey <API_KEY> \
  --workspace-id <WORKSPACE_ID> \
  --project-name <PROJECT_NAME> \
  --workflow-name <WORKFLOW_NAME> \
  --wdl-mainfile <MAINFILE> \
  --wdl-importsfile <IMPORTSFILE> \
  --job-config <JOB_PARAMS> \
  --wait-completion
``` -->

---

## Python API Usage

Integrate CloudOS functionality directly into your Python scripts for automated workflows and custom applications. The Python API provides programmatic access to all CloudOS CLI features.

You can use the package in your own Python scripts:

```python
import cloudos_cli.jobs.job as jb

j = jb.Job(cloudos_url, apikey, None, workspace_id, project_name, workflow_name)
j_id = j.send_job(job_config)
j_status = j.get_job_status(j_id)
```

See the detailed examples in the sections above for comprehensive Python API usage patterns.

---

## Unit Testing

Validate CloudOS CLI functionality and ensure code quality through comprehensive unit testing. The test suite covers all major functionality and API interactions.

Unit tests require:

```
pytest>=6.2.5
requests-mock>=1.9.3
responses>=0.21.0
mock>=3.0.5
```

Run tests from the `cloudos-cli` main folder:

```bash
python -m pytest -s -v
```

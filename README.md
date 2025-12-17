# cloudos-cli

[![CI_tests](https://github.com/lifebit-ai/cloudos-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/lifebit-ai/cloudos-cli/actions/workflows/ci.yml)

Python package for interacting with CloudOS

---

## Table of Contents

- [cloudos-cli](#cloudos-cli)
  - [Table of Contents](#table-of-contents)
  - [Requirements](#requirements)
  - [Installation](#installation)
    - [From PyPI](#from-pypi)
    - [Docker Image](#docker-image)
    - [From Github](#from-github)
  - [Usage](#usage)
  - [Configuration](#configuration)
    - [Configure Default Profile](#configure-default-profile)
    - [Configure Named Profile](#configure-named-profile)
    - [Change the Default Profile](#change-the-default-profile)
    - [List Profiles](#list-profiles)
    - [Remove Profile](#remove-profile)
  - [Commands](#commands)
    - [Configure](#configure)
    - [Project](#project)
      - [List Projects](#list-projects)
      - [Create Projects](#create-projects)
    - [Queue](#queue)
      - [List Queues](#list-queues)
    - [Workflow](#workflow)
      - [List All Available Workflows](#list-all-available-workflows)
      - [Import a Nextflow Workflow](#import-a-nextflow-workflow)
    - [Nextflow Jobs](#nextflow-jobs)
      - [Submit a Job](#submit-a-job)
      - [Check Job Status](#check-job-status)
      - [List Jobs](#list-jobs)
      - [Get Job Results](#get-job-results)
      - [Clone or Resume Job](#clone-or-resume-job)
      - [Abort Jobs](#abort-jobs)
      - [Get Job Details](#get-job-details)
      - [Get Job Workdir](#get-job-workdir)
      - [Get Job Logs](#get-job-logs)
      - [Get Job Costs](#get-job-costs)
      - [Get Job Related Analyses](#get-job-related-analyses)
      - [Delete Job Results](#delete-job-results)
    - [Bash Jobs](#bash-jobs)
      - [Send Array Job](#send-array-job)
      - [Submit a Bash Array Job](#submit-a-bash-array-job)
        - [Options](#options)
          - [Array File](#array-file)
          - [Separator](#separator)
          - [List Columns](#list-columns)
          - [Array File Project](#array-file-project)
          - [Disable Column Check](#disable-column-check)
          - [Array Parameter](#array-parameter)
          - [Custom Script Path](#custom-script-path)
          - [Custom Script Project](#custom-script-project)
      - [Use multiple projects for files in `--parameter` option](#use-multiple-projects-for-files-in---parameter-option)
    - [Link](#link)
      - [Link Folders to Interactive Analysis](#link-folders-to-interactive-analysis)
    - [Datasets](#datasets)
      - [List Files](#list-files)
      - [Move Files](#move-files)
      - [Rename Files](#rename-files)
      - [Copy Files](#copy-files)
      - [Link S3 Folders to Interactive Analysis](#link-s3-folders-to-interactive-analysis)
      - [Create Folder](#create-folder)
      - [Remove Files or Folders](#remove-files-or-folders)
    - [Procurement](#procurement)
      - [List Procurement Images](#list-procurement-images)
      - [Set Procurement Organization Image](#set-procurement-organization-image)
      - [Reset Procurement Organization Image](#reset-procurement-organization-image)
    - [Cromwell and WDL Pipeline Support](#cromwell-and-wdl-pipeline-support)
      - [Manage Cromwell Server](#manage-cromwell-server)
      - [Run WDL Workflows](#run-wdl-workflows)
  - [Python API Usage](#python-api-usage)
      - [Running WDL pipelines using your own scripts](#running-wdl-pipelines-using-your-own-scripts)
  - [Unit Testing](#unit-testing)

---

## Requirements

CloudOS CLI requires Python 3.9 or higher and several key dependencies for API communication, data processing, and user interface functionality.

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

### From PyPI

The repository is also available from [PyPI](https://pypi.org/project/cloudos-cli/):

```bash
pip install cloudos-cli
```

To update CloudOS CLI to the latest version using pip, you can run:

```bash
pip install --upgrade cloudos-cli
```

To check your current version:

```bash
cloudos --version
```

### Docker Image

It is recommended to install it as a docker image using the `Dockerfile` and the `environment.yml` files provided.

To run the existing docker image at `quay.io`:

```bash
docker run --rm -it quay.io/lifebitaiorg/cloudos-cli:latest
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

## Usage

CloudOS CLI can be used both as a command-line interface tool for interactive work and as a Python package for scripting and automation.

To get general information about the tool:

```bash
cloudos --help
```
```console
                                                                                                                        
 Usage: cloudos [OPTIONS] COMMAND [ARGS]...                                                                             
                                                                                                                        
 CloudOS python package: a package for interacting with CloudOS.                                                        
                                                                                                                        
╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --debug        Show detailed error information and tracebacks                                                        │
│ --version      Show the version and exit.                                                                            │
│ --help         Show this message and exit.                                                                           │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ bash               CloudOS bash functionality.                                                                       │
│ configure          CloudOS configuration.                                                                            │
│ cromwell           Cromwell server functionality: check status, start and stop.                                      │
│ datasets           CloudOS datasets functionality.                                                                   │
│ job                CloudOS job functionality: run, check and abort jobs in CloudOS.                                  │
│ procurement        CloudOS procurement functionality.                                                                │
│ project            CloudOS project functionality: list and create projects in CloudOS.                               │
│ queue              CloudOS job queue functionality.                                                                  │
│ workflow           CloudOS workflow functionality: list and import workflows.                                        │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

This will tell you the implemented commands. Each implemented command has its own subcommands with its own `--help`:

```bash
cloudos job list --help
```
```console                                                                                                      Usage: cloudos job list [OPTIONS]                                                                          
                                                                                                            
 Collect workspace jobs from a CloudOS workspace in CSV or JSON format.                                     
                                                                                                            
╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────╮
│ *  --apikey                    -k  TEXT        Your CloudOS API key [required]                           │
│ *  --cloudos-url               -c  TEXT        The CloudOS url you are trying to access to.              │
│                                                Default=https://cloudos.lifebit.ai.                       │
│                                                [required]                                                │
│ *  --workspace-id                  TEXT        The specific CloudOS workspace id. [required]             │
│    --output-basename               TEXT        Output file base name to save jobs list. Default=joblist  │
│    --output-format                 [csv|json]  The desired file format (file extension) for the output.  │
│                                                For json option --all-fields will be automatically set to │
│                                                True. Default=csv.                                        │
│    --all-fields                                Whether to collect all available fields from jobs or just │
│                                                the preconfigured selected fields. Only applicable when   │
│                                                --output-format=csv. Automatically enabled for json       │
│                                                output.                                                   │
│    --last-n-jobs                   TEXT        The number of last workspace jobs to retrieve. You can    │
│                                                use 'all' to retrieve all workspace jobs. Default=30.     │
│    --page                          INTEGER     Response page to retrieve. If --last-n-jobs is set, then  │
│                                                --page value corresponds to the first page to retrieve.   │
│                                                Default=1.                                                │
│    --archived                                  When this flag is used, only archived jobs list is        │
│                                                collected.                                                │
│    --filter-status                 TEXT        Filter jobs by status (e.g., completed, running, failed,  │
│                                                aborted).                                                 │
│    --filter-job-name               TEXT        Filter jobs by job name ( case insensitive ).             │
│    --filter-project                TEXT        Filter jobs by project name.                              │
│    --filter-workflow               TEXT        Filter jobs by workflow/pipeline name.                    │
│    --last                                      When workflows are duplicated, use the latest imported    │
│                                                workflow (by date).                                       │
│    --filter-job-id                 TEXT        Filter jobs by specific job ID.                           │
│    --filter-only-mine                          Filter to show only jobs belonging to the current user.   │
│    --filter-queue                  TEXT        Filter jobs by queue name. Only applies to jobs running   │
│                                                in batch environment. Non-batch jobs are preserved in     │
│                                                results.                                                  │
│    --filter-owner                  TEXT        Filter jobs by owner username.                            │
│    --verbose                                   Whether to print information messages or not.             │
│    --disable-ssl-verification                  Disable SSL certificate verification. Please, remember    │
│                                                that this option is not generally recommended for         │
│                                                security reasons.                                         │
│    --ssl-cert                      TEXT        Path to your SSL certificate file.                        │
│    --debug                                     Show detailed error information and tracebacks               │
│    --profile                       TEXT        Profile to use from the config file                          │
│    --help                                      Show this message and exit.                                  │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

In the same way, each implemented command has its own subcommands with its own `--debug` flag, that will print the full traceback for detailed error debugging. When this flag is not activated, the errors are presented in short descriptive format.

---

## Configuration

CloudOS CLI uses a profile-based configuration system to store your credentials and settings securely. This eliminates the need to provide authentication details with every command and allows you to work with multiple CloudOS environments.

Configuration will be saved in the $HOME path folder regardless of operating system. Here, a new folder named `.cloudos` will be created, with files `credentials` and `config` also being created. The structure will look like:

```console
$HOME
    └── .cloudos/
          ├── credentials     # Stores API keys
          └── config          # Stores all other parameters
```

### Configure Default Profile

To facilitate the reuse of required parameters, you can create profiles. 

To generate a profile called `default`, use the following command:

```bash
cloudos configure
```

This will prompt you for API key, platform URL, project name, platform executor, repository provider, workflow name (if any), and session ID for interactive analysis. This becomes the default profile if no other profile is explicitly set. The default profile allows running all subcommands without adding the `--profile` option.

### Configure Named Profile

To generate a named profile, use the following command:

```bash
cloudos configure --profile {profile-name}
```

The same prompts will appear. If a profile with the same name already exists, the current parameters will appear in square brackets and can be overwritten or left unchanged by pressing Enter/Return.

> [!NOTE]
> When there is already at least 1 previous profile defined, a new question will appear asking to make the current profile as default

### Change the Default Profile

Change the default profile with:

```bash
cloudos configure --profile {other-profile} --make-default
```

### List Profiles

View all configured profiles and identify the default:

```bash
cloudos configure list-profiles
```

The response will look like:

```console
Available profiles:
 - default (default)
 - second-profile
 - third-profile
```

### Remove Profile

Remove any profile with:

```bash
cloudos configure remove-profile --profile second-profile
```

---

## Commands

### Configure

See [Configuration](#configuration) section above for detailed information on setting up profiles and managing your CloudOS CLI configuration.



### Project

Projects in CloudOS provide logical separation of datasets, workflows, and results, making it easier to manage complex research initiatives. You can list all available projects or create new ones using the CLI.

#### List Projects

You can get a summary of all available workspace projects in two different formats:
- **CSV**: A table with a minimum predefined set of columns by default, or all available columns using the `--all-fields` parameter
- **JSON**: All available information from projects in JSON format

To get a CSV table with all available projects for a given workspace:

```bash
cloudos project list --profile my_profile --output-format csv --all-fields
```

The expected output is something similar to:

```console
Executing list...
	Project list collected with a total of 320 projects.
	Project list saved to project_list.csv
```

To get the same information in JSON format:

```bash
cloudos project list --profile my_profile --output-format json
```

#### Create Projects

You can create a new project in your CloudOS workspace using the `project create` command. This command requires the name of the new project and will return the project ID upon successful creation.

```bash
cloudos project create --profile my_profile --new-project "My New Project"
```

The expected output is something similar to:

```console
	Project "My New Project" created successfully with ID: 64f1a23b8e4c9d001234abcd
```


### Queue

Job queues are required for running jobs using AWS batch executor. The available job queues in your CloudOS workspace are listed in the "Compute Resources" section in "Settings". You can get a summary of all available workspace job queues in two formats:
- **CSV**: A table with a selection of the available job queue information. You can get all information using the `--all-fields` flag
- **JSON**: All available information from job queues in JSON format

#### List Queues

This command allows you to view available computational queues and their configurations. Example command for getting all available job queues in JSON format:

```bash
cloudos queue list --profile my_profile --output-format json --output-basename "available_queues"
```

```console
Executing list...
	Job queue list collected with a total of 5 queues.
	Job queue list saved to available_queues.json
```

This command will output the list of available job queues in JSON format and save it to a file named `available_queues.json`. You can use `--output-format csv` for a CSV file, or omit `--output-basename` to print to the console.

> NOTE: The queue name that is visible in CloudOS and must be used with the `--job-queue` parameter is the one in the `label` field.

**Job queues for platform workflows**

Platform workflows (those provided by CloudOS in your workspace as modules) run on separate and specific AWS batch queues. Therefore, CloudOS will automatically assign the valid queue and you should not specify any queue using the `--job-queue` parameter. Any attempt to use this parameter will be ignored. Examples of such platform workflows are "System Tools" and "Data Factory" workflows.


### Workflow

#### List All Available Workflows

You can get a summary of all available workspace workflows in two different formats:
- **CSV**: A table with a minimum predefined set of columns by default, or all available columns using the `--all-fields` parameter
- **JSON**: All available information from workflows in JSON format

To get a CSV table with all available workflows for a given workspace:

```bash
cloudos workflow list --profile my_profile --output-format csv --all-fields
```

The expected output is something similar to:

```console
Executing list...
	Workflow list collected with a total of 609 workflows.
	Workflow list saved to workflow_list.csv
```

To get the same information in JSON format:

```bash
cloudos workflow list --profile my_profile --output-format json
```

```console
Executing list...
	Workflow list collected with a total of 609 workflows.
	Workflow list saved to workflow_list.json
```

The collected workflows are those that can be found in the "WORKSPACE TOOLS" section in CloudOS.

#### Import a Nextflow Workflow

You can import new workflows to your CloudOS workspaces. The requirements are:

- The workflow must be a Nextflow pipeline
- The workflow repository must be located at GitHub, GitLab or BitBucket Server (specified by the `--repository-platform` option. Available options: `github`, `gitlab` and `bitbucketServer`)
- If your repository is private, you must have access to the repository and have linked your GitHub, Gitlab or Bitbucket server accounts to CloudOS

**Usage of the workflow import command**

To import GitHub workflows to CloudOS:

```bash
# Example workflow to import: https://github.com/lifebit-ai/DeepVariant
cloudos workflow import --profile my_profile --workflow-url "https://github.com/lifebit-ai/DeepVariant" --workflow-name "new_name_for_the_github_workflow" --repository-platform github
```

The expected output will be:

```console
CloudOS workflow functionality: list and import workflows.

Executing workflow import...

	Only Nextflow workflows are currently supported.

	Workflow test_import_github_3 was imported successfully with the following ID: 6616a8cb454b09bbb3d9dc20
```

Optionally, you can add a link to your workflow documentation by providing the URL using the `--workflow-docs-link` parameter:

```bash
cloudos workflow import --profile my_profile --workflow-url "https://github.com/lifebit-ai/DeepVariant" --workflow-name "new_name_for_the_github_workflow" --workflow-docs-link "https://github.com/lifebit-ai/DeepVariant/blob/master/README.md" --repository-platform github
```

> NOTE: Importing workflows using cloudos-cli is not yet available in all CloudOS workspaces. If you try to use this feature in a non-prepared workspace you will get the following error message: `It seems your API key is not authorised. Please check if your workspace has support for importing workflows using cloudos-cli`.


### Nextflow Jobs

The job commands allow you to submit, monitor, and manage computational workflows on CloudOS. This includes both Nextflow pipelines and bash scripts, with support for various execution platforms.

#### Submit a Job

You can submit Nextflow workflows to CloudOS using either configuration files or command-line parameters. Jobs can be configured with specific compute resources, execution platforms, parameters, etc.

First, configure your local environment to ease parameter input. We will try to submit a small toy example already available:

```bash
cloudos job run --profile my_profile --workflow-name rnatoy --job-config cloudos_cli/examples/rnatoy.config --resumable
```

As you can see, a file with the job parameters is used to configure the job. This file could be a regular `nextflow.config` file or any file with the following structure:

```
params {
        reads   = s3://lifebit-featured-datasets/pipelines/rnatoy-data
        annot   = s3://lifebit-featured-datasets/pipelines/rnatoy-data/ggal_1_48850000_49020000.bed.gff
}
```

In addition, parameters can also be specified using the command-line `-p` or `--parameter`. For instance:

```bash
cloudos job run \
  --profile my_profile \
  --workflow-name rnatoy \
  --parameter reads=s3://lifebit-featured-datasets/pipelines/rnatoy-data \
  --parameter genome=s3://lifebit-featured-datasets/pipelines/rnatoy-data/ggal_1_48850000_49020000.Ggal71.500bpflank.fa \
  --parameter annot=s3://lifebit-featured-datasets/pipelines/rnatoy-data/ggal_1_48850000_49020000.bed.gff \
  --resumable
```

> NOTE: options `--job-config` and `--parameter` are completely compatible and complementary, so you can use a `--job-config` and add additional parameters using `--parameter` in the same call.

If everything went well, you should see something like:

```console
Executing run...
	Job successfully launched to CloudOS, please check the following link: https://cloudos.lifebit.ai/app/advanced-analytics/analyses/62c83a1191fe06013b7ef355
	Your assigned job id is: 62c83a1191fe06013b7ef355
	Your current job status is: initializing
	To further check your job status you can either go to https://cloudos.lifebit.ai/app/advanced-analytics/analyses/62c83a1191fe06013b7ef355 or use the following command:
    cloudos job status \
        --apikey $MY_API_KEY \
        --cloudos-url https://cloudos.lifebit.ai \
        --job-id 62c83a1191fe06013b7ef355
```

As you can see, the current status is `initializing`. This will change while the job progresses. To check the status, just apply the suggested command.

Another option is to set the `--wait-completion` parameter, which runs the same job run command but waits for its completion:

```bash
cloudos job run --profile my_profile --workflow-name rnatoy --job-config cloudos_cli/examples/rnatoy.config --resumable --wait-completion
```

When setting this parameter, you can also set `--request-interval` to a bigger number (default is 30s) if the job is quite large. This will ensure that the status requests are not sent too close from each other and recognized as spam by the API.

If the job takes less than `--wait-time` (3600 seconds by default), the previous command should have an output similar to:

```console
Executing run...
	Job successfully launched to CloudOS, please check the following link: https://cloudos.lifebit.ai/app/advanced-analytics/analyses/62c83a6191fe06013b7ef363
	Your assigned job id is: 62c83a6191fe06013b7ef363
	Please, wait until job completion or max wait time of 3600 seconds is reached.
	Your current job status is: initializing.
	Your current job status is: running.
	Your job took 420 seconds to complete successfully.
```

When there are duplicate `--workflow-name` in the platform, you can add the `--last` flag to use the latest import of that pipeline in the workspace, based on the date.

_For example, the pipeline `lifebit-process` was imported on May 23 2025 and again on May 30 2025; with the `--last` flag, it will use the import of May 30, 2025._

**AWS Executor Support**

CloudOS supports [AWS batch](https://www.nextflow.io/docs/latest/executor.html?highlight=executors#aws-batch) executor by default.
You can specify the AWS batch queue to use from the ones available in your workspace (see [here](#list-job-queues)) by specifying its name with the `--job-queue` parameter. If none is specified, the most recent suitable queue in your workspace will be selected by default.

Example command:

```bash
cloudos job run --profile my_profile --workflow-name rnatoy --job-config cloudos_cli/examples/rnatoy.config --resumable
```

> Note: From cloudos-cli 2.7.0, the default executor is AWS batch. The previous Apache [ignite](https://www.nextflow.io/docs/latest/ignite.html#apache-ignite) executor is being removed progressively from CloudOS, so most likely will not be available in your CloudOS. Cloudos-cli still supports ignite during this period by adding the `--ignite` flag to the `cloudos job run` command. Please note that if you use the `--ignite` flag in a CloudOS without ignite support, the command will fail.

**Azure Execution Platform Support**

CloudOS can also be configured to use Microsoft Azure compute platforms. If your CloudOS is configured to use Azure, you will need to take into consideration the following:

- When sending jobs to CloudOS using `cloudos job run` command, please use the option `--execution-platform azure`
- Due to the lack of AWS batch queues in Azure, `cloudos queue list` command is not working

Other than that, `cloudos-cli` will work very similarly. For instance, this is a typical send job command:

```bash
cloudos job run --profile my_profile --workflow-name rnatoy --job-config cloudos_cli/examples/rnatoy.config --resumable --execution-platform azure
```

**HPC Execution Support**

CloudOS is also prepared to use an HPC compute infrastructure. For such cases, you will need to take into account the following for your job submissions using `cloudos job run` command:

- Use the following parameter: `--execution-platform hpc`
- Indicate the HPC ID using: `--hpc-id XXXX`

Example command:

```bash
cloudos job run --profile my_profile --workflow-name rnatoy --job-config cloudos_cli/examples/rnatoy.config --execution-platform hpc --hpc-id $YOUR_HPC_ID
```

Please note that HPC execution does not support the following parameters and all of them will be ignored:

- `--job-queue`
- `--resumable | --do-not-save-logs`
- `--instance-type` | `--instance-disk` | `--cost-limit`
- `--storage-mode` | `--lustre-size`
- `--wdl-mainfile` | `--wdl-importsfile` | `--cromwell-token`

#### Check Job Status

To check the status of a submitted job, use the following command:

```bash
cloudos job status --profile my_profile --job-id 62c83a1191fe06013b7ef355
```

The expected output should be something similar to:

```console
Executing status...
	Your current job status is: completed

	To further check your job status you can either go to https://cloudos.lifebit.ai/app/advanced-analytics/analyses/62c83a1191fe06013b7ef355 or repeat the command you just used.
```

#### List Jobs

View your workspace jobs in a clean, formatted table directly in your terminal. The table automatically adapts to your terminal width, showing different column sets for optimal viewing. By default, jobs are displayed as a rich table with job IDs and colored visual status indicators.

**Output Formats**

CloudOS CLI provides three output formats for job listings:

- **Table (default)**: Rich formatted table displayed in the terminal with pagination information
- **CSV**: Tabular format with predefined or all available columns using `--all-fields`
- **JSON**: Complete job information in JSON format (`--all-fields` is always enabled)

**Default Behavior**

By default, the command displays the 10 most recent jobs in a formatted table:

```bash
cloudos job list --profile my_profile
```

The output shows a rich table with job information and pagination details:

```console
Executing list...

                                                    Job List                                                    
┏━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┓
┃ Status ┃ Name         ┃ Project     ┃ Owner    ┃ Pipeline     ┃ ID                      ┃ Submit time  ┃
┡━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━┩
│ ✓      │ analysis_run │ test-proj   │ John     │ rnatoy       │ 692ee71c40e98ed6ed529e43│ 2025-12-02   │
│        │              │             │ Doe      │              │                         │ 15:30:45     │
│ ◐      │ test_job     │ research    │ Jane     │ VEP          │ 692ee81d50f98ed7fe639f54│ 2025-12-02   │
│        │              │             │ Smith    │              │                         │ 14:20:30     │
└────────┴──────────────┴─────────────┴──────────┴──────────────┴─────────────────────────┴──────────────┘

Showing 10 of 45 total jobs | Page 1 of 5
```

**Status Indicators**

Jobs are displayed with colored visual status indicators:
- **Green ✓** Completed
- **Grey ◐** Running
- **Red ✗** Failed
- **Orange ■** Aborted
- **Grey ○** Initialising

**Clickable Job IDs**

Job IDs in the table are clickable hyperlinks (when supported by your terminal) that open the job details page in CloudOS.

**Job Listing Control Options**

CloudOS CLI provides two ways to control the number of jobs retrieved:

1. **Pagination Control (Default)**: Use `--page` and `--page-size` for precise pagination
2. **Last N Jobs**: Use `--last-n-jobs` for retrieving the most recent jobs

> [!IMPORTANT]
> **These options are mutually exclusive**. When `--last-n-jobs` is specified, it takes precedence and `--page`/`--page-size` parameters are ignored. A warning message will be displayed if both are provided.

**Pagination Examples**

Retrieve specific pages using `--page` and `--page-size`:

```bash
# Get page 2 with 15 jobs per page
cloudos job list --profile my_profile --page 2 --page-size 15

# Get page 5 with maximum 100 jobs per page (maximum allowed)
cloudos job list --profile my_profile --page 5 --page-size 100
```

> [!NOTE]
> `--page-size` has a maximum limit of 100 jobs per page. Attempting to use a larger value will result in an error.

**Last N Jobs Examples**

Use `--last-n-jobs` to get the most recent jobs:

```bash
# Get the last 50 jobs
cloudos job list --profile my_profile --last-n-jobs 50

# Get all workspace jobs
cloudos job list --profile my_profile --last-n-jobs all
```

**Customizing Table Columns**

You can customize which columns are displayed in the table using the `--table-columns` option:

```bash
# Show only status, name, and cost columns
cloudos job list --profile my_profile --table-columns status,name,cost

# Show a minimal view
cloudos job list --profile my_profile --table-columns status,name,id,submit_time
```

Available columns: `status`, `name`, `project`, `owner`, `pipeline`, `id`, `submit_time`, `end_time`, `run_time`, `commit`, `cost`, `resources`, `storage_type`

> [!NOTE]
> The `--table-columns` option only applies when using the default table output format (stdout).

**File Output Formats**

To save job lists to files instead of displaying them in the terminal:

```bash
# Save as CSV with default columns
cloudos job list --profile my_profile --output-format csv

# Save as CSV with all available fields
cloudos job list --profile my_profile --output-format csv --all-fields

# Save as JSON with complete job data
cloudos job list --profile my_profile --output-format json
```

The expected output for file formats:

```console
Executing list...
	Job list collected with a total of 10 jobs.
	Job list saved to joblist.csv
```

**Filtering Jobs**

You can find specific jobs within your workspace using the filtering options. Filters can be combined to narrow down results and work with all output formats.

**Available filters:**

- **`--filter-status`**: Filter jobs by execution status (e.g., completed, running, failed, aborted, initialising)
- **`--filter-job-name`**: Filter jobs by job name (case insensitive partial matching)
- **`--filter-project`**: Filter jobs by project name (exact match required)
- **`--filter-workflow`**: Filter jobs by workflow/pipeline name (exact match required)
- **`--filter-job-id`**: Filter jobs by specific job ID (exact match required)
- **`--filter-only-mine`**: Show only jobs belonging to the current user
- **`--filter-owner`**: Show only jobs for the specified owner (exact match required, e.g., "John Doe")
- **`--filter-queue`**: Filter jobs by queue name (only applies to batch jobs)

**Filtering Examples**

Using pagination approach (default):

```bash
# Get completed jobs from page 1 (default 10 jobs)
cloudos job list --profile my_profile --filter-status completed

# Get completed jobs from page 2 with 20 jobs per page
cloudos job list --profile my_profile --page 2 --page-size 20 --filter-status completed
```

Using last-n-jobs approach:

```bash
# Get all completed jobs from the last 50 jobs
cloudos job list --profile my_profile --last-n-jobs 50 --filter-status completed
```

Find jobs with "analysis" in the name from a specific project:

```bash
# Using pagination (gets first 10 matching jobs)
cloudos job list --profile my_profile --filter-job-name analysis --filter-project "My Research Project"

# Using last-n-jobs
cloudos job list --profile my_profile --last-n-jobs 100 --filter-job-name analysis --filter-project "My Research Project"
```

Get all jobs using a specific workflow and queue:

```bash
# Using pagination with larger page size
cloudos job list --profile my_profile --page-size 50 --filter-workflow rnatoy --filter-queue high-priority-queue

# Using last-n-jobs to search all jobs
cloudos job list --profile my_profile --last-n-jobs all --filter-workflow rnatoy --filter-queue high-priority-queue
```

> [!NOTE]
> - Project and workflow names must match exactly (case sensitive)
> - Job name filtering is case insensitive and supports partial matches
> - The `--last` flag can be used with `--filter-workflow` when multiple workflows have the same name
> - When filters are applied, pagination information reflects the filtered results

#### Get Job Results

The following command allows you to get the path where CloudOS stores the output files for a job. This can be used only on your user's jobs and for jobs with "completed" status.

Example:
```bash
cloudos job results --profile my_profile --job-id "12345678910"
```
```console
Executing results...
results: s3://path/to/location/of/results/results/
```

You can also link all result directories to an interactive session using the `--link` flag. This will mount all result directories from the job, providing direct access to output files in your interactive session:

```bash
cloudos job results --profile my_profile --job-id "12345678910" --link --session-id your_session_id
```

**Check Results Deletion Status**

You can check the deletion status of a job's results folder using the `--status` flag. This is useful for monitoring the deletion lifecycle of analysis results.

```bash
cloudos job results --status --profile my_profile --job-id "12345678910"
```

The command will display the current status of the results folder. Possible statuses include:
- **available**: Results are available and accessible
- **scheduled for deletion**: Results are scheduled to be deleted
- **deleting**: Results are currently being deleted
- **deleted**: Results have been deleted
- **failed to delete**: Deletion process failed

Example output for available results:
```console
The results of job 1234567890 are in status: available
```

For results in any state other than available, the output includes additional information about when the status changed and who initiated the change:
```console
The results of job 6912036aa6ed001148c96018 are in status: scheduled for deletion
Status changed at: 2025-11-11T14:43:44.416Z
User: Leila Mansouri (leila.mansouri@lifebit.ai)
```

Use the `--verbose` flag to see detailed information including the results folder name, folder ID, creation and update timestamps:
```bash
cloudos job results --status --profile my_profile --job-id "12345678910" --verbose
```

> [!NOTE]
> If results have been completely deleted, the command will report that the results folder was not found, which may indicate that results have been deleted or scheduled for deletion.

#### Clone or Resume Job

The `clone` command allows you to create a new job based on an existing job's configuration, with the ability to override specific parameters.
The `resume` command allows you to create a new job (with the ability to override specific parameters) without re-running every step but only the ones failed/where changes are applied.
These commands are particularly useful for re-running jobs with slight modifications without having to specify all parameters or starting again from scratch.

> [!NOTE]
> Only jobs initially run with `--resumable` can be resumed.

**Basic Usage:**

Clone a job:
```bash
cloudos job clone \
    --profile my_profile \
    --job-id "60a7b8c9d0e1f2g3h4i5j6k7"
```

Resume a job:
```bash
cloudos job resume \
    --profile my_profile \
    --job-id "60a7b8c9d0e1f2g3h4i5j6k7"
```

**With Parameter Overrides:**

Clone with parameter overrides:
```bash
cloudos job clone \
    --profile my_profile \
    --job-id "60a7b8c9d0e1f2g3h4i5j6k7" \
    --job-queue "high-priority-queue" \
    --cost-limit 50.0 \
    --instance-type "c5.2xlarge" \
    --job-name "cloned_analysis_v2" \
    --nextflow-version "24.04.4" \
    --git-branch "dev" \
    --nextflow-profile "production" \
    --do-not-save-logs \
    --accelerate-file-staging \
    --workflow-name "updated-workflow" \
    -p "input=s3://new-bucket/input.csv" \
    -p "output_dir=s3://new-bucket/results"
```

Resume with parameter overrides:
```bash
cloudos job resume \
    --profile my_profile \
    --job-id "60a7b8c9d0e1f2g3h4i5j6k7" \
    --job-queue "high-priority-queue" \
    --cost-limit 50.0 \
    --instance-type "c5.2xlarge" \
    --job-name "resumed_analysis_v2" \
    --nextflow-version "24.04.4" \
    --git-branch "dev" \
    --nextflow-profile "production" \
    -p "input=s3://new-bucket/input.csv" \
    -p "output_dir=s3://new-bucket/results"
```

**Available Override Options:**
- `--job-queue`: Specify a different job queue
- `--cost-limit`: Set a new cost limit (use -1 for no limit)
- `--instance-type`: Change the master instance type
- `--job-name`: Assign a custom name to the cloned/resumed job
- `--nextflow-version`: Use a different Nextflow version
- `--git-branch`: Switch to a different git branch
- `--nextflow-profile`: Change the Nextflow profile
- `--do-not-save-logs`: Enable/disable log saving
- `--accelerate-file-staging`: Enable/disable fusion filesystem
- `--workflow-name`: Use a different workflow
- `-p, --parameter`: Override or add parameters (can be used multiple times)

> [!NOTE]
> Parameters can be overridden or new ones can be added using `-p` option

#### Abort Jobs

Aborts jobs in the CloudOS workspace that are either running or initializing. It can be used with one or more job IDs provided as a comma-separated string using the `--job-ids` parameter.

Example:
```bash
cloudos job abort --profile my_profile --job-ids "680a3cf80e56949775c02f16"
```

```console
Aborting jobs...
        Job 680a3cf80e56949775c02f16 aborted successfully.
```

#### Get Job Details

Details of a job, including cost, status, and timestamps, can be retrieved with:

```bash
cloudos job details --profile my_profile --job-id 62c83a1191fe06013b7ef355
```

The expected output should be something similar to when using the defaults and the details are displayed in the standard output console:

```console
Executing details...
                                                    Job Details
┏━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Field                    ┃ Value                                                                                 ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Status                   │ completed                                                                             │
│ Name                     │ mutSign_vcf_prep_genome_chart_non_resumable                                           │
│ Project                  │ DB-PR-testing                                                                         │
│ Owner                    │ Name Surname                                                                          │
│ Pipeline                 │ MutSign                                                                               │
│ ID                       │ 68bf2178b4ae9f283ea8a0bf                                                              │
│ Submit time              │ 2025-09-08 18:34:26                                                                   │
│ End time                 │ 2025-09-08 18:38:26                                                                   │
│ Run time                 │ 4m 0s                                                                                 │
│ Commit                   │ 11fea740366b92b2858349b764879792272f2996                                              │
│ Cost                     │ $0.2515                                                                               │
│ Master Instance          │ c5.xlarge                                                                             │
│ Storage                  │ 500 GB                                                                                │
│ Job Queue ID             │ nextflow-job-queue-5c6d3e9bd954e800b23f8c62-f7386cc5-cbdf-40e7-b379                   │
│ Job Queue Name           │ v41                                                                                   │
│ Task Resources           │ 1 CPUs, 4 GB RAM'                                                                 │
│ Pipeline url             │ https://github.com/lifebit-ai/mutational-signature-nf                                 │
│ Nextflow Version         │ 22.10.8                                                                               │
│ Execution Platform       │ Batch AWS                                                                             │
│ Accelerated File Staging │ False                                                                                 │
│ Parameters               │ --snv_indel=lifebit-user-data-106c12d2-cf8f-446c-b77e-661d697c833c/deploit/teams/5c6d │
│                          │ 3e9bd954e800b23f8c62/users/6329e3bd3c0e00014641eeea/projects/655cc29778391a7e1901a5b7 │
│                          │ /jobs/68810fda9b301f037d38c4be/results/results/W0000664B01_W0000665B01/W0000664B01_W0 │
│                          │ 000665B01_filtered.vcf.gz                                                             │
│                          │ --sv=lifebit-user-data-f60fc49a-9081-417e-a4fc-03c52de4c820/deploit/teams/5c6d3e9bd95 │
│                          │ 4e800b23f8c62/users/669a9dfe474e319e71685421/projects/66d864817afbdfa1d4515d56/jobs/6 │
│                          │ 8763aac9e7fe38ec6e9236d/results/results/manta/W0000665B01-W0000664B01/somaticSV_annot │
│                          │ ation.vcf.gz                                                                          │
│                          │ --cnv=lifebit-user-data-106c12d2-cf8f-446c-b77e-661d697c833c/deploit/teams/5c6d3e9bd9 │
│                          │ 54e800b23f8c62/users/6329e3bd3c0e00014641eeea/projects/655cc29778391a7e1901a5b7/jobs/ │
│                          │ 687f5b383e05673d74aab1b9/results/W0000664B01_vs_W0000665B01/W0000664B01.copynumber.ca │
│                          │ veman.csv                                                                             │
│                          │ --sample_name=W0000664B01                                                             │
│ Profile                  │ None                                                                                  │
└──────────────────────────┴───────────────────────────────────────────────────────────────────────────────────────┘
```

To change this behaviour and save the details into a local CSV or JSON, the parameter `--output-format` needs to be set as `--output-format=json` or `--output-format=csv`.

By default, all details are saved in a file with the basename as `{job_id}_details`, for example `68bf2178b4ae9f283ea8a0bf_details.json` or `68bf2178b4ae9f283ea8a0bf_details.config.`. This can be changed with the parameter `--output-basename=new_filename`.

The `details` subcommand, can also take `--parameters` as an argument flag, which will create a new file `*.config` that holds all parameters as a Nextflow configuration file, example:

```console
params {
    parameter_one = value_one
    parameter_two = value_two
    parameter_three = value_three
}
```

This file can later be used when running a job with `cloudos job run --job-config job_details.config ...`.

> [!NOTE]
> Job details can only be retrieved for a single user, cannot see other user's job details.

#### Get Job Workdir

To get the working directory of a job submitted to CloudOS:

```shell
cloudos job workdir \
    --profile profile-name \
    --job-id 62c83a1191fe06013b7ef355
```

The output should be something similar to:

```console
CloudOS job functionality: run, check and abort jobs in CloudOS.

Finding working directory path...
Working directory for job 68747bac9e7fe38ec6e022ad: az://123456789000.blob.core.windows.net/cloudos-987652349087/projects/455654676/jobs/54678856765/work
```

You can also link the working directory to an interactive session using the `--link` flag. This requires specifying a session ID either through the `--session-id` option or from a configured profile:

```shell
cloudos job workdir \
    --profile profile-name \
    --job-id 62c83a1191fe06013b7ef355 \
    --link --session-id your_session_id
```

**Check Working Directory Deletion Status**

You can check the deletion status of a job's working directory using the `--status` flag. This is useful for monitoring the deletion lifecycle of intermediate job files.

```bash
cloudos job workdir --status --profile my_profile --job-id "12345678910"
```

The command will display the current status of the working directory folder. Possible statuses include:
- **available**: Working directory is available and accessible
- **scheduled for deletion**: Working directory is scheduled to be deleted
- **deleting**: Working directory is currently being deleted
- **deleted**: Working directory has been deleted
- **failed to delete**: Deletion process failed

Example output for available working directory:
```console
The working directory of job 6912036aa6ed001148c96018 is in status: available
```

For working directories in any state other than available, the output includes additional information about when the status changed and who initiated the change:
```console
The working directory of job 6912036aa6ed001148c96018 is in status: scheduled for deletion
Status changed at: 2025-11-11T14:43:44.416Z
User: Leila Mansouri (leila.mansouri@lifebit.ai)
```

Use the `--verbose` flag to see detailed information including the working directory folder name, folder ID, creation and update timestamps:
```bash
cloudos job workdir --status --profile my_profile --job-id "12345678910" --verbose
```

> [!NOTE]
> This command only works for jobs that were run with resumable mode enabled (using the `--resumable` flag). Jobs without resumable mode will not have a working directory to check.
> If the working directory has been completely deleted, the command will report that the working directory was not found.

#### Get Job Logs

The following command allows you to get the path to "Nextflow logs", "Nextflow standard output", and "trace" files. It can be used only on your user's jobs, with any status.

Example:
```bash
cloudos job logs --profile my_profile --job-id "12345678910"
```
```console
Executing logs...
Logs URI: s3://path/to/location/of/logs

Nextflow log: s3://path/to/location/of/logs/.nextflow.log

Nextflow standard output: s3://path/to/location/of/logs/stdout.txt

Trace file: s3://path/to/location/of/logs/trace.txt
```

You can also link the logs directory to an interactive session using the `--link` flag. This will mount the entire logs directory, providing access to all log files in your interactive session:

```bash
cloudos job logs --profile my_profile --job-id "12345678910" --link --session-id your_session_id
```

#### Get Job Costs

You can retrieve detailed cost information for any job in your CloudOS workspace using the `job cost` command. This provides insights into compute costs, storage usage, and runtime metrics to help optimize workflows and manage expenses.

The cost information is retrieved from CloudOS and can be displayed in multiple formats:

- **Console display**: Rich formatted tables with pagination for easy viewing
- **CSV**: Structured data for analysis and reporting
- **JSON**: Complete cost data for programmatic processing

To get cost information for a specific job:

```bash
cloudos job cost --profile my_profile --job-id 62c83a1191fe06013b7ef355
```

The expected output is a formatted table showing:

```console
                              Job Cost Details - Job ID: 62c83a1191fe06013b7ef355                              
┏━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━┓
┃        ┃            ┃            ┃            ┃          ┃             ┃            ┃ Compute     ┃         ┃
┃        ┃ Instance   ┃            ┃ Life-cycle ┃          ┃ Compute     ┃ Instance   ┃ storage     ┃         ┃
┃ Type   ┃ id         ┃ Instance   ┃ type       ┃ Run time ┃ storage     ┃ price      ┃ price       ┃ Total   ┃
┡━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━┩
│ Worker │ pgti_mediu │ standard_d │ spot       │ 2m 12s   │ 500 Gb      │ $0.0888/hr │ $0.0298/hr  │ $0.0043 │
│        │ m_pool/tvm │ 8a_v4      │            │          │             │            │             │         │
│        │ ps_e57148f │            │            │          │             │            │             │         │
│        │ f29a2186e2 │            │            │          │             │            │             │         │
│        │ ba07c0566c │            │            │          │             │            │             │         │
│        │ a7d494148a │            │            │          │             │            │             │         │
│        │ 7f8d9d547d │            │            │          │             │            │             │         │
│        │ 8fdbb71ead │            │            │          │             │            │             │         │
│        │ 4355497_p  │            │            │          │             │            │             │         │
│ Worker │ pgti_mediu │ standard_d │ spot       │ 7m 48s   │ 500 Gb      │ $0.0888/hr │ $0.0298/hr  │ $0.0154 │
│        │ m_pool/tvm │ 8a_v4      │            │          │             │            │             │         │
│        │ ps_acc84ab │            │            │          │             │            │             │         │
│        │ 980b9bd654 │            │            │          │             │            │             │         │
│        │ b690de025a │            │            │          │             │            │             │         │
│        │ 7abab8c5e2 │            │            │          │             │            │             │         │
│        │ 7fe60e80c7 │            │            │          │             │            │             │         │
│        │ 34d65f6519 │            │            │          │             │            │             │         │
│        │ 5a56c26_p  │            │            │          │             │            │             │         │
└────────┴────────────┴────────────┴────────────┴──────────┴─────────────┴────────────┴─────────────┴─────────┘
On page 1/2: n = next, p = prev, q = quit

By pressing 'n', it will show the next page or the last if it is the case.

                              Job Cost Details - Job ID: 62c83a1191fe06013b7ef355                              
┏━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━┓
┃        ┃            ┃            ┃            ┃          ┃             ┃            ┃ Compute     ┃         ┃
┃        ┃ Instance   ┃            ┃ Life-cycle ┃          ┃ Compute     ┃ Instance   ┃ storage     ┃         ┃
┃ Type   ┃ id         ┃ Instance   ┃ type       ┃ Run time ┃ storage     ┃ price      ┃ price       ┃ Total   ┃
┡━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━┩
│ Worker │ pgti_large │ standard_d │ spot       │ 1m 24s   │ 500 Gb      │ $0.1780/hr │ $0.0298/hr  │ $0.0049 │
│        │ _pool/tvmp │ 16a_v4     │            │          │             │            │             │         │
│        │ s_fde00bd8 │            │            │          │             │            │             │         │
│        │ b7b0c2fd49 │            │            │          │             │            │             │         │
│        │ c24a9f2d29 │            │            │          │             │            │             │         │
│        │ c2958994d8 │            │            │          │             │            │             │         │
│        │ 125708b7d2 │            │            │          │             │            │             │         │
│        │ ab2309c419 │            │            │          │             │            │             │         │
│        │ 747a8a_p   │            │            │          │             │            │             │         │
│ Worker │ pgti_large │ standard_d │ spot       │ 1m 20s   │ 500 Gb      │ $0.1780/hr │ $0.0298/hr  │ $0.0046 │
│        │ _pool/tvmp │ 16a_v4     │            │          │             │            │             │         │
│        │ s_abe5f8f5 │            │            │          │             │            │             │         │
│        │ afe98535d3 │            │            │          │             │            │             │         │
│        │ a74a73a9e5 │            │            │          │             │            │             │         │
│        │ e2e2d1c181 │            │            │          │             │            │             │         │
│        │ a6b1056a17 │            │            │          │             │            │             │         │
│        │ 6ecaacdb65 │            │            │          │             │            │             │         │
│        │ 0737b7_p   │            │            │          │             │            │             │         │
│        │            │            │            │          │             │            │             │         │
├────────┼────────────┼────────────┼────────────┼──────────┼─────────────┼────────────┼─────────────┼─────────┤
│        │            │            │            │          │             │            │             │ $0.5563 │
└────────┴────────────┴────────────┴────────────┴──────────┴─────────────┴────────────┴─────────────┴─────────┘

In the last page, the total job cost will be in the last row.
```

**Export options:**

Save cost data to CSV for further analysis:

```bash
cloudos job cost --profile my_profile --job-id 62c83a1191fe06013b7ef355 --output-format csv

cat 62c83a1191fe06013b7ef355_costs.csv
Type,Instance id,Instance,Life-cycle type,Run time,Compute storage,Instance price,Compute storage price,Total
Master,186b12c2-a518-40de-8bef-7c43f9adcfce,Standard_D4as_v4,on demand,39m 43s,1000 Gb,$0.2220/hr,$0.0561/hr,$0.1841
Worker,pgti_large_pool/tvmps_e739a24d7e64e06f1006d3410ee74c7929388fb1146231d4be84ecdb2c39db0f_p,standard_d16a_v4,spot,1m 26s,500 Gb,$0.1780/hr,$0.0298/hr,$0.0050
Worker,pgti_large_pool/tvmps_abe5f8f5afe98535d3a74a73a9e5e2e2d1c181a6b1056a176ecaacdb650737b7_p,standard_d16a_v4,spot,1m 20s,500 Gb,$0.1780/hr,$0.0298/hr,$0.0046
Worker,pgti_large_pool/tvmps_dad8c86e744056f581e9298273ff7df99d2f9f2b5dc8f706037b1a8b61c4ce0b_p,standard_d16a_v4,spot,5m 10s,500 Gb,$0.1780/hr,$0.0298/hr,$0.0179
...
```

Save complete cost data to JSON:

```bash
cloudos job cost --profile my_profile --job-id 62c83a1191fe06013b7ef355 --output-format json

cat 62c83a1191fe06013b7ef355_costs.json
{
  "job_id": "688ade923643c2454f5ac77d",
  "cost_table": [
    {
      "Type": "Master",
      "Instance id": "186b12c2-a518-40de-8bef-7c43f9adcfce",
      "Instance": "Standard_D4as_v4",
      "Life-cycle type": "on demand",
      "Run time": "39m 43s",
      "Compute storage": "1000 Gb",
      "Instance price": "$0.2220/hr",
      "Compute storage price": "$0.0561/hr",
      "Total": "$0.1841"
    },
    {
      "Type": "Worker",
      "Instance id": "pgti_medium_pool/tvmps_ba00d365ca2b35cce93b2853480be9afc0202bf2f5633648f2dd576414dd8987_p
",
      "Instance": "standard_d8a_v4",
      "Life-cycle type": "spot",
      "Run time": "19m 55s",
      "Compute storage": "500 Gb",
      "Instance price": "$0.0888/hr",
      "Compute storage price": "$0.0298/hr",
      "Total": "$0.0394"
    },
    ...
    {
      "Type": "Worker",
      "Instance id": "pgti_large_pool/tvmps_abe5f8f5afe98535d3a74a73a9e5e2e2d1c181a6b1056a176ecaacdb650737b7_p"
,
      "Instance": "standard_d16a_v4",
      "Life-cycle type": "spot",
      "Run time": "1m 20s",
      "Compute storage": "500 Gb",
      "Instance price": "$0.1780/hr",
      "Compute storage price": "$0.0298/hr",
      "Total": "$0.0046"
    }
  ],
  "final_cost": "$0.5563"
}

```

#### Get Job Related Analyses

You can view related jobs that share the same working directory in a CloudOS workspace by using the `job related` command. This feature helps track job lineages, resume workflows, and understand job relationships.

The information is retrieved from CloudOS and can be displayed in multiple formats:

- **Console display**: Rich formatted tables with pagination
- **JSON**: Complete job data for programmatic processing

To get related analyses for a specific job:

```bash
cloudos job related --profile my_profile --job-id 66b5e5ded52f33061e2468d5
```

The expected output is a formatted table showing:

```console
Total related analyses found: 15

                                              Related Analyses                                              
┏━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ Status    ┃ Name                               ┃ Owner          ┃ ID                       ┃ Submit time         ┃ Run time  ┃ Total Cost ┃
┡━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━┩
│ completed │ workflow_analysis_v1               │ John Smith     │ 66b5e5ded52f33061e2468d5 │ 2024-08-09 14:23:10 │ 45m 12s   │ $1.2340    │
│ completed │ workflow_analysis_v1_resumed       │ John Smith     │ 66b6f2a1e52f33061e246abc │ 2024-08-10 09:15:22 │ 12m 5s    │ $0.3210    │
│ running   │ workflow_analysis_v2               │ Jane Doe       │ 66b7a3b2f52f33061e246def │ 2024-08-11 11:30:45 │ 5m 30s    │ $0.1150    │
│ failed    │ workflow_analysis_test             │ John Smith     │ 66b8c4d3g52f33061e246ghi │ 2024-08-12 16:42:18 │ 2m 15s    │ $0.0450    │
│ completed │ workflow_downstream_processing     │ Jane Doe       │ 66b9d5e4h52f33061e246jkl │ 2024-08-13 08:20:33 │ 28m 40s   │ $0.7890    │
│ aborted   │ workflow_analysis_v1_test2         │ John Smith     │ 66bae6f5i52f33061e246mno │ 2024-08-14 13:55:07 │ 1m 8s     │ $0.0120    │
│ completed │ workflow_final_results             │ Jane Doe       │ 66bbf807j52f33061e246pqr │ 2024-08-15 10:12:44 │ 18m 22s   │ $0.5670    │
│ queued    │ workflow_reanalysis                │ John Smith     │ 66bcd918k52f33061e246stu │ 2024-08-16 15:38:19 │ N/A       │ N/A        │
│ completed │ workflow_quality_control           │ Jane Doe       │ 66bdea29l52f33061e246vwx │ 2024-08-17 07:45:52 │ 8m 15s    │ $0.2340    │
│ completed │ workflow_variant_calling           │ John Smith     │ 66befb3am52f33061e246yz1 │ 2024-08-18 12:03:28 │ 55m 48s   │ $1.5620    │
└───────────┴────────────────────────────────────┴────────────────┴──────────────────────────┴─────────────────────┴───────────┴────────────┘
On page 1/2: n = next, p = prev, q = quit
```

The table displays key information for each related job:
- **Status**: Current job state (initializing, running, completed, aborting, aborted, failed)
- **Name**: Job name assigned when submitted
- **Owner**: User who submitted the job (first name and last name)
- **ID**: Job identifier in CloudOS
- **Submit time**: When the job was submitted (formatted as YYYY-MM-DD HH:MM:SS)
- **Run time**: Actual execution time (formatted as hours, minutes, seconds)
- **Total Cost**: Compute cost in USD

**Pagination controls:**
- Press `n` to navigate to the next page
- Press `p` to navigate to the previous page
- Press `q` to quit and return to the terminal

The console automatically clears between pages for a clean viewing experience, displaying 10 jobs per page.

**Export options:**

Save related analyses to JSON for programmatic analysis:

```bash
cloudos job related --profile my_profile --job-id 66b5e5ded52f33061e2468d5 --output-format json

cat related_analyses.json
{
  "66b5e5ded52f33061e2468d5": {
    "status": "completed",
    "name": "workflow_analysis_v1",
    "user_name": "John",
    "user_surname": "Smith",
    "_id": "66b5e5ded52f33061e2468d5",
    "createdAt": "2024-08-09T14:23:10.000Z",
    "runTime": 2712,
    "computeCostSpent": 123400
  },
  "66b6f2a1e52f33061e246abc": {
    "status": "completed",
    "name": "workflow_analysis_v1_resumed",
    "user_name": "John",
    "user_surname": "Smith",
    "_id": "66b6f2a1e52f33061e246abc",
    "createdAt": "2024-08-10T09:15:22.000Z",
    "runTime": 725,
    "computeCostSpent": 32100
  },
  ...
}
```

The JSON format includes:
- `status`: Job execution status
- `name`: Job name
- `user_name` and `user_surname`: Owner information
- `_id`: Job identifier
- `createdAt`: ISO 8601 timestamp of job submission
- `runTime`: Execution time in seconds
- `computeCostSpent`: Total cost in cents (divide by 100 for dollars)

**Use cases:**

Related analyses are particularly useful for:
- **Resumed workflows**: Find previous jobs to continue from checkpoints
- **Job lineage tracking**: Understand which jobs are part of the same analysis
- **Cost analysis**: Compare costs across related jobs
- **Debugging**: Identify failed jobs in a workflow series
- **Collaboration**: See all jobs from team members working on shared data

> [!NOTE]
> Related jobs are identified by their shared working directory folder ID. Only jobs within the same workspace that use the same working directory will be displayed.

#### Delete Job Results

CloudOS allows you to permanently delete job results directories to manage storage and clean up completed analyses. This feature provides a safe way to remove final analysis results with built-in confirmation prompts and status tracking.

> [!WARNING]
> Deleting job results is **irreversible**. All data and backups will be permanently removed and cannot be recovered. Use this feature with caution.

**Delete Results with Confirmation**

To delete the results directory of a completed job, use the `--delete` flag with the `job results` command. By default, a confirmation prompt will be displayed before deletion:

```bash
cloudos job results --profile my_profile --job-id 62c83a1191fe06013b7ef355 --delete
```

The expected output will show a warning confirmation:

```console
Executing results...
Results: s3://lifebit-featured-datasets/results/62c83a1191fe06013b7ef355

⚠️ Deleting final analysis results is irreversible. All data and backups will be permanently removed and cannot be recovered. You can skip this confirmation step by providing '-y' or '--yes' flag to 'cloudos job results --delete'. Please confirm that you want to delete final results of this analysis? [y/n]
```

Type `y` to proceed with deletion or `n` to cancel:

```console
y

Results directories deleted successfully.
```

**Skip Confirmation Prompt**

For automated workflows or when you're certain about deletion, you can skip the confirmation prompt using the `-y` or `--yes` flag:

```bash
cloudos job results --profile my_profile --job-id 62c83a1191fe06013b7ef355 --delete --yes
```

This will immediately proceed with deletion without prompting for confirmation:

```console
Executing results...
Results: s3://lifebit-featured-datasets/results/62c83a1191fe06013b7ef355

Results directories deleted successfully.
```

**Error Handling**

The deletion command handles various scenarios with specific error messages:

- **Job not found**: If the specified job ID doesn't exist or is not accessible
- **No results directory**: If the job doesn't have a results directory associated with it
- **Permission denied**: If your API key doesn't have permission to delete the results
- **Resource conflict**: If the folder cannot be deleted due to dependencies

Example when a job has no results:

```bash
cloudos job results --profile my_profile --job-id 62c83a1191fe06013b7ef355 --delete
```

```console
Executing results...
Selected job does not have 'Results' information.
```

> [!NOTE]
> The `--delete` flag is compatible with other `job results` options. You can combine it with `--verbose` for detailed logging, but cannot be used together with `--link` or `--status` flags.

**Bulk Deletion**

For bulk deletion of job results and working directories across multiple jobs in a project, see the [delete_project_jobs.sh utility script](docs/utils/delete_project_jobs.md) in the `utils` folder. This script allows you to efficiently delete results and/or working directories for all jobs in a project.

### Bash Jobs
Execute bash scripts on CloudOS for custom processing workflows. Bash jobs allow you to run shell commands with custom parameters and are ideal for data preprocessing or simple computational tasks.

#### Send Array Job


A bash job can be sent to CloudOS using the command `bash` and the subcommand `job`. In this case, the `--workflow-name` must be a bash job already present in the platform. Bash jobs are identified by bash icon (unlike Nextflow jobs, which are identified with Nextflow icon).

```bash
cloudos bash job \
    --profile my_profile \
    --workflow-name ubuntu \
    --parameter -test_variable=value \
    --parameter --flag=activate \
    --parameter send="yes" \
    --job-name $JOB_NAME \
    --command "echo 'send' > new_file.txt" \
    --resumable
```

The `--command` parameter is required and will setup the command for the parameters to run.

Each `--parameter` can have a different prefix, either '--', '-', or '', depending on the use case. These can be used as many times as needed.

> [!NOTE]
> At the moment only string values are allowed to the `--parameter` options, adding a filepath at the moment does not upload/download the file. This feature will be available in a future implementation.

If everything went well, you should see something like:

```console
CloudOS bash functionality.

        Job successfully launched to CloudOS, please check the following link: https://cloudos.lifebit.ai/app/advanced-analytics/analyses/682622d09f305de717327334
        Your assigned job id is: 682622d09f305de717327334

        Your current job status is: initializing
        To further check your job status you can either go to https://cloudos.lifebit.ai/app/advanced-analytics/analyses/682622d09f305de717327334 or use the following command:
        cloudos job status \
                --apikey $MY_API_KEY \
                --cloudos-url https://cloudos.lifebit.ai \
                --job-id 682622d09f305de717327334
```

As you can see, the current status is `initializing`. This will change while the job progresses. To check the status, just apply the suggested command.

Other options like `--wait-completion` are also available and work in the same way as for the `cloudos job run` command.
Check `cloudos bash job --help` for more details.

#### Submit a Bash Array Job

Run parallel bash jobs across multiple samples or datasets using array files. This is particularly useful for processing large datasets where each row represents a separate computational task.

When running a bash array job, you can specify an array file containing sample information and process each row in parallel. The CLI validates column names and provides flexible parameter mapping.

```bash
cloudos bash array-job --profile my_profile --command "echo {file}" --array-file my_array.csv --separator ,
```

##### Options

###### Array File
- **`--array-file`**: Specifies the path to a file containing a set of columns useful in running the bash job. This option is **required** when using the command `bash array-job`.

###### Separator
- **`--separator`**: Defines the separator to use in the array file. Supported separators include:
    - `,` (comma)
    - `;` (semicolon)
    - `tab`
    - `space`
    - `|` (pipe)
This option is **required** when using the command `bash array-job`.

###### List Columns
- **`--list-columns`**: Lists the columns available in the array file. This is useful for inspecting the structure of the file. This flag disables sending the job, it just prints the column list, one per line:

```console
Columns:
    - column1
    - column2
    - column3
```

###### Array File Project
- **`--array-file-project`**: Specifies the name of the project in which the array file is placed, if it is different from the project specified by `--project-name`.

###### Disable Column Check
- **`--disable-column-check`**: Disables the validation of columns in the array file. This implies that each `--array-parameter` value is not checked against the header of the `--array-file`. For example, `--array-parameter --bar=foo`, without `--disable-column-check`, expects the array file to have column 'foo' inside the file header. If the column is not present, the CLI will throw an error. When `--disable-column-check` flag is added, the column check is not performed and the bash array job is sent to the platform.

> [!NOTE]
> Adding `--disable-column-check` will make the CLI command run without errors, but the errors might appear when checking the job in the platform, if the columns in the array file do not exists, as depicted with `--array-parameter`.

###### Array Parameter
- **`-a` / `--array-parameter`**: Allows specifying the column name present in the header of the array file. Each parameter should be in the format `arary_parameter_name=array_file_column`. For example:
    - `-a --test=value` or
    - `--array-parameter -test=value`
specify a column named 'value' in the array file header. Adding array parameters not present in the header will cause an error. This option can be used multiple times to include as many array parameters as needed. This type of parameter is similar to `-p, --parameter`, both parameters can be interpolated in the bash array job command (either with `--command` or `--custom-script-path`), but this parameter can only be used to name the column present in the header of the array file.

For example, the array file has the following header:

```console
id,bgen,csv
1,s3://data/adipose.bgen,s3://data/adipose.csv
2,s3://data/blood.bgen,s3://data/blood.csv
3,s3://data/brain.bgen,s3://data/brain.csv
...
```
and in the command there is need to go over the `bgen` column, this can be specified as `--array-parameter file=bgen`, refering to the column in the header.

###### Custom Script Path
- **`--custom-script-path`**: Specifies the path to a custom script to run in the bash array job instead of a command. When adding this command, parameter `--command` is ignored. To ensure the script runs successfully, you must either:

1. Use a Shebang Line at the Top of the Script

The shebang (#!) tells the system which interpreter to use to run the script. The path should match absolute path to python or other interpreter installed inside the docker container.

Examples:
`#!/usr/bin/python3` –-> for Python scripts
`#!/usr/bin/Rscript` –-> for R scripts
`#!/bin/bash`        –-> for Bash scripts

Example Python Script:

```python
#!/usr/bin/python3
print("Hello world")
```
 
2. Or use an interpreter command in the executable field

If your script doesn’t have a shebang line, you can execute it by explicitly specifying the interpreter in the executable command:

```console
python my_script.py
Rscript my_script.R
bash my_script.sh
```
This assumes the interpreter is available on the container’s $PATH. If not, you can use the full absolute path instead:

```console
/usr/bin/python3 my_script.py
/usr/local/bin/Rscript my_script.R
```

###### Custom Script Project
- **`--custom-script-project`**: Specifies the name of the project in which the custom script is placed, if it is different from the project specified by `--project-name`.

These options provide flexibility for configuring and running bash array jobs, allowing to tailor the execution for specific requirements.

#### Use multiple projects for files in `--parameter` option

The option `--parameter` could specify a file input located in a different project than option `--project-name`. The files can only be located inside the project's `Data` subfolder, not `Cohorts` or `Analyses Results`. The accepted structures for different parameter projects are:
- `-p/--parameter "--file=<project>/Data/file.txt"`
- `-p/--parameter "--file=<project>/Data/subfolder/file.txt"`
- `-p/--parameter "--file=Data/subfolder/file.txt"` (the same project as `--project-name`)
- `-p/--parameter "--file=<project>/Data/subfolder/*.txt"`
- `-p/--parameter "--file=<project>/Data/*.txt"`
- `-p/--parameter "--file=Data/*.txt"` (the same project as `--project-name`)

The project should be specified at the beginning of the file path. For example:

```bash
cloudos bash array-job --profile my_profile -p file=Data/input.csv
```
This will point to the global project, specified with `--project-name`. In contrast:

```bash
cloudos bash array-job \
    --profile my_profile \
    -p data=Data/input.csv \
    -p exp=PROJECT_EXPRESSION/Data/input.csv \
    --project-name "ADIPOSE"
```
for parameter `exp` it will point to a project named `PROJECT_EXPRESSION` in the File Explorer, and `data` parameter will be found in the global project `ADIPOSE`.

Apart from files, the parameter can also take glob patterns, for example:

```bash
cloudos bash array-job \
    --profile my_profile \
    -p data=Data/input.csv \
    -p exp="PROJECT_EXPRESSION/Data/*.csv" \
    --project-name "ADIPOSE"
```
will take all `csv` file extensions in the specified folder.

> [!NOTE]
> When specifying glob patterns, depending on the terminal it is best to add it in double quotes to avoid the terminal searching for the glob pattern locally, e.g. `-p exp="PROJECT_EXPRESSION/Data/*.csv"`.

> [!NOTE]
> Project names in the `--parameter` option can start with either forward slash `/` or without. The following are the same: `-p data=/PROJECT1/Data/input.csv` and `-p data=PROJECT1/Data/input.csv`.

---

### Datasets

Manage files and folders within your CloudOS File Explorer programmatically. These commands provide comprehensive file management capabilities for organizing research data and results.

#### List Files

Browse files and folders within your CloudOS projects. Use the `--details` flag to get comprehensive information about file ownership, sizes, and modification dates.

```bash
cloudos datasets ls <path> --profile <profile>
```
The output of this command is a list of files and folders present in the specified project.

> [!NOTE]
> If the `<path>` is left empty, the command will return the list of folders present in the selected project.

If you require more information on the files and folder listed, you can use the `--details` flag that will output a table containing the following columns:
- Type (s3 folder, azure folder , virtual folder, file (user uploaded) or file (virtual copy))
- Owner
- Size (in human readable format)
- Last updated
- Virtual Name (the file or folder name)
- Storage Path

**Output Format Options**

The `datasets ls` command supports different output formats using the `--output-format` option:

- **`stdout` (default)**: Displays results in the console with Rich formatting
  - Without `--details`: Simple list of file/folder names with color coding (blue underlined for folders)
  - With `--details`: Rich formatted table with all file information
  
- **`csv`**: Saves results to a CSV file
  - Without `--details`: CSV with two columns: "Name,Storage Path"
  - With `--details`: CSV with columns "Type, Owner, Size, Size (bytes), Last Updated, Virtual Name, Storage Path"

Examples:

```bash
# Simple list to console (default)
cloudos datasets ls Data --profile my_profile

# Detailed table in console
cloudos datasets ls Data --details --profile my_profile

# Simple CSV output
cloudos datasets ls Data --profile my_profile --output-format csv

# Detailed CSV output
cloudos datasets ls Data --details --output-format csv --profile my_profile

# Custom output filename
cloudos datasets ls Data --details --output-format csv --output-basename my_files --profile my_profile
```

When using `--output-format csv`, you can optionally specify a custom base filename using `--output-basename`. If not provided, the filename will be auto-generated based on the path (e.g., `datasets_ls.csv`).

#### Move Files

Relocate files and folders within the same project or across different projects. This is useful for reorganizing data and moving results to appropriate locations.

> [!NOTE]
> Files and folders can be moved **from** `Data` or any of its subfolders (i.e `Data`, `Data/folder/file.txt`) **to** `Data` or any of its subfolders programmatically. Furthermore, only virtual folders can be destination folders.

The move can happen **within the same project**

```bash
cloudos datasets mv <source_path> <destination_path> --profile <profile>
```

But it can also happen **across different projects**  within the same workspace by specifying the destination project name.

```bash
cloudos datasets mv <source_path> <destination_path> --profile <profile> --destination-project-name <project>
```

Any of the `source_path` must be a full path, starting from the `Data` datasets and its folder; any `destination_path` must be a path starting with `Data` and finishing with the folder where to move the file/folder.

An example of such command is:

```
cloudos datasets mv Data/results/my_plot.png Data/plots 
```

#### Rename Files

Change file and folder names while keeping them in the same location. This helps maintain organized file structures and clear naming conventions.

> [!NOTE]
> Files and folders within the `Data` dataset can be renamed using the following command

```bash
cloudos datasets rename <path> <new_name> --profile my_profile 
```
where `path` is the full path to the file/folder to be renamed and `new_name` is just the name, no path required, as the file will not be moved.

> [!NOTE]
> Renaming can only happen in files and folders that are present in the `Data` datasets and that were created or uploaded by your user.

#### Copy Files

Create copies of files and folders for backup purposes or to share data across projects without moving the original files.

> [!NOTE]
> Files and folders can be copied **from** anywhere in the project **to** `Data` or any of its subfolders programmatically (i.e `Data`, `Data/folder/file.txt`). Furthermore, only virtual folders can be destination folders.


The copy can happen **within the same project**
```bash
cloudos datasets cp <source_path> <destination_path> --profile <profile>
```

or it can happen **across different projects**  within the same workspace

```bash
cloudos datasets cp <source_path> <destination_path> --profile <profile> --destination-project-name <project>
```

Any of the `source_path` must be a full path; any `destination_path` must be a path starting with `Data` and finishing with the folder where to move the file/folder. 

An example of such command is:

```
cloudos datasets cp AnalysesResults/my_analysis/results/my_plot.png Data/plots 
```


#### Link S3 Folders to Interactive Analysis

Connect external S3 buckets or internal File Explorer folders to your interactive analysis sessions. This provides direct access to data without needing to copy files.

This subcommand is using the option `--session-id` to access the correct interactive session. This option can be added to the CLI or defined in a profile, for convenience.

```bash
cloudos datasets link <S3_FOLDER_COMPLETE_PATH_OR_VIRTUAL_FOLDER_PATH> --profile <profile> --session-id <SESSION_ID>
```

For example, an s3 folder can be linked like follows
```console
cloudos datasets link s3://bucket/path/folder --profile test --session-id 1234
```

A virtual folder can be linked like
``` concole
cloudos datasets link "Analyses Results/HLA" --session-id 1234
```

> [!NOTE]
> If running the CLI inside a jupyter session, the pre-configured CLI installation will have the session ID already installed and only the `--apikey` needs to be added.

> [!NOTE]
> Virtual folders in File Explorer, the ones a user has created in File explorer and are not actual storage locations, cannot be linked.

#### Create Folder

Create new organizational folders within your projects to maintain structured data hierarchies.

> [!NOTE]
> New folders can be created within the `Data` dataset and its subfolders.

```bash
cloudos datasets mkdir <new_folder_path> --profile my_profile 
```

#### Remove Files or Folders

Remove unnecessary files or empty folders from your File Explorer. Note that this removes files from CloudOS but not from underlying cloud storage.

> [!NOTE]
> Files and folders can be removed in the `Data` datasets and its subfolders. 

```bash
cloudos datasets rm <path> --profile my_profile
```
> [!NOTE]
> If a file was uploaded by the user, in order to be removed you must use  `--force` and that will permanently remove the file. If the file is "linked" (e.g a s3 folder or file), removing it using `cloudos datasets rm` will not remove it from the the s3 bucket.
 
---

### Link

The `cloudos link` command provides a unified interface for linking folders to interactive analysis sessions. This command consolidates functionality previously available through separate commands (`cloudos job results --link`, `cloudos job workdir --link`, `cloudos job logs --link`, and `cloudos datasets link`) into a single, intuitive interface.

#### Link Folders to Interactive Analysis

Link job-related folders or custom S3 paths to your interactive analysis sessions for direct access to data without needing to copy files.

**Two modes of operation:**

1. **Job-based linking** (`--job-id`): Links folders from a completed or running job
   - By default, links results, workdir, and logs folders
   - Use `--results`, `--workdir`, or `--logs` flags to link only specific folders

2. **Direct path linking** (PATH argument): Links a specific S3 path

**Basic usage:**

```bash
# Link all job folders (results, workdir, logs) - default behavior
cloudos link --job-id <JOB_ID> --session-id <SESSION_ID> --profile my_profile

# Link only specific folders from a job
cloudos link --job-id <JOB_ID> --session-id <SESSION_ID> --results --profile my_profile
cloudos link --job-id <JOB_ID> --session-id <SESSION_ID> --workdir --logs --profile my_profile

# Link a specific S3 path
cloudos link s3://bucket/folder --session-id <SESSION_ID> --profile my_profile

# Link a File Explorer path (requires project name)
cloudos link "Data/MyFolder" --project-name my-project --session-id <SESSION_ID> --profile my_profile
```

**Command options:**

- `PATH`: S3 path to link (positional argument, required if `--job-id` is not provided)
- `--apikey` / `-k`: Your CloudOS API key (required)
- `--cloudos-url` / `-c`: The CloudOS URL (default: https://cloudos.lifebit.ai)
- `--workspace-id`: The specific CloudOS workspace ID (required)
- `--session-id`: The specific CloudOS interactive session ID (required)
- `--job-id`: The job ID in CloudOS (links results, workdir, and logs by default)
- `--project-name`: CloudOS project name (required for File Explorer paths)
- `--results`: Link only results folder (only works with `--job-id`)
- `--workdir`: Link only working directory (only works with `--job-id`)
- `--logs`: Link only logs folder (only works with `--job-id`)
- `--verbose`: Print detailed information messages
- `--disable-ssl-verification`: Disable SSL certificate verification
- `--ssl-cert`: Path to your SSL certificate file
- `--profile`: Profile to use from the config file

**Examples:**

```bash
# Link all folders from a completed job
cloudos link --job-id 62c83a1191fe06013b7ef355 --session-id abc123 --profile my_profile

# Link only results from a job
cloudos link --job-id 62c83a1191fe06013b7ef355 --session-id abc123 --results --profile my_profile

# Link workdir and logs (but not results)
cloudos link --job-id 62c83a1191fe06013b7ef355 --session-id abc123 --workdir --logs --profile my_profile

# Link an S3 bucket folder
cloudos link s3://my-bucket/analysis-results/2024 --session-id abc123 --profile my_profile

```

**Error handling:**

The command provides clear error messages for common scenarios:
- Job not completed (for results linking)
- Folders not available or deleted
- Job still initializing
- Invalid paths or permissions

> [!NOTE]
> If running the CLI inside a Jupyter session, the pre-configured CLI installation will have the session ID already configured and only the `--apikey` needs to be added.

> [!NOTE]
> Azure Blob Storage paths (az://) are not supported for linking in Azure environments.

---

### Procurement

CloudOS supports procurement functionality to manage and list images associated with organizations within a given procurement. This feature is useful for administrators and users who need to view available container images across different organizations in their procurement.

#### List Procurement Images

You can get a list of images associated with organizations of a given procurement using the `cloudos procurement images ls` command. This command provides paginated results showing image configurations and metadata.

To list images for a specific procurement, use the following command:

```bash
cloudos procurement images ls \
    -- profile procurement_profile 
    --procurement-id "your_procurement_id_here"
```

**Command options:**

- `--apikey` / `-k`: Your CloudOS API key (required)
- `--cloudos-url` / `-c`: The CloudOS URL you are trying to access (default: https://cloudos.lifebit.ai)
- `--procurement-id`: The specific CloudOS procurement ID (required)
- `--page`: The response page number (default: 1)
- `--limit`: The page size limit (default: 10)
- `--disable-ssl-verification`: Disable SSL certificate verification
- `--ssl-cert`: Path to your SSL certificate file
- `--profile`: Profile to use from the config file

**Example usage:**

```bash
# List images for the procurement (first page, 10 items)
cloudos procurement images ls --profile procurement_profile --procurement-id "your_procurement_id_here"
```

To get more results per page or navigate to different pages:

```bash
# Get 25 images from page 2
cloudos procurement images ls --profile procurement_profile --page 2 --limit 25 --procurement-id "your_procurement_id_here"
```



**Output format:**

The command returns detailed information about image configurations and pagination metadata in JSON format, including:

- **Image configurations**: Details about available container images
- **Pagination metadata**: Information about total pages, current page, and available items

This is particularly useful for understanding what container images are available across different organizations within your procurement and for programmatic access to image inventory.

#### Set Procurement Organization Image

You can set a custom image ID or name for an organization within a procurement using the `cloudos procurement images set` command. This allows you to override the default CloudOS images with your own custom images for specific organizations.

To set a custom image for an organization, use the following command:

```bash
cloudos procurement images set --profile procurement_profile --image-type "JobDefault" --provider "aws" --region "us-east-1" --image-id "ami-0123456789abcdef0" --image-name "custom-image-name" --procurement-id "your_procurement_id_here" --organisation-id "your_organization_id"
```

**Set command options:**

- `--apikey` / `-k`: Your CloudOS API key (required)
- `--cloudos-url` / `-c`: The CloudOS URL you are trying to access (default: https://cloudos.lifebit.ai)
- `--procurement-id`: The specific CloudOS procurement ID (required)
- `--organisation-id`: The organization ID where the change will be applied (required)
- `--image-type`: The CloudOS resource image type (required). Possible values:
  - `RegularInteractiveSessions`
  - `SparkInteractiveSessions`
  - `RStudioInteractiveSessions`
  - `JupyterInteractiveSessions`
  - `JobDefault`
  - `NextflowBatchComputeEnvironment`
- `--provider`: The cloud provider (required). Currently only `aws` is supported
- `--region`: The cloud region (required). Currently only AWS regions are supported
- `--image-id`: The new image ID value (required)
- `--image-name`: The new image name value (optional)
- `--disable-ssl-verification`: Disable SSL certificate verification
- `--ssl-cert`: Path to your SSL certificate file
- `--profile`: Profile to use from the config file

**Set command example:**

```bash
# Set custom image for job execution
cloudos procurement images set --profile procurement_profile --image-type "JobDefault" --provider "aws" --region "us-east-1" --image-id "ami-0123456789abcdef0" --image-name "my-custom-job-image" --procurement-id "your_procurement_id_here" --organisation-id "your_organization_id"
```

#### Reset Procurement Organization Image

You can reset an organization's image configuration back to CloudOS defaults using the `cloudos procurement images reset` command. This removes any custom image configurations and restores the original CloudOS defaults.

To reset an organization's image to defaults, use the following command:

```bash
cloudos procurement images reset --profile procurement_profile --image-type "JobDefault" --provider "aws" --region "us-east-1" --procurement-id "your_procurement_id_here" --organisation-id "your_organization_id"
```

**Reset command options:**

- `--apikey` / `-k`: Your CloudOS API key (required)
- `--cloudos-url` / `-c`: The CloudOS URL you are trying to access (default: https://cloudos.lifebit.ai)
- `--procurement-id`: The specific CloudOS procurement ID (required)
- `--organisation-id`: The organization ID where the change will be applied (required)
- `--image-type`: The CloudOS resource image type (required). Same values as for `set` command
- `--provider`: The cloud provider (required). Currently only `aws` is supported
- `--region`: The cloud region (required). Currently only AWS regions are supported
- `--disable-ssl-verification`: Disable SSL certificate verification
- `--ssl-cert`: Path to your SSL certificate file
- `--profile`: Profile to use from the config file

**Reset command example:**

```bash
# Reset image configuration to CloudOS defaults
cloudos procurement images reset --profile procurement_profile --image-type "JobDefault" --provider "aws" --region "us-east-1" --procurement-id "your_procurement_id_here" --organisation-id "your_organization_id"
```


### Cromwell and WDL Pipeline Support

#### Manage Cromwell Server

In order to run WDL pipelines, a Cromwell server in CloudOS should be running. This server can be accessed to check its status, restart it or stop it, using the following commands:

```bash
# Check Cromwell status
cloudos cromwell status --profile my_profile
```

```console
Executing status...
	Current Cromwell server status is: Stopped
```

```bash    
# Cromwell start
cloudos cromwell start --profile my_profile
```

```console
Starting Cromwell server...
	Current Cromwell server status is: Initializing

	Current Cromwell server status is: Running
```

```bash
# Cromwell stop
cloudos cromwell stop --profile my_profile
```

```console
Stopping Cromwell server...
	Current Cromwell server status is: Stopped
```

#### Run WDL Workflows

To run WDL workflows, `cloudos job run` command can be used normally, but adding two extra parameters:

- `--wdl-mainfile`: name of the mainFile (*.wdl) file used by the CloudOS workflow.
- `--wdl-importsfile` [Optional]: name of the workflow imported file (importsFile, *.zip).

All the rest of the `cloudos job run` functionality is available.

> NOTE: WDL does not support `profiles` and therefore, `--nextflow-profile` option is not available. Instead, use `--job-config` and/or `--parameter`. The format of the job config file is expected to be the same as for nextflow pipelines.

Example of job config file for WDL workflows:

```bash
params {
 test.hello.name = aasdajdad
  test.bye.nameTwo = asijdadads
  test.number.x = 2
  test.greeter.morning = true
  test.wf_hello_in = bomba
  test.arrayTest = ["lala"]
  test.mapTest = {"some":"props"}
}
```

> NOTE: when using `--parameter` option, if the value needs quotes (`"`) you will need to escape them. E.g.: `--parameter test.arrayTest=[\"lala\"]`

```bash
cloudos job run --profile my_profile --project-name wdl-test --workflow-name "wdl-test" --wdl-mainfile hello.wdl --wdl-importsfile imports_7mb.zip --job-config cloudos/examples/wdl.config --wait-completion
```

```console
Executing run...
    WDL workflow detected

    Current Cromwell server status is: Stopped

    Starting Cromwell server...

    Current Cromwell server status is: Initializing


    Current Cromwell server status is: Running

    *******************************************************************************
    Cromwell server is now running. Plase, remember to stop it when your
    job finishes. You can use the following command:
    cloudos cromwell stop \
        --cromwell-token $CROMWELL_TOKEN \
        --cloudos-url $CLOUDOS \
        --workspace-id $WORKSPACE_ID
    *******************************************************************************

	Job successfully launched to CloudOS, please check the following link: ****
	Your assigned job id is: ****
	Please, wait until job completion or max wait time of 3600 seconds is reached.
	Your current job status is: initializing.
	Your current job status is: running.
	Your job took 60 seconds to complete successfully.
```

---

## Python API Usage

To illustrate how to import the package and use its functionality inside
your own python scripts, we will perform a job submission and check its
status from inside a python script.

Again, we will set up the environment to ease the work:

```python
import cloudos_cli.jobs.job as jb
import json


# GLOBAL VARS.
apikey = 'xxxxx'
cloudos_url = 'https://cloudos.lifebit.ai'
workspace_id = 'xxxxx'
project_name = 'API jobs'
workflow_name = 'rnatoy'
job_config = 'cloudos/examples/rnatoy.config'
```

First, create the `Job` object:

```python
j = jb.Job(cloudos_url, apikey, None, workspace_id, project_name, workflow_name)
print(j)
```

Then, send the job:

```python
j_id = j.send_job(job_config)
```

To check the status:

```python
j_status = j.get_job_status(j_id, workspace_id)
j_status_h = json.loads(j_status.content)["status"]
print(j_status_h)
```

The status will change while your job progresses, so to check again just
repeat the above code.

You can also collect your last 30 submitted jobs for a given workspace using the
following command.

```python
result = j.get_job_list(workspace_id)
my_jobs_r = result['jobs']  # Extract jobs list from the result
my_jobs = j.process_job_list(my_jobs_r)
print(my_jobs)
```

Or inspect all the available workflows for a given workspace using the
following command.

```python
my_workflows_r = j.get_workflow_list(workspace_id)
my_workflows = j.process_workflow_list(my_workflows_r)
print(my_workflows)
```

Similarly, you can inspect all the available projects for a given workspace using the
following command.

```python
my_projects_r = j.get_project_list(workspace_id)
my_projects = j.process_project_list(my_projects_r)
print(my_projects)
```

#### Running WDL pipelines using your own scripts

You can even run WDL pipelines. First check the Cromwell server status and restart it if Stopped:

```python
import cloudos_cli.clos as cl
import cloudos_cli.jobs.job as jb
import json


# GLOBAL VARS.
apikey = 'xxxxx'
cloudos_url = 'https://cloudos.lifebit.ai'
workspace_id = 'xxxxx'
project_name = 'wdl-test'
workflow_name = 'wdl- test'
mainfile = 'hello.wdl'
importsfile = 'imports_7mb.zip'
job_config = 'cloudos/examples/wdl.config'

# First create cloudos object
cl = cl.Cloudos(cloudos_url, apikey, None)

# Then, check Cromwell status
c_status = cl.get_cromwell_status(workspace_id)
c_status_h = json.loads(c_status.content)["status"]
print(c_status_h)

# Start Cromwell server
cl.cromwell_switch(workspace_id, 'restart')

# Check again Cromwell status (wait until status: 'Running')
c_status = cl.get_cromwell_status(workspace_id)
c_status_h = json.loads(c_status.content)["status"]
print(c_status_h)

# Send a job (wait until job has status: 'Completed')
j = jb.Job(cloudos_url, apikey, None, workspace_id, project_name, workflow_name, True, mainfile,
           importsfile)
j_id = j.send_job(job_config, workflow_type='wdl', cromwell_id=json.loads(c_status.content)["_id"])
j_status = j.get_job_status(j_id, workspace_id)
j_status_h = json.loads(j_status.content)["status"]
print(j_status_h)

# Stop Cromwell server
cl.cromwell_switch(workspace_id, 'stop')

# Check again Cromwell status
c_status = cl.get_cromwell_status(workspace_id)
c_status_h = json.loads(c_status.content)["status"]
print(c_status_h)
```


---

## Unit Testing

Unit tests require 4 additional packages:

```
pytest>=6.2.5
requests-mock>=1.9.3
responses>=0.21.0
mock>=3.0.5
```

Command to run tests from the `cloudos-cli` main folder: 

```
python -m pytest -s -v
``` 

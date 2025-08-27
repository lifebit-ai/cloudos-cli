# cloudos-cli

[![CI_tests](https://github.com/lifebit-ai/cloudos-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/lifebit-ai/cloudos-cli/actions/workflows/ci.yml)

Python package for interacting with CloudOS

## Requirements

The package requires Python >= 3.9 and the following python packages:

```
click>=8.0.1
pandas>=1.3.4
numpy>=1.26.4
requests>=2.26.0
rich_click>=1.8.2
```

## Installation

### Docker image
It is recommended to install it as a docker image using the `Dockerfile`
and the `environment.yml` files provided.

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

You will need Python >= 3.7 and pip installed.

Clone the repo and install it using pip:

```bash
git clone https://github.com/lifebit-ai/cloudos-cli
cd cloudos-cli
pip install -r requirements.txt
pip install .
```

> NOTE: To be able to call the `cloudos` executable, ensure that the local clone of the `cloudos-cli` folder is included in the `PATH` variable ,using for example the command `export PATH="/absolute/path/to/cloudos-cli:$PATH"`.

## Configuration

Configuration will be saved in the $HOME path folder regardless of operating system. Here, a new folder named `.cloudos` will be created, with files `credentials` and `config` also being created. The structure will look like:

```console
$HOME
  └── .cloudos
        ├── credentials     <-- holds API key
        └── config          <-- holds all other parameters
```

### Configure default profile

To facilitate the reuse of required parameters, profiles can be created. 

In order to generate a profile called `default`, the following command can be used:

```console
cloudos configure
```

This will bring in prompts for API, platform URL, project name, platform executor, repository provider, workflow name (if any) and session ID for interactive analysis. This will be the default profile if no other was explicitly set. The default profile allows running all subcommands without adding `--profile` option in the command line.

### Configure named profile

In order to generate a named profile, the following command can be used:

```console
cloudos configure --profile {profile-name}
```

The same prompts as before will apear. If there is already a profile with the same name, the set parameters will appear in square brackets, where they can be overwritten or left unmodified by pressing Enter/Return.

> [!NOTE]
> When there is already at least 1 previous profile defined, a new question will appear asking to make the current profile as default

### Change the default profile

This can be achieved with:

```console
cloudos configure --profile {other-profile} --make-default
```

### List profiles

At any time it can be seen how many profiles are present and which is the default:

```console
cloudos configure list-profiles
```

The response will look like:

```console
Available profiles:
 - default (default)
 - second-profile
 - third-profile
```

### Remove profile

Any profile can be remove with:

```console
cloudos configure remove-profile --profile second-profile
```

## Usage

The package is meant to be used both as a CLI tool and as a regular package to
import to your own scripts.

### Usage as a Command Line Interface tool

To get general information about the tool:

```bash
cloudos --help
```
```console
 Usage: cloudos [OPTIONS] COMMAND [ARGS]...                                                                                                                        
                                                                                                                                                                   
 CloudOS python package: a package for interacting with CloudOS.                                                                                                   
                                                                                                                                                                   
╭─ Options ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --version      Show the version and exit.                                                                                                                       │
│ --help         Show this message and exit.                                                                                                                      │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ bash                   CloudOS bash functionality.                                                                                                              │
│ configure              CloudOS configuration.                                                                                                                   │
│ cromwell               Cromwell server functionality: check status, start and stop.                                                                             │
│ job                    CloudOS job functionality: run, check and abort jobs in CloudOS.                                                                         │
│ project                CloudOS project functionality: list and create projects in CloudOS.                                                                       │
│ queue                  CloudOS job queue functionality.                                                                                                         │
│ workflow               CloudOS workflow functionality: list and import workflows.                                                                               │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
``` 

This will tell you the implemented commands. Each implemented command has its
own subcommands with its own `--help`:

```bash
cloudos job run --help
```
```console
 Usage: cloudos job run [OPTIONS]                                                                                                                           
                                                                                                                                                            
 Submit a job to CloudOS.                                                                                                                                   
                                                                                                                                                            
╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ *  --apikey                         -k  TEXT                                   Your CloudOS API key [required]                                           │
│    --cloudos-url                    -c  TEXT                                   The CloudOS url you are trying to access to.                              │
│                                                                                Default=https://cloudos.lifebit.ai.                                       │
│ *  --workspace-id                       TEXT                                   The specific CloudOS workspace id. [required]                             │
│ *  --project-name                       TEXT                                   The name of a CloudOS project. [required]                                 │
│ *  --workflow-name                      TEXT                                   The name of a CloudOS workflow or pipeline. [required]                    │
│    --job-config                         TEXT                                   A config file similar to a nextflow.config file, but only with the        │
│                                                                                parameters to use with your job.                                          │
│    --parameter                      -p  TEXT                                   A single parameter to pass to the job call. It should be in the following │
│                                                                                form: parameter_name=parameter_value. E.g.: -p                            │
│                                                                                input=s3://path_to_my_file. You can use this option as many times as      │
│                                                                                parameters you want to include.                                           │
│    --nextflow-profile                   TEXT                                   A comma separated string indicating the nextflow profile/s to use with    │
│                                                                                your job.                                                                 │
│    --nextflow-version                   [22.10.8|24.04.4|22.11.1-edge|latest]  Nextflow version to use when executing the workflow in CloudOS.           │
│                                                                                Default=22.10.8.                                                          │
│    --git-commit                         TEXT                                   The git commit hash to run for the selected pipeline. If not specified it │
│                                                                                defaults to the last commit of the default branch.                        │
│    --git-tag                            TEXT                                   The tag to run for the selected pipeline. If not specified it defaults to │
│                                                                                the last commit of the default branch.                                    │
│    --git-branch                         TEXT                                   The branch to run for the selected pipeline. If not specified it defaults │
│                                                                                to the last commit of the default branch.                                 │
│    --job-name                           TEXT                                   The name of the job. Default=new_job.                                     │
│    --resumable                                                                 Whether to make the job able to be resumed or not.                        │
│    --do-not-save-logs                                                          Avoids process log saving. If you select this option, your job process    │
│                                                                                logs will not be stored.                                                  │
│    --job-queue                          TEXT                                   Name of the job queue to use with a batch job.                            │
│    --instance-type                      TEXT                                   The type of compute instance to use as master node.                       │
│                                                                                Default=c5.xlarge(aws)|Standard_D4as_v4(azure).                           │
│    --instance-disk                      INTEGER                                The disk space of the master node instance, in GB. Default=500.           │
│    --storage-mode                       TEXT                                   Either 'lustre' or 'regular'. Indicates if the user wants to select       │
│                                                                                regular or lustre storage. Default=regular.                               │
│    --lustre-size                        INTEGER                                The lustre storage to be used when --storage-mode=lustre, in GB. It       │
│                                                                                should be 1200 or a multiple of it. Default=1200.                         │
│    --wait-completion                                                           Whether to wait to job completion and report final job status.            │
│    --wait-time                          INTEGER                                Max time to wait (in seconds) to job completion. Default=3600.            │
│    --wdl-mainfile                       TEXT                                   For WDL workflows, which mainFile (.wdl) is configured to use.            │
│    --wdl-importsfile                    TEXT                                   For WDL workflows, which importsFile (.zip) is configured to use.         │
│    --cromwell-token                 -t  TEXT                                   Specific Cromwell server authentication token. Currently, not necessary   │
│                                                                                as apikey can be used instead, but maintained for backwards               │
│                                                                                compatibility.                                                            │
│    --repository-platform                TEXT                                   Name of the repository platform of the workflow. Default=github.          │
│    --execution-platform                 [aws|azure|hpc]                        Name of the execution platform implemented in your CloudOS. Default=aws.  │
│    --hpc-id                             TEXT                                   ID of your HPC, only applicable when --execution-platform=hpc.            │
│                                                                                Default=660fae20f93358ad61e0104b                                          │
│    --azure-worker-instance-type         TEXT                                   The worker node instance type to be used in azure.                        │
│                                                                                Default=Standard_D4as_v4                                                  │
│    --azure-worker-instance-disk         INTEGER                                The disk size in GB for the worker node to be used in azure. Default=100  │
│    --azure-worker-instance-spot                                                Whether the azure worker nodes have to be spot instances or not.          │
│    --cost-limit                         FLOAT                                  Add a cost limit to your job. Default=30.0 (For no cost limit please use  │
│                                                                                -1).                                                                      │
│    --accelerate-file-staging                                                   Enables AWS S3 mountpoint for quicker file staging.                       │
│    --use-private-docker-repository                                             Allows to use private docker repository for running jobs. The Docker user │
│                                                                                account has to be already linked to CloudOS.                              │
│    --verbose                                                                   Whether to print information messages or not.                             │
│    --request-interval                   INTEGER                                Time interval to request (in seconds) the job status. For large jobs is   │
│                                                                                important to use a high number to make fewer requests so that is not      │
│                                                                                considered spamming by the API. Default=30.                               │
│    --disable-ssl-verification                                                  Disable SSL certificate verification. Please, remember that this option   │
│                                                                                is not generally recommended for security reasons.                        │
│    --ssl-cert                           TEXT                                   Path to your SSL certificate file.                                        │
│    --profile                            TEXT                                   Profile to use from the config file                                       │
│    --help                                                                      Show this message and exit.                                               │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

#### Send a job to CloudOS

First, configure your local environment to ease parameters input. We will
try to submit a small toy example already available.

```bash
MY_API_KEY="xxxxx"
CLOUDOS="https://cloudos.lifebit.ai"
WORKSPACE_ID="xxxxx"
PROJECT_NAME="API jobs"
WORKFLOW_NAME="rnatoy"
JOB_PARAMS="cloudos_cli/examples/rnatoy.config"
```

As you can see, a file with the job parameters is used to configure the
job. This file could be a regular `nextflow.config` file or any file with the
following structure:

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
    --cloudos-url $CLOUDOS \
    --apikey $MY_API_KEY \
    --workspace-id $WORKSPACE_ID \
    --project-name "$PROJECT_NAME" \
    --workflow-name $WORKFLOW_NAME \
    --job-config $JOB_PARAMS \
    --resumable
```

In addition, parameters can also be specified using the command-line `-p` or `--parameter`. For instance,
the previous command is equivalent to:

```bash
cloudos job run \
    --cloudos-url $CLOUDOS \
    --apikey $MY_API_KEY \
    --workspace-id $WORKSPACE_ID \
    --project-name "$PROJECT_NAME" \
    --workflow-name $WORKFLOW_NAME \
    --parameter reads=s3://lifebit-featured-datasets/pipelines/rnatoy-data \
    --parameter genome=s3://lifebit-featured-datasets/pipelines/rnatoy-data/ggal_1_48850000_49020000.Ggal71.500bpflank.fa \
    --parameter annot=s3://lifebit-featured-datasets/pipelines/rnatoy-data/ggal_1_48850000_49020000.bed.gff \
    --resumable
```

> NOTE: options `--job-config` and `--parameter` are completely compatible and complementary, so you can use a
`--job-config` and adding additional parameters using `--parameter` in the same call.

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

As you can see, the current status is `initializing`. This will change
while the job progresses. To check the status, just apply the suggested
command.

Another option is to set the `--wait-completion` parameter, which run the same
job run command but waiting for its completion:

```bash
cloudos job run \
    --cloudos-url $CLOUDOS \
    --apikey $MY_API_KEY \
    --workspace-id $WORKSPACE_ID \
    --project-name "$PROJECT_NAME" \
    --workflow-name $WORKFLOW_NAME \
    --job-config $JOB_PARAMS \
    --resumable \
    --wait-completion
```

When setting this parameter, you can also set `--request-interval` to a bigger number (default is 30s) if the job is quite large. This will ensure that the status requests are not sent too close from each other and recognized as spam by the API.

If the job takes less than `--wait-time` (3600 seconds by default), the
previous command should have an output similar to:

```console
Executing run...
	Job successfully launched to CloudOS, please check the following link: https://cloudos.lifebit.ai/app/advanced-analytics/analyses/62c83a6191fe06013b7ef363
	Your assigned job id is: 62c83a6191fe06013b7ef363
	Please, wait until job completion or max wait time of 3600 seconds is reached.
	Your current job status is: initializing.
	Your current job status is: running.
	Your job took 420 seconds to complete successfully.
```

When there are duplicated `--workflow-name` in the platform, the flag `--last` can be added, and it will use the latest import of that pipeline in the workspace, based on the date. For example, the pipeline `lifebit-process` was imported on May 23 2025 and again on May 30 2025, with the `--last` flag, it will use the import of May 30 of 2025.

#### Send a bash job to CloudOS (sequential sample processing)

A bash job can be sent to CloudOS using the command `bash` and the subcommand `job`. In this case, the `--workflow-name` must be a bash job already
present in the platform. Bash jobs are identified by bash icon (unlike Nextflow jobs, which are identified with Nextflow icon).

```bash
WORKFLOW_NAME="ubuntu"  # This should be a bash workflow
cloudos bash job \
    --cloudos-url $CLOUDOS \
    --apikey $MY_API_KEY \
    --workspace-id $WORKSPACE_ID \
    --project-name "$PROJECT_NAME" \
    --workflow-name $WORKFLOW_NAME \
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

As you can see, the current status is `initializing`. This will change
while the job progresses. To check the status, just apply the suggested
command.

Other options like `--wait-completion` are also available and work in the same way as for the `cloudos job run` command.
Check `cloudos bash job --help` for more details.

#### Send a bash array-job to CloudOS (parallel sample processing)

When running a bash array job, the following options are available to customize the behavior:

##### Array File
- **`--array-file`**: Specifies the path to a file containing a set of columns useful in running the bash job. This option is **required** when using the command `bash array-job`.

##### Separator
- **`--separator`**: Defines the separator to use in the array file. Supported separators include:
    - `,` (comma)
    - `;` (semicolon)
    - `tab`
    - `space`
    - `|` (pipe)
This option is **required** when using the command `bash array-job`.

##### List Columns
- **`--list-columns`**: Lists the columns available in the array file. This is useful for inspecting the structure of the file. This flag disables sending the job, it just prints the column list, one per line:

```console
Columns:
    - column1
    - column2
    - column3
```

##### Array File Project
- **`--array-file-project`**: Specifies the name of the project in which the array file is placed, if it is different from the project specified by `--project-name`.

##### Disable Column Check
- **`--disable-column-check`**: Disables the validation of columns in the array file. This implies that each `--array-parameter` value is not checked against the header of the `--array-file`. For example, `--array-parameter --bar=foo`, without `--disable-column-check`, expects the array file to have column 'foo' inside the file header. If the column is not present, the CLI will throw an error. When `--disable-column-check` flag is added, the column check is not performed and the bash array job is sent to the platform.

> [!NOTE]
> Adding `--disable-column-check` will make the CLI command run without errors, but the errors might appear when checking the job in the platform, if the columns in the array file do not exists, as depicted with `--array-parameter`.

##### Array Parameter
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

##### Custom Script Path
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

##### Custom Script Project
- **`--custom-script-project`**: Specifies the name of the project in which the custom script is placed, if it is different from the project specified by `--project-name`.

These options provide flexibility for configuring and running bash array jobs, allowing to tailor the execution for specific requirements.

#### Use multiple projects for files in `--parameter` option

The option `--parameter`, could specify a file input located in a different project than option `--project-name`. The files can only be located inside the project's `Data` subfolder, not `Cohorts` or `Analyses Results`. The accepted structures for different parameter projects are:
- `-p/--parameter "--file=<project>/Data/file.txt"`
- `-p/--parameter "--file=<project>/Data/subfolder/file.txt"`
- `-p/--parameter "--file=Data/subfolder/file.txt"` (the same project as `--project-name`)
- `-p/--parameter "--file=<project>/Data/subfolder/*.txt"`
- `-p/--parameter "--file=<project>/Data/*.txt"`
- `-p/--parameter "--file=Data/*.txt"` (the same project as `--project-name`)

The project, should be specified at the beginning of the file path. For example:

```console
cloudos bash array-job \
    -p file=Data/input.csv
...
```
This will point to the global project, specified with `--project-name`. In contrast:

```console
cloudos bash array-job \
    -p data=Data/input.csv
    -p exp=PROJECT_EXPRESSION/Data/input.csv \
    --project-name "ADIPOSE"
...
```
for parameter `exp` it will point to a project named `PROJECT_EXPRESSION` in the File Explorer, and `data` parameter will be found in the global project `ADIPOSE`.

Apart from files, the parameter can also take glob patterns, for example:

```console
cloudos bash array-job \
    -p data=Data/input.csv
    -p exp="PROJECT_EXPRESSION/Data/*.csv" \
    --project-name "ADIPOSE"
...
```
will take all `csv` file extensions in the specified folder.

> [!NOTE]
> When specifying glob patterns, depending on the terminal is best to add it in double quotes to avoid the terminal searching for the glob pattern locally, e.g. `-p exp="PROJECT_EXPRESSION/Data/*.csv"`.

> [!NOTE]
> Project names in the `--parameter` option can start with either forward slash `/` or without. The following are the same `-p data=/PROJECT1/Data/input.csv` and `-p data=PROJECT1/Data/input.csv`.

#### Get path to logs of job from CloudOS

Get the path to "Nextflow logs", "Nextflow standard output", and "trace" files. It can be used only on your user's jobs, with any status.

Example
```console
cloudos job logs --cloudos-url $CLOUDOS \
    --apikey $MY_API_KEY \
    --workspace-id $WORKSPACE_ID \
    --job-id "12345678910"
    

Executing logs...
Logs URI: s3://path/to/location/of/logs

Nextflow log: s3://path/to/location/of/logs/.nextflow.log

Nextflow standard output: s3://path/to/location/of/logs/stdout.txt

Trace file: s3://path/to/location/of/logs/trace.txt
```

#### Get path to result files of jobs from CloudOS

Get the path where CloudOS stores the output files for a job. This can be used only on your user's jobs and for jobs with "completed" status.

Example
```console
cloudos job logs --cloudos-url $CLOUDOS \
    --apikey $MY_API_KEY \
    --workspace-id $WORKSPACE_ID \
    --job-id "12345678910"
    

Executing results...
results: s3://path/to/location/of/results/results/
```

#### Abort single or multiple jobs from CloudOS

Aborts jobs in the CloudOS workspace that are either running or initialising. It can be used with one or more job IDs provided as a comma separated string using the `--job-ids` parameter.

Example:
```console
cloudos job abort \
    --cloudos-url $CLOUDOS \
    --apikey $MY_API_KEY \
    --workspace-id $WORKSPACE_ID \
    --job-ids "680a3cf80e56949775c02f16"


Aborting jobs...
        Job 680a3cf80e56949775c02f16 aborted successfully.
```


#### Clone a job with optional parameter overrides

The `clone` command allows you to create a new job based on an existing job's configuration, with the ability to override specific parameters. This is useful for re-running jobs with slight modifications without having to specify all parameters from scratch.

Basic usage:
```console
cloudos job clone \
    --profile MY_PROFILE
    --job-id "60a7b8c9d0e1f2g3h4i5j6k7"
```

Clone with parameter overrides:
```console
cloudos job clone \
    --profile MY_PROFILE
    --job-id "60a7b8c9d0e1f2g3h4i5j6k7" \
    --job-queue "high-priority-queue" \
    --cost-limit 50.0 \
    --instance-type "c5.2xlarge" \
    --job-name "cloned_analysis_v2" \
    --nextflow-version "24.04.4" \
    --git-branch "dev" \
    --nextflow-profile "production" \
    --do-not-save-logs true \
    --accelerate-file-staging true \
    --workflow-name "updated-workflow" \
    -p "input=s3://new-bucket/input.csv" \
    -p "output_dir=s3://new-bucket/results"
```

Available override options:
- `--job-queue`: Specify a different job queue
- `--cost-limit`: Set a new cost limit (use -1 for no limit)
- `--instance-type`: Change the master instance type
- `--job-name`: Assign a custom name to the cloned job
- `--nextflow-version`: Use a different Nextflow version
- `--git-branch`: Switch to a different git branch
- `--nextflow-profile`: Change the Nextflow profile
- `--do-not-save-logs`: Enable/disable log saving
- `--accelerate-file-staging`: Enable/disable fusion filesystem
- `--workflow-name`: Use a different workflow
- `-p, --parameter`: Override or add parameters (can be used multiple times)

> [!NOTE]
> Parameters can be overridden or new ones can be added using `-p` option

#### Executor support

CloudOS supports [AWS batch](https://www.nextflow.io/docs/latest/executor.html?highlight=executors#aws-batch) executor by default.
You can specify the AWS batch queue to
use, from the ones available in your workspace (see [here](#get-a-list-of-the-available-job-queues))
by specifying its name with the `--job-queue` parameter.
If none is specified, the most recent suitable queue in your workspace will be selected by default.
Example command:

```bash
cloudos job run \
    --cloudos-url $CLOUDOS \
    --apikey $MY_API_KEY \
    --workspace-id $WORKSPACE_ID \
    --project-name "$PROJECT_NAME" \
    --workflow-name $WORKFLOW_NAME \
    --job-config $JOB_PARAMS \
    --resumable
```

> Note: from cloudos-cli 2.7.0, the default executor is AWS batch. The previous Apache [ignite](https://www.nextflow.io/docs/latest/ignite.html#apache-ignite)
> executor is being removed progressively from CloudOS, so most likely will not be available in your CloudOS. Cloudos-cli is still supporting ignite during this
> period, by adding the `--ignite` flag to the `cloudos job run` command. Please, note that if you use `--ignite` flag in a CloudOS without ignite support,
> the command fail.

#### Azure execution platform support

CloudOS can also be configured to use Microsoft Azure compute platforms.
If your CloudOS is configured to
use Azure, you will need to take into consideration the following:

- When sending jobs to CloudOS using `cloudos job run` command, please use the option `--execution-platform azure`.
- Due to the lack of AWS batch queues in Azure, `cloudos queue list` command is not working.

Other than that, `cloudos-cli` will work very similarly. For instance, this is a typical send job command:

```bash
cloudos job run \
    --cloudos-url $CLOUDOS \
    --apikey $MY_API_KEY \
    --workspace-id $WORKSPACE_ID \
    --project-name "$PROJECT_NAME" \
    --workflow-name $WORKFLOW_NAME \
    --job-config $JOB_PARAMS \
    --resumable \
    --execution-platform azure
```

#### HPC execution support

CloudOS is also prepared to use an HPC compute infrastructure. For such cases, you will need to take into account the following for your job submissions using `cloudos job run` command:

- Use the following parameter: `--execution-platform hpc`.
- Indicate the HPC ID using: `--hpc-id XXXX`.

Example command:

```bash
cloudos job run \
    --cloudos-url $CLOUDOS \
    --apikey $MY_API_KEY \
    --workspace-id $WORKSPACE_ID \
    --project-name "$PROJECT_NAME" \
    --workflow-name $WORKFLOW_NAME \
    --job-config $JOB_PARAMS \
    --execution-platform hpc \
    --hpc-id $YOUR_HPC_ID
```

Please, note that HPC execution do not support the following parameters and all of them will be ignored:

- `--job-queue`
- `--resumable | --do-not-save-logs`
- `--instance-type` | `--instance-disk` | `--cost-limit`
- `--storage-mode` | `--lustre-size`
- `--wdl-mainfile` | `--wdl-importsfile` | `--cromwell-token`

#### Check job status

To check the status of a submitted job, just use the suggested command:

```bash
cloudos job status \
    --apikey $MY_API_KEY \
    --cloudos-url $CLOUDOS \
    --job-id 62c83a1191fe06013b7ef355
```

The expected output should be something similar to:

```console
Executing status...
	Your current job status is: completed

	To further check your job status you can either go to https://cloudos.lifebit.ai/app/advanced-analytics/analyses/62c83a1191fe06013b7ef355 or repeat the command you just used.
```

#### Check job details

To check the details of a submitted job, the subcommand `details` of `job` can be used.

For example, with explicit variable for required parameters:

```bash
cloudos job details \
    --apikey $MY_API_KEY \
    --job-id 62c83a1191fe06013b7ef355
```

Or with a defined profile:

```bash
cloudos job details \
    --profile job-details \
    --job-id 62c83a1191fe06013b7ef355
```

The expected output should be something similar to when using the defaults and the details are displayed in the standard output console:

```console
Executing details...
                                             Job Details                                              
┏━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Field                    ┃ Value                                                                   ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Parameters               │ -test=value                                                             │
│                          │ --gaq=test                                                              │
│                          │ cryo=yes                                                                │
│ Command                  │ echo 'test' > new_file.txt                                              │
│ Revision                 │ sha256:6015f66923d7afbc53558d7ccffd325d43b4e249f41a6e93eef074c9505d2233 │
│ Nextflow Version         │ None                                                                    │
│ Execution Platform       │ Batch AWS                                                               │
│ Profile                  │ None                                                                    │
│ Master Instance          │ c5.xlarge                                                               │
│ Storage                  │ 500                                                                     │
│ Job Queue                │ nextflow-job-queue-5c6d3e9bd954e800b23f8c62-feee                        │
│ Accelerated File Staging │ None                                                                    │
│ Task Resources           │ 1 CPUs, 4 GB RAM                                                        │
└──────────────────────────┴─────────────────────────────────────────────────────────────────────────┘
```

To change this behaviour and save the details into a local JSON, the parameter `--output-format` needs to be set as `--output-format=json`.

By default, all details are saved in a file with the basename as `job_details`, for example `job_details.json` or `job_details.config.`. This can be changed with the parameter `--output-basename=new_filename`.

The `details` subcommand, can also take `--parameters` as an argument flag, which will create a new file `*.config` that holds all parameters as a Nexflow configuration file, example:

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

#### Get a list of workspace jobs from a CloudOS

You can get a summary of the workspace's last 30 submitted jobs (or a selected number of last jobs using `--last-n-jobs n` parameter) in two different formats:

- CSV: this is a table with a minimum predefined set of columns by default, or all the
available columns using the `--all-fields` argument.
- JSON: all the available information from the workspace jobs, in JSON format (`--all-fields` is always enabled for this format).

To get a list with the workspace's last 30 submitted jobs, in CSV format, use
the following command:

```bash
cloudos job list \
    --cloudos-url $CLOUDOS \
    --apikey $MY_API_KEY \
    --workspace-id $WORKSPACE_ID \
    --output-format csv \
    --all-fields
```

The expected output is something similar to:

```console
Executing list...
	Job list collected with a total of 30 jobs.
	Job list saved to joblist.csv
```

In addition, a file named `joblist.csv` is created.

To get the same information, but for all the workspace's jobs and in JSON format, use the following command:

```bash
cloudos job list \
    --cloudos-url $CLOUDOS \
    --apikey $MY_API_KEY \
    --workspace-id $WORKSPACE_ID \
    --last-n-jobs all \
    --output-format json
```
```console
Executing list...
	Job list collected with a total of 276 jobs.
	Job list saved to joblist.json
```

#### Get a list of all available workflows from a CloudOS workspace

You can get a summary of all the available workspace workflows in two different formats:
- CSV: this is a table with a minimum predefined set of columns by default, or all the
available columns using the `--all-fields` parameter.
- JSON: all the available information from workflows, in JSON format.

To get a CSV table with all the available workflows for a given workspace, use
the following command:

```bash
cloudos workflow list \
    --cloudos-url $CLOUDOS \
    --apikey $MY_API_KEY \
    --workspace-id $WORKSPACE_ID \
    --output-format csv \
    --all-fields
```

The expected output is something similar to:

```console
Executing list...
	Workflow list collected with a total of 609 workflows.
	Workflow list saved to workflow_list.csv
```

To get the same information, but in JSON format, use the following command:

```bash
cloudos workflow list \
    --cloudos-url $CLOUDOS \
    --apikey $MY_API_KEY \
    --workspace-id $WORKSPACE_ID \
    --output-format json
```

```console
Executing list...
	Workflow list collected with a total of 609 workflows.
	Workflow list saved to workflow_list.json
```

The collected workflows are those that can be found in "WORKSPACE TOOLS" section in CloudOS.

#### Import a Nextflow workflow to a CloudOS workspace

You can import new workflows to your CloudOS workspaces. The only requirements are:

- The workflow is a Nextflow pipeline.
- The workflow repository is located at GitHub, GitLab or BitBucket Server (specified by the option `--repository-platform`. Available options: `github`, `gitlab` and `bitbucketServer`)
- If your repository is private, you have access to the repository and to have linked your GitHub, Gitlab or Bitbucket server accounts to CloudOS.

#### Usage of the workflow import command

To import GitHub workflows to CloudOS, you can use the following command:

```bash
# Example workflow to import: https://github.com/lifebit-ai/DeepVariant
WORKFLOW_URL="https://github.com/lifebit-ai/DeepVariant"

cloudos workflow import \
    --cloudos-url $CLOUDOS \
    --apikey $MY_API_KEY \
    --workspace-id $WORKSPACE_ID \
    --workflow-url $WORKFLOW_URL \
    --workflow-name "new_name_for_the_github_workflow" \
    --repository-platform github
```

The expected output will be:

```console
CloudOS workflow functionality: list and import workflows.

Executing workflow import...

	[Message] Only Nextflow workflows are currently supported.

	Workflow test_import_github_3 was imported successfully with the following ID: 6616a8cb454b09bbb3d9dc20
```

Optionally, you can add a link to your workflow documentation by providing the URL using the parameter `--workflow-docs-link`. E.g.:

```bash
cloudos workflow import \
    --cloudos-url $CLOUDOS \
    --apikey $MY_API_KEY \
    --workspace-id $WORKSPACE_ID \
    --workflow-url $WORKFLOW_URL \
    --workflow-name "new_name_for_the_github_workflow" \
    --workflow-docs-link "https://github.com/lifebit-ai/DeepVariant/blob/master/README.md" \
    --repository-platform github
```

> NOTE: please, take into account that importing workflows using cloudos-cli is not yet available in all the CloudOS workspaces. If you try to use this feature in a non-prepared workspace you will get the following error message: `It seems your API key is not authorised. Please check if your workspace has support for importing workflows using cloudos-cli`.

#### Get a list of all available projects from a CloudOS workspace

Similarly to the `workflows` functionality, you can get a summary of all the available workspace
projects in two different formats:
- CSV: this is a table with a minimum predefined set of columns by default, or all the
available columns using the `--all-fields` parameter.
- JSON: all the available information from projects, in JSON format.

To get a CSV table with all the available projects for a given workspace, use
the following command:

```bash
cloudos project list \
    --cloudos-url $CLOUDOS \
    --apikey $MY_API_KEY \
    --workspace-id $WORKSPACE_ID \
    --output-format csv \
    --all-fields
```

The expected output is something similar to:

```console
Executing list...
	Workflow list collected with a total of 320 projects.
	Workflow list saved to project_list.csv
```

#### Create a new project in CloudOS

You can create a new project in your CloudOS workspace using the `project create` command.
This command requires the name of the new project and will return the project ID upon successful creation.

```bash
cloudos project create \
    --cloudos-url $CLOUDOS \
    --apikey $MY_API_KEY \
    --workspace-id $WORKSPACE_ID \
    --new-project "My New Project"
```

The expected output is something similar to:

```console
	Project "My New Project" created successfully with ID: 64f1a23b8e4c9d001234abcd
```

#### Get a list of the available job queues

Job queues are required for running jobs using AWS batch executor. The available job queues in your CloudOS workspace are
listed in the "Compute Resources" section in "Settings".
You can get a summary of all the available workspace job queues in two formats:
- CSV: this is a table with a selection of the available job queue information. Alternatively, you can
get all the information using the `--all-fields` flag.
- JSON: all the available information from job queues, in JSON format.

Example command: getting all available job queues in JSON format.

```bash
cloudos queue list \
    --cloudos-url $CLOUDOS \
    --apikey $MY_API_KEY \
    --workspace-id $WORKSPACE_ID \
    --output-format json \
    --output-basename "available_queues"
```

```
Executing list...
	Job queue list collected with a total of 5 queues.
	Job queue list saved to available_queues.json
```

> NOTE: the queue name that is visible in CloudOS and has to be used in combination with `--job-queue` parameter is
the one in `label` field.

##### Job queues for platform workflows

Platform workflows, i.e., those provided by CloudOS in your workspace as modules, run on separated and specific AWS batch queues.
Therefore, CloudOS will automatically assign the valid queue and the user should not specify any queue using the `--job-queue` paramater.
Any attempt of using this parameter will be ignored. Examples of such platform workflows are "System Tools" and "Data Factory" workflows.

#### Explore files programmatically

##### Listing files

To list files present in File Explorer in a given project (whether they are analysis results, cohorts etc.), the user can run the following command:
```
cloudos datasets ls <path> --profile <profile name>
```
Please, note that in the above example a preconfigured profile has been used. If no profile is provided and there is no default profile, the user will need to provide the following commands:
```bash
cloudos datasets ls <path> \
    --cloudos-url $CLOUDOS \
    --apikey $MY_API_KEY \
    --workspace-id $WORKSPACE_ID \
    --project-name $PROJEC_NAME
```


The output of this command is a list of files and folders present in the specified project.
If the `<path>` is left empty, the command will return the list of folders present in the selected project.

If you require more information on the files and folder listed, you can use the `--details` flag that will output a table containing the following columns:
- Type (folder or file)
- Owner
- Size in human readable format
- Last updated
- File Name (the file or folder name)
- Storage Path

##### Moving files

Files and folders can be moved **from** `Data` or any of its subfolders (i.e `Data`, `Data/folder/file.txt`) **to** `Data` or any of its subfolders programmatically.

1. The move can happen **within the same project** running the following command:
```
cloudos datasets mv <souce_path> <destination_path> --profile <profile name>
```
where the source project as well as the destination one is the one defined in the profile.

2. The move can also happen **across different projects**  within the same workspace by running the following command
```
cloudos datasets mv <source_path> <destiantion_path> --profile <profile_name> --destination-project-name <project_name>
```
In this case, only the source project is the one specified in the profile.

Any of the `source_path` must be a full path, starting from the `Data` datasets and its folder; any `destination_path` must be a path starting with `Data` and finishing with the folder where to move the file/folder. An example of such command is:

```
cloudos datasets mv Data/results/my_plot.png Data/plots 
```

Please, note that in the above example a preconfigured profile has been used. If no profile is provided and there is no default profile, the user will need to also provide the following flags
```bash
    --cloudos-url $CLOUDOS \
    --apikey $MY_API_KEY \
    --workspace-id $WORKSPACE_ID \
    --project-name $PROJEC_NAME
```

#### Renaming files

Files and folders within the `Data` dataset can be renamed using the following command

```
cloudos datasets rename <path> <new_name>
```
where `path` is the full path to the file/folder to be renamed and `new_name` is just the name, no path required, as the file will not be moved.

Please, be aware that renaming can only happen in files and folders that are present in the `Data` datasets and that were created or uploaded by your user.

Please, note that in the above example a preconfigured profile has been used. If no profile is provided and there is no default profile, the user will need to also provide the following flags

```bash
    --cloudos-url $CLOUDOS \
    --apikey $MY_API_KEY \
    --workspace-id $WORKSPACE_ID \
    --project-name $PROJEC_NAME
```

#### Copying files and folders

Files and folders can be copied **from** anywhere in the project **to** `Data` or any of its subfolders programmatically (i.e `Data`, `Data/folder/file.txt`).

1. The copy can happen **within the same project** running the following command:
```
cloudos datasets cp <souce_path> <destination_path> --profile <profile name>
```
where the source project as well as the destination one is the one defined in the profile.

2. The move can also happen **across different projects**  within the same workspace by running the following command
```
cloudos datasets cp <source_path> <destiantion_path> --profile <profile_name> --destination-project-name <project_name>
```
In this case, only the source project is the one specified in the profile.

Any of the `source_path` must be a full path; any `destination_path` must be a path starting with `Data` and finishing with the folder where to move the file/folder. An example of such command is:

```
cloudos datasets cp AnalysesResults/my_analysis/results/my_plot.png Data/plots 
```

Please, note that in the above example a preconfigured profile has been used. If no profile is provided and there is no default profile, the user will need to also provide the following flags
```bash
    --cloudos-url $CLOUDOS \
    --apikey $MY_API_KEY \
    --workspace-id $WORKSPACE_ID \
    --project-name $PROJEC_NAME
```

#### Linking S3 folders to Interactive Analysis

The CLI can link S3 folders into an interactive session, which will appear in the left panel of the session as "mounted". This subcommand is using the option `--session-id` to access the correct interactive session. This option can be added to the CLI or defined in a profile, for convenience.

The usage of the subcommand is as follows:

```console
cloudos datasets link <S3 FOLDER COMPLETE PATH> <options>
```

For example:

```console
cloudos datasets link s3://bucket/path/folder --profile test
```
where profile `test` has already defined the `--session-id`.

Or specifying explicitly:

```console
cloudos datasets link s3://bucket/path/folder --profile test --session-id 1234
```
where profile `test` is used for all other necessary variables, but `--session-id` is overwritten from the command line.

> [!NOTE]
> If running the CLI inside a jupyter session, the pre-configured CLI installation will have the session ID already installed and only the `--apikey` needs to be added.

#### Linking a File Explorer folder to Interactive Analysis

Linking a File Explorer folder to an Interactive Analysis session can be done using the same subcommand as for the s3 folders:

```console
cloudos datasets link <File Explorer FOLDER PATH> <options>
```

Examples (one per line):

```console
cloudos datasets link Data/ingest_data --profile test
cloudos datasets link Data/SEQUENCES --session-id 1234
cloudos datasets link Data/SEQUENCES/HCC --session-id 1234
cloudos datasets link "Analyses Results/HLA" --session-id 1234
```

> [!NOTE]
> Virtual folders in File Explorer, the ones a user has created in File explorer and are not actual storage locations, cannot be linked.

#### Create a (virtual) folder

New folders can be created within the `Data` dataset and its subfolders using the following command

```
cloudos datasets mkdir <new_folder_path>
```
where ` new_folder_path` is the path to the folder to be created.

Please, be aware that the folder creation can only happen in `Data` or its sub-folders.

Please, note that in the above example a preconfigured profile has been used. If no profile is provided and there is no default profile, the user will need to also provide the following flags

```bash
    --cloudos-url $CLOUDOS \
    --apikey $MY_API_KEY \
    --workspace-id $WORKSPACE_ID \
    --project-name $PROJEC_NAME
```
#### Removing files and folders

Files and folders can be removed from file explorer (in the `Data` datasets and its subfolders) using the following command

```
cloudos datasets rm <path> 
```
where `path` is the full path to the file/folder to be removed.

Please, be aware that removing files and folders will only remove them from the file explorer and not from the corresponding cloud storage.

Please, keep in mind that you are only allowed to remove files or folders in `Data` or its subfolders.

Please, note that in the above example a preconfigured profile has been used. If no profile is provided and there is no default profile, the user will need to also provide the following flags

```bash
    --cloudos-url $CLOUDOS \
    --apikey $MY_API_KEY \
    --workspace-id $WORKSPACE_ID \
    --project-name $PROJEC_NAME
```

### Procurement image management

CloudOS supports procurement functionality to manage and list images associated with organizations within a given procurement. This feature is useful for administrators and users who need to view available container images across different organizations in their procurement.

#### List procurement images

You can get a list of images associated with organizations of a given procurement using the `cloudos procurement images ls` command. This command provides paginated results showing image configurations and metadata.

To list images for a specific procurement, use the following command:

```bash
cloudos procurement images ls \
    --cloudos-url $CLOUDOS \
    --apikey $MY_API_KEY \
    --procurement-id "your_procurement_id_here"
```

#### Command options

The `cloudos procurement images ls` command supports the following options:

- `--apikey` / `-k`: Your CloudOS API key (required)
- `--cloudos-url` / `-c`: The CloudOS URL you are trying to access (default: https://cloudos.lifebit.ai)
- `--procurement-id`: The specific CloudOS procurement ID (required)
- `--page`: The response page number (default: 1)
- `--limit`: The page size limit (default: 10)
- `--disable-ssl-verification`: Disable SSL certificate verification
- `--ssl-cert`: Path to your SSL certificate file
- `--profile`: Profile to use from the config file

#### Example usage

Here's a complete example of how to list procurement images:

```bash
# Set up your environment variables
MY_API_KEY="xxxxx"
CLOUDOS="https://cloudos.lifebit.ai"
PROCUREMENT_ID="your_procurement_id"

# List images for the procurement (first page, 10 items)
cloudos procurement images ls \
    --cloudos-url $CLOUDOS \
    --apikey $MY_API_KEY \
    --procurement-id $PROCUREMENT_ID
```

To get more results per page or navigate to different pages:

```bash
# Get 25 images from page 2
cloudos procurement images ls \
    --cloudos-url $CLOUDOS \
    --apikey $MY_API_KEY \
    --procurement-id $PROCUREMENT_ID \
    --page 2 \
    --limit 25
```

#### Using profiles

You can also use profiles to simplify the command, and `--procurement-id` is now a configurable parameter when configuring a new profile.

With the new profile, you can run:

```bash
cloudos procurement images ls --profile procurement-profile
```

#### Output format

The command returns detailed information about image configurations and pagination metadata in JSON format, including:

- **Image configurations**: Details about available container images
- **Pagination metadata**: Information about total pages, current page, and available items

This is particularly useful for understanding what container images are available across different organizations within your procurement and for programmatic access to image inventory.

#### Set procurement organization image

You can set a custom image ID or name for an organization within a procurement using the `cloudos procurement images set` command. This allows you to override the default CloudOS images with your own custom images for specific organizations.

To set a custom image for an organization, use the following command:

```bash
cloudos procurement images set \
    --cloudos-url $CLOUDOS \
    --apikey $MY_API_KEY \
    --procurement-id "your_procurement_id" \
    --organisation-id "your_organization_id" \
    --image-type "JobDefault" \
    --provider "aws" \
    --region "us-east-1" \
    --image-id "ami-0123456789abcdef0" \
    --image-name "custom-image-name"
```

##### Set command options

The `cloudos procurement images set` command supports the following options:

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

##### Set command example

Here's a complete example showing how to set a custom image:

```bash
# Set up your environment variables
MY_API_KEY="xxxxx"
CLOUDOS="https://cloudos.lifebit.ai"
PROCUREMENT_ID="your_procurement_id"
ORGANISATION_ID="your_organization_id"

# Set custom image for job execution
cloudos procurement images set \
    --cloudos-url $CLOUDOS \
    --apikey $MY_API_KEY \
    --procurement-id $PROCUREMENT_ID \
    --organisation-id $ORGANISATION_ID \
    --image-type "JobDefault" \
    --provider "aws" \
    --region "us-east-1" \
    --image-id "ami-0123456789abcdef0" \
    --image-name "my-custom-job-image"
```

#### Reset procurement organization image

You can reset an organization's image configuration back to CloudOS defaults using the `cloudos procurement images reset` command. This removes any custom image configurations and restores the original CloudOS defaults.

To reset an organization's image to defaults, use the following command:

```bash
cloudos procurement images reset \
    --cloudos-url $CLOUDOS \
    --apikey $MY_API_KEY \
    --procurement-id "your_procurement_id" \
    --organisation-id "your_organization_id" \
    --image-type "JobDefault" \
    --provider "aws" \
    --region "us-east-1"
```

##### Reset command options

The `cloudos procurement images reset` command supports the following options:

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

##### Reset command example

Here's a complete example showing how to reset an image to defaults:

```bash
# Set up your environment variables
MY_API_KEY="xxxxx"
CLOUDOS="https://cloudos.lifebit.ai"
PROCUREMENT_ID="your_procurement_id"
ORGANISATION_ID="your_organization_id"

# Reset image configuration to CloudOS defaults
cloudos procurement images reset \
    --cloudos-url $CLOUDOS \
    --apikey $MY_API_KEY \
    --procurement-id $PROCUREMENT_ID \
    --organisation-id $ORGANISATION_ID \
    --image-type "JobDefault" \
    --provider "aws" \
    --region "us-east-1"
```

### WDL pipeline support

#### Cromwell server managing

In order to run WDL pipelines, a Cromwell server in CloudOS should be running. This server can
be accessed to check its status, restart it or stop it, using the following commands:

```bash
# Check Cromwell status
cloudos cromwell status \
    --cloudos-url $CLOUDOS \
    --apikey $MY_API_KEY \
    --workspace-id $WORKSPACE_ID
```

```console
Executing status...
	Current Cromwell server status is: Stopped
```

```bash    
# Cromwell start
cloudos cromwell start \
    --cloudos-url $CLOUDOS \
    --apikey $MY_API_KEY \
    --workspace-id $WORKSPACE_ID
```

```console
Starting Cromwell server...
	Current Cromwell server status is: Initializing

	Current Cromwell server status is: Running
```

```bash
# Cromwell stop
cloudos cromwell stop \
    --cloudos-url $CLOUDOS \
    --apikey $MY_API_KEY \
    --workspace-id $WORKSPACE_ID
```

```console
Stopping Cromwell server...
	Current Cromwell server status is: Stopped
```

#### Running WDL workflows

To run WDL workflows, `cloudos job run` command can be used normally, but adding two extra
parameters:

- `--wdl-mainfile`: name of the mainFile (*.wdl) file used by the CloudOS workflow.
- `--wdl-importsfile` [Optional]: name of the worfklow imported file (importsFile, *.zip).

All the rest of the `cloudos job run` functionality is available.

> NOTE: WDL does not support `profiles` and therefore, `--nextflow-profile` option is not
available. Instead, use `--job-config` and/or `--parameter`. The format of the job config file is
expected to be the same as for nextflow pipelines.

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

> NOTE: when using `--parameter` option, if the value needs quotes (`"`) you will need to escape them.
E.g.: `--parameter test.arrayTest=[\"lala\"]`

```bash
# Configure variables
MY_API_KEY="xxxxx"
CLOUDOS="https://cloudos.lifebit.ai"
WORKSPACE_ID="xxxxx"
PROJECT_NAME="wdl-test"
WORKFLOW_NAME="wdl- test"
MAINFILE="hello.wdl"
IMPORTSFILE="imports_7mb.zip"
JOB_PARAMS="cloudos/examples/wdl.config"

# Run job
cloudos job run \
  --cloudos-url $CLOUDOS \
  --apikey $MY_API_KEY \
  --workspace-id $WORKSPACE_ID \
  --project-name $PROJECT_NAME \
  --workflow-name "$WORKFLOW_NAME" \
  --wdl-mainfile $MAINFILE \
  --wdl-importsfile $IMPORTSFILE \
  --job-config $JOB_PARAMS \
  --wait-completion
```

```console
Executing run...
    WDL workflow detected

    Current Cromwell server status is: Stopped

    Starting Cromwell server...

    Current Cromwell server status is: Initializing


    Current Cromwell server status is: Running

    *******************************************************************************
    [WARNING] Cromwell server is now running. Plase, remember to stop it when your
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

### Import the functionality to your own python scripts

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
j_status = j.get_job_status(j_id)
j_status_h = json.loads(j_status.content)["status"]
print(j_status_h)
```

The status will change while your job progresses, so to check again just
repeat the above code.

You can also collect your last 30 submitted jobs for a given workspace using the
following command.

```python
my_jobs_r = j.get_job_list(workspace_id)
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
j_status = j.get_job_status(j_id)
j_status_h = json.loads(j_status.content)["status"]
print(j_status_h)

# Stop Cromwell server
cl.cromwell_switch(workspace_id, 'stop')

# Check again Cromwell status
c_status = cl.get_cromwell_status(workspace_id)
c_status_h = json.loads(c_status.content)["status"]
print(c_status_h)
```

### unit testing

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

# cloudos

Python package for interacting with CloudOS

## Requirements

The package requires Python >= 3.8 and the following python packages:

```
click>=8.0.1
pandas>=1.3.4
requests>=2.26.0
```

## Installation

### Docker image
It is recommended to install it as a docker image using the `Dockerfile`
and the `environment.yml` files provided.

To run the existing docker image at `quay.io`:

```bash
docker run --rm -it quay.io/lifebitaiorg/cloudos-cli:latest
```

### From Github

You will need Python >= 3.8 and pip installed.

Clone the repo and install it using pip:

```bash
git clone https://github.com/lifebit-ai/cloudos-cli
cd cloudos-cli
pip install -r requirements.txt
pip install .
```

> NOTE: To be able to call the `cloudos` executable, ensure that the local clone of the `cloudos-cli` folder is included in the `PATH` variable ,using for example the command `export PATH="/absolute/path/to/cloudos-cli:$PATH"`.
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

Options:
  --version  Show the version and exit.
  --help     Show this message and exit.

Commands:
  cromwell  Cromwell server functionality: check status, start and stop.
  job       CloudOS job functionality: run and check jobs in CloudOS.
  project   CloudOS project functionality: list projects in CloudOS.
  workflow  CloudOS workflow functionality: list workflows in CloudOS.
``` 

This will tell you the implemented commands. Each implemented command has its
own subcommands with its own `--help`:

```bash
cloudos job run --help
```
```console
Options:
  -k, --apikey TEXT           Your CloudOS API key  [required]
  -c, --cloudos-url TEXT      The CloudOS url you are trying to access to.
                              Default=https://cloudos.lifebit.ai.
  --workspace-id TEXT         The specific CloudOS workspace id.  [required]
  --project-name TEXT         The name of a CloudOS project.  [required]
  --workflow-name TEXT        The name of a CloudOS workflow or pipeline.
                              [required]
  --job-config TEXT           A config file similar to a nextflow.config file,
                              but only with the parameters to use with your
                              job.
  -p, --parameter TEXT        A single parameter to pass to the job call. It
                              should be in the following form:
                              parameter_name=parameter_value. E.g.: -p
                              input=s3://path_to_my_file. You can use this
                              option as many times as parameters you want to
                              include.
  --nextflow-profile TEXT     A comma separated string indicating the nextflow
                              profile/s to use with your job.
  --git-commit TEXT           The exact whole 40 character commit hash to run
                              for the selected pipeline. If not specified it
                              defaults to the last commit of the default
                              branch.
  --git-tag TEXT              The tag to run for the selected pipeline. If not
                              specified it defaults to the last commit of the
                              default branch.
  --job-name TEXT             The name of the job. Default=new_job.
  --resumable                 Whether to make the job able to be resumed or
                              not.
  --batch                     Whether to make use the batch executor instead
                              of the default ignite.
  --instance-type TEXT        The type of AMI to use. Default=c5.xlarge.
  --instance-disk INTEGER     The amount of disk storage to configure.
                              Default=500.
  --spot                      Whether to make a spot instance.
  --storage-mode TEXT         Either 'lustre' or 'regular'. Indicates if the
                              user wants to select regular or lustre storage.
                              Default=regular.
  --lustre-size INTEGER       The lustre storage to be used when --storage-
                              mode=lustre, in GB. It should be 1200 or a
                              multiple of it. Default=1200.
  --wait-completion           Whether to wait to job completion and report
                              final job status.
  --wait-time INTEGER         Max time to wait (in seconds) to job completion.
                              Default=3600.
  --wdl-mainfile TEXT         For WDL workflows, which mainFile (.wdl) is
                              configured to use.
  --wdl-importsfile TEXT      For WDL workflows, which importsFile (.zip) is
                              configured to use.
  -t, --cromwell-token TEXT   Specific Cromwell server authentication token.
                              Currently, not necessary as apikey can be used
                              instead, but maintained for backwards
                              compatibility.
  --repository-platform TEXT  Name of the repository platform of the workflow.
                              Default=github.
  --cost-limit FLOAT          Add a cost limit to your job. Default=30.0 (For
                              no cost limit please use -1).
  --verbose                   Whether to print information messages or not.
  --request-interval INTEGER  Time interval to request (in seconds) the job
                              status. For large jobs is important to use a
                              high number to make fewer requests so that is
                              not considered spamming by the API. Default=30.
  --disable-ssl-verification  Disable SSL certificate verification. Please,
                              remember that this option is not generally
                              recommended for security reasons.
  --ssl-cert TEXT             Path to your SSL certificate file.
  --help                      Show this message and exit.
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
JOB_PARAMS="cloudos/examples/rnatoy.config"
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
    --resumable \
    --spot
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
    --resumable \
    --spot
```

> NOTE: options `--job-config` and `--parameter` are completely compatible and complementary, so you can use a
`--job-config` and adding additional parameters using `--parameter` in the same call.

If everything went well, you should see something like:

```console
Executing run...
	Job successfully launched to CloudOS, please check the following link: https://cloudos.lifebit.ai/app/jobs/62c83a1191fe06013b7ef355
	Your assigned job id is: 62c83a1191fe06013b7ef355
	Your current job status is: initializing
	To further check your job status you can either go to https://cloudos.lifebit.ai/app/jobs/62c83a1191fe06013b7ef355 or use the following command:
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
    --spot \
    --wait-completion
```

When setting this parameter, you can also set `--request-interval` to a bigger number (default is 30s) if the job is quite large. This will ensure that the status requests are not sent too close from each other and recognized as spam by the API.

If the job takes less than `--wait-time` (3600 seconds by default), the
previous command should have an output similar to:

```console
Executing run...
	Job successfully launched to CloudOS, please check the following link: https://cloudos.lifebit.ai/app/jobs/62c83a6191fe06013b7ef363
	Your assigned job id is: 62c83a6191fe06013b7ef363
	Please, wait until job completion or max wait time of 3600 seconds is reached.
	Your current job status is: initializing.
	Your current job status is: running.
	Your job took 420 seconds to complete successfully.
```

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

	To further check your job status you can either go to https://cloudos.lifebit.ai/app/jobs/62c83a1191fe06013b7ef355 or repeat the command you just used.
```

#### Get a list of your jobs from a CloudOS workspace

You can get a summary of your last 30 submitted jobs (or your selected number of last jobs using `--last-n-jobs n`
parameter) in two different formats:

- CSV: this is a table with a minimum predefined set of columns by default, or all the
available columns using the `--all-fields` argument.
- JSON: all the available information from your jobs, in JSON format.

To get a list with your last 30 submitted jobs to a given workspace, in CSV format, use
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

To get the same information, but for all your jobs and in JSON format, use the following command:

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

#### Get a list of all available projects from a CloudOS workspace

Similarly to the `workflows` functionality, you can get a summary of all the available workspace
projects in two different formats:
- CSV: this is a table with a minimum predefined set of columns by default, or all the
available columns using the `--all-fields` parameter.
- JSON: all the available information from workflows, in JSON format.

To get a CSV table with all the available workflows for a given workspace, use
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
import cloudos.jobs.job as jb
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
import cloudos.clos as cl
import cloudos.jobs.job as jb
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

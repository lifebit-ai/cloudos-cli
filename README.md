# cloudos

__Date:__ 2021-08-18\
__Version:__ 0.0.1

Python package for interacting with CloudOS

## Requirements

The package requires Python >= 3.8 and the following python packages:

```
click
requests
```

## Installation

### Docker image
It is recommended to install it as a docker image using the `Dockerfile`
and the `environment.yml` files provided.

To run the existing docker image at `quay.io/lifebitai`:

```
docker run --rm -it quay.io/dpineyro/cloudos-py:latest
```

### From Github

You will need Python >= 3.8 and pip installed.

Clone the repo and install it using pip:

```
git clone https://github.com/lifebit-ai/cloudos-py
git checkout dev
cd cloudos-py
pip install -r requirements.txt
pip install .
```

## Usage

The package is meant to be used both as a CLI tool and as a regular package to
import to your own scripts.

### Usage as a Command Line Interface tool

To get general information about the tool:

```
$ cloudos --help
Usage: cloudos [OPTIONS] COMMAND [ARGS]...

  CloudOS python package: a package for interacting with CloudOS.

Options:
  --help  Show this message and exit.

Commands:
  jobstatus
  runjob
``` 

This will tell you the implemented commands. Each implemented command has its
own `--help`:

```
$ cloudos runjob --help
CloudOS python package: a package for interacting with CloudOS.

Usage: cloudos runjob [OPTIONS]

Options:
  -k, --apikey TEXT        Your CloudOS API key  [required]
  -c, --cloudos-url TEXT   The CloudOS url you are trying to access to.
                           Default=https://cloudos.lifebit.ai.
  --workspace-id TEXT      The specific CloudOS workspace id.  [required]
  --project-name TEXT      The name of a CloudOS project.  [required]
  --workflow-name TEXT     The name of a CloudOS workflow or pipeline.
                           [required]
  --job-params TEXT        A nextflow.config file or similar, with the
                           parameters to use with your job.  [required]
  --job-name TEXT          The name of the job. Default=new_job.
  --resumable              Whether to make the job able to be resumed or not.
  --instance-type TEXT     The type of AMI to use. Default=c5.xlarge.
  --instance-disk INTEGER  The amount of disk storage to configure.
                           Default=500.
  --spot                   Whether to make a spot instance.
  --verbose                Whether to print information messages or not.
  --help                   Show this message and exit.
```

#### Send a job to CloudOS

First, configure your local environment to ease parameters input. We will
try to submit a small toy example already available.

```bash
MY_API_KEY="xxxxx"
WORKSPACE_ID="5c6d3e9bd954e800b23f8c62"
PROJECT_NAME="API jobs"
WORKFLOW_NAME="rnatoy"
JOB_PARAMS="cloudos/examples/rnatoy.config"
```

As you can see, a file with the job parameters is required to configure the
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
cloudos runjob \
    -k $MY_API_KEY \
    --workspace-id $WORKSPACE_ID \
    --project-name "$PROJECT_NAME" \
    --workflow-name $WORKFLOW_NAME \
    --job-params $JOB_PARAMS \
    --resumable \
    --spot
```

If everything went well, you should see something like:

```
CloudOS python package: a package for interacting with CloudOS.

Job successfully launched to CloudOS, please check the following link: https://cloudos.lifebit.ai/app/jobs/612027b07db707019a095075
Your assigned job id is: 612027b07db707019a095075
Your current job status is: initializing
To further check your job status you can either go to https://cloudos.lifebit.ai/app/jobs/612027b07db707019a095075 or use the following command:
cloudos jobstatus \
    --apikey $MY_API_KEY \
    --cloudos-url https://cloudos.lifebit.ai \
    --job-id 612027b07db707019a095075
```

As you can see, the current status is `initializing`. This will change
while the job progresses. To check the status, just apply the suggested
command.

#### Check job status

To check the status of a submitted job, just use the suggested command:

```bash
cloudos jobstatus \
    --apikey $MY_API_KEY \
    --cloudos-url https://cloudos.lifebit.ai \
    --job-id 612027b07db707019a095075
```

You will see the following output while the job is running:

```
CloudOS python package: a package for interacting with CloudOS.

Your current job status is: running

To further check your job status you can either go to https://cloudos.lifebit.ai/app/jobs/612027b07db707019a095075 or repeat the command you just used.
```

And eventually, if everything went correctly:


```
CloudOS python package: a package for interacting with CloudOS.

Your current job status is: completed

To further check your job status you can either go to https://cloudos.lifebit.ai/app/jobs/612027b07db707019a095075 or repeat the command you just used.
```


### Import the functionality to your own python scripts

To illustrate how to import the package and use its functionality inside
your own python scripts, we will perform a job submission and check its
status from inside a python script.

Again, we will set up the environment to ease the work:

```python
import cloudos.jobs.job as job
import json


# GLOBAL VARS.
apikey = 'xxxxx'
cloudos_url = 'https://cloudos.lifebit.ai'
workspace_id = '5c6d3e9bd954e800b23f8c62'
project_name = 'API jobs'
workflow_name = 'rnatoy'
job_params = 'cloudos/examples/rnatoy.config'
job_name = 'new_job'
resumable = True
instance_type = 'c5.xlarge'
instance_disk = 500
spot = True
```

First, create the `Job` object:

```python
j = job.Job(apikey, cloudos_url, workspace_id, project_name, workflow_name)
print(j)
```

Then, send the job:

```python
j_id = j.send_job(job_params,
                  job_name,
                  resumable,
                  instance_type,
                  instance_disk,
                  spot)
```

To check the status:

```python
j_status = j.get_job_status(j_id)
j_status_h = json.loads(j_status.content)["status"]
print(j_status_h)
```

The status will change while your job progresses, so to check again just
repeat the above code.

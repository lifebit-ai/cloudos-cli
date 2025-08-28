## lifebit-ai/cloudos-cli: changelog

## v2.52.0 (2025-08-25)

### Feat

-  Implements filtering options for `cloudos job list` (`filter_status`, `filter_job_name`, `filter_project`, `filter_workflow`, `filter_job_id`, `filter_only_mine` , `filter_owner`, `filter_queue` )


## v2.51.0 (2025-08-21)

### Fix

- set image name 

## v2.50.0 (2025-08-14)

### Feat

- Improves error messages for api-related errors
- removes the traceback to make the error more user-friendly
- adds a --debug flag to allow users/developers to get the traceback

## v2.49.0 (2025-08-07)

### Feat

- Enhanced CSV export functionality for job lists with improved column naming, ordering, and data formatting

## v2.48.0 (2025-08-06)

### Feat

- Adds support for creating new projects with 'cloudos project create' command

## v2.47.1 (2025-07-30)

### Fix

- Patches procurement_id requirement error in all commands

## v2.47.0 (2025-07-29)

### Feat

- Adds support for set and reset organisation images associated with a given procurement.

## v2.46.0 (2025-07-28)

### Feat

- Adds support for listing organisation images associated with a given procurement.

## v2.45.0 (2025-07-18)

### Feat

- Implements `--last` flag to use the last imported workflow in case of duplication

## v2.44.0 (2025-07-17)

### Feat

- Implements searching the API for workflow name

## v2.43.0 (2025-07-17)

### Feat

- Implements searching the API for project name to get project id

## v2.42.0 (2025-07-17)

### Feat

- Link File Explorer folder to Interactive Analysis

## v2.41.0 (2025-07-14)

### Feat

- Adds azure support for `datasets cp`

## v2.40.0 (2025-07-11)

### Feat

- Adds azure support for `datasets ls --details`

## v2.39.0 (2025-07-14)

### Feat

- Adds azure support for `datasets ls`

## v2.38.3 (2025-07-08)

### Fix

- Array file project

## v2.38.2 (2025-07-07)

### Fix

- Adds error message for `cp` `mv` and `rm` for forbidden operations on s3folders and files

## v2.38.1 (2025-07-04)

### Fix

- Set `--workflow-name` as required in `cloudos workflow import` to trigger the correct error message

## v2.38.0 (2025-07-03)

### Feat

- Links S3 folder to Interactive Analysis (`cloudos datasets link`)

## v2.37.1 (2025-07-01)

### Fix

- Change error messaging for missing parameters that could be configured in profiles

## v2.37.0 (2025-06-30)

### Feat

- Allows **specifying** different projects for parameter options i.e. `-p --file1=PROJECT1/Data/input.csv -p --file2=Project2/Data/input.csv`

## v2.36.0 (2025-06-27)

### Feat

- Adds command to remove files.
- Adds ci tests for cp and mkdir
- Patch s3 folders listing files

## v2.35.0 (2025-06-27)

### Feat

-  Adds command to create new folders

## v2.34.0 (2025-06-25)

### Feat

- Adds command to copy files and folders within and across projects within the same workspace.

## v2.33.0 (2025-06-25)

### Feat

- Send bash array-jobs to the platform
- Retrieve columns from bash array files using the API

## v2.32.1 (2025-06-25)

### Patch

- Fixes how data items and glob patterns are identified in job details.

## v2.32.0 (2025-06-17)

### Feat

- Adds command to rename files.

## v2.31.1 (2025-06-17)

### Patch

- Make repository platform consistent in configuration

## v2.31.0 (2025-06-17)

### Feat

- Adds command to show the path to logs and results of jobs

## v2.30.0 (2025-06-16)

### Feat

- Unify all workflow import platforms into a single child class

## v2.29.0 (2025-06-13)

### Feat

- Adds command to move files within and across project within the same workspace.

## v2.28.0 (2025-06-11)

### Feat

- Adds new subcommand `details` for `job`, to retrieve and view job details either in stdout or json

## v2.27.0 (2025-06-10)

### Feat

- Adds command to list details of files `cloudos datasets ls <path> --profile <profile> --details`

## v2.26.1 (2025-06-10)

### Patch

- Fix PyPi build

## v2.26.0 (2025-06-05)

- Adds datasets class
- Adds command to list files `cloudos datasets ls <path> --profile <profile>`

## v2.25.0 (2025-05-30)

### Feat

- Adds the ability to import workflows from Gitlab and Github

## v2.24.0 (2025-05-29)

### Feat

- Adds `--azure-worker-instance-type` to `cloudos job run` command, to be able to specify the worker node instance type to be used in azure
- Adds `--azure-worker-instance-disk` to `cloudos job run` command, to be able to specify the disk size in GB for the worker node to be used in azure
- Adds `--azure-worker-instance-spot` to `cloudos job run` command, to be able to specify whether the azure worker nodes have to be spot instances or not

## v2.23.0 (2025-05-26)

- Updates jobs POST endpoint from v1 to v2
- Removes `cloudos job run-curated-examples` functionality, as it was deprecated from the platform
- Removes the following deprecated `cloudos job run` flags: `spot`, `ignite`, `batch` 
- Adds `--git-branch` to `cloudos job run` command, to be able to specify the git branch to run

## v2.22.0 (2025-05-15)

### Feat

- Adds ability to send bash jobs in sequential sample processing (only strings)
- Updates requirements

## v2.21.0 (2025-05-13)

### Feat

- Adds ability to configure profiles for all commands

## v2.20.0 (2025-04-25)

### Feat

- Adds ability to abort jobs (single or multiple)

## v2.19.1 (2025-04-14)

### Fix

- Jobs URL fix for pointing to updated path

## v2.19.0 (2025-03-27)

### Feature

- Update Nextflow version dependencies for aws, azure and hpc environments
- Adds [rich_click](https://github.com/ewels/rich-click) to improve help output text

## v2.18.0 (2025-03-05)

### Feature

- Updates GET projects endpoint to v2.

## v2.17.0 (2025-02-20)

### Feature

- Adapts the repository to be uploaded to PyPI. The adaptation required the change of the module name, from `cloudos` to `clouods_cli`.

## v2.16.0 (2025-01-21)

### Feature

- Adds the new parameter `--use_private_docker_repository` to launch jobs using private docker images from a linked docker.io account.

## v2.15.0 (2025-01-16)

### Feature

- Updates GET workflows endpoint to v3.

## v2.14.0 (2024-12-18)

- Adds the new `--accelerate-file-staging` parameter to job submission to add support for AWS S3 mountpoint for quicker file staging.

## v2.13.0 (2024-12-03)

### Feature

- Adds new `--archived` flag to `cloudos job list` to allow getting archived jobs list.

### Patch

- Updates GET job list to use API v2 endpoint.

## v2.12.0 (2024-11-27)

### Feature

- Adds the new parameter `--nextflow-version` to select the Nextflow version for job submissions.
- Now `--cloudos-url` can also take URLs with a trailing `/`

## v2.11.2 (2024-11-6)

### Fix

- Updates API requests to only use API key via HTTP header. Done in preparation for the upcoming deprecation of API key via parameters in CloudOS API.

## v2.11.1 (2024-10-22)

### Fix

- Updates queue support to disallow queue selection on fixed-queue workflows.

## v2.11.0 (2024-04-16)

- Now, the default `cloudos job run` command will save job process logs. To prevent saving process logs, you can use the new flag `--do-not-save-logs`.
- Removes unsupported `--spot` option from `cloudos job run`.

## v2.10.0 (2024-04-11)

- Adds the new parameter `--workflow-docs-link` to add a documentation link to the imported workflow.

## v2.9.0 (2024-04-09)

- Adds `workflow import` command, allowing user to import Nextflow workflows to CloudOS.

## v2.8.0 (2024-04-05)

- Adds support for using CloudOS HPC executor.

## v2.7.0 (2024-03-21)

### Feature

- Changes the default Nextflow executor to be AWSbatch. Now, the `--batch` flag is no longer necessary (although it's maintained for backwards compatibility) and a new `--ignite` flag is created to support ignite if available.
- Selects the CloudOS workspace default queue, when no valid `--job-queue` is provided.

## v2.6.3 (2024-03-19)

### Fix

- Discards archived worflows from the executable ones, as they will always produce an error.

## v2.6.2 (2024-01-12)

### Fix

- Adds an error strategy to retry GET/POST requests on time-out errors.

## v2.6.1 (2023-10-11)

### Fix

- Improve parsing of parameters added with `-p`. Now they can include internal `=` symbols.

## v2.6.0 (2023-06-22)

### Feature

- adds Azure support

## v2.5.0 (2023-05-02)

### Feature

- adds job queue support to batch runs

## v2.4.0 (2023-04-28)

### Feature

- add queue list command

## v2.3.0 (2023-04-26)

### Feature

- add run-curated-examples command

## v2.2.0 (2023-04-19)

### Documentation

- add commitizen support

### Feature

- add project list
- add workflows list --curated option

### 2.1.0 - 2023-03-30
- Feature: `cloudos job list` has the new parameter `--last-n-jobs n`, if used, the last
`n` jobs from the user will be collected. Default is last 30, which was the previous behaviour.

### 2.0.1 - 2023-03-07
- Removes some default fields returned from `cloudos job list` command in preparation for
its deprecation from the CloudOS API. In particular, the following fields were removed:
    * `resumeWorkDir`
    * `project.user`
    * `project.team`

### 2.0.0 - 2023-02-20
- Remove all cohort browser functionality that will be maintained in a separated
repository.

### 1.3.2 - 2023-02-08
- Patch: fixes problems with CloudOS environments using the new API specification for
`projects` endpoint while maintaining backwards compatibility.

### 1.3.1 - 2022-12-01
- Patch: fixes `BarRequestException` and `TimeOutException` messages when the response from
the API server is empty.

### 1.3.0 - 2022-11-07
- All Cromwell functionality works now with personal API key. The
`--cromwell-token` argument is maintained for backwards compatibility, but can
be completely substituted by `--apikey`.
- Changes `--wdl-importsfile` parameter to be optional even when running a
WDL pipeline as `importsFiles` are not always present in WDL pipelines.
- Fixes some incomplete error messages.

### 1.2.1 - 2022-11-03
- Modifies default `--cost-limit` from infinite (`-1`) to `30.0`. This will prevent
wasting resources without a purpose of running a pipeline.

### 1.2.0 - 2022-10-28
- Adds `--disable-ssl-verification` new flag to be able to disable SSL certificate
verification when required. It also disables `urllib3` associated warning messages.
- Adds `--ssl-cert` new option to specify the path to the corresponding SSL certificate
file.

### 1.1.0 - 2022-09-29
- Adds `--request-interval` new parameter to allow the custom time specification
for job status request. This will be useful for big jobs, to specify a bigger
interval since a smaller one is causing the API to consider it as spam or simply
to crash.
- Changes `REQUEST_INTERVAL` for `REQUEST_INTERVAL_CROMWELL`. This is only used in the
`cromwell` workflows.

### 1.0.0 - 2022-07-28
- Adds `--parameter / -p` new argument to allow to specify the job
parameters using the command-line.
This version introduces a backwards incompatible change
The -p flag is now used for parameters and not for the nextflow profile.
Commands that utilised -p for denoting a profile will break with this release.

### 0.1.4 - 2022-07-27
- Unittests added for method `load` and `create` from class `Cloudos`

### 0.1.3 - 2022-07-26
- Adds `--cost-limit <float>` to `cloudos job run` command. It is
used to indicate the job cost limit, in $.

### 0.1.2b - 2022-07-26
- Adds worked example of CohortBrowser to README

### 0.1.2 - 2022-07-14
- Adds WDL pipeline support, iteration 2: WDL workflows can be run
using the regular `cloudos job run` using the new arguments:
    * `--wdl-mainfile`
    * `--wdl-importsfile`
    * `--cromwell-token`
- Adds the new argument `--repository-platform` to specify the
repository platform (Default: 'github').

### 0.1.1 - 2022-07-12
- Adds WDL pipeline support, iteration 1: cromwell server managing.
Now, a new command `cloudos cromwell` is available, with the following
subcommands:
    * status
    * start
    * stop

### 0.1.0 - 2022-07-07
- Adds `cloudos workflow list` command. This command allows to
collect all the workflows data from a given workspace.
- Adds JSON output for `cloudos job list` and `cloudos workflow list`
commands.

### 0.0.9 - 2022-06-28
- Adds support for lustre storage with the new `--storage-mode` and
`--lustre-size` parameters.

### 0.0.8 - 2022-06-16
- Adds `--nextflow-profile` parameter to accept nextflow profiles. It
also makes `--job-config` parameter optional, as a run with only
profiles is possible.

### 0.0.7a - 2022-04-07
- Hotfix: extends the wait time from 1s to 60s when checking for job
status (`--wait-completion true`). This helps preventing API call
errors from CloudOS API server.

### 0.0.7 - 2021-03-10
- Adds support for aborted jobs
- Adds `--batch` option to `job` subtool to be able to use `batch`
executor instead of the default `ignite` in CloudOS.

### 0.0.6 - 2021-12-09
- Unittests added for method `process_job_list` from class `Cloudos`
- Unittests added for method `convert_nextflow_to_json` from class `Jobs`

### 0.0.5b - 2021-11-24
- Adds Cohort class

### 0.0.5 - 2021-11-16
- Adds `git-commit` and `--git-tag` optional arguments to 
`cloudos job run` to be able to set the github commit or tag
to run.

### 0.0.4 - 2021-10-15
- Changes `--job-params` to `--job-config`
- Removes the collection of the `project.description` column from the 
returned json when listing all jobs, as this column is not available
in all the CloudOS workspaces.

### 0.0.3 - 2021-09-08
- Adds `cloudos job list` command.
- Minor changes in `stdout` of the other commands to improve
readability.
- Adds a small docstring to each command.

### 0.0.2 - 2021-09-07
- Refactors `runjob` and `jobstatus` commands. Now, the main
`cloudos` tool have the `job` subtool which in turn has its
`run` and `status` commands performing the previous
functionality. This way, now the tool can be used with:
`cloudos job run [OPTIONS]` and `cloudos job status [OPTIONS]`.
- Adding `--wait-completion` option to `cloudos job run` command,
to be able to wait until job completion or failure.

### 0.0.1 - 2021-08-18
Initial implementation of the `cloudos` python package:
- Implements `runjob` and `jobstatus` commands to send jobs and get
their status, respectively.

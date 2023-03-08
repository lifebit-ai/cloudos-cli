## lifebit-ai/cloudos-cli: changelog

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

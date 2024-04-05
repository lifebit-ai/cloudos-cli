#!/usr/bin/env python3

import click
import cloudos.jobs.job as jb
from cloudos.clos import Cloudos
from cloudos.queue.queue import Queue
import json
import time
import sys
import os
import urllib3
from ._version import __version__
from concurrent.futures import ThreadPoolExecutor, as_completed

# GLOBAL VARS
JOB_COMPLETED = 'completed'
JOB_FAILED = 'failed'
JOB_ABORTED = 'aborted'
JOB_RUNNING = 'running'
REQUEST_INTERVAL_CROMWELL = 30


def ssl_selector(disable_ssl_verification, ssl_cert):
    """Verify value selector.

    This function stablish the value that will be passed to requests.verify
    variable.

    Parameters
    ----------
    disable_ssl_verification : bool
        Whether to disable SSL verification.
    ssl_cert : string
        String indicating the path to the SSL certificate file to use.

    Returns
    -------
    verify_ssl : [bool | string]
        Either a bool or a path string to be passed to requests.verify to control
        SSL verification.
    """
    if disable_ssl_verification:
        verify_ssl = False
        print('[WARNING] Disabling SSL verification')
        urllib3.disable_warnings()
    elif ssl_cert is None:
        verify_ssl = True
    elif os.path.isfile(ssl_cert):
        verify_ssl = ssl_cert
    else:
        raise FileNotFoundError(f"The specified file '{ssl_cert}' was not found")
    return verify_ssl


@click.group()
@click.version_option(__version__)
def run_cloudos_cli():
    """CloudOS python package: a package for interacting with CloudOS."""
    print(run_cloudos_cli.__doc__ + '\n')
    print('Version: ' + __version__ + '\n')


@run_cloudos_cli.group()
def job():
    """CloudOS job functionality: run and check jobs in CloudOS."""
    print(job.__doc__ + '\n')


@run_cloudos_cli.group()
def workflow():
    """CloudOS workflow functionality: list workflows in CloudOS."""
    print(workflow.__doc__ + '\n')


@run_cloudos_cli.group()
def project():
    """CloudOS project functionality: list projects in CloudOS."""
    print(project.__doc__ + '\n')


@run_cloudos_cli.group()
def cromwell():
    """Cromwell server functionality: check status, start and stop."""
    print(cromwell.__doc__ + '\n')


@run_cloudos_cli.group()
def queue():
    """CloudOS job queue functionality."""
    print(queue.__doc__ + '\n')


@job.command('run')
@click.option('-k',
              '--apikey',
              help='Your CloudOS API key',
              required=True)
@click.option('-c',
              '--cloudos-url',
              help=('The CloudOS url you are trying to access to. ' +
                    'Default=https://cloudos.lifebit.ai.'),
              default='https://cloudos.lifebit.ai')
@click.option('--workspace-id',
              help='The specific CloudOS workspace id.',
              required=True)
@click.option('--project-name',
              help='The name of a CloudOS project.',
              required=True)
@click.option('--workflow-name',
              help='The name of a CloudOS workflow or pipeline.',
              required=True)
@click.option('--job-config',
              help=('A config file similar to a nextflow.config file, ' +
                    'but only with the parameters to use with your job.'))
@click.option('-p',
              '--parameter',
              multiple=True,
              help=('A single parameter to pass to the job call. It should be in the ' +
                    'following form: parameter_name=parameter_value. E.g.: ' +
                    '-p input=s3://path_to_my_file. You can use this option as many ' +
                    'times as parameters you want to include.'))
@click.option('--nextflow-profile',
              help=('A comma separated string indicating the nextflow profile/s ' +
                    'to use with your job.'))
@click.option('--git-commit',
              help=('The exact whole 40 character commit hash to run for ' +
                    'the selected pipeline. ' +
                    'If not specified it defaults to the last commit ' +
                    'of the default branch.'))
@click.option('--git-tag',
              help=('The tag to run for the selected pipeline. ' +
                    'If not specified it defaults to the last commit ' +
                    'of the default branch.'))
@click.option('--job-name',
              help='The name of the job. Default=new_job.',
              default='new_job')
@click.option('--resumable',
              help='Whether to make the job able to be resumed or not.',
              is_flag=True)
@click.option('--batch',
              help=('[Deprecated in 2.7.0] Since v2.7.0, the default executor is AWSbatch ' +
                    'so there is no need to use this flag. It is maintained for ' +
                    'backwards compatibility.'),
              is_flag=True)
@click.option('--ignite',
              help=('This flag allows running ignite executor if available. Please, note ' +
                    'that ignite executor is being deprecated and may not be available in your ' +
                    'CloudOS.'),
              is_flag=True)
@click.option('--job-queue',
              help='Name of the job queue to use with a batch job.')
@click.option('--instance-type',
              help=('The type of execution platform compute instance to use. ' +
                    'Default=c5.xlarge(aws)|Standard_D4as_v4(azure).'),
              default='NONE_SELECTED')
@click.option('--instance-disk',
              help='The amount of disk storage to configure. Default=500.',
              type=int,
              default=500)
@click.option('--spot',
              help='Whether to make a spot instance.',
              is_flag=True)
@click.option('--storage-mode',
              help=('Either \'lustre\' or \'regular\'. Indicates if the user wants to select ' +
                    'regular or lustre storage. Default=regular.'),
              default='regular')
@click.option('--lustre-size',
              help=('The lustre storage to be used when --storage-mode=lustre, in GB. It should ' +
                    'be 1200 or a multiple of it. Default=1200.'),
              type=int,
              default=1200)
@click.option('--wait-completion',
              help=('Whether to wait to job completion and report final ' +
                    'job status.'),
              is_flag=True)
@click.option('--wait-time',
              help=('Max time to wait (in seconds) to job completion. ' +
                    'Default=3600.'),
              default=3600)
@click.option('--wdl-mainfile',
              help='For WDL workflows, which mainFile (.wdl) is configured to use.',)
@click.option('--wdl-importsfile',
              help='For WDL workflows, which importsFile (.zip) is configured to use.',)
@click.option('-t',
              '--cromwell-token',
              help=('Specific Cromwell server authentication token. Currently, not necessary ' +
                    'as apikey can be used instead, but maintained for backwards compatibility.'))
@click.option('--repository-platform',
              help='Name of the repository platform of the workflow. Default=github.',
              default='github')
@click.option('--execution-platform',
              help='Name of the execution platform implemented in your CloudOS. Default=aws.',
              type=click.Choice(['aws', 'azure', 'hpc']),
              default='aws')
@click.option('--hpc-id',
              help=('ID of your HPC, only applicable when execution-platform=hpc. ' +
                    'Default=660fae20f93358ad61e0104b'),
              default='660fae20f93358ad61e0104b')
@click.option('--cost-limit',
              help='Add a cost limit to your job. Default=30.0 (For no cost limit please use -1).',
              type=float,
              default=30.0)
@click.option('--verbose',
              help='Whether to print information messages or not.',
              is_flag=True)
@click.option('--request-interval',
              help=('Time interval to request (in seconds) the job status. ' +
                    'For large jobs is important to use a high number to ' +
                    'make fewer requests so that is not considered spamming by the API. ' +
                    'Default=30.'),
              default=30)
@click.option('--disable-ssl-verification',
              help=('Disable SSL certificate verification. Please, remember that this option is ' +
                    'not generally recommended for security reasons.'),
              is_flag=True)
@click.option('--ssl-cert',
              help='Path to your SSL certificate file.')
def run(apikey,
        cloudos_url,
        workspace_id,
        project_name,
        workflow_name,
        job_config,
        parameter,
        git_commit,
        git_tag,
        job_name,
        resumable,
        batch,
        ignite,
        job_queue,
        nextflow_profile,
        instance_type,
        instance_disk,
        spot,
        storage_mode,
        lustre_size,
        wait_completion,
        wait_time,
        wdl_mainfile,
        wdl_importsfile,
        cromwell_token,
        repository_platform,
        execution_platform,
        hpc_id,
        cost_limit,
        verbose,
        request_interval,
        disable_ssl_verification,
        ssl_cert):
    """Submit a job to CloudOS."""
    print('Executing run...')
    verify_ssl = ssl_selector(disable_ssl_verification, ssl_cert)
    if instance_type == 'NONE_SELECTED':
        if execution_platform == 'aws':
            instance_type = 'c5.xlarge'
        elif execution_platform == 'azure':
            instance_type = 'Standard_D4as_v4'
        else:
            instance_type = None
    if execution_platform == 'azure' or execution_platform == 'hpc':
        batch = None
        spot = None
    elif ignite:
        batch = None
        print('\n[Warning] You have specified ignite executor. Please, note that ignite is being ' +
              'removed from CloudOS, so the command may fail. Check ignite availability in your ' +
              'CloudOS\n')
    else:
        batch = True
    if execution_platform == 'hpc':
        print('\nHPC execution platform selected')
        if hpc_id is None:
            raise ValueError('Please, specify your HPC ID using --hpc parameter')
        print('[Message] Please, take into account that HPC execution do not support ' +
              'the following parameters and all of them will be ignored:\n' +
              '\t--resumable\n' +
              '\t--job-queue\n' +
              '\t--instance-type | --instance-disk | --spot | --cost-limit\n' +
              '\t--storage-mode | --lustre-size\n' +
              '\t--wdl-mainfile | --wdl-importsfile | --cromwell-token\n')
    if verbose:
        print('\t...Detecting workflow type')
    cl = Cloudos(cloudos_url, apikey, cromwell_token)
    workflow_type = cl.detect_workflow(workflow_name, workspace_id, verify_ssl)
    if execution_platform == 'hpc' and workflow_type == 'wdl':
        raise ValueError(f'The workflow {workflow_name} is a WDL workflow. ' +
                         'WDL is not supported on HPC execution platform.')
    if workflow_type == 'wdl':
        print('\tWDL workflow detected\n')
        if wdl_mainfile is None:
            raise ValueError('Please, specify WDL mainFile using --wdl-mainfile <mainFile>.')
        c_status = cl.get_cromwell_status(workspace_id, verify_ssl)
        c_status_h = json.loads(c_status.content)["status"]
        print(f'\tCurrent Cromwell server status is: {c_status_h}\n')
        if c_status_h == 'Stopped':
            print('\tStarting Cromwell server...\n')
            cl.cromwell_switch(workspace_id, 'restart', verify_ssl)
            elapsed = 0
            while elapsed < 300 and c_status_h != 'Running':
                c_status_old = c_status_h
                time.sleep(REQUEST_INTERVAL_CROMWELL)
                elapsed += REQUEST_INTERVAL_CROMWELL
                c_status = cl.get_cromwell_status(workspace_id, verify_ssl)
                c_status_h = json.loads(c_status.content)["status"]
                if c_status_h != c_status_old:
                    print(f'\tCurrent Cromwell server status is: {c_status_h}\n')
        if c_status_h != 'Running':
            raise Exception('Cromwell server did not restarted properly.')
        cromwell_id = json.loads(c_status.content)["_id"]
        print('\t' + ('*' * 80) + '\n' +
              '\t[WARNING] Cromwell server is now running. Please, remember to stop it when ' +
              'your\n' + '\tjob finishes. You can use the following command:\n' +
              '\tcloudos cromwell stop \\\n' +
              '\t\t--cromwell-token $CROMWELL_TOKEN \\\n' +
              f'\t\t--cloudos-url {cloudos_url} \\\n' +
              f'\t\t--workspace-id {workspace_id}\n' +
              '\t' + ('*' * 80) + '\n')
    else:
        cromwell_id = None
    if verbose:
        print('\t...Preparing objects')
    j = jb.Job(cloudos_url, apikey, None, workspace_id, project_name, workflow_name,
               mainfile=wdl_mainfile, importsfile=wdl_importsfile,
               repository_platform=repository_platform, verify=verify_ssl)
    if verbose:
        print('\tThe following Job object was created:')
        print('\t' + str(j))
        print('\t...Sending job to CloudOS\n')
    queue = Queue(cloudos_url=cloudos_url, apikey=apikey, cromwell_token=cromwell_token,
                  workspace_id=workspace_id, verify=verify_ssl)
    job_queue_id = queue.fetch_job_queue_id(workflow_type=workflow_type, batch=batch,
                                            job_queue=job_queue)
    j_id = j.send_job(job_config=job_config,
                      parameter=parameter,
                      git_commit=git_commit,
                      git_tag=git_tag,
                      job_name=job_name,
                      resumable=resumable,
                      batch=batch,
                      job_queue_id=job_queue_id,
                      nextflow_profile=nextflow_profile,
                      instance_type=instance_type,
                      instance_disk=instance_disk,
                      spot=spot,
                      storage_mode=storage_mode,
                      lustre_size=lustre_size,
                      execution_platform=execution_platform,
                      hpc_id=hpc_id,
                      workflow_type=workflow_type,
                      cromwell_id=cromwell_id,
                      cost_limit=cost_limit,
                      verify=verify_ssl)
    print(f'\tYour assigned job id is: {j_id}\n')
    j_url = f'{cloudos_url}/app/jobs/{j_id}'
    if wait_completion:
        print('\tPlease, wait until job completion (max wait time of ' +
              f'{wait_time} seconds).\n')
        j_status = j.wait_job_completion(job_id=j_id,
                                         wait_time=wait_time,
                                         request_interval=request_interval,
                                         verbose=verbose,
                                         verify=verify_ssl)
        j_name = j_status['name']
        j_final_s = j_status['status']
        if j_final_s == JOB_COMPLETED:
            print(f'\nJob status for job "{j_name}" (ID: {j_id}): {j_final_s}')
            sys.exit(0)
        else:
            print(f'\nJob status for job "{j_name}" (ID: {j_id}): {j_final_s}')
            sys.exit(1)
    else:
        j_status = j.get_job_status(j_id, verify_ssl)
        j_status_h = json.loads(j_status.content)["status"]
        print(f'\tYour current job status is: {j_status_h}')
        print('\tTo further check your job status you can either go to ' +
              f'{j_url} or use the following command:\n' +
              '\tcloudos job status \\\n' +
              '\t\t--apikey $MY_API_KEY \\\n' +
              f'\t\t--cloudos-url {cloudos_url} \\\n' +
              f'\t\t--job-id {j_id}\n')


@job.command('run-curated-examples')
@click.option('-k',
              '--apikey',
              help='Your CloudOS API key',
              required=True)
@click.option('-c',
              '--cloudos-url',
              help=('The CloudOS url you are trying to access to. ' +
                    'Default=https://cloudos.lifebit.ai.'),
              default='https://cloudos.lifebit.ai')
@click.option('--workspace-id',
              help='The specific CloudOS workspace id.',
              required=True)
@click.option('--project-name',
              help='The name of a CloudOS project.',
              required=True)
@click.option('--resumable',
              help='Whether to make the job able to be resumed or not.',
              is_flag=True)
@click.option('--batch',
              help=('[Deprecated in 2.7.0] Since v2.7.0, the default executor is AWSbatch ' +
                    'so there is no need to use this flag. It is maintained for ' +
                    'backwards compatibility.'),
              is_flag=True)
@click.option('--ignite',
              help=('This flag allows running ignite executor if available. Please, note ' +
                    'that ignite executor is being deprecated and may not be available in your ' +
                    'CloudOS.'),
              is_flag=True)
@click.option('--instance-type',
              help=('The type of execution platform compute instance to use. ' +
                    'Default=c5.xlarge(aws)|Standard_D4as_v4(azure).'),
              default='NONE_SELECTED')
@click.option('--instance-disk',
              help='The amount of disk storage to configure. Default=500.',
              type=int,
              default=500)
@click.option('--spot',
              help='Whether to make a spot instance.',
              is_flag=True)
@click.option('--storage-mode',
              help=('Either \'lustre\' or \'regular\'. Indicates if the user wants to select ' +
                    'regular or lustre storage. Default=regular.'),
              default='regular')
@click.option('--lustre-size',
              help=('The lustre storage to be used when --storage-mode=lustre, in GB. It should ' +
                    'be 1200 or a multiple of it. Default=1200.'),
              type=int,
              default=1200)
@click.option('--execution-platform',
              help='Name of the execution platform implemented in your CloudOS. Default=aws.',
              type=click.Choice(['aws', 'azure']),
              default='aws')
@click.option('--cost-limit',
              help='Add a cost limit to your job. Default=30.0 (For no cost limit please use -1).',
              type=float,
              default=30.0)
@click.option('--wait-completion',
              help=('Whether to wait to job completion and report final ' +
                    'job status.'),
              is_flag=True)
@click.option('--wait-time',
              help=('Max time to wait (in seconds) to job completion. ' +
                    'Default=3600.'),
              default=3600)
@click.option('--request-interval',
              help=('Time interval to request (in seconds) the job status. ' +
                    'For large jobs is important to use a high number to ' +
                    'make fewer requests so that is not considered spamming by the API. ' +
                    'Default=30.'),
              default=30)
@click.option('--verbose',
              help='Whether to print information messages or not.',
              is_flag=True)
@click.option('--disable-ssl-verification',
              help=('Disable SSL certificate verification. Please, remember that this option is ' +
                    'not generally recommended for security reasons.'),
              is_flag=True)
@click.option('--ssl-cert',
              help='Path to your SSL certificate file.')
def run_curated_examples(apikey,
                         cloudos_url,
                         workspace_id,
                         project_name,
                         resumable,
                         batch,
                         ignite,
                         instance_type,
                         instance_disk,
                         spot,
                         storage_mode,
                         lustre_size,
                         execution_platform,
                         cost_limit,
                         wait_completion,
                         wait_time,
                         request_interval,
                         verbose,
                         disable_ssl_verification,
                         ssl_cert):
    """Run all the curated workflows with example parameters.

    NOTE that currently, only Nextflow workflows are supported.
    """
    verify_ssl = ssl_selector(disable_ssl_verification, ssl_cert)
    cl = Cloudos(cloudos_url, apikey, None)
    curated_workflows = cl.get_curated_workflow_list(workspace_id, verify=verify_ssl)
    job_id_list = []
    runnable_curated_workflows = [
        w for w in curated_workflows if w['workflowType'] == 'nextflow' and len(w['parameters']) > 0
    ]
    if instance_type == 'NONE_SELECTED':
        if execution_platform == 'aws':
            instance_type = 'c5.xlarge'
        if execution_platform == 'azure':
            instance_type = 'Standard_D4as_v4'
    if execution_platform == 'azure':
        batch = None
        spot = None
    elif ignite:
        batch = None
        print('\n[Warning] You have specified ignite executor. Please, note that ignite is being ' +
              'removed from CloudOS, so the command may fail. Check ignite availability in your ' +
              'CloudOS\n')
    else:
        batch = True
    for workflow in runnable_curated_workflows:
        workflow_name = workflow['name']
        j = jb.Job(cloudos_url, apikey, None, workspace_id, project_name, workflow_name,
                   repository_platform=workflow['repository']['platform'], verify=verify_ssl)
        j_id = j.send_job(example_parameters=workflow['parameters'],
                          job_name=f"{workflow['name']}|Example_Run",
                          resumable=resumable,
                          batch=batch,
                          instance_type=instance_type,
                          instance_disk=instance_disk,
                          spot=spot,
                          storage_mode=storage_mode,
                          lustre_size=lustre_size,
                          execution_platform=execution_platform,
                          workflow_type='nextflow',
                          cost_limit=cost_limit,
                          verify=verify_ssl)
        print(f'\tYour assigned job id is: {j_id}\n')
        job_id_list.append(j_id)
    print(f'\n\tAll {len(runnable_curated_workflows)} curated job launched successfully!\n')
    if wait_completion:
        print('\tPlease, wait until jobs completion (max wait time of ' +
              f'{wait_time} seconds).\n')
        # Multi-threaded api requests, max_workers is hard-coded to not allow for
        # big numbers that can collapse API server.
        threads = []
        with ThreadPoolExecutor(max_workers=20) as executor:
            for j in job_id_list:
                threads.append(executor.submit(cl.wait_job_completion,
                                               job_id=j,
                                               wait_time=wait_time,
                                               request_interval=request_interval,
                                               verbose=verbose,
                                               verify=verify_ssl)
                               )
        j_status_all = [task.result() for task in as_completed(threads)]
        # Summary of job status
        print("\n\tCurated example runs final status:\n")
        for j_s in j_status_all:
            j_name = j_s['name']
            j_id = j_s['id']
            j_status = j_s['status']
            print(f'\t\tJob status for job "{j_name}" (ID: {j_id}): {j_status}')
        successful_jobs = [j_s for j_s in j_status_all if j_s['status'] == JOB_COMPLETED]
        failed_jobs = [j_s for j_s in j_status_all if j_s['status'] == JOB_FAILED]
        aborted_jobs = [j_s for j_s in j_status_all if j_s['status'] == JOB_ABORTED]
        running_jobs = [j_s for j_s in j_status_all if j_s['status'] == JOB_RUNNING]
        print(f"""\n\tJob summary:
              Successful jobs.....:  {len(successful_jobs)}
              Failed jobs.........:  {len(failed_jobs)}
              Jobs still running..:  {len(running_jobs)}
              Aborted jobs........:  {len(aborted_jobs)}
            -------------------------------
              Total jobs..........:  {len(j_status_all)}""")


@job.command('status')
@click.option('-k',
              '--apikey',
              help='Your CloudOS API key',
              required=True)
@click.option('-c',
              '--cloudos-url',
              help=('The CloudOS url you are trying to access to. ' +
                    'Default=https://cloudos.lifebit.ai.'),
              default='https://cloudos.lifebit.ai')
@click.option('--job-id',
              help='The job id in CloudOS to search for.',
              required=True)
@click.option('--verbose',
              help='Whether to print information messages or not.',
              is_flag=True)
@click.option('--disable-ssl-verification',
              help=('Disable SSL certificate verification. Please, remember that this option is ' +
                    'not generally recommended for security reasons.'),
              is_flag=True)
@click.option('--ssl-cert',
              help='Path to your SSL certificate file.')
def job_status(apikey,
               cloudos_url,
               job_id,
               verbose,
               disable_ssl_verification,
               ssl_cert):
    """Check job status in CloudOS."""
    print('Executing status...')
    verify_ssl = ssl_selector(disable_ssl_verification, ssl_cert)
    if verbose:
        print('\t...Preparing objects')
    cl = Cloudos(cloudos_url, apikey, None)
    if verbose:
        print('\tThe following Cloudos object was created:')
        print('\t' + str(cl) + '\n')
        print(f'\tSearching for job id: {job_id}')
    j_status = cl.get_job_status(job_id, verify_ssl)
    j_status_h = json.loads(j_status.content)["status"]
    print(f'\tYour current job status is: {j_status_h}\n')
    j_url = f'{cloudos_url}/app/jobs/{job_id}'
    print(f'\tTo further check your job status you can either go to {j_url} ' +
          'or repeat the command you just used.')


@job.command('list')
@click.option('-k',
              '--apikey',
              help='Your CloudOS API key',
              required=True)
@click.option('-c',
              '--cloudos-url',
              help=('The CloudOS url you are trying to access to. ' +
                    'Default=https://cloudos.lifebit.ai.'),
              default='https://cloudos.lifebit.ai')
@click.option('--workspace-id',
              help='The specific CloudOS workspace id.',
              required=True)
@click.option('--output-basename',
              help=('Output file base name to save jobs list. ' +
                    'Default=joblist'),
              default='joblist',
              required=False)
@click.option('--output-format',
              help='The desired file format (file extension) for the output. Default=csv.',
              type=click.Choice(['csv', 'json'], case_sensitive=False),
              default='csv')
@click.option('--all-fields',
              help=('Whether to collect all available fields from jobs or ' +
                    'just the preconfigured selected fields. Only applicable ' +
                    'when --output-format=csv'),
              is_flag=True)
@click.option('--last-n-jobs',
              help=("The number of last user's jobs to retrieve. You can use 'all' to " +
                    "retrieve all user's jobs. Default=30."),
              default='30')
@click.option('--page',
              help=('Response page to retrieve. If --last-n-jobs is set, then --page ' +
                    'value corresponds to the first page to retrieve. Default=1.'),
              type=int,
              default=1)
@click.option('--verbose',
              help='Whether to print information messages or not.',
              is_flag=True)
@click.option('--disable-ssl-verification',
              help=('Disable SSL certificate verification. Please, remember that this option is ' +
                    'not generally recommended for security reasons.'),
              is_flag=True)
@click.option('--ssl-cert',
              help='Path to your SSL certificate file.')
def list_jobs(apikey,
              cloudos_url,
              workspace_id,
              output_basename,
              output_format,
              all_fields,
              last_n_jobs,
              page,
              verbose,
              disable_ssl_verification,
              ssl_cert):
    """Collect all your jobs from a CloudOS workspace in CSV format."""
    verify_ssl = ssl_selector(disable_ssl_verification, ssl_cert)
    outfile = output_basename + '.' + output_format
    print('Executing list...')
    if verbose:
        print('\t...Preparing objects')
    cl = Cloudos(cloudos_url, apikey, None)
    if verbose:
        print('\tThe following Cloudos object was created:')
        print('\t' + str(cl) + '\n')
        print('\tSearching for jobs in the following workspace: ' +
              f'{workspace_id}')
    if last_n_jobs != 'all':
        try:
            last_n_jobs = int(last_n_jobs)
        except ValueError:
            print("[ERROR] last-n-jobs value was not valid. Please use a positive int or 'all'")
            raise
    my_jobs_r = cl.get_job_list(workspace_id, last_n_jobs, page, verify_ssl)
    if output_format == 'csv':
        my_jobs = cl.process_job_list(my_jobs_r, all_fields)
        my_jobs.to_csv(outfile, index=False)
        print(f'\tJob list collected with a total of {my_jobs.shape[0]} jobs.')
    elif output_format == 'json':
        with open(outfile, 'w') as o:
            o.write(json.dumps(my_jobs_r))
        print(f'\tJob list collected with a total of {len(my_jobs_r)} jobs.')
    else:
        raise ValueError('Unrecognised output format. Please use one of [csv|json]')
    print(f'\tJob list saved to {outfile}')


@workflow.command('list')
@click.option('-k',
              '--apikey',
              help='Your CloudOS API key',
              required=True)
@click.option('-c',
              '--cloudos-url',
              help=('The CloudOS url you are trying to access to. ' +
                    'Default=https://cloudos.lifebit.ai.'),
              default='https://cloudos.lifebit.ai')
@click.option('--workspace-id',
              help='The specific CloudOS workspace id.',
              required=True)
@click.option('--output-basename',
              help=('Output file base name to save workflow list. ' +
                    'Default=workflow_list'),
              default='workflow_list',
              required=False)
@click.option('--output-format',
              help='The desired file format (file extension) for the output. Default=csv.',
              type=click.Choice(['csv', 'json'], case_sensitive=False),
              default='csv')
@click.option('--all-fields',
              help=('Whether to collect all available fields from workflows or ' +
                    'just the preconfigured selected fields. Only applicable ' +
                    'when --output-format=csv'),
              is_flag=True)
@click.option('--curated',
              help='Whether to collect curated workflows only.',
              is_flag=True)
@click.option('--verbose',
              help='Whether to print information messages or not.',
              is_flag=True)
@click.option('--disable-ssl-verification',
              help=('Disable SSL certificate verification. Please, remember that this option is ' +
                    'not generally recommended for security reasons.'),
              is_flag=True)
@click.option('--ssl-cert',
              help='Path to your SSL certificate file.')
def list_workflows(apikey,
                   cloudos_url,
                   workspace_id,
                   output_basename,
                   output_format,
                   all_fields,
                   curated,
                   verbose,
                   disable_ssl_verification,
                   ssl_cert):
    """Collect all workflows from a CloudOS workspace in CSV format."""
    verify_ssl = ssl_selector(disable_ssl_verification, ssl_cert)
    outfile = output_basename + '.' + output_format
    print('Executing list...')
    if verbose:
        print('\t...Preparing objects')
    cl = Cloudos(cloudos_url, apikey, None)
    if verbose:
        print('\tThe following Cloudos object was created:')
        print('\t' + str(cl) + '\n')
        print('\tSearching for workflows in the following workspace: ' +
              f'{workspace_id}')
    if curated:
        my_workflows_r = cl.get_curated_workflow_list(workspace_id, verify=verify_ssl)
    else:
        my_workflows_r = cl.get_workflow_list(workspace_id, verify=verify_ssl)
    if output_format == 'csv':
        my_workflows = cl.process_workflow_list(my_workflows_r, all_fields)
        my_workflows.to_csv(outfile, index=False)
        print(f'\tWorkflow list collected with a total of {my_workflows.shape[0]} workflows.')
    elif output_format == 'json':
        with open(outfile, 'w') as o:
            o.write(json.dumps(my_workflows_r))
        print(f'\tWorkflow list collected with a total of {len(my_workflows_r)} workflows.')
    else:
        raise ValueError('Unrecognised output format. Please use one of [csv|json]')
    print(f'\tWorkflow list saved to {outfile}')


@project.command('list')
@click.option('-k',
              '--apikey',
              help='Your CloudOS API key',
              required=True)
@click.option('-c',
              '--cloudos-url',
              help=('The CloudOS url you are trying to access to. ' +
                    'Default=https://cloudos.lifebit.ai.'),
              default='https://cloudos.lifebit.ai')
@click.option('--workspace-id',
              help='The specific CloudOS workspace id.',
              required=True)
@click.option('--output-basename',
              help=('Output file base name to save project list. ' +
                    'Default=project_list'),
              default='project_list',
              required=False)
@click.option('--output-format',
              help='The desired file format (file extension) for the output. Default=csv.',
              type=click.Choice(['csv', 'json'], case_sensitive=False),
              default='csv')
@click.option('--all-fields',
              help=('Whether to collect all available fields from projects or ' +
                    'just the preconfigured selected fields. Only applicable ' +
                    'when --output-format=csv'),
              is_flag=True)
@click.option('--verbose',
              help='Whether to print information messages or not.',
              is_flag=True)
@click.option('--disable-ssl-verification',
              help=('Disable SSL certificate verification. Please, remember that this option is ' +
                    'not generally recommended for security reasons.'),
              is_flag=True)
@click.option('--ssl-cert',
              help='Path to your SSL certificate file.')
def list_projects(apikey,
                  cloudos_url,
                  workspace_id,
                  output_basename,
                  output_format,
                  all_fields,
                  verbose,
                  disable_ssl_verification,
                  ssl_cert):
    """Collect all projects from a CloudOS workspace in CSV format."""
    verify_ssl = ssl_selector(disable_ssl_verification, ssl_cert)
    outfile = output_basename + '.' + output_format
    print('Executing list...')
    if verbose:
        print('\t...Preparing objects')
    cl = Cloudos(cloudos_url, apikey, None)
    if verbose:
        print('\tThe following Cloudos object was created:')
        print('\t' + str(cl) + '\n')
        print('\tSearching for projects in the following workspace: ' +
              f'{workspace_id}')
    my_projects_r = cl.get_project_list(workspace_id, verify_ssl)
    if output_format == 'csv':
        my_projects = cl.process_project_list(my_projects_r, all_fields)
        my_projects.to_csv(outfile, index=False)
        print(f'\tProject list collected with a total of {my_projects.shape[0]} projects.')
    elif output_format == 'json':
        with open(outfile, 'w') as o:
            o.write(my_projects_r.text)
        content = json.loads(my_projects_r.content)
        if 'projects' in content:
            content_l = len(content['projects'])
        else:
            content_l = len(content)
        print('\tProject list collected with a total of ' +
              f'{content_l} projects.')
    else:
        raise ValueError('Unrecognised output format. Please use one of [csv|json]')
    print(f'\tProject list saved to {outfile}')


@cromwell.command('status')
@click.version_option()
@click.option('-k',
              '--apikey',
              help='Your CloudOS API key.')
@click.option('-t',
              '--cromwell-token',
              help=('Specific Cromwell server authentication token. You can use it instead of ' +
                    'the apikey.'))
@click.option('-c',
              '--cloudos-url',
              help=('The CloudOS url you are trying to access to. ' +
                    'Default=https://cloudos.lifebit.ai.'),
              default='https://cloudos.lifebit.ai')
@click.option('--workspace-id',
              help='The specific CloudOS workspace id.',
              required=True)
@click.option('--verbose',
              help='Whether to print information messages or not.',
              is_flag=True)
@click.option('--disable-ssl-verification',
              help=('Disable SSL certificate verification. Please, remember that this option is ' +
                    'not generally recommended for security reasons.'),
              is_flag=True)
@click.option('--ssl-cert',
              help='Path to your SSL certificate file.')
def cromwell_status(apikey,
                    cromwell_token,
                    cloudos_url,
                    workspace_id,
                    verbose,
                    disable_ssl_verification,
                    ssl_cert):
    """Check Cromwell server status in CloudOS."""
    if apikey is None and cromwell_token is None:
        raise ValueError("Please, use one of the following tokens: '--apikey', '--cromwell_token'")
    print('Executing status...')
    verify_ssl = ssl_selector(disable_ssl_verification, ssl_cert)
    if verbose:
        print('\t...Preparing objects')
    cl = Cloudos(cloudos_url, apikey, cromwell_token)
    if verbose:
        print('\tThe following Cloudos object was created:')
        print('\t' + str(cl) + '\n')
        print(f'\tChecking Cromwell status in {workspace_id} workspace')
    c_status = cl.get_cromwell_status(workspace_id, verify_ssl)
    c_status_h = json.loads(c_status.content)["status"]
    print(f'\tCurrent Cromwell server status is: {c_status_h}\n')


@cromwell.command('start')
@click.version_option()
@click.option('-k',
              '--apikey',
              help='Your CloudOS API key.')
@click.option('-t',
              '--cromwell-token',
              help=('Specific Cromwell server authentication token. You can use it instead of ' +
                    'the apikey.'))
@click.option('-c',
              '--cloudos-url',
              help=('The CloudOS url you are trying to access to. ' +
                    'Default=https://cloudos.lifebit.ai.'),
              default='https://cloudos.lifebit.ai')
@click.option('--workspace-id',
              help='The specific CloudOS workspace id.',
              required=True)
@click.option('--wait-time',
              help=('Max time to wait (in seconds) to Cromwell restart. ' +
                    'Default=300.'),
              default=300)
@click.option('--verbose',
              help='Whether to print information messages or not.',
              is_flag=True)
@click.option('--disable-ssl-verification',
              help=('Disable SSL certificate verification. Please, remember that this option is ' +
                    'not generally recommended for security reasons.'),
              is_flag=True)
@click.option('--ssl-cert',
              help='Path to your SSL certificate file.')
def cromwell_restart(apikey,
                     cromwell_token,
                     cloudos_url,
                     workspace_id,
                     wait_time,
                     verbose,
                     disable_ssl_verification,
                     ssl_cert):
    """Restart Cromwell server in CloudOS."""
    if apikey is None and cromwell_token is None:
        raise ValueError("Please, use one of the following tokens: '--apikey', '--cromwell_token'")
    verify_ssl = ssl_selector(disable_ssl_verification, ssl_cert)
    action = 'restart'
    print('Starting Cromwell server...')
    if verbose:
        print('\t...Preparing objects')
    cl = Cloudos(cloudos_url, apikey, cromwell_token)
    if verbose:
        print('\tThe following Cloudos object was created:')
        print('\t' + str(cl) + '\n')
        print(f'\tStarting Cromwell server in {workspace_id} workspace')
    cl.cromwell_switch(workspace_id, action, verify_ssl)
    c_status = cl.get_cromwell_status(workspace_id, verify_ssl)
    c_status_h = json.loads(c_status.content)["status"]
    print(f'\tCurrent Cromwell server status is: {c_status_h}\n')
    elapsed = 0
    while elapsed < wait_time and c_status_h != 'Running':
        c_status_old = c_status_h
        time.sleep(REQUEST_INTERVAL_CROMWELL)
        elapsed += REQUEST_INTERVAL_CROMWELL
        c_status = cl.get_cromwell_status(workspace_id, verify_ssl)
        c_status_h = json.loads(c_status.content)["status"]
        if c_status_h != c_status_old:
            print(f'\tCurrent Cromwell server status is: {c_status_h}\n')
    if c_status_h != 'Running':
        print(f'\tYour current Cromwell status is: {c_status_h}. The ' +
              f'selected wait-time of {wait_time} was exceeded. Please, ' +
              'consider to set a longer wait-time.')
        print('\tTo further check your Cromwell status you can either go to ' +
              f'{cloudos_url} or use the following command:\n' +
              '\tcloudos cromwell status \\\n' +
              f'\t\t--cloudos-url {cloudos_url} \\\n' +
              '\t\t--cromwell-token $CROMWELL_TOKEN \\\n' +
              f'\t\t--workspace-id {workspace_id}')
        sys.exit(1)


@cromwell.command('stop')
@click.version_option()
@click.option('-k',
              '--apikey',
              help='Your CloudOS API key.')
@click.option('-t',
              '--cromwell-token',
              help=('Specific Cromwell server authentication token. You can use it instead of ' +
                    'the apikey.'))
@click.option('-c',
              '--cloudos-url',
              help=('The CloudOS url you are trying to access to. ' +
                    'Default=https://cloudos.lifebit.ai.'),
              default='https://cloudos.lifebit.ai')
@click.option('--workspace-id',
              help='The specific CloudOS workspace id.',
              required=True)
@click.option('--verbose',
              help='Whether to print information messages or not.',
              is_flag=True)
@click.option('--disable-ssl-verification',
              help=('Disable SSL certificate verification. Please, remember that this option is ' +
                    'not generally recommended for security reasons.'),
              is_flag=True)
@click.option('--ssl-cert',
              help='Path to your SSL certificate file.')
def cromwell_stop(apikey,
                  cromwell_token,
                  cloudos_url,
                  workspace_id,
                  verbose,
                  disable_ssl_verification,
                  ssl_cert):
    """Stop Cromwell server in CloudOS."""
    if apikey is None and cromwell_token is None:
        raise ValueError("Please, use one of the following tokens: '--apikey', '--cromwell_token'")
    verify_ssl = ssl_selector(disable_ssl_verification, ssl_cert)
    action = 'stop'
    print('Stopping Cromwell server...')
    if verbose:
        print('\t...Preparing objects')
    cl = Cloudos(cloudos_url, apikey, cromwell_token)
    if verbose:
        print('\tThe following Cloudos object was created:')
        print('\t' + str(cl) + '\n')
        print(f'\tStopping Cromwell server in {workspace_id} workspace')
    cl.cromwell_switch(workspace_id, action, verify_ssl)
    c_status = cl.get_cromwell_status(workspace_id, verify_ssl)
    c_status_h = json.loads(c_status.content)["status"]
    print(f'\tCurrent Cromwell server status is: {c_status_h}\n')


@queue.command('list')
@click.option('-k',
              '--apikey',
              help='Your CloudOS API key',
              required=True)
@click.option('-c',
              '--cloudos-url',
              help=('The CloudOS url you are trying to access to. ' +
                    'Default=https://cloudos.lifebit.ai.'),
              default='https://cloudos.lifebit.ai')
@click.option('--workspace-id',
              help='The specific CloudOS workspace id.',
              required=True)
@click.option('--output-basename',
              help=('Output file base name to save job queue list. ' +
                    'Default=job_queue_list'),
              default='job_queue_list',
              required=False)
@click.option('--output-format',
              help='The desired file format (file extension) for the output. Default=csv.',
              type=click.Choice(['csv', 'json'], case_sensitive=False),
              default='csv')
@click.option('--all-fields',
              help=('Whether to collect all available fields from workflows or ' +
                    'just the preconfigured selected fields. Only applicable ' +
                    'when --output-format=csv'),
              is_flag=True)
@click.option('--disable-ssl-verification',
              help=('Disable SSL certificate verification. Please, remember that this option is ' +
                    'not generally recommended for security reasons.'),
              is_flag=True)
@click.option('--ssl-cert',
              help='Path to your SSL certificate file.')
def list_queues(apikey,
                cloudos_url,
                workspace_id,
                output_basename,
                output_format,
                all_fields,
                disable_ssl_verification,
                ssl_cert):
    """Collect all available job queues from a CloudOS workspace."""
    verify_ssl = ssl_selector(disable_ssl_verification, ssl_cert)
    outfile = output_basename + '.' + output_format
    print('Executing list...')
    j_queue = Queue(cloudos_url, apikey, None, workspace_id, verify=verify_ssl)
    my_queues = j_queue.get_job_queues()
    if len(my_queues) == 0:
        raise ValueError('No AWS batch queues found. Please, make sure that your CloudOS supports AWS bath queues')
    if output_format == 'csv':
        queues_processed = j_queue.process_queue_list(my_queues, all_fields)
        queues_processed.to_csv(outfile, index=False)
        print(f'\tJob queue list collected with a total of {queues_processed.shape[0]} queues.')
    elif output_format == 'json':
        with open(outfile, 'w') as o:
            o.write(json.dumps(my_queues))
        print(f'\tJob queue list collected with a total of {len(my_queues)} queues.')
    else:
        raise ValueError('Unrecognised output format. Please use one of [csv|json]')
    print(f'\tJob queue list saved to {outfile}')


if __name__ == "__main__":
    run_cloudos_cli()

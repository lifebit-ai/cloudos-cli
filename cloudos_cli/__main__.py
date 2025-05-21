#!/usr/bin/env python3

import rich_click as click
import cloudos_cli.jobs.job as jb
from cloudos_cli.clos import Cloudos
from cloudos_cli.queue.queue import Queue
import json
import time
import sys
import os
import urllib3
from ._version import __version__
from concurrent.futures import ThreadPoolExecutor, as_completed
from cloudos_cli.configure.configure import ConfigurationProfile


# GLOBAL VARS
JOB_COMPLETED = 'completed'
JOB_FAILED = 'failed'
JOB_ABORTED = 'aborted'
JOB_RUNNING = 'running'
REQUEST_INTERVAL_CROMWELL = 30
AWS_NEXTFLOW_VERSIONS = ['22.10.8', '24.04.4']
AZURE_NEXTFLOW_VERSIONS = ['22.11.1-edge']
HPC_NEXTFLOW_VERSIONS = ['22.10.8']
AWS_NEXTFLOW_LATEST = '24.04.4'
AZURE_NEXTFLOW_LATEST = '22.11.1-edge'
HPC_NEXTFLOW_LATEST = '22.10.8'
ABORT_JOB_STATES = ['running', 'initializing']
CLOUDOS_URL = 'https://cloudos.lifebit.ai'
INIT_PROFILE = 'initialisingProfile'


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
@click.pass_context
def run_cloudos_cli(ctx):
    """CloudOS python package: a package for interacting with CloudOS."""
    print(run_cloudos_cli.__doc__ + '\n')
    print('Version: ' + __version__ + '\n')
    ctx.ensure_object(dict)
    config_manager = ConfigurationProfile()
    profile_to_use = config_manager.determine_default_profile()
    if profile_to_use is None:
        print('[Warning] No profile found. Please create one with "cloudos configure".\n')
        shared_config = dict({
            'apikey': '',
            'cloudos_url': CLOUDOS_URL,
            'workspace_id': '',
            'project_name': '',
            'workflow_name': '',
            'repository_platform': 'github',
            'execution_platform': 'aws',
            'profile': INIT_PROFILE
        })
        ctx.default_map = dict({
            'job': {
                'run': shared_config,
                'run-curated-examples': shared_config,
                'abort': shared_config,
                'status': shared_config,
                'list': shared_config,
            },
            'workflow': {
                'list': shared_config,
                'import': shared_config
            },
            'project': {
                'list': shared_config
            },
            'cromwell': {
                'status': shared_config,
                'start': shared_config,
                'stop': shared_config
            },
            'queue': {
                'list': shared_config
            },
            'bash': {
                'job': shared_config
            }
        })
    else:
        profile_data = config_manager.load_profile(profile_name=profile_to_use)
        shared_config = dict({
            'apikey': profile_data.get('apikey', ""),
            'cloudos_url': profile_data.get('cloudos_url', ""),
            'workspace_id': profile_data.get('workspace_id', ""),
            'project_name': profile_data.get('project_name', ""),
            'workflow_name': profile_data.get('workflow_name', ""),
            'repository_platform': profile_data.get('repository_platform', ""),
            'execution_platform': profile_data.get('execution_platform', ""),
            'profile': profile_to_use
        })
        ctx.default_map = dict({
            'job': {
                'run': shared_config,
                'run-curated-examples': shared_config,
                'abort': shared_config,
                'status': shared_config,
                'list': shared_config,
            },
            'workflow': {
                'list': shared_config,
                'import': shared_config
            },
            'project': {
                'list': shared_config
            },
            'cromwell': {
                'status': shared_config,
                'start': shared_config,
                'stop': shared_config
            },
            'queue': {
                'list': shared_config
            },
            'bash': {
                'job': shared_config
            }
        })


@run_cloudos_cli.group()
def job():
    """CloudOS job functionality: run, check and abort jobs in CloudOS."""
    print(job.__doc__ + '\n')


@run_cloudos_cli.group()
def workflow():
    """CloudOS workflow functionality: list and import workflows."""
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


@run_cloudos_cli.group()
def bash():
    """CloudOS bash functionality."""
    print(bash.__doc__ + '\n')


@run_cloudos_cli.group(invoke_without_command=True)
@click.option('--profile', help='Profile to use from the config file', default='default')
@click.option('--make-default',
              is_flag=True,
              help='Make the profile the default one.')
@click.pass_context
def configure(ctx, profile, make_default):
    """CloudOS configuration."""
    print(configure.__doc__ + '\n')
    profile = profile or ctx.obj['profile']
    config_manager = ConfigurationProfile()

    if ctx.invoked_subcommand is None and profile == "default" and not make_default:
        config_manager.create_profile_from_input(profile_name="default")

    if profile != "default" and not make_default:
        config_manager.create_profile_from_input(profile_name=profile)
    if make_default:
        config_manager.make_default_profile(profile_name=profile)


@job.command('run')
@click.option('-k',
              '--apikey',
              help='Your CloudOS API key',
              required=True)
@click.option('-c',
              '--cloudos-url',
              help=(f'The CloudOS url you are trying to access to. Default={CLOUDOS_URL}.'),
              default=CLOUDOS_URL)
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
@click.option('--nextflow-version',
              help=('Nextflow version to use when executing the workflow in CloudOS. ' +
                    'Please, note that versions above 22.10.8 are only DSL2 compatible. ' +
                    'Default=22.10.8.'),
              type=click.Choice(['22.10.8', '24.04.4', '22.11.1-edge', 'latest']),
              default='22.10.8')
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
@click.option('--do-not-save-logs',
              help=('Avoids process log saving. If you select this option, your job process ' +
                    'logs will not be stored.'),
              is_flag=True)
@click.option('--spot',
              help=('[Deprecated in 2.11.0] This option has been deprecated and has no effect. ' +
                    'Spot instances are no longer available in CloudOS.'),
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
              help=('ID of your HPC, only applicable when --execution-platform=hpc. ' +
                    'Default=660fae20f93358ad61e0104b'),
              default='660fae20f93358ad61e0104b')
@click.option('--cost-limit',
              help='Add a cost limit to your job. Default=30.0 (For no cost limit please use -1).',
              type=float,
              default=30.0)
@click.option('--accelerate-file-staging',
              help='Enables AWS S3 mountpoint for quicker file staging.',
              is_flag=True)
@click.option('--use-private-docker-repository',
              help=('Allows to use private docker repository for running jobs. The Docker user ' +
                    'account has to be already linked to CloudOS.'),
              is_flag=True)
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
@click.option('--profile', help='Profile to use from the config file', default=None)
@click.pass_context
def run(ctx,
        apikey,
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
        do_not_save_logs,
        spot,
        batch,
        ignite,
        job_queue,
        nextflow_profile,
        nextflow_version,
        instance_type,
        instance_disk,
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
        accelerate_file_staging,
        use_private_docker_repository,
        verbose,
        request_interval,
        disable_ssl_verification,
        ssl_cert,
        profile):
    """Submit a job to CloudOS."""
    profile = profile or ctx.default_map['job']['run']['profile']
    # Create a dictionary with required and non-required params
    required_dict = {
        'apikey': True,
        'workspace_id': True,
        'workflow_name': True,
        'project_name': True
    }
    # determine if the user provided all required parameters
    config_manager = ConfigurationProfile()
    apikey, cloudos_url, workspace_id, workflow_name, repository_platform, execution_platform, project_name = (
        config_manager.load_profile_and_validate_data(
            ctx,
            INIT_PROFILE,
            CLOUDOS_URL,
            profile=profile,
            required_dict=required_dict,
            apikey=apikey,
            cloudos_url=cloudos_url,
            workspace_id=workspace_id,
            workflow_name=workflow_name,
            repository_platform=repository_platform,
            execution_platform=execution_platform,
            project_name=project_name
        )
    )

    verify_ssl = ssl_selector(disable_ssl_verification, ssl_cert)
    if spot:
        print('[Message] You have specified spot instances but they are no longer available ' +
              'in CloudOS. Option ignored.')
    if do_not_save_logs:
        save_logs = False
    else:
        save_logs = True
    if instance_type == 'NONE_SELECTED':
        if execution_platform == 'aws':
            instance_type = 'c5.xlarge'
        elif execution_platform == 'azure':
            instance_type = 'Standard_D4as_v4'
        else:
            instance_type = None
    if execution_platform == 'azure' or execution_platform == 'hpc':
        batch = None
    elif ignite:
        batch = None
        print('[Warning] You have specified ignite executor. Please, note that ignite is being ' +
              'removed from CloudOS, so the command may fail. Check ignite availability in your ' +
              'CloudOS')
    else:
        batch = True
    if execution_platform == 'hpc':
        print('\n[Message] HPC execution platform selected')
        if hpc_id is None:
            raise ValueError('Please, specify your HPC ID using --hpc parameter')
        print('[Message] Please, take into account that HPC execution do not support ' +
              'the following parameters and all of them will be ignored:\n' +
              '\t--job-queue\n' +
              '\t--resumable | --do-not-save-logs\n' +
              '\t--instance-type | --instance-disk | --cost-limit\n' +
              '\t--storage-mode | --lustre-size\n' +
              '\t--wdl-mainfile | --wdl-importsfile | --cromwell-token\n')
        wdl_mainfile = None
        wdl_importsfile = None
        storage_mode = 'regular'
        save_logs = False
    if accelerate_file_staging:
        if execution_platform != 'aws':
            print('[Message] You have selected accelerate file staging, but this function is ' +
                  'only available when execution platform is AWS. The accelerate file staging ' +
                  'will not be applied')
            use_mountpoints = False
        else:
            use_mountpoints = True
            print('[Message] Enabling AWS S3 mountpoint for accelerated file staging. ' +
                  'Please, take into consideration the following:\n' +
                  '\t- It significantly reduces runtime and compute costs but may increase network costs.\n' +
                  '\t- Requires extra memory. Adjust process memory or optimise resource usage if necessary.\n' +
                  '\t- This is still a CloudOS BETA feature.\n')
    else:
        use_mountpoints = False
    if verbose:
        print('\t...Detecting workflow type')
    cl = Cloudos(cloudos_url, apikey, cromwell_token)
    workflow_type = cl.detect_workflow(workflow_name, workspace_id, verify_ssl)
    is_module = cl.is_module(workflow_name, workspace_id, verify_ssl)
    if execution_platform == 'hpc' and workflow_type == 'wdl':
        raise ValueError(f'The workflow {workflow_name} is a WDL workflow. ' +
                         'WDL is not supported on HPC execution platform.')
    if workflow_type == 'wdl':
        print('[Message] WDL workflow detected')
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
    if is_module:
        if job_queue is not None:
            print(f'[Message] Ignoring job queue "{job_queue}" for ' +
                  f'Platform Workflow "{workflow_name}". Platform Workflows ' +
                  'use their own predetermined queues.')
        job_queue_id = None
        if nextflow_version != '22.10.8':
            print(f'[Message] The selected worflow \'{workflow_name}\' ' +
                  'is a CloudOS module. CloudOS modules only work with ' +
                  'Nextflow version 22.10.8. Switching to use 22.10.8')
        nextflow_version = '22.10.8'
    else:
        queue = Queue(cloudos_url=cloudos_url, apikey=apikey, cromwell_token=cromwell_token,
                      workspace_id=workspace_id, verify=verify_ssl)
        job_queue_id = queue.fetch_job_queue_id(workflow_type=workflow_type, batch=batch,
                                                job_queue=job_queue)
    if use_private_docker_repository:
        if is_module:
            print(f'[Message] Workflow "{workflow_name}" is a CloudOS module. ' +
                  'Option --use-private-docker-repository will be ignored.')
            docker_login = False
        else:
            me = j.get_user_info(verify=verify_ssl)['dockerRegistriesCredentials']
            if len(me) == 0:
                raise Exception('User private Docker repository has been selected but your user ' +
                                'credentials have not been configured yet. Please, link your ' +
                                'Docker account to CloudOS before using ' +
                                '--use-private-docker-repository option.')
            print('[Message] Use private Docker repository has been selected. A custom job ' +
                  'queue to support private Docker containers and/or Lustre FSx will be created for ' +
                  'your job. The selected job queue will serve as a template.')
            docker_login = True
    else:
        docker_login = False
    if nextflow_version == 'latest':
        if execution_platform == 'aws':
            nextflow_version = AWS_NEXTFLOW_LATEST
        elif execution_platform == 'azure':
            nextflow_version = AZURE_NEXTFLOW_LATEST
        else:
            nextflow_version = HPC_NEXTFLOW_LATEST
        print('[Message] You have specified Nextflow version \'latest\' for execution platform ' +
              f'\'{execution_platform}\'. The workflow will use the ' +
              f'latest version available on CloudOS: {nextflow_version}.')
    if execution_platform == 'aws':
        if nextflow_version not in AWS_NEXTFLOW_VERSIONS:
            print('[Message] For execution platform \'aws\', the workflow will use the default ' +
                  '\'22.10.8\' version on CloudOS.')
            nextflow_version = '22.10.8'
    if execution_platform == 'azure':
        if nextflow_version not in AZURE_NEXTFLOW_VERSIONS:
            print('[Message] For execution platform \'azure\', the workflow will use the \'22.11.1-edge\' ' +
                  'version on CloudOS.')
            nextflow_version = '22.11.1-edge'
    if execution_platform == 'hpc':
        if nextflow_version not in HPC_NEXTFLOW_VERSIONS:
            print('[Message] For execution platform \'hpc\', the workflow will use the \'22.10.8\' version on CloudOS.')
            nextflow_version = '22.10.8'
    if nextflow_version != '22.10.8':
        print(f'[Warning] You have specified Nextflow version {nextflow_version}. This version requires the pipeline ' +
              'to be written in DSL2 and does not support DSL1.')
    print('\nExecuting run...')
    if workflow_type == 'nextflow':
        print(f'\tNextflow version: {nextflow_version}')
    j_id = j.send_job(job_config=job_config,
                      parameter=parameter,
                      git_commit=git_commit,
                      git_tag=git_tag,
                      job_name=job_name,
                      resumable=resumable,
                      save_logs=save_logs,
                      batch=batch,
                      job_queue_id=job_queue_id,
                      nextflow_profile=nextflow_profile,
                      nextflow_version=nextflow_version,
                      instance_type=instance_type,
                      instance_disk=instance_disk,
                      storage_mode=storage_mode,
                      lustre_size=lustre_size,
                      execution_platform=execution_platform,
                      hpc_id=hpc_id,
                      workflow_type=workflow_type,
                      cromwell_id=cromwell_id,
                      cost_limit=cost_limit,
                      use_mountpoints=use_mountpoints,
                      docker_login=docker_login,
                      verify=verify_ssl)
    print(f'\tYour assigned job id is: {j_id}\n')
    j_url = f'{cloudos_url}/app/advanced-analytics/analyses/{j_id}'
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
              help=(f'The CloudOS url you are trying to access to. Default={CLOUDOS_URL}.'),
              default=CLOUDOS_URL)
@click.option('--workspace-id',
              help='The specific CloudOS workspace id.',
              required=True)
@click.option('--project-name',
              help='The name of a CloudOS project.',
              required=True)
@click.option('--resumable',
              help='Whether to make the job able to be resumed or not.',
              is_flag=True)
@click.option('--do-not-save-logs',
              help=('Avoids process log saving. If you select this option, your job process ' +
                    'logs will not be stored.'),
              is_flag=True)
@click.option('--spot',
              help=('[Deprecated in 2.11.0] This option has been deprecated and has no effect. ' +
                    'Spot instances are no longer available in CloudOS.'),
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
@click.option('--accelerate-file-staging',
              help='Enables AWS S3 mountpoint for quicker file staging.',
              is_flag=True)
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
@click.option('--profile', help='Profile to use from the config file', default=None)
@click.pass_context
def run_curated_examples(ctx,
                         apikey,
                         cloudos_url,
                         workspace_id,
                         project_name,
                         resumable,
                         do_not_save_logs,
                         spot,
                         batch,
                         ignite,
                         instance_type,
                         instance_disk,
                         storage_mode,
                         lustre_size,
                         execution_platform,
                         cost_limit,
                         accelerate_file_staging,
                         wait_completion,
                         wait_time,
                         request_interval,
                         verbose,
                         disable_ssl_verification,
                         ssl_cert,
                         profile):
    """Run all the curated workflows with example parameters.

    NOTE that currently, only Nextflow workflows are supported.
    """
    profile = profile or ctx.default_map['job']['run-curated-examples']['profile']
    # Create a dictionary with required and non-required params
    required_dict = {
        'apikey': True,
        'workspace_id': True,
        'workflow_name': False,
        'project_name': True
    }
    # determine if the user provided all required parameters
    config_manager = ConfigurationProfile()
    apikey, cloudos_url, workspace_id, workflow_name, repository_platform, execution_platform, project_name = (
        config_manager.load_profile_and_validate_data(
            ctx,
            INIT_PROFILE,
            CLOUDOS_URL,
            profile=profile,
            required_dict=required_dict,
            apikey=apikey,
            cloudos_url=cloudos_url,
            workspace_id=workspace_id,
            execution_platform=execution_platform,
            project_name=project_name
        )
    )

    verify_ssl = ssl_selector(disable_ssl_verification, ssl_cert)
    cl = Cloudos(cloudos_url, apikey, None)
    curated_workflows = cl.get_curated_workflow_list(workspace_id, verify=verify_ssl)
    job_id_list = []
    runnable_curated_workflows = [
        w for w in curated_workflows if w['workflowType'] == 'nextflow' and len(w['parameters']) > 0
    ]
    if spot:
        print('\n[Message] You have specified spot instances but they are no longer available ' +
              'in CloudOS. Option ignored.\n')
    if do_not_save_logs:
        save_logs = False
    else:
        save_logs = True
    if instance_type == 'NONE_SELECTED':
        if execution_platform == 'aws':
            instance_type = 'c5.xlarge'
        if execution_platform == 'azure':
            instance_type = 'Standard_D4as_v4'
    if execution_platform == 'azure':
        batch = None
    elif ignite:
        batch = None
        print('\n[Warning] You have specified ignite executor. Please, note that ignite is being ' +
              'removed from CloudOS, so the command may fail. Check ignite availability in your ' +
              'CloudOS\n')
    else:
        batch = True
    if accelerate_file_staging:
        if execution_platform != 'aws':
            print('[Message] You have selected accelerate file staging, but this function is ' +
                  'only available when execution platform is AWS. The accelerate file staging ' +
                  'will not be applied')
            use_mountpoints = False
        else:
            use_mountpoints = True
            print('[Message] Enabling AWS S3 mountpoint for accelerated file staging. ' +
                  'Please, take into consideration the following:\n' +
                  '\t- It significantly reduces runtime and compute costs but may increase network costs.\n' +
                  '\t- Requires extra memory. Adjust process memory or optimise resource usage if necessary.\n' +
                  '\t- This is still a CloudOS BETA feature.\n')
    else:
        use_mountpoints = False
    for workflow in runnable_curated_workflows:
        workflow_name = workflow['name']
        j = jb.Job(cloudos_url, apikey, None, workspace_id, project_name, workflow_name,
                   repository_platform=workflow['repository']['platform'], verify=verify_ssl)
        j_id = j.send_job(example_parameters=workflow['parameters'],
                          job_name=f"{workflow['name']}|Example_Run",
                          resumable=resumable,
                          save_logs=save_logs,
                          batch=batch,
                          instance_type=instance_type,
                          instance_disk=instance_disk,
                          storage_mode=storage_mode,
                          lustre_size=lustre_size,
                          execution_platform=execution_platform,
                          workflow_type='nextflow',
                          cost_limit=cost_limit,
                          use_mountpoints=use_mountpoints,
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
              help=(f'The CloudOS url you are trying to access to. Default={CLOUDOS_URL}.'),
              default=CLOUDOS_URL)
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
@click.option('--profile', help='Profile to use from the config file', default=None)
@click.pass_context
def job_status(ctx,
               apikey,
               cloudos_url,
               job_id,
               verbose,
               disable_ssl_verification,
               ssl_cert,
               profile):
    """Check job status in CloudOS."""
    profile = profile or ctx.default_map['job']['status']['profile']
    # Create a dictionary with required and non-required params
    required_dict = {
        'apikey': True,
        'workspace_id': False,
        'workflow_name': False,
        'project_name': False
    }
    # determine if the user provided all required parameters
    config_manager = ConfigurationProfile()
    apikey, cloudos_url, workspace_id, workflow_name, repository_platform, execution_platform, project_name = (
        config_manager.load_profile_and_validate_data(
            ctx,
            INIT_PROFILE,
            CLOUDOS_URL,
            profile=profile,
            required_dict=required_dict,
            apikey=apikey,
            cloudos_url=cloudos_url
        )
    )

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
    j_url = f'{cloudos_url}/app/advanced-analytics/analyses/{job_id}'
    print(f'\tTo further check your job status you can either go to {j_url} ' +
          'or repeat the command you just used.')


@job.command('list')
@click.option('-k',
              '--apikey',
              help='Your CloudOS API key',
              required=True)
@click.option('-c',
              '--cloudos-url',
              help=(f'The CloudOS url you are trying to access to. Default={CLOUDOS_URL}.'),
              default=CLOUDOS_URL)
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
@click.option('--archived',
              help=('When this flag is used, only archived jobs list is collected.'),
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
@click.option('--profile', help='Profile to use from the config file', default=None)
@click.pass_context
def list_jobs(ctx,
              apikey,
              cloudos_url,
              workspace_id,
              output_basename,
              output_format,
              all_fields,
              last_n_jobs,
              page,
              archived,
              verbose,
              disable_ssl_verification,
              ssl_cert,
              profile):
    """Collect all your jobs from a CloudOS workspace in CSV format."""
    profile = profile or ctx.default_map['job']['list']['profile']
    # Create a dictionary with required and non-required params
    required_dict = {
        'apikey': True,
        'workspace_id': True,
        'workflow_name': False,
        'project_name': False
    }
    # determine if the user provided all required parameters
    config_manager = ConfigurationProfile()
    apikey, cloudos_url, workspace_id, workflow_name, repository_platform, execution_platform, project_name = (
        config_manager.load_profile_and_validate_data(
            ctx,
            INIT_PROFILE,
            CLOUDOS_URL,
            profile=profile,
            required_dict=required_dict,
            apikey=apikey,
            cloudos_url=cloudos_url,
            workspace_id=workspace_id
        )
    )

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
    # Check if the user provided the --page option
    ctx = click.get_current_context()
    if not isinstance(page, int) or page < 1:
        raise ValueError('Please, use a positive integer (>= 1) for the --page parameter')
    if last_n_jobs != 'all':
        try:
            last_n_jobs = int(last_n_jobs)
        except ValueError:
            print("[ERROR] last-n-jobs value was not valid. Please use a positive int or 'all'")
            raise
    my_jobs_r = cl.get_job_list(workspace_id, last_n_jobs, page, archived, verify_ssl)
    if len(my_jobs_r) == 0:
        if ctx.get_parameter_source('page') == click.core.ParameterSource.DEFAULT:
            print('\t[Message] A total of 0 jobs collected. This is likely because your workspace ' +
                  'has no jobs created yet.')
        else:
            print('\t[Message] A total of 0 jobs collected. This is likely because the --page you requested ' +
                  'does not exist. Please, try a smaller number for --page or collect all the jobs by not ' +
                  'using --page parameter.')
    elif output_format == 'csv':
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


@job.command('abort')
@click.option('-k',
              '--apikey',
              help='Your CloudOS API key',
              required=True)
@click.option('-c',
              '--cloudos-url',
              help=(f'The CloudOS url you are trying to access to. Default={CLOUDOS_URL}.'),
              default=CLOUDOS_URL)
@click.option('--workspace-id',
              help='The specific CloudOS workspace id.',
              required=True)
@click.option('--job-ids',
              help=('One or more job ids to abort. If more than ' +
                    'one is provided, they must be provided as ' +
                    'a comma separated list of ids. E.g. id1,id2,id3'),
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
@click.option('--profile', help='Profile to use from the config file', default=None)
@click.pass_context
def abort_jobs(ctx,
               apikey,
               cloudos_url,
               workspace_id,
               job_ids,
               verbose,
               disable_ssl_verification,
               ssl_cert,
               profile):
    """Abort all specified jobs from a CloudOS workspace."""
    profile = profile or ctx.default_map['job']['abort']['profile']
    # Create a dictionary with required and non-required params
    required_dict = {
        'apikey': True,
        'workspace_id': True,
        'workflow_name': False,
        'project_name': False
    }
    # determine if the user provided all required parameters
    config_manager = ConfigurationProfile()
    apikey, cloudos_url, workspace_id, workflow_name, repository_platform, execution_platform, project_name = (
        config_manager.load_profile_and_validate_data(
            ctx,
            INIT_PROFILE,
            CLOUDOS_URL,
            profile=profile,
            required_dict=required_dict,
            apikey=apikey,
            cloudos_url=cloudos_url,
            workspace_id=workspace_id
        )
    )

    verify_ssl = ssl_selector(disable_ssl_verification, ssl_cert)
    print('Aborting jobs...')
    if verbose:
        print('\t...Preparing objects')
    cl = Cloudos(cloudos_url, apikey, None)
    if verbose:
        print('\tThe following Cloudos object was created:')
        print('\t' + str(cl) + '\n')
        print('\tSearching for jobs in the following workspace: ' +
              f'{workspace_id}')
    # check if the user provided an empty job list
    jobs = job_ids.replace(' ', '')
    if not jobs:
        raise ValueError('No job IDs provided. Please specify at least one job ID to abort.')
    jobs = jobs.split(',')

    for job in jobs:
        try:
            j_status = cl.get_job_status(job, verify_ssl)
        except Exception as e:
            print(f"[WARNING] Failed to get status for job {job}, please make sure it exists in the workspace: {e}")
            continue
        j_status_content = json.loads(j_status.content)
        # check if job id is valid & is in working state (initial, running)
        if j_status_content['status'] not in ABORT_JOB_STATES:
            print("[WARNING] Job {job} is not in a state that can be aborted and is ignored. " +
                  f"Current status: {j_status_content['status']}")
        else:
            cl.abort_job(job, workspace_id, verify_ssl)
            print(f"\tJob '{job}' aborted successfully.")


@workflow.command('list')
@click.option('-k',
              '--apikey',
              help='Your CloudOS API key',
              required=True)
@click.option('-c',
              '--cloudos-url',
              help=(f'The CloudOS url you are trying to access to. Default={CLOUDOS_URL}.'),
              default=CLOUDOS_URL)
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
@click.option('--profile', help='Profile to use from the config file', default=None)
@click.pass_context
def list_workflows(ctx,
                   apikey,
                   cloudos_url,
                   workspace_id,
                   output_basename,
                   output_format,
                   all_fields,
                   curated,
                   verbose,
                   disable_ssl_verification,
                   ssl_cert,
                   profile):
    """Collect all workflows from a CloudOS workspace in CSV format."""
    profile = profile or ctx.default_map['workflow']['list']['profile']
    # Create a dictionary with required and non-required params
    required_dict = {
        'apikey': True,
        'workspace_id': True,
        'workflow_name': False,
        'project_name': False
    }
    # determine if the user provided all required parameters
    config_manager = ConfigurationProfile()
    apikey, cloudos_url, workspace_id, workflow_name, repository_platform, execution_platform, project_name = (
        config_manager.load_profile_and_validate_data(
            ctx,
            INIT_PROFILE,
            CLOUDOS_URL,
            profile=profile,
            required_dict=required_dict,
            apikey=apikey,
            cloudos_url=cloudos_url,
            workspace_id=workspace_id
        )
    )

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


@workflow.command('import')
@click.option('-k',
              '--apikey',
              help='Your CloudOS API key',
              required=True)
@click.option('-c',
              '--cloudos-url',
              help=(f'The CloudOS url you are trying to access to. Default={CLOUDOS_URL}.'),
              default=CLOUDOS_URL)
@click.option('--workspace-id',
              help='The specific CloudOS workspace id.',
              required=True)
@click.option('--workflow-url',
              help=('URL of the workflow to import. Please, note that it should ' +
                    'be the URL shown in the browser, and it should come without ' +
                    'any of the .git or /browse extensions.'),
              required=True)
@click.option('--workflow-name',
              help="The name that the workflow will have in CloudOS",
              required=True)
@click.option('--workflow-docs-link',
              help="Workflow documentation URL.",
              default='')
@click.option('--repository-project-id',
              type=int,
              help="The ID of your repository project",
              required=True)
@click.option('--repository-id',
              type=int,
              help="The ID of your repository. Only required for GitHub repositories")
@click.option('--disable-ssl-verification',
              help=('Disable SSL certificate verification. Please, remember that this option is ' +
                    'not generally recommended for security reasons.'),
              is_flag=True)
@click.option('--ssl-cert',
              help='Path to your SSL certificate file.')
@click.option('--profile', help='Profile to use from the config file', default=None)
@click.pass_context
def import_workflows(ctx,
                     apikey,
                     cloudos_url,
                     workspace_id,
                     workflow_url,
                     workflow_name,
                     repository_project_id,
                     workflow_docs_link,
                     repository_id,
                     disable_ssl_verification,
                     ssl_cert,
                     profile):
    """Imports workflows to CloudOS."""
    profile = profile or ctx.default_map['workflow']['import']['profile']
    # Create a dictionary with required and non-required params
    required_dict = {
        'apikey': True,
        'workspace_id': True,
        'workflow_name': False,
        'project_name': False
    }
    # determine if the user provided all required parameters
    config_manager = ConfigurationProfile()
    apikey, cloudos_url, workspace_id, workflow_name, repository_platform, execution_platform, project_name = (
        config_manager.load_profile_and_validate_data(
            ctx,
            INIT_PROFILE,
            CLOUDOS_URL,
            profile=profile,
            required_dict=required_dict,
            apikey=apikey,
            cloudos_url=cloudos_url,
            workspace_id=workspace_id,
            workflow_name=workflow_name
        )
    )

    verify_ssl = ssl_selector(disable_ssl_verification, ssl_cert)
    print('Executing workflow import...\n')
    print('\t[Message] Only Nextflow workflows are currently supported.\n')
    cl = Cloudos(cloudos_url, apikey, None)
    workflow_id = cl.workflow_import(workspace_id,
                                     workflow_url,
                                     workflow_name,
                                     repository_project_id,
                                     workflow_docs_link,
                                     repository_id,
                                     verify=verify_ssl)
    print(f'\tWorkflow {workflow_name} was imported successfully with the ' +
          f'following ID: {workflow_id}')


@project.command('list')
@click.option('-k',
              '--apikey',
              help='Your CloudOS API key',
              required=True)
@click.option('-c',
              '--cloudos-url',
              help=(f'The CloudOS url you are trying to access to. Default={CLOUDOS_URL}.'),
              default=CLOUDOS_URL)
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
@click.option('--page',
              help=('Response page to retrieve. Default=1.'),
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
@click.option('--profile', help='Profile to use from the config file', default=None)
@click.pass_context
def list_projects(ctx,
                  apikey,
                  cloudos_url,
                  workspace_id,
                  output_basename,
                  output_format,
                  all_fields,
                  page,
                  verbose,
                  disable_ssl_verification,
                  ssl_cert,
                  profile):
    """Collect all projects from a CloudOS workspace in CSV format."""
    profile = profile or ctx.default_map['project']['list']['profile']
    # Create a dictionary with required and non-required params
    required_dict = {
        'apikey': True,
        'workspace_id': True,
        'workflow_name': False,
        'project_name': False
    }
    # determine if the user provided all required parameters
    config_manager = ConfigurationProfile()
    apikey, cloudos_url, workspace_id, workflow_name, repository_platform, execution_platform, project_name = (
        config_manager.load_profile_and_validate_data(
            ctx,
            INIT_PROFILE,
            CLOUDOS_URL,
            profile=profile,
            required_dict=required_dict,
            apikey=apikey,
            cloudos_url=cloudos_url,
            workspace_id=workspace_id
        )
    )

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
    # Check if the user provided the --page option
    ctx = click.get_current_context()
    if ctx.get_parameter_source('page') == click.core.ParameterSource.DEFAULT:
        get_all = True
    else:
        get_all = False
        if not isinstance(page, int) or page < 1:
            raise ValueError('Please, use a positive integer (>= 1) for the --page parameter')
    my_projects_r = cl.get_project_list(workspace_id, verify_ssl, page=page, get_all=get_all)
    if len(my_projects_r) == 0:
        if ctx.get_parameter_source('page') == click.core.ParameterSource.DEFAULT:
            print('\t[Message] A total of 0 projects collected. This is likely because your workspace ' +
                  'has no projects created yet.')
        else:
            print('\t[Message] A total of 0 projects collected. This is likely because the --page you ' +
                  'requested does not exist. Please, try a smaller number for --page or collect all the ' +
                  'projects by not using --page parameter.')
    elif output_format == 'csv':
        my_projects = cl.process_project_list(my_projects_r, all_fields)
        my_projects.to_csv(outfile, index=False)
        print(f'\tProject list collected with a total of {my_projects.shape[0]} projects.')
    elif output_format == 'json':
        with open(outfile, 'w') as o:
            o.write(json.dumps(my_projects_r))
        print(f'\tProject list collected with a total of {len(my_projects_r)} projects.')
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
              help=(f'The CloudOS url you are trying to access to. Default={CLOUDOS_URL}.'),
              default=CLOUDOS_URL)
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
@click.option('--profile', help='Profile to use from the config file', default=None)
@click.pass_context
def cromwell_status(ctx,
                    apikey,
                    cromwell_token,
                    cloudos_url,
                    workspace_id,
                    verbose,
                    disable_ssl_verification,
                    ssl_cert,
                    profile):
    """Check Cromwell server status in CloudOS."""
    profile = profile or ctx.default_map['cromwell']['status']['profile']
    # Create a dictionary with required and non-required params
    required_dict = {
        'apikey': True,
        'workspace_id': True,
        'workflow_name': False,
        'project_name': False
    }
    # determine if the user provided all required parameters
    config_manager = ConfigurationProfile()
    apikey, cloudos_url, workspace_id, workflow_name, repository_platform, execution_platform, project_name = (
        config_manager.load_profile_and_validate_data(
            ctx,
            INIT_PROFILE,
            CLOUDOS_URL,
            profile=profile,
            required_dict=required_dict,
            cloudos_url=cloudos_url,
            workspace_id=workspace_id
        )
    )

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
              help=(f'The CloudOS url you are trying to access to. Default={CLOUDOS_URL}.'),
              default=CLOUDOS_URL)
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
@click.option('--profile', help='Profile to use from the config file', default=None)
@click.pass_context
def cromwell_restart(ctx,
                     apikey,
                     cromwell_token,
                     cloudos_url,
                     workspace_id,
                     wait_time,
                     verbose,
                     disable_ssl_verification,
                     ssl_cert,
                     profile):
    """Restart Cromwell server in CloudOS."""
    profile = profile or ctx.default_map['cromwell']['status']['profile']
    # Create a dictionary with required and non-required params
    required_dict = {
        'apikey': True,
        'workspace_id': True,
        'workflow_name': False,
        'project_name': False
    }
    # determine if the user provided all required parameters
    config_manager = ConfigurationProfile()
    apikey, cloudos_url, workspace_id, workflow_name, repository_platform, execution_platform, project_name = (
        config_manager.load_profile_and_validate_data(
            ctx,
            INIT_PROFILE,
            CLOUDOS_URL,
            profile=profile,
            required_dict=required_dict,
            cloudos_url=cloudos_url,
            workspace_id=workspace_id
        )
    )

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
              help=(f'The CloudOS url you are trying to access to. Default={CLOUDOS_URL}.'),
              default=CLOUDOS_URL)
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
@click.option('--profile', help='Profile to use from the config file', default=None)
@click.pass_context
def cromwell_stop(ctx,
                  apikey,
                  cromwell_token,
                  cloudos_url,
                  workspace_id,
                  verbose,
                  disable_ssl_verification,
                  ssl_cert,
                  profile):
    """Stop Cromwell server in CloudOS."""
    profile = profile or ctx.default_map['cromwell']['status']['profile']
    # Create a dictionary with required and non-required params
    required_dict = {
        'apikey': True,
        'workspace_id': True,
        'workflow_name': False,
        'project_name': False
    }
    # determine if the user provided all required parameters
    config_manager = ConfigurationProfile()
    apikey, cloudos_url, workspace_id, workflow_name, repository_platform, execution_platform, project_name = (
        config_manager.load_profile_and_validate_data(
            ctx,
            INIT_PROFILE,
            CLOUDOS_URL,
            profile=profile,
            required_dict=required_dict,
            cloudos_url=cloudos_url,
            workspace_id=workspace_id
        )
    )

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
              help=(f'The CloudOS url you are trying to access to. Default={CLOUDOS_URL}.'),
              default=CLOUDOS_URL)
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
@click.option('--profile', help='Profile to use from the config file', default=None)
@click.pass_context
def list_queues(ctx,
                apikey,
                cloudos_url,
                workspace_id,
                output_basename,
                output_format,
                all_fields,
                disable_ssl_verification,
                ssl_cert,
                profile):
    """Collect all available job queues from a CloudOS workspace."""
    profile = profile or ctx.default_map['queue']['list']['profile']
    # Create a dictionary with required and non-required params
    required_dict = {
        'apikey': True,
        'workspace_id': True,
        'workflow_name': False,
        'project_name': False
    }
    # determine if the user provided all required parameters
    config_manager = ConfigurationProfile()
    apikey, cloudos_url, workspace_id, workflow_name, repository_platform, execution_platform, project_name = (
        config_manager.load_profile_and_validate_data(
            ctx,
            INIT_PROFILE,
            CLOUDOS_URL,
            profile=profile,
            required_dict=required_dict,
            apikey=apikey,
            cloudos_url=cloudos_url,
            workspace_id=workspace_id
        )
    )

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


@configure.command('list-profiles')
def list_profiles():
    config_manager = ConfigurationProfile()
    config_manager.list_profiles()


@configure.command('remove-profile')
@click.option('--profile',
              help='Name of the profile. Not using this option will lead to profile named "deafults" being generated',
              required=True)
@click.pass_context
def remove_profile(ctx, profile):
    profile = profile or ctx.obj['profile']
    config_manager = ConfigurationProfile()
    config_manager.remove_profile(profile)


@bash.command('job')
@click.option('-k',
              '--apikey',
              help='Your CloudOS API key',
              required=True)
@click.option('--command',
              help='The command to run in the bash job.',
              required=True)
@click.option('-c',
              '--cloudos-url',
              help=(f'The CloudOS url you are trying to access to. Default={CLOUDOS_URL}.'),
              default=CLOUDOS_URL)
@click.option('--workspace-id',
              help='The specific CloudOS workspace id.',
              required=True)
@click.option('--project-name',
              help='The name of a CloudOS project.',
              required=True)
@click.option('--workflow-name',
              help='The name of a CloudOS workflow or pipeline.',
              required=True)
@click.option('-p',
              '--parameter',
              multiple=True,
              help=('A single parameter to pass to the job call. It should be in the ' +
                    'following form: parameter_name=parameter_value. E.g.: ' +
                    '-p --test=value or -p -test=value or -p test=value. You can use this option as many ' +
                    'times as parameters you want to include.'))
@click.option('--job-name',
              help='The name of the job. Default=new_job.',
              default='new_job')
@click.option('--do-not-save-logs',
              help=('Avoids process log saving. If you select this option, your job process ' +
                    'logs will not be stored.'),
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
@click.option('--cpus',
              help='The number of CPUs to use for the task\'s master node. Default=1.',
              type=int,
              default=1)
@click.option('--memory',
              help='The amount of memory, in GB, to use for the task\'s master node. Default=4.',
              type=int,
              default=4)
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
@click.option('--repository-platform',
              help='Name of the repository platform of the workflow. Default=github.',
              default='github')
@click.option('--execution-platform',
              help='Name of the execution platform implemented in your CloudOS. Default=aws.',
              default='aws')
@click.option('--cost-limit',
              help='Add a cost limit to your job. Default=30.0 (For no cost limit please use -1).',
              type=float,
              default=30.0)
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
@click.option('--profile', help='Profile to use from the config file', default=None)
@click.pass_context
def run_bash_job(ctx,
                 apikey,
                 command,
                 cloudos_url,
                 workspace_id,
                 project_name,
                 workflow_name,
                 parameter,
                 job_name,
                 do_not_save_logs,
                 job_queue,
                 instance_type,
                 instance_disk,
                 cpus,
                 memory,
                 storage_mode,
                 lustre_size,
                 wait_completion,
                 wait_time,
                 repository_platform,
                 execution_platform,
                 cost_limit,
                 request_interval,
                 disable_ssl_verification,
                 ssl_cert,
                 profile):
    """Run a bash job in CloudOS."""
    profile = profile or ctx.default_map['bash']['job']['profile']
    # Create a dictionary with required and non-required params
    required_dict = {
        'apikey': True,
        'workspace_id': True,
        'workflow_name': True,
        'project_name': True
    }

    # determine if the user provided all required parameters
    config_manager = ConfigurationProfile()
    apikey, cloudos_url, workspace_id, workflow_name, repository_platform, execution_platform, project_name = (
        config_manager.load_profile_and_validate_data(
            ctx,
            INIT_PROFILE,
            CLOUDOS_URL,
            profile=profile,
            required_dict=required_dict,
            apikey=apikey,
            cloudos_url=cloudos_url,
            workspace_id=workspace_id,
            workflow_name=workflow_name,
            repository_platform=repository_platform,
            execution_platform=execution_platform,
            project_name=project_name
        )
    )

    verify_ssl = ssl_selector(disable_ssl_verification, ssl_cert)

    if instance_type == 'NONE_SELECTED':
        if execution_platform == 'aws':
            instance_type = 'c5.xlarge'
        elif execution_platform == 'azure':
            instance_type = 'Standard_D4as_v4'
        else:
            instance_type = None

    j = jb.Job(cloudos_url, apikey, None, workspace_id, project_name, workflow_name,
               mainfile=None, importsfile=None,
               repository_platform=repository_platform, verify=verify_ssl)

    if execution_platform == 'azure' or execution_platform == 'hpc':
        batch = None
    else:
        batch = True

    if job_queue is not None:
        queue = Queue(cloudos_url=cloudos_url, apikey=apikey, cromwell_token=None,
                      workspace_id=workspace_id, verify=verify_ssl)
        # I have to add 'nextflow', other wise the job queue id is not found
        job_queue_id = queue.fetch_job_queue_id(workflow_type='nextflow', batch=batch,
                                                job_queue=job_queue)
    else:
        job_queue_id = None
    j_id = j.send_job(job_config=None,
                      parameter=parameter,
                      git_commit=None,
                      git_tag=None,
                      job_name=job_name,
                      resumable=False,
                      save_logs=do_not_save_logs,
                      batch=True,
                      job_queue_id=job_queue_id,
                      workflow_type='docker',
                      nextflow_profile=None,
                      nextflow_version=None,
                      instance_type=instance_type,
                      instance_disk=instance_disk,
                      storage_mode=storage_mode,
                      lustre_size=lustre_size,
                      execution_platform=execution_platform,
                      hpc_id=None,
                      cost_limit=cost_limit,
                      verify=verify_ssl,
                      command=command,
                      cpus=cpus,
                      memory=memory)

    print(f'\tYour assigned job id is: {j_id}\n')
    j_url = f'{cloudos_url}/app/advanced-analytics/analyses/{j_id}'
    if wait_completion:
        print('\tPlease, wait until job completion (max wait time of ' +
              f'{wait_time} seconds).\n')
        j_status = j.wait_job_completion(job_id=j_id,
                                         wait_time=wait_time,
                                         request_interval=request_interval,
                                         verbose=False,
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


if __name__ == "__main__":
    run_cloudos_cli()

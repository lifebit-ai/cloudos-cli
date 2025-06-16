#!/usr/bin/env python3

import rich_click as click
import cloudos_cli.jobs.job as jb
from cloudos_cli.clos import Cloudos
from cloudos_cli.import_wf.import_wf import ImportGitlab, ImportGithub
from cloudos_cli.queue.queue import Queue
from cloudos_cli.utils.errors import BadRequestException
import json
import time
import sys
from ._version import __version__
from cloudos_cli.configure.configure import ConfigurationProfile
from rich.console import Console
from rich.table import Table
from cloudos_cli.datasets import Datasets
from cloudos_cli.utils.resources import ssl_selector, format_bytes
from rich.style import Style


# GLOBAL VARS
JOB_COMPLETED = 'completed'
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

@click.group()
@click.version_option(__version__)
@click.pass_context
def run_cloudos_cli(ctx):
    """CloudOS python package: a package for interacting with CloudOS."""
    ctx.ensure_object(dict)
    if ctx.invoked_subcommand not in ['datasets'] and ctx.args and ctx.args[0] == 'ls':
        print(run_cloudos_cli.__doc__ + '\n')
        print('Version: ' + __version__ + '\n')
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
                'abort': shared_config,
                'status': shared_config,
                'list': shared_config,
                'details': shared_config
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
            },
            'datasets': {
                'ls': shared_config,
                'mv': shared_config
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
                'abort': shared_config,
                'status': shared_config,
                'list': shared_config,
                'details': shared_config
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
            },
            'datasets': {
                'ls': shared_config,
                'mv': shared_config
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


@run_cloudos_cli.group()
@click.pass_context
def datasets(ctx):
    """CloudOS datasets functionality."""
    if ctx.args and ctx.args[0] != 'ls':
        print(datasets.__doc__ + '\n')


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
                    'Default=22.10.8.'),
              type=click.Choice(['22.10.8', '24.04.4', '22.11.1-edge', 'latest']),
              default='22.10.8')
@click.option('--git-commit',
              help=('The git commit hash to run for ' +
                    'the selected pipeline. ' +
                    'If not specified it defaults to the last commit ' +
                    'of the default branch.'))
@click.option('--git-tag',
              help=('The tag to run for the selected pipeline. ' +
                    'If not specified it defaults to the last commit ' +
                    'of the default branch.'))
@click.option('--git-branch',
              help=('The branch to run for the selected pipeline. ' +
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
@click.option('--job-queue',
              help='Name of the job queue to use with a batch job.')
@click.option('--instance-type',
              help=('The type of compute instance to use as master node. ' +
                    'Default=c5.xlarge(aws)|Standard_D4as_v4(azure).'),
              default='NONE_SELECTED')
@click.option('--instance-disk',
              help='The disk space of the master node instance, in GB. Default=500.',
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
@click.option('--azure-worker-instance-type',
              help=('The worker node instance type to be used in azure. ' +
                    'Default=Standard_D4as_v4'),
              default='Standard_D4as_v4')
@click.option('--azure-worker-instance-disk',
              help='The disk size in GB for the worker node to be used in azure. Default=100',
              type=int,
              default=100)
@click.option('--azure-worker-instance-spot',
              help='Whether the azure worker nodes have to be spot instances or not.',
              is_flag=True)
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
        git_branch,
        job_name,
        resumable,
        do_not_save_logs,
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
        azure_worker_instance_type,
        azure_worker_instance_disk,
        azure_worker_instance_spot,
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
        batch = False
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
        if execution_platform == 'azure':
            print(f'[Message] The selected worflow \'{workflow_name}\' ' +
                  'is a CloudOS module. For these workflows, worker nodes '+
                  'are managed internally. For this reason, the options '+
                  'azure-worker-instance-type, azure-worker-instance-disk and '+
                  'azure-worker-instance-spot are not taking effect.')
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
    if nextflow_version != '22.10.8' and nextflow_version != '22.11.1-edge':
        print(f'[Warning] You have specified Nextflow version {nextflow_version}. This version requires the pipeline ' +
              'to be written in DSL2 and does not support DSL1.')
    print('\nExecuting run...')
    if workflow_type == 'nextflow':
        print(f'\tNextflow version: {nextflow_version}')
    j_id = j.send_job(job_config=job_config,
                      parameter=parameter,
                      is_module =is_module,
                      git_commit=git_commit,
                      git_tag=git_tag,
                      git_branch=git_branch,
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
                      azure_worker_instance_type=azure_worker_instance_type,
                      azure_worker_instance_disk=azure_worker_instance_disk,
                      azure_worker_instance_spot=azure_worker_instance_spot,
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


@job.command('details')
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
@click.option('--output-format',
              help='The desired display for the output, either directly in standard output or saved as file. Default=stdout.',
              type=click.Choice(['stdout', 'json'], case_sensitive=False),
              default='stdout')
@click.option('--output-basename',
              help=('Output file base name to save jobs details. ' +
                    'Default=job_details'),
              default='job_details',
              required=False)
@click.option('--parameters',
              help=('Whether to generate a ".config" file that can be used as input for --job-config parameter. ' +
                    'It will have the same basename as defined in "--output-basename". '),
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
def job_details(ctx,
               apikey,
               cloudos_url,
               job_id,
               output_format,
               output_basename,
               parameters,
               verbose,
               disable_ssl_verification,
               ssl_cert,
               profile):
    """Retrieve job details in CloudOS."""
    profile = profile or ctx.default_map['job']['details']['profile']
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

    print('Executing details...')
    verify_ssl = ssl_selector(disable_ssl_verification, ssl_cert)
    if verbose:
        print('\t...Preparing objects')
    cl = Cloudos(cloudos_url, apikey, None)
    if verbose:
        print('\tThe following Cloudos object was created:')
        print('\t' + str(cl) + '\n')
        print(f'\tSearching for job id: {job_id}')

    # check if the API gives a 403 error/forbidden error
    try:
        j_details = cl.get_job_status(job_id, verify_ssl)
    except BadRequestException as e:
        if '403' in str(e) or 'Forbidden' in str(e):
            print("[Error] API can only show job details of your own jobs, cannot see other user's job details.")
            sys.exit(1)
    j_details_h = json.loads(j_details.content)

    # Check if the job details contain parameters
    if j_details_h["parameters"] != []:
        param_kind_map = {
            'textValue': 'textValue',
            'arrayFileColumn': 'columnName',
            'globPattern': 'globPattern',
            'lustreFileSystem': 'fileSystem',
        }
        # there are different types of parameters, arrayFileColumn, globPattern, lustreFileSystem
        # get first the type of parameter, then the value based on the parameter kind
        concats = []
        for param in j_details_h["parameters"]:
            if param['parameterKind'] == 'dataItem':
                # For dataItem, we need to use specific nested keys
                concats.append(f"{param['prefix']}{param['name']}={param['dataItem']['item']['name']}")
            else:
                # For other parameter kinds, we use the appropriate key from param_kind_map
                concats.append(f"{param['prefix']}{param['name']}={param[param_kind_map[param['parameterKind']]]}")
        concat_string = '\n'.join(concats)
        # If the user requested to save the parameters in a config file
        if parameters:
            # Create a config file with the parameters
            config_filename = f"{output_basename}.config"
            with open(config_filename, 'w') as config_file:
                config_file.write("params {\n")
                for param in j_details_h["parameters"]:
                    config_file.write(f"\t{param['name']} = {param['textValue']}\n")
                config_file.write("}\n")
            print(f"\tJob parameters have been saved to '{config_filename}'")
    else:
        concat_string = 'No parameters provided'
        if parameters:
            print("\tNo parameters found in the job details, no config file will be created.")

    # Determine the execution platform based on jobType
    executors = {
        'nextflowAWS':'Batch AWS',
        'nextflowAzure': 'Batch Azure',
        'nextflowGcp': 'GCP',
        'nextflowHpc': 'HPC',
        'nextflowKubernetes': 'Kubernetes',
        'dockerAWS': 'Batch AWS',
        'cromwellAWS': 'Batch AWS'
    }
    execution_platform = executors.get(j_details_h["jobType"], "None")

    # revision
    if j_details_h["jobType"] == "dockerAWS":
        revision = j_details_h["revision"]["digest"]
    else:
        revision = j_details_h["revision"]["commit"]

    # Output the job details
    if output_format == 'stdout':
        console = Console()
        table = Table(title="Job Details")

        table.add_column("Field", style="cyan", no_wrap=True)
        table.add_column("Value", style="magenta", overflow="fold")

        table.add_row("Job Status", str(j_details_h["status"]))
        table.add_row("Parameters", concat_string)
        if j_details_h["jobType"] == "dockerAWS":
            table.add_row("Command", str(j_details_h["command"]))
        table.add_row("Revision", str(revision))
        table.add_row("Nextflow Version", str(j_details_h.get("nextflowVersion", "None")))
        table.add_row("Execution Platform", execution_platform)
        table.add_row("Profile", str(j_details_h.get("profile", "None")))
        table.add_row("Master Instance", str(j_details_h["masterInstance"]["usedInstance"]["type"]))
        if j_details_h["jobType"] == "nextflowAzure":
            try:
                table.add_row("Worker Node", str(j_details_h["azureBatch"]["vmType"]))
            except KeyError:
                table.add_row("Worker Node", "Not Specified")
        table.add_row("Storage", str(j_details_h["storageSizeInGb"]) + " GB")
        if j_details_h["jobType"] != "nextflowAzure":
            try:
                table.add_row("Job Queue ID", str(j_details_h["batch"]["jobQueue"]["name"]))
                table.add_row("Job Queue Name", str(j_details_h["batch"]["jobQueue"]["label"]))
            except KeyError:
                table.add_row("Job Queue", "Master Node")
        table.add_row("Accelerated File Staging", str(j_details_h.get("usesFusionFileSystem", "None")))
        table.add_row("Task Resources", f"{str(j_details_h['resourceRequirements']['cpu'])} CPUs, " +
                                        f"{str(j_details_h['resourceRequirements']['ram'])} GB RAM")

        console.print(table)
    else:
        # Create a JSON object with the key-value pairs
        job_details_json = {
            "Job Status": str(j_details_h["status"]),
            "Parameters": ','.join(concat_string.split()),
            "Revision": str(revision),
            "Nextflow Version": str(j_details_h.get("nextflowVersion", "None")),
            "Execution Platform": execution_platform,
            "Profile": str(j_details_h.get("profile", "None")),
            "Master Instance": str(j_details_h["masterInstance"]["usedInstance"]["type"]),
            "Storage": str(j_details_h["storageSizeInGb"]) + " GB",
            "Accelerated File Staging": str(j_details_h.get("usesFusionFileSystem", "None")),
            "Task Resources": f"{str(j_details_h['resourceRequirements']['cpu'])} CPUs, " + \
                              f"{str(j_details_h['resourceRequirements']['ram'])} GB RAM"

        }

        # Conditionally add the "Command" key if the jobType is "dockerAWS"
        if j_details_h["jobType"] == "dockerAWS":
            job_details_json["Command"] = str(j_details_h["command"])

        # Conditionally add the "Job Queue" key if the jobType is not "nextflowAzure"
        if j_details_h["jobType"] != "nextflowAzure":
            try:
                job_details_json["Job Queue ID"] = str(j_details_h["batch"]["jobQueue"]["name"])
                job_details_json["Job Queue Name"] = str(j_details_h["batch"]["jobQueue"]["label"])
            except KeyError:
                job_details_json["Job Queue"] = "Master Node"

        if j_details_h["jobType"] == "nextflowAzure":
            try:
                job_details_json["Worker Node"] = str(j_details_h["azureBatch"]["vmType"])
            except KeyError:
                job_details_json["Worker Node"] = "Not Specified"

        # Write the JSON object to a file
        with open(f"{output_basename}.json", "w") as json_file:
            json.dump(job_details_json, json_file, indent=4, ensure_ascii=False)
        print(f"\tJob details have been saved to '{output_basename}.json'")


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
              help=('The CloudOS url you are trying to access to. ' +
                    f'Default={CLOUDOS_URL}.'),
              default=CLOUDOS_URL)
@click.option('--workspace-id',
              help='The specific CloudOS workspace id.',
              required=True)
@click.option("--platform", type=click.Choice(["github", "gitlab"]),
              help=('Repository service where the workflow is located. Valid choices: github, gitlab. ' +
                    'Default=github'),
              default="github")
@click.option("--workflow-name", help="The name that the workflow will have in CloudOS.", required=True)
@click.option("-w", "--workflow-url", help="URL of the workflow repository.", required=True)
@click.option("-d", "--workflow-docs-link", help="URL to the documentation of the workflow.", default='')
@click.option("--cost-limit", help="Cost limit for the workflow. Default: $30 USD.", default=30)
@click.option("--workflow-description", help="Workflow description", default="")
@click.option('--disable-ssl-verification',
              help=('Disable SSL certificate verification. Please, remember that this option is ' +
                    'not generally recommended for security reasons.'),
              is_flag=True)
@click.option('--ssl-cert',
              help='Path to your SSL certificate file.')
@click.option('--profile', help='Profile to use from the config file', default=None)
@click.pass_context
def import_wf(ctx,
              apikey,
              cloudos_url,
              workspace_id,
              workflow_name,
              workflow_url,
              workflow_docs_link,
              cost_limit,
              workflow_description,
              platform,
              disable_ssl_verification,
              ssl_cert,
              profile):
    """
    Import workflows from supported repository providers.
    """
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
    repo_services = {"gitlab": ImportGitlab, "github": ImportGithub}
    repo_cls = repo_services[platform]
    repo_import = repo_cls(cloudos_url=cloudos_url, cloudos_apikey=apikey, workspace_id=workspace_id,
                             platform=platform, workflow_name=workflow_name, workflow_url=workflow_url,
                             workflow_docs_link=workflow_docs_link, cost_limit=cost_limit, workflow_description=workflow_description, verify=verify_ssl)
    workflow_id = repo_import.import_workflow()
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
              help=('The type of compute instance to use as master node. ' +
                    'Default=c5.xlarge(aws)|Standard_D4as_v4(azure).'),
              default='NONE_SELECTED')
@click.option('--instance-disk',
              help='The disk space of the master node instance, in GB. Default=500.',
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

    if job_queue is not None:
        batch = True
        queue = Queue(cloudos_url=cloudos_url, apikey=apikey, cromwell_token=None,
                      workspace_id=workspace_id, verify=verify_ssl)
        # I have to add 'nextflow', other wise the job queue id is not found
        job_queue_id = queue.fetch_job_queue_id(workflow_type='nextflow', batch=batch,
                                                job_queue=job_queue)
    else:
        job_queue_id = None
        batch = False
    j_id = j.send_job(job_config=None,
                      parameter=parameter,
                      git_commit=None,
                      git_tag=None,
                      git_branch=None,
                      job_name=job_name,
                      resumable=False,
                      save_logs=do_not_save_logs,
                      batch=batch,
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


@datasets.command(name="ls")
@click.argument("path", required=False, nargs=1)
@click.option('-k',
              '--apikey',
              help='Your CloudOS API key.',
              required=True)
@click.option('-c',
              '--cloudos-url',
              help=(f'The CloudOS url you are trying to access to. Default={CLOUDOS_URL}.'),
              default=CLOUDOS_URL,
              required=True)
@click.option('--workspace-id',
              help='The specific CloudOS workspace id.',
              required=True)
@click.option('--disable-ssl-verification',
              help=('Disable SSL certificate verification. Please, remember that this option is ' +
                    'not generally recommended for security reasons.'),
              is_flag=True)
@click.option('--ssl-cert',
              help='Path to your SSL certificate file.')
@click.option('--project-name',
              help='The name of a CloudOS project.')
@click.option('--profile', help='Profile to use from the config file', default=None)
@click.option('--details',
              help=('When selected, it prints the details of the listed files. ' +
                    'Details contains "Type", "Owner", "Size", "Last Updated", ' +
                    '"Filepath", "S3 Path".'),
              is_flag=True)
@click.pass_context
def list_files(ctx,
               apikey,
               cloudos_url,
               workspace_id,
               disable_ssl_verification,
               ssl_cert,
               project_name,
               profile,
               path,
               details):
    """List contents of a path within a CloudOS workspace dataset."""

    # fallback to ctx default if profile not specified
    profile = profile or ctx.default_map['datasets']['list'].get('profile')

    config_manager = ConfigurationProfile()
    required_dict = {
        'apikey': True,
        'workspace_id': True,
        'workflow_name': False,
        'project_name': False
    }

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
            workflow_name=None,
            repository_platform=None,
            execution_platform=None,
            project_name=project_name
        )
    )

    verify_ssl = ssl_selector(disable_ssl_verification, ssl_cert)

    datasets = Datasets(
        cloudos_url=cloudos_url,
        apikey=apikey,
        workspace_id=workspace_id,
        project_name=project_name,
        verify=verify_ssl,
        cromwell_token=None
    )

    try:
        result = datasets.list_folder_content(path)
        contents = result.get("contents") or result.get("datasets", [])
        if not contents:
            contents = result.get("files", []) + result.get("folders", [])

        if details:
            console = Console(width=None)  # Avoid terminal width truncation

            table = Table(show_header=True, header_style="bold white")
            table.add_column("Type", style="cyan", no_wrap=True)
            table.add_column("Owner", style="white")
            table.add_column("Size", style="magenta")
            table.add_column("Last Updated", style="green")
            table.add_column("Filepath", style="bold", overflow="fold")
            table.add_column("S3 Path", style="dim", no_wrap=False, overflow="fold", ratio=2)

            for item in contents:
                is_folder = "folderType" in item or item.get("isDir", False)
                type_ = "folder" if is_folder else "file"

                user = item.get("user")
                if isinstance(user, dict):
                    name = user.get("name", "").strip()
                    surname = user.get("surname", "").strip()
                    if name and surname:
                        owner = f"{name} {surname}"
                    elif name:
                        owner = name
                    elif surname:
                        owner = surname
                    else:
                        owner = "-"
                else:
                    owner = "-"

                raw_size = item.get("sizeInBytes", item.get("size"))
                size = format_bytes(raw_size) if not is_folder and raw_size is not None else "-"

                updated = item.get("updatedAt") or item.get("lastModified", "-")
                filepath = item.get("name", "-")

                if is_folder:
                    s3_bucket = item.get("s3BucketName")
                    s3_key = item.get("s3Prefix")
                    s3_path = f"s3://{s3_bucket}/{s3_key}" if s3_bucket and s3_key else "-"
                else:
                    s3_bucket = item.get("s3BucketName")
                    s3_key = item.get("s3ObjectKey") or item.get("s3Prefix")
                    s3_path = f"s3://{s3_bucket}/{s3_key}" if s3_bucket and s3_key else "-"

                style = Style(color="blue", underline=True) if is_folder else None
                table.add_row(type_, owner, size, updated, filepath, s3_path, style=style)

            console.print(table)

        else:
            console = Console()
            for item in contents:
                name = item.get("name", "")
                is_folder = item.get("folderType") or item.get("isDir")
                if is_folder:
                    console.print(f"[blue underline]{name}[/]")
                else:
                    console.print(name)

    except Exception as e:
        click.echo(f"[ERROR] {str(e)}", err=True)


@datasets.command(name="mv")
@click.argument("source_path", required=True)
@click.argument("destination_path", required=True)
@click.option('-k', '--apikey', required=True, help='Your CloudOS API key.')
@click.option('-c', '--cloudos-url', default=CLOUDOS_URL, required=False, help='The CloudOS URL.')
@click.option('--workspace-id', required=True, help='The CloudOS workspace ID.')
@click.option('--project-name', required=True, help='The source project name.')
@click.option('--destination-project-name', required=False, help='The destination project name. Defaults to the source project.')
@click.option('--disable-ssl-verification', is_flag=True, help='Disable SSL certificate verification.')
@click.option('--ssl-cert', help='Path to your SSL certificate file.')
@click.option('--profile', default=None, help='Profile to use from the config file.')
@click.pass_context
def move_files(ctx, source_path, destination_path, apikey, cloudos_url, workspace_id,
               project_name, destination_project_name,
               disable_ssl_verification, ssl_cert, profile):
    """
    Move a file or folder from a source path to a destination path within or across CloudOS projects.

    SOURCE_PATH [path] : the full path to the file or folder to move. It must be a 'Data' folder path. E.g.: 'Data/folderA/file.txt'\n
    DESTINATION_PATH [path]: the full path to the destination folder. It must be a 'Data' folder path. E.g.: 'Data/folderB'
    """

    profile = profile or ctx.default_map['datasets']['move'].get('profile')
    destination_project_name = destination_project_name or project_name

    # Validate destination constraint
    if not destination_path.strip("/").startswith("Data/") and destination_path.strip("/") != "Data":
        click.echo("[ERROR] Destination path must begin with 'Data/' or be 'Data'.", err=True)
        sys.exit(1)
    if not source_path.strip("/").startswith("Data/") and source_path.strip("/") != "Data":
        click.echo("[ERROR] SOURCE_PATH must start with  'Data/' or be 'Data'.", err=True)
        sys.exit(1)
    click.echo('Loading configuration profile')
    # Load configuration profile
    config_manager = ConfigurationProfile()
    required_dict = {
        'apikey': True,
        'workspace_id': True,
        'workflow_name': False,
        'project_name': True
    }

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
            workflow_name=None,
            repository_platform=None,
            execution_platform=None,
            project_name=project_name
        )
    )

    verify_ssl = ssl_selector(disable_ssl_verification, ssl_cert)
    # Initialize Datasets clients
    source_client = Datasets(
        cloudos_url=cloudos_url,
        apikey=apikey,
        workspace_id=workspace_id,
        project_name=project_name,
        verify=verify_ssl,
        cromwell_token=None
    )

    dest_client = Datasets(
        cloudos_url=cloudos_url,
        apikey=apikey,
        workspace_id=workspace_id,
        project_name=destination_project_name,
        verify=verify_ssl,
        cromwell_token=None
    )
    click.echo('Checking source path')
    # === Resolve Source Item ===
    source_parts = source_path.strip("/").split("/")
    source_parent_path = "/".join(source_parts[:-1]) if len(source_parts) > 1 else None
    source_item_name = source_parts[-1]

    try:
        source_contents = source_client.list_folder_content(source_parent_path)
    except Exception as e:
        click.echo(f"[ERROR] Could not resolve source path '{source_path}': {str(e)}", err=True)
        sys.exit(1)

    found_source = None
    for collection in ["files", "folders"]:
        for item in source_contents.get(collection, []):
            if item.get("name") == source_item_name:
                found_source = item
                break
        if found_source:
            break
    if not found_source:
        click.echo(f"[ERROR] Item '{source_item_name}' not found in '{source_parent_path or '[project root]'}'", err=True)
        sys.exit(1)

    source_id = found_source["_id"]
    source_kind = "Folder" if "folderType" in found_source else "File"
    click.echo("Checking destination path")
    # === Resolve Destination Folder ===
    dest_parts = destination_path.strip("/").split("/")
    dest_folder_name = dest_parts[-1]
    dest_parent_path = "/".join(dest_parts[:-1]) if len(dest_parts) > 1 else None

    try:
        dest_contents = dest_client.list_folder_content(dest_parent_path)
        match = next((f for f in dest_contents.get("folders", []) if f.get("name") == dest_folder_name), None)
        if not match:
            raise ValueError(f"Could not resolve destination folder '{destination_path}'")

        target_id = match["_id"]
        folder_type = match.get("folderType")
        # Normalize kind: top-level datasets are kind=Dataset, all other folders are kind=Folder
        if folder_type in ("VirtualFolder", "S3Folder", "Folder"):
            target_kind = "Folder"
        elif isinstance(folder_type, bool) and folder_type:  # legacy dataset structure
            target_kind = "Dataset"
        else:
            raise ValueError(f"Unrecognized folderType '{folder_type}' for destination '{destination_path}'")

    except Exception as e:
        click.echo(f"[ERROR] Could not resolve destination path '{destination_path}': {str(e)}", err=True)
        sys.exit(1)
    click.echo(f"Moving {source_kind} '{source_item_name}' to '{destination_path}' in project '{destination_project_name} ...")
    # === Perform Move ===
    try:
        response = source_client.move_files_and_folders(
            source_id=source_id,
            source_kind=source_kind,
            target_id=target_id,
            target_kind=target_kind
        )
        if response.ok:
           click.secho(f"[SUCCESS] {source_kind} '{source_item_name}' moved to '{destination_path}' in project '{destination_project_name}'.", fg="green", bold=True)
        else:
            click.echo(f"[ERROR] Move failed: {response.status_code} - {response.text}", err=True)
            sys.exit(1)
    except Exception as e:
        click.echo(f"[ERROR] Move operation failed: {str(e)}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    run_cloudos_cli()

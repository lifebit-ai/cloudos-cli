#!/usr/bin/env python3

import rich_click as click
import cloudos_cli.jobs.job as jb
from cloudos_cli.clos import Cloudos
from cloudos_cli.import_wf.import_wf import ImportWorflow
from cloudos_cli.queue.queue import Queue
from cloudos_cli.utils.errors import BadRequestException
import json
import time
import sys
import traceback
from ._version import __version__
from cloudos_cli.configure.configure import ConfigurationProfile
from rich.console import Console
from rich.table import Table
from cloudos_cli.datasets import Datasets
from cloudos_cli.procurement import Images
from cloudos_cli.utils.resources import ssl_selector, format_bytes
from rich.style import Style
from cloudos_cli.utils.array_job import generate_datasets_for_project
from cloudos_cli.utils.details import get_path
from cloudos_cli.link import Link


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


def handle_exception(show_traceback=False):
    """Custom exception handler for CloudOS CLI"""
    def exception_handler(exc_type, exc_value, exc_traceback):
        # Handle keyboard interrupt gracefully
        if issubclass(exc_type, KeyboardInterrupt):
            sys.exit(1)
        
        if show_traceback:
            # Show full traceback for debugging
            traceback.print_exception(exc_type, exc_value, exc_traceback)
        else:
            # Show only the error message
            click.echo(click.style(f"Error: {exc_value}", fg='red'), err=True)
        
        sys.exit(1)
    
    return exception_handler


@click.group()
@click.option('--debug', is_flag=True, help='Show detailed error information and tracebacks')
@click.version_option(__version__)
@click.pass_context
def run_cloudos_cli(ctx, debug):
    """CloudOS python package: a package for interacting with CloudOS."""
    ctx.ensure_object(dict)
    ctx.obj['debug'] = debug
    
    # Set up custom exception handling based on debug flag
    if not debug:
        sys.excepthook = handle_exception(show_traceback=False)
    else:
        sys.excepthook = handle_exception(show_traceback=True)
    
    if ctx.invoked_subcommand not in ['datasets']:
        print(run_cloudos_cli.__doc__ + '\n')
        print('Version: ' + __version__ + '\n')
    config_manager = ConfigurationProfile()
    profile_to_use = config_manager.determine_default_profile()
    if profile_to_use is None:
        console = Console()
        console.print(
            "[bold yellow][Warning] No profile found. Please create one with \"cloudos configure\"."
        )
        shared_config = dict({
            'apikey': '',
            'cloudos_url': CLOUDOS_URL,
            'workspace_id': '',
            'procurement_id': '',
            'project_name': '',
            'workflow_name': '',
            'repository_platform': 'github',
            'execution_platform': 'aws',
            'profile': INIT_PROFILE,
            'session_id': '',
        })
        ctx.default_map = dict({
            'job': {
                'run': shared_config,
                'abort': shared_config,
                'status': shared_config,
                'list': shared_config,
                'logs': shared_config,
                'results': shared_config,
                'details': shared_config,
                'clone': shared_config
            },
            'workflow': {
                'list': shared_config,
                'import': shared_config
            },
            'project': {
                'list': shared_config,
                'create': shared_config
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
                'job': shared_config,
                'array-job': shared_config
            },
            'datasets': {
                'ls': shared_config,
                'mv': shared_config,
                'rename': shared_config,
                'cp': shared_config,
                'link': shared_config,
                'mkdir': shared_config,
                'rm': shared_config
            },
            'procurement': {
                'images': {
                    'ls': shared_config,
                    'set': shared_config,
                    'reset': shared_config
                }
            }
        })
    else:
        profile_data = config_manager.load_profile(profile_name=profile_to_use)
        shared_config = dict({
            'apikey': profile_data.get('apikey', ""),
            'cloudos_url': profile_data.get('cloudos_url', ""),
            'workspace_id': profile_data.get('workspace_id', ""),
            'procurement_id': profile_data.get('procurement_id', ""),
            'project_name': profile_data.get('project_name', ""),
            'workflow_name': profile_data.get('workflow_name', ""),
            'repository_platform': profile_data.get('repository_platform', ""),
            'execution_platform': profile_data.get('execution_platform', ""),
            'profile': profile_to_use,
            'session_id': profile_data.get('session_id', "")
        })
        ctx.default_map = dict({
            'job': {
                'run': shared_config,
                'abort': shared_config,
                'status': shared_config,
                'list': shared_config,
                'logs': shared_config,
                'results': shared_config,
                'details': shared_config,
                'clone': shared_config
            },
            'workflow': {
                'list': shared_config,
                'import': shared_config
            },
            'project': {
                'list': shared_config,
                'create': shared_config
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
                'job': shared_config,
                'array-job': shared_config
            },
            'datasets': {
                'ls': shared_config,
                'mv': shared_config,
                'rename': shared_config,
                'cp': shared_config,
                'link': shared_config,
                'mkdir': shared_config,
                'rm': shared_config
            },
            'procurement': {
                'images': {
                    'ls': shared_config,
                    'set': shared_config,
                    'reset': shared_config
                }
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
    """CloudOS project functionality: list and create projects in CloudOS."""
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
def procurement():
    """CloudOS procurement functionality."""
    print(procurement.__doc__ + '\n')


@procurement.group()
def images():
    """CloudOS procurement images functionality."""


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
              default=CLOUDOS_URL,
              required=True)
@click.option('--workspace-id',
              help='The specific CloudOS workspace id.',
              required=True)
@click.option('--project-name',
              help='The name of a CloudOS project.',
              required=True)
@click.option('--workflow-name',
              help='The name of a CloudOS workflow or pipeline.',
              required=True)
@click.option('--last',
              help=('When the workflows are duplicated, use the latest imported workflow (by date).'),
              is_flag=True)
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
@click.option('--repository-platform', type=click.Choice(["github", "gitlab", "bitbucketServer"]),
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
        last,
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
        'project_name': True,
        'procurement_id': False
    }
    # determine if the user provided all required parameters
    config_manager = ConfigurationProfile()
    user_options = (
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
    apikey = user_options['apikey']
    cloudos_url = user_options['cloudos_url']
    workspace_id = user_options['workspace_id']
    workflow_name = user_options['workflow_name']
    repository_platform = user_options['repository_platform']
    execution_platform = user_options['execution_platform']
    project_name = user_options['project_name']

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
    workflow_type = cl.detect_workflow(workflow_name, workspace_id, verify_ssl, last)
    is_module = cl.is_module(workflow_name, workspace_id, verify_ssl, last)
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
               repository_platform=repository_platform, verify=verify_ssl, last=last)
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
                  'is a CloudOS module. For these workflows, worker nodes ' +
                  'are managed internally. For this reason, the options ' +
                  'azure-worker-instance-type, azure-worker-instance-disk and ' +
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
                      is_module=is_module,
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
              default=CLOUDOS_URL,
              required=True)
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
        'project_name': False,
        'procurement_id': False
    }
    # determine if the user provided all required parameters
    config_manager = ConfigurationProfile()
    user_options = (
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
    apikey = user_options['apikey']
    cloudos_url = user_options['cloudos_url']

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


@job.command('logs')
@click.option('-k',
              '--apikey',
              help='Your CloudOS API key',
              required=True)
@click.option('-c',
              '--cloudos-url',
              help=(f'The CloudOS url you are trying to access to. Default={CLOUDOS_URL}.'),
              default=CLOUDOS_URL,
              required=True)
@click.option('--workspace-id',
              help='The specific CloudOS workspace id.',
              required=True)
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
def job_logs(ctx,
             apikey,
             cloudos_url,
             workspace_id,
             job_id,
             verbose,
             disable_ssl_verification,
             ssl_cert,
             profile):
    """Get the path to the logs of a specified job."""
    profile = profile or ctx.default_map['job']['logs']['profile']
    # Create a dictionary with required and non-required params
    required_dict = {
        'apikey': True,
        'workspace_id': True,
        'workflow_name': False,
        'project_name': False,
        'procurement_id': False
    }
    # determine if the user provided all required parameters
    config_manager = ConfigurationProfile()
    user_options = (
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
    apikey = user_options['apikey']
    cloudos_url = user_options['cloudos_url']
    workspace_id = user_options['workspace_id']

    print('Executing logs...')
    verify_ssl = ssl_selector(disable_ssl_verification, ssl_cert)
    if verbose:
        print('\t...Preparing objects')
    cl = Cloudos(cloudos_url, apikey, None)
    if verbose:
        print('\tThe following Cloudos object was created:')
        print('\t' + str(cl) + '\n')
        print(f'\tSearching for job id: {job_id}')
    logs = cl.get_job_logs(job_id, workspace_id, verify_ssl)
    for name, path in logs.items():
        print(f"{name}: {path}\n")


@job.command('results')
@click.option('-k',
              '--apikey',
              help='Your CloudOS API key',
              required=True)
@click.option('-c',
              '--cloudos-url',
              help=(f'The CloudOS url you are trying to access to. Default={CLOUDOS_URL}.'),
              default=CLOUDOS_URL,
              required=True)
@click.option('--workspace-id',
              help='The specific CloudOS workspace id.',
              required=True)
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
def job_results(ctx,
                apikey,
                cloudos_url,
                workspace_id,
                job_id,
                verbose,
                disable_ssl_verification,
                ssl_cert,
                profile):
    """Get the path to the results of a specified job."""
    profile = profile or ctx.default_map['job']['results']['profile']
    # Create a dictionary with required and non-required params
    required_dict = {
        'apikey': True,
        'workspace_id': True,
        'workflow_name': False,
        'project_name': False,
        'procurement_id': False
    }
    # determine if the user provided all required parameters
    config_manager = ConfigurationProfile()
    user_options = (
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
    apikey = user_options['apikey']
    cloudos_url = user_options['cloudos_url']
    workspace_id = user_options['workspace_id']

    print('Executing results...')
    verify_ssl = ssl_selector(disable_ssl_verification, ssl_cert)
    if verbose:
        print('\t...Preparing objects')
    cl = Cloudos(cloudos_url, apikey, None)
    if verbose:
        print('\tThe following Cloudos object was created:')
        print('\t' + str(cl) + '\n')
        print(f'\tSearching for job id: {job_id}')
    logs = cl.get_job_results(job_id, workspace_id, verify_ssl)
    for name, path in logs.items():
        print(f"{name}: {path}\n")


@job.command('details')
@click.option('-k',
              '--apikey',
              help='Your CloudOS API key',
              required=True)
@click.option('-c',
              '--cloudos-url',
              help=(f'The CloudOS url you are trying to access to. Default={CLOUDOS_URL}.'),
              default=CLOUDOS_URL,
              required=True)
@click.option('--job-id',
              help='The job id in CloudOS to search for.',
              required=True)
@click.option('--output-format',
              help=('The desired display for the output, either directly in standard output or saved as file. ' +
                    'Default=stdout.'),
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
        'project_name': False,
        'procurement_id': False
    }
    # determine if the user provided all required parameters
    config_manager = ConfigurationProfile()
    user_options = (
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
    apikey = user_options['apikey']
    cloudos_url = user_options['cloudos_url']
    execution_platform = user_options['execution_platform']

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

    # Determine the execution platform based on jobType
    executors = {
        'nextflowAWS': 'Batch AWS',
        'nextflowAzure': 'Batch Azure',
        'nextflowGcp': 'GCP',
        'nextflowHpc': 'HPC',
        'nextflowKubernetes': 'Kubernetes',
        'dockerAWS': 'Batch AWS',
        'cromwellAWS': 'Batch AWS'
    }
    execution_platform = executors.get(j_details_h["jobType"], "None")
    storage_provider = "s3://" if execution_platform == "Batch AWS" else "az://"

    # Check if the job details contain parameters
    if j_details_h["parameters"] != []:
        param_kind_map = {
            'textValue': 'textValue',
            'arrayFileColumn': 'columnName',
            'globPattern': 'globPattern',
            'lustreFileSystem': 'fileSystem',
            'dataItem': 'dataItem'
        }
        # there are different types of parameters, arrayFileColumn, globPattern, lustreFileSystem
        # get first the type of parameter, then the value based on the parameter kind
        concats = []
        for param in j_details_h["parameters"]:
            concats.append(f"{param['prefix']}{param['name']}={get_path(param, param_kind_map, execution_platform, storage_provider, 'asis')}")
        concat_string = '\n'.join(concats)

        # If the user requested to save the parameters in a config file
        if parameters:
            # Create a config file with the parameters
            config_filename = f"{output_basename}.config"
            with open(config_filename, 'w') as config_file:
                config_file.write("params {\n")
                for param in j_details_h["parameters"]:
                    config_file.write(f"\t{param['name']} = {get_path(param, param_kind_map, execution_platform, storage_provider)}\n")
                config_file.write("}\n")
            print(f"\tJob parameters have been saved to '{config_filename}'")
    else:
        concat_string = 'No parameters provided'
        if parameters:
            print("\tNo parameters found in the job details, no config file will be created.")

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
        # when the job is just running this value might not be present
        master_instance = j_details_h.get("masterInstance", {})
        used_instance = master_instance.get("usedInstance", {})
        instance_type = used_instance.get("type", "N/A")
        table.add_row("Master Instance", str(instance_type))
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
            "Storage": str(j_details_h["storageSizeInGb"]) + " GB",
            "Accelerated File Staging": str(j_details_h.get("usesFusionFileSystem", "None")),
            "Task Resources": f"{str(j_details_h['resourceRequirements']['cpu'])} CPUs, " +
                              f"{str(j_details_h['resourceRequirements']['ram'])} GB RAM"

        }

        # when the job is just running this value might not be present
        master_instance = j_details_h.get("masterInstance", {})
        used_instance = master_instance.get("usedInstance", {})
        instance_type = used_instance.get("type", "N/A")
        job_details_json["Master Instance"] = str(instance_type)

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
              default=CLOUDOS_URL,
              required=True)
@click.option('--workspace-id',
              help='The specific CloudOS workspace id.',
              required=True)
@click.option('--output-basename',
              help=('Output file base name to save jobs list. ' +
                    'Default=joblist'),
              default='joblist',
              required=False)
@click.option('--output-format',
              help='The desired file format (file extension) for the output. For json option --all-fields will be automatically set to True. Default=csv.',
              type=click.Choice(['csv', 'json'], case_sensitive=False),
              default='csv')
@click.option('--all-fields',
              help=('Whether to collect all available fields from jobs or ' +
                    'just the preconfigured selected fields. Only applicable ' +
                    'when --output-format=csv. Automatically enabled for json output.'),
              is_flag=True)
@click.option('--last-n-jobs',
              help=("The number of last workspace jobs to retrieve. You can use 'all' to " +
                    "retrieve all workspace jobs. Default=30."),
              default='30')
@click.option('--page',
              help=('Response page to retrieve. If --last-n-jobs is set, then --page ' +
                    'value corresponds to the first page to retrieve. Default=1.'),
              type=int,
              default=1)
@click.option('--archived',
              help=('When this flag is used, only archived jobs list is collected.'),
              is_flag=True)
@click.option('--filter-status',
              help='Filter jobs by status (e.g., completed, running, failed, aborted).')
@click.option('--filter-job-name',
              help='Filter jobs by job name ( case insensitive ).')
@click.option('--filter-project',
              help='Filter jobs by project name.')
@click.option('--filter-workflow',
              help='Filter jobs by workflow/pipeline name.')
@click.option('--last',
              help=('When workflows are duplicated, use the latest imported workflow (by date).'),
              is_flag=True)
@click.option('--filter-job-id',
              help='Filter jobs by specific job ID.')
@click.option('--filter-only-mine',
              help='Filter to show only jobs belonging to the current user.',
              is_flag=True)
@click.option('--filter-queue',
              help='Filter jobs by queue name. Only applies to jobs running in batch environment. Non-batch jobs are preserved in results.')
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
              filter_status,
              filter_job_name,
              filter_project,
              filter_workflow,
              last,
              filter_job_id,
              filter_only_mine,
              #filter_owner,
              filter_queue,
              verbose,
              disable_ssl_verification,
              ssl_cert,
              profile):
    """Collect workspace jobs from a CloudOS workspace in CSV or JSON format."""
    profile = profile or ctx.default_map['job']['list']['profile']
    # Create a dictionary with required and non-required params
    required_dict = {
        'apikey': True,
        'workspace_id': True,
        'workflow_name': False,
        'project_name': False,
        'procurement_id': False
    }
    # determine if the user provided all required parameters
    config_manager = ConfigurationProfile()
    user_options = (
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
    apikey = user_options['apikey']
    cloudos_url = user_options['cloudos_url']
    workspace_id = user_options['workspace_id']

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

    my_jobs_r = cl.get_job_list(workspace_id, last_n_jobs, page, archived, verify_ssl,
                                filter_status=filter_status,
                                filter_job_name=filter_job_name,
                                filter_project=filter_project,
                                filter_workflow=filter_workflow,
                                filter_job_id=filter_job_id,
                                filter_only_mine=filter_only_mine,
                                filter_queue=filter_queue,
                                last=last)
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
        cl.save_job_list_to_csv(my_jobs, outfile)
    elif output_format == 'json':
        with open(outfile, 'w') as o:
            o.write(json.dumps(my_jobs_r))
        print(f'\tJob list collected with a total of {len(my_jobs_r)} jobs.')
        print(f'\tJob list saved to {outfile}')
    else:
        raise ValueError('Unrecognised output format. Please use one of [csv|json]')


@job.command('abort')
@click.option('-k',
              '--apikey',
              help='Your CloudOS API key',
              required=True)
@click.option('-c',
              '--cloudos-url',
              help=(f'The CloudOS url you are trying to access to. Default={CLOUDOS_URL}.'),
              default=CLOUDOS_URL,
              required=True)
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
        'project_name': False,
        'procurement_id': False
    }
    # determine if the user provided all required parameters
    config_manager = ConfigurationProfile()
    user_options = (
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
    apikey = user_options['apikey']
    cloudos_url = user_options['cloudos_url']
    workspace_id = user_options['workspace_id']

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


@job.command('clone')
@click.option('-k',
              '--apikey',
              help='Your CloudOS API key',
              required=True)
@click.option('-c',
              '--cloudos-url',
              help=(f'The CloudOS url you are trying to access to. Default={CLOUDOS_URL}.'),
              default=CLOUDOS_URL,
              required=True)
@click.option('--workspace-id',
              help='The specific CloudOS workspace id.',
              required=True)
@click.option('--project-name',
              help='The name of a CloudOS project.')
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
              type=click.Choice(['22.10.8', '24.04.4', '22.11.1-edge', 'latest']))
@click.option('--git-branch',
              help=('The branch to run for the selected pipeline. ' +
                    'If not specified it defaults to the last commit ' +
                    'of the default branch.'))
@click.option('--job-name',
              help='The name of the job. If not set, will take the name of the cloned job.')
@click.option('--do-not-save-logs',
              help=('Avoids process log saving. If you select this option, your job process ' +
                    'logs will not be stored.'),
              is_flag=True)
@click.option('--job-queue',
              help=('Name of the job queue to use with a batch job. ' +
                   'In Azure workspaces, this option is ignored.'))
@click.option('--instance-type',
              help=('The type of compute instance to use as master node. ' +
                    'Default=c5.xlarge(aws)|Standard_D4as_v4(azure).'))
@click.option('--cost-limit',
              help='Add a cost limit to your job. Default=30.0 (For no cost limit please use -1).',
              type=float)
@click.option('--job-id',
              help='The CloudOS job id of the job to be cloned.',
              required=True)
@click.option('--accelerate-file-staging',
              help='Enables AWS S3 mountpoint for quicker file staging.',
              is_flag=True)
@click.option('--resumable',
              help='Whether to make the job able to be resumed or not.',
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
@click.option('--profile',
              help='Profile to use from the config file',
              default=None)
@click.pass_context
def clone_job(ctx,
              apikey,
              cloudos_url,
              workspace_id,
              project_name,
              parameter,
              nextflow_profile,
              nextflow_version,
              git_branch,
              job_name,
              do_not_save_logs,
              job_queue,
              instance_type,
              cost_limit,
              job_id,
              accelerate_file_staging,
              resumable,
              verbose,
              disable_ssl_verification,
              ssl_cert,
              profile):
    """Clone an existing job with optional parameter overrides."""
    profile = profile or ctx.default_map['job']['clone']['profile']

    # Create a dictionary with required and non-required params
    required_dict = {
        'apikey': True,
        'workspace_id': True,
        'workflow_name': False,
        'project_name': False,
        'procurement_id': False
    }

    # Determine if the user provided all required parameters
    config_manager = ConfigurationProfile()
    user_options = (
        config_manager.load_profile_and_validate_data(
            ctx,
            INIT_PROFILE,
            CLOUDOS_URL,
            profile=profile,
            required_dict=required_dict,
            apikey=apikey,
            cloudos_url=cloudos_url,
            workspace_id=workspace_id,
            project_name=project_name
        )
    )
    apikey = user_options['apikey']
    cloudos_url = user_options['cloudos_url']
    workspace_id = user_options['workspace_id']

    verify_ssl = ssl_selector(disable_ssl_verification, ssl_cert)

    print('Cloning job...')
    if verbose:
        print('\t...Preparing objects')

    # Create Job object (set dummy values for project_name and workflow_name, since they come from the cloned job)
    job_obj = jb.Job(cloudos_url, apikey, None, workspace_id, None, None, workflow_id=1234, project_id="None",
               mainfile=None, importsfile=None,verify=verify_ssl)

    if verbose:
        print('\tThe following Job object was created:')
        print('\t' + str(job_obj) + '\n')
        print(f'\tCloning job {job_id} in workspace: {workspace_id}')

    try:
        # Clone the job with provided overrides
        cloned_job_id = job_obj.clone_job(
            source_job_id=job_id,
            queue_name=job_queue,
            cost_limit=cost_limit,
            master_instance=instance_type,
            job_name=job_name,
            nextflow_version=nextflow_version,
            branch=git_branch,
            profile=nextflow_profile,
            do_not_save_logs=do_not_save_logs,
            use_fusion=accelerate_file_staging,
            resumable=resumable,
            # only when explicitly setting --project-name will be overridden, else using the original project
            project_name=project_name if ctx.get_parameter_source("project_name") == click.core.ParameterSource.COMMANDLINE else None,
            parameters=list(parameter) if parameter else None,
            verify=verify_ssl
        )
        if verbose:
            print(f'\tCloned job ID: {cloned_job_id}')

        print(f"Job successfully cloned. New job ID: {cloned_job_id}")

    except BadRequestException as e:
        if verbose:
            print(f'\tError details: {e}')
        raise ValueError(f"Failed to clone job: {e}")
    except Exception as e:
        if verbose:
            print(f'\tError details: {e}')
        raise ValueError(f"An error occurred while cloning the job: {e}")


@workflow.command('list')
@click.option('-k',
              '--apikey',
              help='Your CloudOS API key',
              required=True)
@click.option('-c',
              '--cloudos-url',
              help=(f'The CloudOS url you are trying to access to. Default={CLOUDOS_URL}.'),
              default=CLOUDOS_URL,
              required=True)
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
        'project_name': False,
        'procurement_id': False
    }
    # determine if the user provided all required parameters
    config_manager = ConfigurationProfile()
    user_options = (
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
    apikey = user_options['apikey']
    cloudos_url = user_options['cloudos_url']
    workspace_id = user_options['workspace_id']

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
              default=CLOUDOS_URL,
              required=True)
@click.option('--workspace-id',
              help='The specific CloudOS workspace id.',
              required=True)
@click.option('--repository-platform', type=click.Choice(["github", "gitlab", "bitbucketServer"]),
              help='Name of the repository platform of the workflow. Default=github.',
              default='github')
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
              repository_platform,
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
        'workflow_name': True,
        'project_name': False,
        'procurement_id': False
    }
    # determine if the user provided all required parameters
    config_manager = ConfigurationProfile()
    user_options = (
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
            repository_platform=repository_platform
        )
    )
    apikey = user_options['apikey']
    cloudos_url = user_options['cloudos_url']
    workspace_id = user_options['workspace_id']
    workflow_name = user_options['workflow_name']
    repository_platform = user_options['repository_platform']

    verify_ssl = ssl_selector(disable_ssl_verification, ssl_cert)
    repo_import = ImportWorflow(
        cloudos_url=cloudos_url, cloudos_apikey=apikey, workspace_id=workspace_id, platform=repository_platform,
        workflow_name=workflow_name, workflow_url=workflow_url, workflow_docs_link=workflow_docs_link,
        cost_limit=cost_limit, workflow_description=workflow_description, verify=verify_ssl
    )
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
              default=CLOUDOS_URL,
              required=True)
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
        'project_name': False,
        'procurement_id': False
    }
    # determine if the user provided all required parameters
    config_manager = ConfigurationProfile()
    user_options = (
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
    apikey = user_options['apikey']
    cloudos_url = user_options['cloudos_url']
    workspace_id = user_options['workspace_id']

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


@project.command('create')
@click.option('-k',
              '--apikey',
              help='Your CloudOS API key',
              required=True)
@click.option('-c',
              '--cloudos-url',
              help=(f'The CloudOS url you are trying to access to. Default={CLOUDOS_URL}.'),
              default=CLOUDOS_URL,
              required=True)
@click.option('--workspace-id',
              help='The specific CloudOS workspace id.',
              required=True)
@click.option('--new-project',
              help='The name for the new project.',
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
def create_project(ctx,
                   apikey,
                   cloudos_url,
                   workspace_id,
                   new_project,
                   verbose,
                   disable_ssl_verification,
                   ssl_cert,
                   profile):
    """Create a new project in CloudOS."""
    profile = profile or ctx.default_map['project']['create']['profile']
    # Create a dictionary with required and non-required params
    required_dict = {
        'apikey': True,
        'workspace_id': True,
        'workflow_name': False,
        'project_name': False,
        'procurement_id': False
    }
    # determine if the user provided all required parameters
    config_manager = ConfigurationProfile()
    user_options = (
        config_manager.load_profile_and_validate_data(
            ctx,
            INIT_PROFILE,
            CLOUDOS_URL,
            profile=profile,
            required_dict=required_dict,
            apikey=apikey,
            cloudos_url=cloudos_url,
            workspace_id=workspace_id,
            project_name=new_project
        )
    )
    # replace the profile parameters with arguments given by the user
    apikey = user_options['apikey']
    cloudos_url = user_options['cloudos_url']
    workspace_id = user_options['workspace_id']

    # verify ssl configuration
    verify_ssl = ssl_selector(disable_ssl_verification, ssl_cert)

    # Print basic output
    if verbose:
        print(f'\tUsing CloudOS URL: {cloudos_url}')
        print(f'\tUsing workspace: {workspace_id}')
        print(f'\tProject name: {new_project}')

    cl = Cloudos(cloudos_url=cloudos_url, apikey=apikey, cromwell_token=None)

    try:
        project_id = cl.create_project(workspace_id, new_project, verify_ssl)
        print(f'\tProject "{new_project}" created successfully with ID: {project_id}')
        if verbose:
            print(f'\tProject URL: {cloudos_url}/app/projects/{project_id}')
    except Exception as e:
        print(f'\tError creating project: {str(e)}')
        sys.exit(1)


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
              default=CLOUDOS_URL,
              required=True)
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
        'project_name': False,
        'procurement_id': False
    }
    # determine if the user provided all required parameters
    config_manager = ConfigurationProfile()
    user_options = (
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
    apikey = user_options['apikey']
    cloudos_url = user_options['cloudos_url']
    workspace_id = user_options['workspace_id']

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
              default=CLOUDOS_URL,
              required=True)
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
        'project_name': False,
        'procurement_id': False
    }
    # determine if the user provided all required parameters
    config_manager = ConfigurationProfile()
    user_options = (
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
    apikey = user_options['apikey']
    cloudos_url = user_options['cloudos_url']
    workspace_id = user_options['workspace_id']

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
              default=CLOUDOS_URL,
              required=True)
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
        'project_name': False,
        'procurement_id': False
    }
    # determine if the user provided all required parameters
    config_manager = ConfigurationProfile()
    user_options = (
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
    apikey = user_options['apikey']
    cloudos_url = user_options['cloudos_url']
    workspace_id = user_options['workspace_id']

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
              default=CLOUDOS_URL,
              required=True)
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
        'project_name': False,
        'procurement_id': False
    }
    # determine if the user provided all required parameters
    config_manager = ConfigurationProfile()
    user_options = (
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
    apikey = user_options['apikey']
    cloudos_url = user_options['cloudos_url']
    workspace_id = user_options['workspace_id']

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
              default=CLOUDOS_URL,
              required=True)
@click.option('--workspace-id',
              help='The specific CloudOS workspace id.',
              required=True)
@click.option('--project-name',
              help='The name of a CloudOS project.',
              required=True)
@click.option('--workflow-name',
              help='The name of a CloudOS workflow or pipeline.',
              required=True)
@click.option('--last',
              help=('When the workflows are duplicated, use the latest imported workflow (by date).'),
              is_flag=True)
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
@click.option('--repository-platform', type=click.Choice(["github", "gitlab", "bitbucketServer"]),
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
                 last,
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
        'project_name': True,
        'procurement_id': False
    }

    # determine if the user provided all required parameters
    config_manager = ConfigurationProfile()
    user_options = (
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
    apikey = user_options['apikey']
    cloudos_url = user_options['cloudos_url']
    workspace_id = user_options['workspace_id']
    workflow_name = user_options['workflow_name']
    repository_platform = user_options['repository_platform']
    execution_platform = user_options['execution_platform']
    project_name = user_options['project_name']

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
               repository_platform=repository_platform, verify=verify_ssl, last=last)

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
                      command={"command": command},
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


@bash.command('array-job')
@click.option('-k',
              '--apikey',
              help='Your CloudOS API key',
              required=True)
@click.option('--command',
              help='The command to run in the bash job.')
@click.option('-c',
              '--cloudos-url',
              help=(f'The CloudOS url you are trying to access to. Default={CLOUDOS_URL}.'),
              default=CLOUDOS_URL,
              required=True)
@click.option('--workspace-id',
              help='The specific CloudOS workspace id.',
              required=True)
@click.option('--project-name',
              help='The name of a CloudOS project.',
              required=True)
@click.option('--workflow-name',
              help='The name of a CloudOS workflow or pipeline.',
              required=True)
@click.option('--last',
              help=('When the workflows are duplicated, use the latest imported workflow (by date).'),
              is_flag=True)
@click.option('-p',
              '--parameter',
              multiple=True,
              help=('A single parameter to pass to the job call. It should be in the ' +
                    'following form: parameter_name=parameter_value. E.g.: ' +
                    '-p --test=value or -p -test=value or -p test=value. You can use this option as many ' +
                    'times as parameters you want to include. ' +
                    'For parameters pointing to a file, the format expected is ' +
                    'parameter_name=<project>/Data/parameter_value. The parameter value must be a ' +
                    'file located in the `Data` subfolder. If no <project> is specified, it defaults to ' +
                    'the project specified by the profile or --project-name parameter. ' +
                    'E.g.: -p "--file=Data/file.txt" or "--file=<project>/Data/folder/file.txt"'))
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
@click.option('--repository-platform', type=click.Choice(["github", "gitlab", "bitbucketServer"]),
              help='Name of the repository platform of the workflow. Default=github.',
              default='github')
@click.option('--execution-platform',
              help='Name of the execution platform implemented in your CloudOS. Default=aws.',
              type=click.Choice(['aws', 'azure', 'hpc']),
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
@click.option('--array-file',
              help=('Path to a file containing an array of commands to run in the bash job.'),
              default=None,
              required=True)
@click.option('--separator',
              help=('Separator to use in the array file. Default=",".'),
              type=click.Choice([',', ';', 'tab', 'space', '|']),
              default=",",
              required=True)
@click.option('--list-columns',
              help=('List columns present in the array file. ' +
                    'This option will not run any job.'),
              is_flag=True)
@click.option('--array-file-project',
              help=('Name of the project in which the array file is placed, if different from --project-name.'),
              default=None)
@click.option('--disable-column-check',
              help=('Disable the check for the columns in the array file. ' +
                    'This option is only used when --array-file is provided.'),
              is_flag=True)
@click.option('-a', '--array-parameter',
              multiple=True,
              help=('A single parameter to pass to the job call only for specifying array parameter. It should be in the ' +
                    'following form: parameter_name=parameter_value. E.g.: ' +
                    '-a --test=value or -a -test=value or -a test=value. You can use this option as many ' +
                    'times as parameters you want to include.'))
@click.option('--custom-script-path',
              help=('Path of a custom script to run in the bash array job instead of a command.'),
              default=None)
@click.option('--custom-script-project',
              help=('Name of the project to use when running the custom command script, if ' +
                    'different than --project-name.'),
              default=None)
@click.pass_context
def run_bash_array_job(ctx,
                       apikey,
                       command,
                       cloudos_url,
                       workspace_id,
                       project_name,
                       workflow_name,
                       last,
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
                       profile,
                       array_file,
                       separator,
                       list_columns,
                       array_file_project,
                       disable_column_check,
                       array_parameter,
                       custom_script_path,
                       custom_script_project):
    """Run a bash array job in CloudOS."""
    profile = profile or ctx.default_map['bash']['array-job']['profile']

    # Create a dictionary with required and non-required params
    required_dict = {
        'apikey': True,
        'workspace_id': True,
        'workflow_name': True,
        'project_name': True,
        'procurement_id': False
    }

    # determine if the user provided all required parameters
    config_manager = ConfigurationProfile()
    user_options = (
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
    apikey = user_options['apikey']
    cloudos_url = user_options['cloudos_url']
    workspace_id = user_options['workspace_id']
    workflow_name = user_options['workflow_name']
    repository_platform = user_options['repository_platform']
    execution_platform = user_options['execution_platform']
    project_name = user_options['project_name']

    verify_ssl = ssl_selector(disable_ssl_verification, ssl_cert)

    if not list_columns and not (command or custom_script_path):
        raise click.UsageError("Must provide --command or --custom-script-path if --list-columns is not set.")

    # when not set, use the global project name
    if array_file_project is None:
        array_file_project = project_name

    # this needs to be in another call to datasets, by default it uses the global project name
    if custom_script_project is None:
        custom_script_project = project_name

    # setup separators for API and array file (the're different)
    separators = {
        ",": { "api": ",", "file": "," },
        ";": { "api": "%3B", "file": ";" },
        "space": { "api": "+", "file": " " },
        "tab": { "api": "tab", "file": "tab" },
        "|": { "api": "%7C", "file": "|" }
    }

    # setup important options for the job
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

    j = jb.Job(cloudos_url, apikey, None, workspace_id, project_name, workflow_name,
               mainfile=None, importsfile=None,
               repository_platform=repository_platform, verify=verify_ssl, last=last)

    # retrieve columns
    r = j.retrieve_cols_from_array_file(
        array_file,
        generate_datasets_for_project(cloudos_url, apikey, workspace_id, array_file_project, verify_ssl),
        separators[separator]['api'],
        verify_ssl
    )

    if not disable_column_check:
        columns = json.loads(r.content).get("headers", None)
        # pass this to the SEND JOB API call
        # b'{"headers":[{"index":0,"name":"id"},{"index":1,"name":"title"},{"index":2,"name":"filename"},{"index":3,"name":"file2name"}]}'
        if columns is None:
            raise ValueError("No columns found in the array file metadata.")
        if list_columns:
            print("Columns: ")
            for col in columns:
                print(f"\t- {col['name']}")
            return
    else:
        columns = []

    # setup parameters for the job
    cmd = j.setup_params_array_file(
        custom_script_path,
        generate_datasets_for_project(cloudos_url, apikey, workspace_id, custom_script_project, verify_ssl),
        command,
        separators[separator]['file']
    )

    # check columns in the array file vs parameters added
    if not disable_column_check and array_parameter:
        print("\nChecking columns in the array file vs parameters added...\n")
        for ap in array_parameter:
            ap_split = ap.split('=')
            ap_value = '='.join(ap_split[1:])
            for col in columns:
                if col['name'] == ap_value:
                    print(f"Found column '{ap_value}' in the array file.")
                    break
            else:
                raise ValueError(f"Column '{ap_value}' not found in the array file. " +
                                 "Columns in array-file: ", f"{separator}".join([col['name'] for col in columns]))

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

    # send job
    j_id = j.send_job(job_config=None,
                      parameter=parameter,
                      array_parameter=array_parameter,
                      array_file_header=columns,
                      git_commit=None,
                      git_tag=None,
                      git_branch=None,
                      job_name=job_name,
                      resumable=False,
                      save_logs=save_logs,
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
                      command=cmd,
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
                    '"File Name", "Storage Path".'),
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

    profile = profile or ctx.default_map['datasets']['list'].get('profile')
    config_manager = ConfigurationProfile()

    required_dict = {
        'apikey': True,
        'workspace_id': True,
        'workflow_name': False,
        'project_name': False,
        'procurement_id': False
    }

    user_options = config_manager.load_profile_and_validate_data(
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

    apikey = user_options['apikey']
    cloudos_url = user_options['cloudos_url']
    workspace_id = user_options['workspace_id']
    project_name = user_options['project_name']
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
            console = Console(width=None)
            table = Table(show_header=True, header_style="bold white")
            table.add_column("Type", style="cyan", no_wrap=True)
            table.add_column("Owner", style="white")
            table.add_column("Size", style="magenta")
            table.add_column("Last Updated", style="green")
            table.add_column("File Name", style="bold", overflow="fold")
            table.add_column("Storage Path", style="dim", no_wrap=False, overflow="fold", ratio=2)

            for item in contents:
                is_folder = "folderType" in item or item.get("isDir", False)
                type_ = "folder" if is_folder else "file"

                user = item.get("user", {})
                if isinstance(user, dict):
                    name = user.get("name", "").strip()
                    surname = user.get("surname", "").strip()
                else:
                    name = surname = ""
                if name and surname:
                    owner = f"{name} {surname}"
                elif name:
                    owner = name
                elif surname:
                    owner = surname
                else:
                    owner = "-"

                raw_size = item.get("sizeInBytes", item.get("size"))
                size = format_bytes(raw_size) if not is_folder and raw_size is not None else "-"

                updated = item.get("updatedAt") or item.get("lastModified", "-")
                filepath = item.get("name", "-")

                if item.get("fileType") == "S3File" or item.get("folderType") == "S3Folder":
                    bucket = item.get("s3BucketName")
                    key = item.get("s3ObjectKey") or item.get("s3Prefix")
                    s3_path = f"s3://{bucket}/{key}" if bucket and key else "-"
                elif item.get("fileType") == "AzureBlobFile" or item.get("folderType") == "AzureBlobFolder":
                    account = item.get("blobStorageAccountName")
                    container = item.get("blobContainerName")
                    key = item.get("blobName") if item.get("fileType") == "AzureBlobFile" else item.get("blobPrefix")
                    s3_path = f"az://{account}.blob.core.windows.net/{container}/{key}" if account and container and key else "-"
                else:
                    s3_path = "-"

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
@click.option('-c', '--cloudos-url', default=CLOUDOS_URL, required=True, help='The CloudOS URL.')
@click.option('--workspace-id', required=True, help='The CloudOS workspace ID.')
@click.option('--project-name', required=True, help='The source project name.')
@click.option('--destination-project-name', required=False,
              help='The destination project name. Defaults to the source project.')
@click.option('--disable-ssl-verification', is_flag=True, help='Disable SSL certificate verification.')
@click.option('--ssl-cert', help='Path to your SSL certificate file.')
@click.option('--profile', default=None, help='Profile to use from the config file.')
@click.pass_context
def move_files(ctx, source_path, destination_path, apikey, cloudos_url, workspace_id,
               project_name, destination_project_name,
               disable_ssl_verification, ssl_cert, profile):
    """
    Move a file or folder from a source path to a destination path within or across CloudOS projects.

    SOURCE_PATH [path]: the full path to the file or folder to move. It must be a 'Data' folder path.
     E.g.: 'Data/folderA/file.txt'\n
    DESTINATION_PATH [path]: the full path to the destination folder. It must be a 'Data' folder path.
     E.g.: 'Data/folderB'
    """

    profile = profile or ctx.default_map['datasets']['move'].get('profile')
    
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
        'project_name': True,
        'procurement_id': False
    }

    user_options = (
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
    apikey = user_options['apikey']
    cloudos_url = user_options['cloudos_url']
    workspace_id = user_options['workspace_id']
    project_name = user_options['project_name']

    verify_ssl = ssl_selector(disable_ssl_verification, ssl_cert)

    destination_project_name = destination_project_name or project_name
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
        click.echo(f"[ERROR] Item '{source_item_name}' not found in '{source_parent_path or '[project root]'}'",
                   err=True)
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
        if folder_type in ("VirtualFolder", "Folder"):
            target_kind = "Folder"
        elif folder_type=="S3Folder":
            click.echo(f"[ERROR] Item '{source_item_name}' could not be moved to '{destination_path}' as the destination folder is not modifiable.",
                   err=True)
            sys.exit(1)
        elif isinstance(folder_type, bool) and folder_type:  # legacy dataset structure
            target_kind = "Dataset"
        else:
            raise ValueError(f"Unrecognized folderType '{folder_type}' for destination '{destination_path}'")

    except Exception as e:
        click.echo(f"[ERROR] Could not resolve destination path '{destination_path}': {str(e)}", err=True)
        sys.exit(1)
    click.echo(f"Moving {source_kind} '{source_item_name}' to '{destination_path}' " +
               f"in project '{destination_project_name} ...")
    # === Perform Move ===
    try:
        response = source_client.move_files_and_folders(
            source_id=source_id,
            source_kind=source_kind,
            target_id=target_id,
            target_kind=target_kind
        )
        if response.ok:
            click.secho(f"[SUCCESS] {source_kind} '{source_item_name}' moved to '{destination_path}' " +
                        f"in project '{destination_project_name}'.", fg="green", bold=True)
        else:
            click.echo(f"[ERROR] Move failed: {response.status_code} - {response.text}", err=True)
            sys.exit(1)
    except Exception as e:
        click.echo(f"[ERROR] Move operation failed: {str(e)}", err=True)
        sys.exit(1)


@datasets.command(name="rename")
@click.argument("source_path", required=True)
@click.argument("new_name", required=True)
@click.option('-k', '--apikey', required=True, help='Your CloudOS API key.')
@click.option('-c', '--cloudos-url', default=CLOUDOS_URL, required=True, help='The CloudOS URL.')
@click.option('--workspace-id', required=True, help='The CloudOS workspace ID.')
@click.option('--project-name', required=True, help='The project name.')
@click.option('--disable-ssl-verification', is_flag=True, help='Disable SSL certificate verification.')
@click.option('--ssl-cert', help='Path to your SSL certificate file.')
@click.option('--profile', default=None, help='Profile to use from the config file.')
@click.pass_context
def renaming_item(ctx, source_path, new_name, apikey, cloudos_url,
                    workspace_id, project_name,
                    disable_ssl_verification, ssl_cert, profile):
    """
    Rename a file or folder in a CloudOS project.

    SOURCE_PATH [path]: the full path to the file or folder to rename. It must be a 'Data' folder path.
     E.g.: 'Data/folderA/old_name.txt'\n
    NEW_NAME [name]: the new name to assign to the file or folder. E.g.: 'new_name.txt'
    """
    if not source_path.strip("/").startswith("Data/"):
        click.echo("[ERROR] SOURCE_PATH must start with 'Data/', pointing to a file/folder in that dataset.", err=True)
        sys.exit(1)
    click.echo("Loading configuration profile...")
    config_manager = ConfigurationProfile()
    required_dict = {
        'apikey': True,
        'workspace_id': True,
        'workflow_name': False,
        'project_name': True,
        'procurement_id': False
    }

    user_options = (
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
    apikey = user_options['apikey']
    cloudos_url = user_options['cloudos_url']
    workspace_id = user_options['workspace_id']
    project_name = user_options['project_name']

    verify_ssl = ssl_selector(disable_ssl_verification, ssl_cert)
    # Initialize Datasets clients
    client = Datasets(
        cloudos_url=cloudos_url,
        apikey=apikey,
        workspace_id=workspace_id,
        project_name=project_name,
        verify=verify_ssl,
        cromwell_token=None
    )

    parts = source_path.strip("/").split("/")

    parent_path = "/".join(parts[:-1])
    target_name = parts[-1]

    try:
        contents = client.list_folder_content(parent_path)
    except Exception as e:
        click.echo(f"[ERROR] Could not list contents at '{parent_path or '[project root]'}': {str(e)}", err=True)
        sys.exit(1)

    # Search for file/folder
    found_item = None
    for category in ["files", "folders"]:
        for item in contents.get(category, []):
            if item.get("name") == target_name:
                found_item = item
                break
        if found_item:
            break

    if not found_item:
        click.echo(f"[ERROR] Item '{target_name}' not found in '{parent_path or '[project root]'}'", err=True)
        sys.exit(1)

    item_id = found_item["_id"]
    kind = "Folder" if "folderType" in found_item else "File"

    click.echo(f"Renaming {kind} '{target_name}' to '{new_name}'...")
    try:
        response = client.rename_item(item_id=item_id, new_name=new_name, kind=kind)
        if response.ok:
            click.secho(
                f"[SUCCESS] {kind} '{target_name}' renamed to '{new_name}' in folder '{parent_path}'.",
                fg="green",
                bold=True
            )
        else:
            click.echo(f"[ERROR] Rename failed: {response.status_code} - {response.text}", err=True)
            sys.exit(1)
    except Exception as e:
        click.echo(f"[ERROR] Rename operation failed: {str(e)}", err=True)
        sys.exit(1)


@datasets.command(name="cp")
@click.argument("source_path", required=True)
@click.argument("destination_path", required=True)
@click.option('-k', '--apikey', required=True, help='Your CloudOS API key.')
@click.option('-c', '--cloudos-url', default=CLOUDOS_URL, required=True, help='The CloudOS URL.')
@click.option('--workspace-id', required=True, help='The CloudOS workspace ID.')
@click.option('--project-name', required=True, help='The source project name.')
@click.option('--destination-project-name', required=False, help='The destination project name. Defaults to the source project.')
@click.option('--disable-ssl-verification', is_flag=True, help='Disable SSL certificate verification.')
@click.option('--ssl-cert', help='Path to your SSL certificate file.')
@click.option('--profile', default=None, help='Profile to use from the config file.')
@click.pass_context
def copy_item_cli(ctx, source_path, destination_path, apikey, cloudos_url,
                  workspace_id, project_name, destination_project_name,
                  disable_ssl_verification, ssl_cert, profile):
    """
    Copy a file or folder (S3 or virtual) from SOURCE_PATH to DESTINATION_PATH.

    SOURCE_PATH [path]: the full path to the file or folder to copy.
     E.g.: AnalysesResults/my_analysis/results/my_plot.png\n
    DESTINATION_PATH [path]: the full path to the destination folder. It must be a 'Data' folder path.
     E.g.: Data/plots
    """
    click.echo("Loading configuration profile...")
    config_manager = ConfigurationProfile()
    required_dict = {
        'apikey': True,
        'workspace_id': True,
        'workflow_name': False,
        'project_name': True,
        'procurement_id': False
    }
    user_options = config_manager.load_profile_and_validate_data(
        ctx, INIT_PROFILE, CLOUDOS_URL, profile=profile,
        required_dict=required_dict,
        apikey=apikey,
        cloudos_url=cloudos_url,
        workspace_id=workspace_id,
        workflow_name=None,
        repository_platform=None,
        execution_platform=None,
        project_name=project_name
    )
    apikey = user_options['apikey']
    cloudos_url = user_options['cloudos_url']
    workspace_id = user_options['workspace_id']
    project_name = user_options['project_name']

    destination_project_name = destination_project_name or project_name
    verify_ssl = ssl_selector(disable_ssl_verification, ssl_cert)
    # Initialize clients
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
    # Validate paths
    dest_parts = destination_path.strip("/").split("/")
    if not dest_parts or dest_parts[0] != "Data":
        click.echo("[ERROR] DESTINATION_PATH must start with 'Data/'.", err=True)
        sys.exit(1)
    # Parse source and destination
    source_parts = source_path.strip("/").split("/")
    source_parent = "/".join(source_parts[:-1]) if len(source_parts) > 1 else ""
    source_name = source_parts[-1]
    dest_folder_name = dest_parts[-1]
    dest_parent = "/".join(dest_parts[:-1]) if len(dest_parts) > 1 else ""
    try:
        source_content = source_client.list_folder_content(source_parent)
        dest_content = dest_client.list_folder_content(dest_parent)
    except Exception as e:
        click.echo(f"[ERROR] Could not access paths: {str(e)}", err=True)
        sys.exit(1)
    # Find the source item
    source_item = None
    for item in source_content.get('files', []) + source_content.get('folders', []):
        if item.get("name") == source_name:
            source_item = item
            break
    if not source_item:
        click.echo(f"[ERROR] Item '{source_name}' not found in '{source_parent or '[project root]'}'", err=True)
        sys.exit(1)
    # Find the destination folder
    destination_folder = None
    for folder in dest_content.get("folders", []):
        if folder.get("name") == dest_folder_name:
            destination_folder = folder
            break
    if not destination_folder:
        click.echo(f"[ERROR] Destination folder '{destination_path}' not found.", err=True)
        sys.exit(1)
    try:
        # Determine item type
        if "fileType" in source_item:
            item_type = "file"
        elif source_item.get("folderType") == "VirtualFolder":
            item_type = "virtual_folder"
        elif "s3BucketName" in source_item and source_item.get("folderType") == "S3Folder":
            item_type = "s3_folder"
        else:
            click.echo("[ERROR] Could not determine item type.", err=True)
            sys.exit(1)
        click.echo(f"Copying {item_type.replace('_', ' ')} '{source_name}' to '{destination_path}'...")
        if destination_folder.get("folderType") is True and destination_folder.get("kind") in ("Data", "Cohorts", "AnalysesResults"):
            destination_kind = "Dataset"
        elif destination_folder.get("folderType")=="S3Folder":
            click.echo(f"[ERROR] Item '{source_name}' could not be copied to '{destination_path}' as the destination folder is not modifiable.",
                   err=True)
            sys.exit(1)
        else:
            destination_kind = "Folder"
        response = source_client.copy_item(
            item=source_item,
            destination_id=destination_folder["_id"],
            destination_kind=destination_kind
        )
        if response.ok:
            click.secho("[SUCCESS] Item copied successfully.", fg="green", bold=True)
        else:
            click.echo(f"[ERROR] Copy failed: {response.status_code} - {response.text}", err=True)
            sys.exit(1)
    except Exception as e:
        click.echo(f"[ERROR] Copy operation failed: {str(e)}", err=True)
        sys.exit(1)


@datasets.command(name="mkdir")
@click.argument("new_folder_path", required=True)
@click.option('-k', '--apikey', required=True, help='Your CloudOS API key.')
@click.option('-c', '--cloudos-url', default=CLOUDOS_URL, required=True, help='The CloudOS URL.')
@click.option('--workspace-id', required=True, help='The CloudOS workspace ID.')
@click.option('--project-name', required=True, help='The project name.')
@click.option('--disable-ssl-verification', is_flag=True, help='Disable SSL certificate verification.')
@click.option('--ssl-cert', help='Path to your SSL certificate file.')
@click.option('--profile', default=None, help='Profile to use from the config file.')
@click.pass_context
def mkdir_item(ctx, new_folder_path, apikey, cloudos_url,
               workspace_id, project_name,
               disable_ssl_verification, ssl_cert, profile):
    """
    Create a virtual folder in a CloudOS project.

    NEW_FOLDER_PATH [path]: Full path to the new folder including its name. Must start with 'Data'.
    """
    new_folder_path = new_folder_path.strip("/")
    if not new_folder_path.startswith("Data"):
        click.echo("[ERROR] NEW_FOLDER_PATH must start with 'Data'.", err=True)
        sys.exit(1)

    path_parts = new_folder_path.split("/")
    if len(path_parts) < 2:
        click.echo("[ERROR] NEW_FOLDER_PATH must include at least a parent folder and the new folder name.", err=True)
        sys.exit(1)

    parent_path = "/".join(path_parts[:-1])
    folder_name = path_parts[-1]

    click.echo("Loading configuration profile...")
    config_manager = ConfigurationProfile()
    required_dict = {
        'apikey': True,
        'workspace_id': True,
        'workflow_name': False,
        'project_name': True,
        'procurement_id': False
    }

    user_options = (
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
    apikey = user_options['apikey']
    cloudos_url = user_options['cloudos_url']
    workspace_id = user_options['workspace_id']
    project_name = user_options['project_name']

    verify_ssl = ssl_selector(disable_ssl_verification, ssl_cert)

    client = Datasets(
        cloudos_url=cloudos_url,
        apikey=apikey,
        workspace_id=workspace_id,
        project_name=project_name,
        verify=verify_ssl,
        cromwell_token=None
    )

    # Split parent path to get its parent + name
    parent_parts = parent_path.split("/")
    parent_name = parent_parts[-1]
    parent_of_parent_path = "/".join(parent_parts[:-1])

    # List the parent of the parent
    try:
        contents = client.list_folder_content(parent_of_parent_path)
    except Exception as e:
        click.echo(f"[ERROR] Could not list contents at '{parent_of_parent_path}': {str(e)}", err=True)
        sys.exit(1)

    # Find the parent folder in the contents
    folder_info = next(
        (f for f in contents.get("folders", []) if f.get("name") == parent_name),
        None
    )

    if not folder_info:
        click.echo(f"[ERROR] Could not find folder '{parent_name}' in '{parent_of_parent_path}'.", err=True)
        sys.exit(1)

    parent_id = folder_info.get("_id")
    folder_type = folder_info.get("folderType")

    if folder_type is True:
        parent_kind = "Dataset"
    elif isinstance(folder_type, str):
        parent_kind = "Folder"
    else:
        click.echo(f"[ERROR] Unrecognized folderType for '{parent_path}'.", err=True)
        sys.exit(1)

    # Create the folder
    click.echo(f"Creating folder '{folder_name}' under '{parent_path}' ({parent_kind})...")
    try:
        response = client.create_virtual_folder(name=folder_name, parent_id=parent_id, parent_kind=parent_kind)
        if response.ok:
            click.secho(f"[SUCCESS] Folder '{folder_name}' created under '{parent_path}'", fg="green", bold=True)
        else:
            click.echo(f"[ERROR] Folder creation failed: {response.status_code} - {response.text}", err=True)
            sys.exit(1)
    except Exception as e:
        click.echo(f"[ERROR] Folder creation failed: {str(e)}", err=True)
        sys.exit(1)


@datasets.command(name="rm")
@click.argument("target_path", required=True)
@click.option('-k', '--apikey', required=True, help='Your CloudOS API key.')
@click.option('-c', '--cloudos-url', default=CLOUDOS_URL, required=True, help='The CloudOS URL.')
@click.option('--workspace-id', required=True, help='The CloudOS workspace ID.')
@click.option('--project-name', required=True, help='The project name.')
@click.option('--disable-ssl-verification', is_flag=True, help='Disable SSL certificate verification.')
@click.option('--ssl-cert', help='Path to your SSL certificate file.')
@click.option('--profile', default=None, help='Profile to use from the config file.')
@click.pass_context
def rm_item(ctx, target_path, apikey, cloudos_url,
            workspace_id, project_name,
            disable_ssl_verification, ssl_cert, profile):
    """
    Delete a file or folder in a CloudOS project.

    TARGET_PATH [path]: the full path to the file or folder to delete. Must start with 'Data'. \n
    E.g.: 'Data/folderA/file.txt' or 'Data/my_analysis/results/folderB'
    """
    if not target_path.strip("/").startswith("Data/"):
        click.echo("[ERROR] TARGET_PATH must start with 'Data/', pointing to a file or folder.", err=True)
        sys.exit(1)
    click.echo("Loading configuration profile...")
    config_manager = ConfigurationProfile()
    required_dict = {
        'apikey': True,
        'workspace_id': True,
        'workflow_name': False,
        'project_name': True,
        'procurement_id': False
    }

    user_options = (
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
    apikey = user_options['apikey']
    cloudos_url = user_options['cloudos_url']
    workspace_id = user_options['workspace_id']
    project_name = user_options['project_name']

    verify_ssl = ssl_selector(disable_ssl_verification, ssl_cert)

    client = Datasets(
        cloudos_url=cloudos_url,
        apikey=apikey,
        workspace_id=workspace_id,
        project_name=project_name,
        verify=verify_ssl,
        cromwell_token=None
    )

    parts = target_path.strip("/").split("/")
    parent_path = "/".join(parts[:-1])
    item_name = parts[-1]

    try:
        contents = client.list_folder_content(parent_path)
    except Exception as e:
        click.echo(f"[ERROR] Could not list contents at '{parent_path or '[project root]'}': {str(e)}", err=True)
        sys.exit(1)

    found_item = None
    for item in contents.get('files', []) + contents.get('folders', []):
        if item.get("name") == item_name:
            found_item = item
            break

    if not found_item:
        click.echo(f"[ERROR] Item '{item_name}' not found in '{parent_path or '[project root]'}'", err=True)
        sys.exit(1)

    item_id = found_item.get("_id",'')
    kind = "Folder" if "folderType" in found_item else "File"
    if item_id=='':
        click.echo(f"[ERROR] Item '{item_name}' could not be removed as the parent folder is not modifiable.",
                   err=True)
        sys.exit(1)
    click.echo(f"Deleting {kind} '{item_name}' from '{parent_path or '[root]'}'...")
    try:
        response = client.delete_item(item_id=item_id, kind=kind)
        if response.ok:
            click.secho(
                f"[SUCCESS] {kind} '{item_name}' was deleted from '{parent_path or '[root]'}'.",
                fg="green", bold=True
            )
            click.secho("This item will still be available on your Cloud Provider.", fg="yellow")
        else:
            click.echo(f"[ERROR] Deletion failed: {response.status_code} - {response.text}", err=True)
            sys.exit(1)
    except Exception as e:
        click.echo(f"[ERROR] Delete operation failed: {str(e)}", err=True)
        sys.exit(1)


@datasets.command(name="link")
@click.argument("path", required=True)
@click.option('-k', '--apikey', help='Your CloudOS API key', required=True)
@click.option('-c', '--cloudos-url',
              help=(f'The CloudOS url you are trying to access to. Default={CLOUDOS_URL}.'),
              default=CLOUDOS_URL)
@click.option('--project-name',
              help='The name of a CloudOS project.',
              required=False)
@click.option('--workspace-id', help='The specific CloudOS workspace id.', required=True)
@click.option('--session-id', help='The specific CloudOS interactive session id.', required=True)
@click.option('--disable-ssl-verification', is_flag=True, help='Disable SSL certificate verification.')
@click.option('--ssl-cert', help='Path to your SSL certificate file.')
@click.option('--profile', help='Profile to use from the config file', default='default')
@click.pass_context
def link(ctx, path, apikey, cloudos_url, project_name, workspace_id, session_id, disable_ssl_verification, ssl_cert, profile):
    """
    Link a folder (S3 or File Explorer) to an active interactive analysis.

    PATH [path]: the full path to the S3 folder to link or relative to File Explorer. 
    E.g.: 's3://bucket-name/folder/subfolder', 'Data/Downloads' or 'Data'.
    """

    profile = profile or ctx.default_map['datasets']['link']['profile']

    # Create a dictionary with required and non-required params
    required_dict = {
        'apikey': True,
        'workspace_id': True,
        'workflow_name': False,
        'project_name': False,
        'procurement_id': False
    }
    # determine if the user provided all required parameters
    config_manager = ConfigurationProfile()
    user_options = (
        config_manager.load_profile_and_validate_data(
            ctx,
            INIT_PROFILE,
            CLOUDOS_URL,
            profile=profile,
            required_dict=required_dict,
            apikey=apikey,
            cloudos_url=cloudos_url,
            workspace_id=workspace_id,
            session_id=session_id,
            project_name=project_name
        )
    )
    # Unpack the user options
    apikey = user_options['apikey']
    cloudos_url = user_options['cloudos_url']
    workspace_id = user_options['workspace_id']
    session_id = user_options['session_id']
    project_name = user_options['project_name']

    if not path.startswith("s3://") and project_name is None:
        # for non-s3 paths we need the project, for S3 we don't
        raise click.UsageError("When using File Explorer paths '--project-name' needs to be defined")

    verify_ssl = ssl_selector(disable_ssl_verification, ssl_cert)

    link_p = Link(
        cloudos_url=cloudos_url,
        apikey=apikey,
        workspace_id=workspace_id,
        cromwell_token=None,
        project_name=project_name,
        verify=verify_ssl
    )
    link_p.link_folder(path, session_id)


@images.command(name="ls")
@click.option('-k',
              '--apikey',
              help='Your CloudOS API key.',
              required=True)
@click.option('-c',
              '--cloudos-url',
              help=(f'The CloudOS url you are trying to access to. Default={CLOUDOS_URL}.'),
              default=CLOUDOS_URL,
              required=True)
@click.option('--procurement-id', help='The specific CloudOS procurement id.', required=True)
@click.option('--page', help='The response page. Defaults to 1.', required=False, default=1)
@click.option('--limit', help='The page size limit. Defaults to 10', required=False, default=10)
@click.option('--disable-ssl-verification',
              help=('Disable SSL certificate verification. Please, remember that this option is ' +
                    'not generally recommended for security reasons.'),
              is_flag=True)
@click.option('--ssl-cert',
              help='Path to your SSL certificate file.')
@click.option('--profile', help='Profile to use from the config file', default=None)
@click.pass_context
def list_images(ctx,
                apikey,
                cloudos_url,
                procurement_id,
                disable_ssl_verification,
                ssl_cert,
                profile,
                page,
                limit):
    """List images associated with organisations of a given procurement."""

    profile = profile or ctx.default_map['procurement']['images']['ls'].get('profile')
    config_manager = ConfigurationProfile()

    required_dict = {
        'apikey': True,
        'workspace_id': False,
        'workflow_name': False,
        'project_name': False,
        'procurement_id': True
    }

    user_options = config_manager.load_profile_and_validate_data(
        ctx,
        INIT_PROFILE,
        CLOUDOS_URL,
        profile=profile,
        required_dict=required_dict,
        apikey=apikey,
        cloudos_url=cloudos_url,
        workspace_id=None,
        project_name=None,
        workflow_name=None,
        execution_platform=None,
        repository_platform=None,
        session_id=None,
        procurement_id=procurement_id
    )

    apikey = user_options['apikey']
    cloudos_url = user_options['cloudos_url']
    procurement_id = user_options['procurement_id']
    verify_ssl = ssl_selector(disable_ssl_verification, ssl_cert)

    procurement_images = Images(
        cloudos_url=cloudos_url,
        apikey=apikey,
        procurement_id=procurement_id,
        verify=verify_ssl,
        cromwell_token=None,
        page=page,
        limit=limit
    )

    try:
        result = procurement_images.list_procurement_images()
        console = Console()
        console.print(result)

    except Exception as e:
        click.echo(f"[ERROR] {str(e)}", err=True)


@images.command(name="set")
@click.option('-k',
              '--apikey',
              help='Your CloudOS API key.',
              required=True)
@click.option('-c',
              '--cloudos-url',
              help=(f'The CloudOS url you are trying to access to. Default={CLOUDOS_URL}.'),
              default=CLOUDOS_URL,
              required=True)
@click.option('--procurement-id', help='The specific CloudOS procurement id.', required=True)
@click.option('--organisation-id', help='The Organisation Id where the change is going to be applied.', required=True)
@click.option('--image-type', help='The CloudOS resource image type.', required=True, 
            type=click.Choice(['RegularInteractiveSessions', 'SparkInteractiveSessions', 'RStudioInteractiveSessions', 'JupyterInteractiveSessions', 'JobDefault', 'NextflowBatchComputeEnvironment']))
@click.option('--provider', help='The cloud provider. Only aws is supported.', required=True, type=click.Choice(['aws']), default='aws')
@click.option('--region', help='The cloud region. Only aws regions are supported.', required=True)
@click.option('--image-id', help='The new image id value.', required=True)
@click.option('--image-name', help='The new image name value.', required=False)
@click.option('--disable-ssl-verification',
              help=('Disable SSL certificate verification. Please, remember that this option is ' +
                    'not generally recommended for security reasons.'),
              is_flag=True)
@click.option('--ssl-cert',
              help='Path to your SSL certificate file.')
@click.option('--profile', help='Profile to use from the config file', default=None)
@click.pass_context
def set_organisation_image(ctx,
                           apikey,
                           cloudos_url,
                           procurement_id,
                           organisation_id,
                           image_type,
                           provider,
                           region,
                           image_id,
                           image_name,
                           disable_ssl_verification,
                           ssl_cert,
                           profile):
    """Set a new image id or name to image associated with an organisations of a given procurement."""

    profile = profile or ctx.default_map['procurement']['images']['ls'].get('profile')
    config_manager = ConfigurationProfile()

    required_dict = {
        'apikey': True,
        'workspace_id': False,
        'workflow_name': False,
        'project_name': False,
        'procurement_id': True
    }

    user_options = config_manager.load_profile_and_validate_data(
        ctx,
        INIT_PROFILE,
        CLOUDOS_URL,
        profile=profile,
        required_dict=required_dict,
        apikey=apikey,
        cloudos_url=cloudos_url,
        workspace_id=None,
        project_name=None,
        workflow_name=None,
        execution_platform=None,
        repository_platform=None,
        session_id=None,
        procurement_id=procurement_id
    )

    apikey = user_options['apikey']
    cloudos_url = user_options['cloudos_url']
    procurement_id = user_options['procurement_id']
    verify_ssl = ssl_selector(disable_ssl_verification, ssl_cert)

    procurement_images = Images(
        cloudos_url=cloudos_url,
        apikey=apikey,
        procurement_id=procurement_id,
        verify=verify_ssl,
        cromwell_token=None
    )

    try:
        result = procurement_images.set_procurement_organisation_image(
           organisation_id,
           image_type,
           provider,
           region,
           image_id,
           image_name
        )
        console = Console()
        console.print(result)

    except Exception as e:
        click.echo(f"[ERROR] {str(e)}", err=True)


@images.command(name="reset")
@click.option('-k',
              '--apikey',
              help='Your CloudOS API key.',
              required=True)
@click.option('-c',
              '--cloudos-url',
              help=(f'The CloudOS url you are trying to access to. Default={CLOUDOS_URL}.'),
              default=CLOUDOS_URL,
              required=True)
@click.option('--procurement-id', help='The specific CloudOS procurement id.', required=True)
@click.option('--organisation-id', help='The Organisation Id where the change is going to be applied.', required=True)
@click.option('--image-type', help='The CloudOS resource image type.', required=True, 
            type=click.Choice(['RegularInteractiveSessions', 'SparkInteractiveSessions', 'RStudioInteractiveSessions', 'JupyterInteractiveSessions', 'JobDefault', 'NextflowBatchComputeEnvironment']))
@click.option('--provider', help='The cloud provider. Only aws is supported.', required=True, type=click.Choice(['aws']), default='aws')
@click.option('--region', help='The cloud region. Only aws regions are supported.', required=True)
@click.option('--disable-ssl-verification',
              help=('Disable SSL certificate verification. Please, remember that this option is ' +
                    'not generally recommended for security reasons.'),
              is_flag=True)
@click.option('--ssl-cert',
              help='Path to your SSL certificate file.')
@click.option('--profile', help='Profile to use from the config file', default=None)
@click.pass_context
def reset_organisation_image(ctx,
                             apikey,
                             cloudos_url,
                             procurement_id,
                             organisation_id,
                             image_type,
                             provider,
                             region,
                             disable_ssl_verification,
                             ssl_cert,
                             profile):
    """Reset image associated with an organisations of a given procurement to CloudOS defaults."""

    profile = profile or ctx.default_map['procurement']['images']['set'].get('profile')
    config_manager = ConfigurationProfile()

    required_dict = {
        'apikey': True,
        'workspace_id': False,
        'workflow_name': False,
        'project_name': False,
        'procurement_id': True
    }

    user_options = config_manager.load_profile_and_validate_data(
        ctx,
        INIT_PROFILE,
        CLOUDOS_URL,
        profile=profile,
        required_dict=required_dict,
        apikey=apikey,
        cloudos_url=cloudos_url,
        workspace_id=None,
        project_name=None,
        workflow_name=None,
        execution_platform=None,
        repository_platform=None,
        session_id=None,
        procurement_id=procurement_id
    )

    apikey = user_options['apikey']
    cloudos_url = user_options['cloudos_url']
    procurement_id = user_options['procurement_id']
    verify_ssl = ssl_selector(disable_ssl_verification, ssl_cert)

    procurement_images = Images(
        cloudos_url=cloudos_url,
        apikey=apikey,
        procurement_id=procurement_id,
        verify=verify_ssl,
        cromwell_token=None
    )

    try:
        result = procurement_images.reset_procurement_organisation_image(
           organisation_id,
           image_type,
           provider,
           region
        )
        console = Console()
        console.print(result)

    except Exception as e:
        click.echo(f"[ERROR] {str(e)}", err=True)


if __name__ == "__main__":
    try:
        run_cloudos_cli()
    except Exception as e:
        # Check if debug flag was passed (fallback for cases where Click doesn't handle it)
        debug_mode = '--debug' in sys.argv
        
        if debug_mode:
            traceback.print_exc()
        else:
            click.echo(click.style(f"Error: {e}", fg='red'), err=True)
        sys.exit(1)

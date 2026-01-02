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
from cloudos_cli.utils.details import create_job_details, create_job_list_table
from cloudos_cli.link import Link
from cloudos_cli.cost.cost import CostViewer
from cloudos_cli.logging.logger import setup_logging, update_command_context_from_click
import logging
from cloudos_cli.configure.configure import (
    with_profile_config,
    build_default_map_for_group,
    get_shared_config,
    CLOUDOS_URL
)
from cloudos_cli.related_analyses.related_analyses import related_analyses


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


def custom_exception_handler(exc_type, exc_value, exc_traceback):
    """Custom exception handler that respects debug mode"""
    console = Console(stderr=True)
    # Initialise logger
    debug_mode = '--debug' in sys.argv
    setup_logging(debug_mode)
    logger = logging.getLogger("CloudOS")
    if get_debug_mode():
        logger.error(exc_value, exc_info=exc_value)
        console.print("[yellow]Debug mode: showing full traceback[/yellow]")
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
    else:
        # Extract a clean error message
        if hasattr(exc_value, 'message'):
            error_msg = exc_value.message
        elif str(exc_value):
            error_msg = str(exc_value)
        else:
            error_msg = f"{exc_type.__name__}"
        logger.error(exc_value)
        console.print(f"[bold red]Error: {error_msg}[/bold red]")

        # For network errors, give helpful context
        if 'HTTPSConnectionPool' in str(exc_value) or 'Max retries exceeded' in str(exc_value):
            console.print("[yellow]Tip: This appears to be a network connectivity issue. Please check your internet connection and try again.[/yellow]")

# Install the custom exception handler
sys.excepthook = custom_exception_handler


def pass_debug_to_subcommands(group_cls=click.RichGroup):
    """Custom Group class that passes --debug option to all subcommands"""

    class DebugGroup(group_cls):
        def add_command(self, cmd, name=None):
            # Add debug option to the command if it doesn't already have it
            if isinstance(cmd, (click.Command, click.Group)):
                has_debug = any(param.name == 'debug' for param in cmd.params)
                if not has_debug:
                    debug_option = click.Option(
                        ['--debug'], 
                        is_flag=True, 
                        help='Show detailed error information and tracebacks',
                        is_eager=True,
                        expose_value=False,
                        callback=self._debug_callback
                    )
                    cmd.params.insert(-1, debug_option)  # Insert at the end for precedence

            super().add_command(cmd, name)

        def _debug_callback(self, ctx, param, value):
            """Callback to handle debug flag"""
            global _global_debug
            if value:
                _global_debug = True
                ctx.meta['debug'] = True
            else:
                ctx.meta['debug'] = False
            return value

    return DebugGroup


def get_debug_mode():
    """Get current debug mode state"""
    return _global_debug


# Helper function for debug setup
def _setup_debug(ctx, param, value):
    """Setup debug mode globally and in context"""
    global _global_debug
    _global_debug = value
    if value:
        ctx.meta['debug'] = True
    else:
        ctx.meta['debug'] = False
    return value


@click.group(cls=pass_debug_to_subcommands())
@click.option('--debug', is_flag=True, help='Show detailed error information and tracebacks', 
              is_eager=True, expose_value=False, callback=_setup_debug)
@click.version_option(__version__)
@click.pass_context
def run_cloudos_cli(ctx):
    """CloudOS python package: a package for interacting with CloudOS."""
    update_command_context_from_click(ctx)
    ctx.ensure_object(dict)

    if ctx.invoked_subcommand not in ['datasets']:
        print(run_cloudos_cli.__doc__ + '\n')
        print('Version: ' + __version__ + '\n')
    
    # Load shared configuration (handles missing profiles and fields gracefully)
    shared_config = get_shared_config()
    
    # Automatically build default_map from registered commands
    ctx.default_map = build_default_map_for_group(run_cloudos_cli, shared_config)


@run_cloudos_cli.group(cls=pass_debug_to_subcommands())
def job():
    """CloudOS job functionality: run, clone, resume, check and abort jobs in CloudOS."""
    print(job.__doc__ + '\n')


@run_cloudos_cli.group(cls=pass_debug_to_subcommands())
def workflow():
    """CloudOS workflow functionality: list and import workflows."""
    print(workflow.__doc__ + '\n')


@run_cloudos_cli.group(cls=pass_debug_to_subcommands())
def project():
    """CloudOS project functionality: list and create projects in CloudOS."""
    print(project.__doc__ + '\n')


@run_cloudos_cli.group(cls=pass_debug_to_subcommands())
def cromwell():
    """Cromwell server functionality: check status, start and stop."""
    print(cromwell.__doc__ + '\n')


@run_cloudos_cli.group(cls=pass_debug_to_subcommands())
def queue():
    """CloudOS job queue functionality."""
    print(queue.__doc__ + '\n')


@run_cloudos_cli.group(cls=pass_debug_to_subcommands())
def bash():
    """CloudOS bash functionality."""
    print(bash.__doc__ + '\n')


@run_cloudos_cli.group(cls=pass_debug_to_subcommands())
def procurement():
    """CloudOS procurement functionality."""
    print(procurement.__doc__ + '\n')


@procurement.group(cls=pass_debug_to_subcommands())
def images():
    """CloudOS procurement images functionality."""


@run_cloudos_cli.group(cls=pass_debug_to_subcommands())
@click.pass_context
def datasets(ctx):
    """CloudOS datasets functionality."""
    update_command_context_from_click(ctx)
    if ctx.args and ctx.args[0] != 'ls':
        print(datasets.__doc__ + '\n')


@run_cloudos_cli.group(cls=pass_debug_to_subcommands(), invoke_without_command=True)
@click.option('--profile', help='Profile to use from the config file', default='default')
@click.option('--make-default',
              is_flag=True,
              help='Make the profile the default one.')
@click.pass_context
def configure(ctx, profile, make_default):
    """CloudOS configuration."""
    print(configure.__doc__ + '\n')
    update_command_context_from_click(ctx)
    profile = profile or ctx.obj['profile']
    config_manager = ConfigurationProfile()

    if ctx.invoked_subcommand is None and profile == "default" and not make_default:
        config_manager.create_profile_from_input(profile_name="default")

    if profile != "default" and not make_default:
        config_manager.create_profile_from_input(profile_name=profile)
    if make_default:
        config_manager.make_default_profile(profile_name=profile)


@job.command('run', cls=click.RichCommand)
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
@click.option('--accelerate-saving-results',
              help='Enables saving results directly to cloud storage bypassing the master node.',
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
@with_profile_config(required_params=['apikey', 'workspace_id', 'workflow_name', 'project_name'])
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
        accelerate_saving_results,
        use_private_docker_repository,
        verbose,
        request_interval,
        disable_ssl_verification,
        ssl_cert,
        profile):
    """Submit a job to CloudOS."""

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
        print('\nHPC execution platform selected')
        if hpc_id is None:
            raise ValueError('Please, specify your HPC ID using --hpc parameter')
        print('Please, take into account that HPC execution do not support ' +
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
            print('You have selected accelerate file staging, but this function is ' +
                  'only available when execution platform is AWS. The accelerate file staging ' +
                  'will not be applied')
            use_mountpoints = False
        else:
            use_mountpoints = True
            print('Enabling AWS S3 mountpoint for accelerated file staging. ' +
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
        print('WDL workflow detected')
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
        click.secho('\t' + ('*' * 80) + '\n' +
              '\tCromwell server is now running. Please, remember to stop it when ' +
              'your\n' + '\tjob finishes. You can use the following command:\n' +
              '\tcloudos cromwell stop \\\n' +
              '\t\t--cromwell-token $CROMWELL_TOKEN \\\n' +
              f'\t\t--cloudos-url {cloudos_url} \\\n' +
              f'\t\t--workspace-id {workspace_id}\n' +
              '\t' + ('*' * 80) + '\n', fg='yellow', bold=True)
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
            print(f'Ignoring job queue "{job_queue}" for ' +
                  f'Platform Workflow "{workflow_name}". Platform Workflows ' +
                  'use their own predetermined queues.')
        job_queue_id = None
        if nextflow_version != '22.10.8':
            print(f'The selected worflow \'{workflow_name}\' ' +
                  'is a CloudOS module. CloudOS modules only work with ' +
                  'Nextflow version 22.10.8. Switching to use 22.10.8')
        nextflow_version = '22.10.8'
        if execution_platform == 'azure':
            print(f'The selected worflow \'{workflow_name}\' ' +
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
            print(f'Workflow "{workflow_name}" is a CloudOS module. ' +
                  'Option --use-private-docker-repository will be ignored.')
            docker_login = False
        else:
            me = j.get_user_info(verify=verify_ssl)['dockerRegistriesCredentials']
            if len(me) == 0:
                raise Exception('User private Docker repository has been selected but your user ' +
                                'credentials have not been configured yet. Please, link your ' +
                                'Docker account to CloudOS before using ' +
                                '--use-private-docker-repository option.')
            print('Use private Docker repository has been selected. A custom job ' +
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
        print('You have specified Nextflow version \'latest\' for execution platform ' +
              f'\'{execution_platform}\'. The workflow will use the ' +
              f'latest version available on CloudOS: {nextflow_version}.')
    if execution_platform == 'aws':
        if nextflow_version not in AWS_NEXTFLOW_VERSIONS:
            print('For execution platform \'aws\', the workflow will use the default ' +
                  '\'22.10.8\' version on CloudOS.')
            nextflow_version = '22.10.8'
    if execution_platform == 'azure':
        if nextflow_version not in AZURE_NEXTFLOW_VERSIONS:
            print('For execution platform \'azure\', the workflow will use the \'22.11.1-edge\' ' +
                  'version on CloudOS.')
            nextflow_version = '22.11.1-edge'
    if execution_platform == 'hpc':
        if nextflow_version not in HPC_NEXTFLOW_VERSIONS:
            print('For execution platform \'hpc\', the workflow will use the \'22.10.8\' version on CloudOS.')
            nextflow_version = '22.10.8'
    if nextflow_version != '22.10.8' and nextflow_version != '22.11.1-edge':
        click.secho(f'You have specified Nextflow version {nextflow_version}. This version requires the pipeline ' +
              'to be written in DSL2 and does not support DSL1.', fg='yellow', bold=True)
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
                      accelerate_saving_results=accelerate_saving_results,
                      docker_login=docker_login,
                      verify=verify_ssl)
    print(f'\tYour assigned job id is: {j_id}\n')
    j_url = f'{cloudos_url}/app/advanced-analytics/analyses/{j_id}'
    if wait_completion:
        print('\tPlease, wait until job completion (max wait time of ' +
              f'{wait_time} seconds).\n')
        j_status = j.wait_job_completion(job_id=j_id,
                                         workspace_id=workspace_id,
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
        j_status = j.get_job_status(j_id, workspace_id, verify_ssl)
        j_status_h = json.loads(j_status.content)["status"]
        print(f'\tYour current job status is: {j_status_h}')
        print('\tTo further check your job status you can either go to ' +
              f'{j_url} or use the following command:\n' +
              '\tcloudos job status \\\n' +
              f'\t\t--profile my_profile \\\n' +
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
@with_profile_config(required_params=['apikey', 'workspace_id'])
def job_status(ctx,
               apikey,
               cloudos_url,
               workspace_id,
               job_id,
               verbose,
               disable_ssl_verification,
               ssl_cert,
               profile):
    """Check job status in CloudOS."""
    # apikey, cloudos_url, and workspace_id are now automatically resolved by the decorator

    print('Executing status...')
    verify_ssl = ssl_selector(disable_ssl_verification, ssl_cert)
    if verbose:
        print('\t...Preparing objects')
    cl = Cloudos(cloudos_url, apikey, None)
    if verbose:
        print('\tThe following Cloudos object was created:')
        print('\t' + str(cl) + '\n')
        print(f'\tSearching for job id: {job_id}')
    try:
        j_status = cl.get_job_status(job_id, workspace_id, verify_ssl)
        j_status_h = json.loads(j_status.content)["status"]
        print(f'\tYour current job status is: {j_status_h}\n')
        j_url = f'{cloudos_url}/app/advanced-analytics/analyses/{job_id}'
        print(f'\tTo further check your job status you can either go to {j_url} ' +
              'or repeat the command you just used.')
    except BadRequestException as e:
        raise ValueError(f"Job '{job_id}' not found or not accessible. {str(e)}")
    except Exception as e:
        raise ValueError(f"Failed to retrieve working directory for job '{job_id}'. {str(e)}")


@job.command('workdir')
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
@click.option('--link',
              help='Link the working directory to an interactive session.',
              is_flag=True)
@click.option('--delete',
              help='Delete the results directory of a CloudOS job.',
              is_flag=True)
@click.option('-y', '--yes',
              help='Skip confirmation prompt when deleting results.',
              is_flag=True)
@click.option('--session-id',
              help='The specific CloudOS interactive session id. Required when using --link flag.',
              required=False)
@click.option('--status',
              help='Check the deletion status of the working directory.',
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
@with_profile_config(required_params=['apikey', 'workspace_id'])
def job_workdir(ctx,
                apikey,
                cloudos_url,
                workspace_id,
                job_id,
                link,
                delete,
                yes,
                session_id,
                status,
                verbose,
                disable_ssl_verification,
                ssl_cert,
                profile):
    """Get the path to the working directory of a specified job or check deletion status."""
    # apikey, cloudos_url, and workspace_id are now automatically resolved by the decorator
    # session_id is also resolved if provided in profile

    verify_ssl = ssl_selector(disable_ssl_verification, ssl_cert)

    # Handle --status flag
    if status:
        console = Console()
        
        if verbose:
            console.print('[bold cyan]Checking deletion status of job working directory...[/bold cyan]')
            console.print('\t[dim]...Preparing objects[/dim]')
            console.print('\t[bold]Using the following parameters:[/bold]')
            console.print(f'\t\t[cyan]CloudOS url:[/cyan] {cloudos_url}')
            console.print(f'\t\t[cyan]Workspace ID:[/cyan] {workspace_id}')
            console.print(f'\t\t[cyan]Job ID:[/cyan] {job_id}')
        
        # Use Cloudos object to access the deletion status method
        cl = Cloudos(cloudos_url, apikey, None)
        
        if verbose:
            console.print('\t[dim]The following Cloudos object was created:[/dim]')
            console.print('\t' + str(cl) + '\n')
        
        try:
            deletion_status = cl.get_workdir_deletion_status(
                job_id=job_id,
                workspace_id=workspace_id,
                verify=verify_ssl
            )
            
            # Convert API status to user-friendly terminology with color
            status_config = {
                "ready": ("available", "green"),
                "deleting": ("deleting", "yellow"),
                "scheduledForDeletion": ("scheduled for deletion", "yellow"),
                "deleted": ("deleted", "red"),
                "failedToDelete": ("failed to delete", "red")
            }
            
            # Get the status of the workdir folder itself and convert it
            api_status = deletion_status.get("status", "unknown")
            folder_status, status_color = status_config.get(api_status, (api_status, "white"))
            folder_info = deletion_status.get("items", {})
            
            # Display results in a clear, styled format with human-readable sentence
            console.print(f'The working directory of job [cyan]{deletion_status["job_id"]}[/cyan] is in status: [bold {status_color}]{folder_status}[/bold {status_color}]')
            
            # For non-available statuses, always show update time and user info
            if folder_status != "available":
                if folder_info.get("updatedAt"):
                    console.print(f'[magenta]Status changed at:[/magenta] {folder_info.get("updatedAt")}')
                
                # Show user information - prefer deletedBy over user field
                user_info = folder_info.get("deletedBy") or folder_info.get("user", {})
                if user_info:
                    user_name = f"{user_info.get('name', '')} {user_info.get('surname', '')}".strip()
                    user_email = user_info.get('email', '')
                    if user_name or user_email:
                        user_display = f'{user_name} ({user_email})' if user_name and user_email else (user_name or user_email)
                        console.print(f'[blue]User:[/blue] {user_display}')
            
            # Display detailed information if verbose
            if verbose:
                console.print(f'\n[bold]Additional information:[/bold]')
                console.print(f'  [cyan]Job name:[/cyan] {deletion_status["job_name"]}')
                console.print(f'  [cyan]Working directory folder name:[/cyan] {deletion_status["workdir_folder_name"]}')
                console.print(f'  [cyan]Working directory folder ID:[/cyan] {deletion_status["workdir_folder_id"]}')
                
                # Show folder metadata if available
                if folder_info.get("createdAt"):
                    console.print(f'  [cyan]Created at:[/cyan] {folder_info.get("createdAt")}')
                if folder_info.get("updatedAt"):
                    console.print(f'  [cyan]Updated at:[/cyan] {folder_info.get("updatedAt")}')
                if folder_info.get("folderType"):
                    console.print(f'  [cyan]Folder type:[/cyan] {folder_info.get("folderType")}')
        
        except ValueError as e:
            raise click.ClickException(str(e))
        except Exception as e:
            raise click.ClickException(f"Failed to retrieve deletion status: {str(e)}")
        
        return

    # Validate link flag requirements AFTER loading profile
    if link and not session_id:
        raise click.ClickException("--session-id is required when using --link flag")

    print('Finding working directory path...')
    if verbose:
        print('\t...Preparing objects')
        print('\tUsing the following parameters:')
        print(f'\t\tCloudOS url: {cloudos_url}')
        print(f'\t\tWorkspace ID: {workspace_id}')
        print(f'\t\tJob ID: {job_id}')
        if link:
            print(f'\t\tSession ID: {session_id}')
    cl = Cloudos(cloudos_url, apikey, None)
    if verbose:
        print('\tThe following Cloudos object was created:')
        print('\t' + str(cl) + '\n')
        print(f'\tSearching for job id: {job_id}')
    try:
        workdir = cl.get_job_workdir(job_id, workspace_id, verify_ssl)
        print(f"Working directory for job {job_id}: {workdir}")
        
        # Link to interactive session if requested
        if link:
            if verbose:
                print(f'\tLinking working directory to interactive session {session_id}...')
            
            # Use Link class to perform the linking
            link_client = Link(
                cloudos_url=cloudos_url,
                apikey=apikey,
                cromwell_token=None,  # Not needed for linking operations
                workspace_id=workspace_id,
                project_name=None,  # Not needed for S3 paths
                verify=verify_ssl
            )
            
            link_client.link_folder(workdir.strip(), session_id)
            
    except BadRequestException as e:
        raise ValueError(f"Job '{job_id}' not found or not accessible. {str(e)}")
    except Exception as e:
        raise ValueError(f"Failed to retrieve working directory for job '{job_id}'. {str(e)}")

    # Delete workdir directory if requested
    if delete:
        try:
            # Ask for confirmation unless --yes flag is provided
            if not yes:
                confirmation_message = (
                    "\n⚠️ Deleting intermediate results is permanent and cannot be undone. "
                    "All associated data will be permanently removed and cannot be recovered. "
                    "The current job, as well as any other jobs sharing the same working directory, "
                    "will no longer be resumable. This action will be logged in the audit trail "
                    "(if auditing is enabled for your organisation), and you will be recorded as "
                    "the user who performed the deletion. You can skip this confirmation step by "
                    "providing -y or --yes flag to cloudos job workdir --delete. Please confirm "
                    "that you want to delete intermediate results of this analysis? [y/n] "
                )
                click.secho(confirmation_message, fg='black', bg='yellow')
                user_input = input().strip().lower()
                if user_input != 'y':
                    print('\nDeletion cancelled.')
                    return
            # Proceed with deletion
            job = jb.Job(cloudos_url, apikey, None, workspace_id, None, None, workflow_id=1234, project_id="None",
                        mainfile=None, importsfile=None, verify=verify_ssl)
            job.delete_job_results(job_id, "workDirectory", verify=verify_ssl)
            click.secho('\nIntermediate results directories deleted successfully.', fg='green', bold=True)
        except BadRequestException as e:
            raise ValueError(f"Job '{job_id}' not found or not accessible. {str(e)}")
        except Exception as e:
            raise ValueError(f"Failed to retrieve intermediate results for job '{job_id}'. {str(e)}")
    else:
        if yes:
            click.secho("\n'--yes' flag is ignored when '--delete' is not specified.", fg='yellow', bold=True)


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
@click.option('--link',
              help='Link the logs directories to an interactive session.',
              is_flag=True)
@click.option('--session-id',
              help='The specific CloudOS interactive session id. Required when using --link flag.',
              required=False)
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
@with_profile_config(required_params=['apikey', 'workspace_id'])
def job_logs(ctx,
             apikey,
             cloudos_url,
             workspace_id,
             job_id,
             link,
             session_id,
             verbose,
             disable_ssl_verification,
             ssl_cert,
             profile):
    """Get the path to the logs of a specified job."""
    # apikey, cloudos_url, and workspace_id are now automatically resolved by the decorator
    # session_id is also resolved if provided in profile

    # Validate link flag requirements AFTER loading profile
    if link and not session_id:
        raise click.ClickException("--session-id is required when using --link flag")

    print('Executing logs...')
    verify_ssl = ssl_selector(disable_ssl_verification, ssl_cert)
    if verbose:
        print('\t...Preparing objects')
        print('\tUsing the following parameters:')
        print(f'\t\tCloudOS url: {cloudos_url}')
        print(f'\t\tWorkspace ID: {workspace_id}')
        print(f'\t\tJob ID: {job_id}')
        if link:
            print(f'\t\tSession ID: {session_id}')
    cl = Cloudos(cloudos_url, apikey, None)
    if verbose:
        print('\tThe following Cloudos object was created:')
        print('\t' + str(cl) + '\n')
        print(f'\tSearching for job id: {job_id}')
    try:
        logs = cl.get_job_logs(job_id, workspace_id, verify_ssl)
        for name, path in logs.items():
            print(f"{name}: {path}")
        
        # Link to interactive session if requested
        if link:
            if logs:
                # Extract the parent logs directory from any log file path
                # All log files should be in the same logs directory
                first_log_path = next(iter(logs.values()))
                # Remove the filename to get the logs directory
                # e.g., "s3://bucket/path/to/logs/filename.txt" -> "s3://bucket/path/to/logs"
                logs_dir = '/'.join(first_log_path.split('/')[:-1])
                
                if verbose:
                    print(f'\tLinking logs directory to interactive session {session_id}...')
                    print(f'\t\tLogs directory: {logs_dir}')
                
                # Use Link class to perform the linking
                link_client = Link(
                    cloudos_url=cloudos_url,
                    apikey=apikey,
                    cromwell_token=None,  # Not needed for linking operations
                    workspace_id=workspace_id,
                    project_name=None,  # Not needed for S3 paths
                    verify=verify_ssl
                )
                
                link_client.link_folder(logs_dir, session_id)
            else:
                if verbose:
                    print('\tNo logs found to link.')
            
    except BadRequestException as e:
        raise ValueError(f"Job '{job_id}' not found or not accessible. {str(e)}")
    except Exception as e:
        raise ValueError(f"Failed to retrieve logs for job '{job_id}'. {str(e)}")


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
@click.option('--link',
              help='Link the results directories to an interactive session.',
              is_flag=True)
@click.option('--delete',
              help='Delete the results directory of a CloudOS job.',
              is_flag=True)
@click.option('-y', '--yes',
              help='Skip confirmation prompt when deleting results.',
              is_flag=True)
@click.option('--session-id',
              help='The specific CloudOS interactive session id. Required when using --link flag.',
              required=False)
@click.option('--status',
              help='Check the deletion status of the job results.',
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
@with_profile_config(required_params=['apikey', 'workspace_id'])
def job_results(ctx,
                apikey,
                cloudos_url,
                workspace_id,
                job_id,
                link,
                delete,
                yes,
                session_id,
                status,
                verbose,
                disable_ssl_verification,
                ssl_cert,
                profile):
    """Get the path to the results of a specified job or check deletion status."""
    # apikey, cloudos_url, and workspace_id are now automatically resolved by the decorator
    # session_id is also resolved if provided in profile

    verify_ssl = ssl_selector(disable_ssl_verification, ssl_cert)

    # Handle --status flag
    if status:
        console = Console()
        
        if verbose:
            console.print('[bold cyan]Checking deletion status of job results...[/bold cyan]')
            console.print('\t[dim]...Preparing objects[/dim]')
            console.print('\t[bold]Using the following parameters:[/bold]')
            console.print(f'\t\t[cyan]CloudOS url:[/cyan] {cloudos_url}')
            console.print(f'\t\t[cyan]Workspace ID:[/cyan] {workspace_id}')
            console.print(f'\t\t[cyan]Job ID:[/cyan] {job_id}')
        
        # Use Cloudos object to access the deletion status method
        cl = Cloudos(cloudos_url, apikey, None)
        
        if verbose:
            console.print('\t[dim]The following Cloudos object was created:[/dim]')
            console.print('\t' + str(cl) + '\n')
        
        try:
            deletion_status = cl.get_results_deletion_status(
                job_id=job_id,
                workspace_id=workspace_id,
                verify=verify_ssl
            )
            
            # Convert API status to user-friendly terminology with color
            status_config = {
                "ready": ("available", "green"),
                "deleting": ("deleting", "yellow"),
                "scheduledForDeletion": ("scheduled for deletion", "yellow"),
                "deleted": ("deleted", "red"),
                "failedToDelete": ("failed to delete", "red")
            }
            
            # Get the status of the results folder itself and convert it
            api_status = deletion_status.get("status", "unknown")
            folder_status, status_color = status_config.get(api_status, (api_status, "white"))
            folder_info = deletion_status.get("items", {})
            
            # Display results in a clear, styled format with human-readable sentence
            console.print(f'The results of job [cyan]{deletion_status["job_id"]}[/cyan] are in status: [bold {status_color}]{folder_status}[/bold {status_color}]')
            
            # For non-available statuses, always show update time and user info
            if folder_status != "available":
                if folder_info.get("updatedAt"):
                    console.print(f'[magenta]Status changed at:[/magenta] {folder_info.get("updatedAt")}')
                
                # Show user information - prefer deletedBy over user field
                user_info = folder_info.get("deletedBy") or folder_info.get("user", {})
                if user_info:
                    user_name = f"{user_info.get('name', '')} {user_info.get('surname', '')}".strip()
                    user_email = user_info.get('email', '')
                    if user_name or user_email:
                        user_display = f'{user_name} ({user_email})' if user_name and user_email else (user_name or user_email)
                        console.print(f'[blue]User:[/blue] {user_display}')
            
            # Display detailed information if verbose
            if verbose:
                console.print(f'\n[bold]Additional information:[/bold]')
                console.print(f'  [cyan]Job name:[/cyan] {deletion_status["job_name"]}')
                console.print(f'  [cyan]Results folder name:[/cyan] {deletion_status["results_folder_name"]}')
                console.print(f'  [cyan]Results folder ID:[/cyan] {deletion_status["results_folder_id"]}')
                
                # Show folder metadata if available
                if folder_info.get("createdAt"):
                    console.print(f'  [cyan]Created at:[/cyan] {folder_info.get("createdAt")}')
                if folder_info.get("updatedAt"):
                    console.print(f'  [cyan]Updated at:[/cyan] {folder_info.get("updatedAt")}')
                if folder_info.get("folderType"):
                    console.print(f'  [cyan]Folder type:[/cyan] {folder_info.get("folderType")}')
        
        except ValueError as e:
            raise click.ClickException(str(e))
        except Exception as e:
            raise click.ClickException(f"Failed to retrieve deletion status: {str(e)}")
        
        return

    # Validate link flag requirements AFTER loading profile
    if link and not session_id:
        raise click.ClickException("--session-id is required when using --link flag")

    print('Executing results...')
    if verbose:
        print('\t...Preparing objects')
        print('\tUsing the following parameters:')
        print(f'\t\tCloudOS url: {cloudos_url}')
        print(f'\t\tWorkspace ID: {workspace_id}')
        print(f'\t\tJob ID: {job_id}')
        if link:
            print(f'\t\tSession ID: {session_id}')
    cl = Cloudos(cloudos_url, apikey, None)
    if verbose:
        print('\tThe following Cloudos object was created:')
        print('\t' + str(cl) + '\n')
        print(f'\tSearching for job id: {job_id}')
    try:
        results_path = cl.get_job_results(job_id, workspace_id, verify_ssl)
        print(f"results: {results_path}")

        # Link to interactive session if requested
        if link:
            if verbose:
                print(f'\tLinking results directory to interactive session {session_id}...')

            # Use Link class to perform the linking
            link_client = Link(
                cloudos_url=cloudos_url,
                apikey=apikey,
                cromwell_token=None,  # Not needed for linking operations
                workspace_id=workspace_id,
                project_name=None,  # Not needed for S3 paths
                verify=verify_ssl
            )

            if verbose:
                print(f'\t\tLinking results ({results_path})...')
            
            link_client.link_folder(results_path, session_id)

        # Delete results directory if requested
        if delete:
            # Ask for confirmation unless --yes flag is provided
            if not yes:
                confirmation_message = (
                    "\n⚠️ Deleting final analysis results is irreversible. "
                    "All data and backups will be permanently removed and cannot be recovered. "
                    "You can skip this confirmation step by providing '-y' or '--yes' flag to "
                    "'cloudos job results --delete'. "
                    "Please confirm that you want to delete final results of this analysis? [y/n] "
                )
                click.secho(confirmation_message, fg='black', bg='yellow')
                user_input = input().strip().lower()
                if user_input != 'y':
                    print('\nDeletion cancelled.')
                    return
            if verbose:
                print(f'\nDeleting result directories from CloudOS...')
            # Proceed with deletion
            job = jb.Job(cloudos_url, apikey, None, workspace_id, None, None, workflow_id=1234, project_id="None",
                        mainfile=None, importsfile=None, verify=verify_ssl)
            job.delete_job_results(job_id, "analysisResults", verify=verify_ssl)
            click.secho('\nResults directories deleted successfully.', fg='green', bold=True)
        else:
            if yes:
                click.secho("\n'--yes' flag is ignored when '--delete' is not specified.", fg='yellow', bold=True)
    except BadRequestException as e:
        raise ValueError(f"Job '{job_id}' not found or not accessible. {str(e)}")
    except Exception as e:
        raise ValueError(f"Failed to retrieve results for job '{job_id}'. {str(e)}")


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
@click.option('--workspace-id',
              help='The specific CloudOS workspace id.',
              required=True)
@click.option('--job-id',
              help='The job id in CloudOS to search for.',
              required=True)
@click.option('--output-format',
              help=('The desired display for the output, either directly in standard output or saved as file. ' +
                    'Default=stdout.'),
              type=click.Choice(['stdout', 'csv', 'json'], case_sensitive=False),
              default='stdout')
@click.option('--output-basename',
              help=('Output file base name to save jobs details. ' +
                    'Default={job_id}_details'),
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
@with_profile_config(required_params=['apikey', 'workspace_id'])
def job_details(ctx,
                apikey,
                cloudos_url,
                workspace_id,
                job_id,
                output_format,
                output_basename,
                parameters,
                verbose,
                disable_ssl_verification,
                ssl_cert,
                profile):
    """Retrieve job details in CloudOS."""
    # apikey, cloudos_url, and workspace_id are now automatically resolved by the decorator

    if ctx.get_parameter_source('output_basename') == click.core.ParameterSource.DEFAULT:
        output_basename = f"{job_id}_details"

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
        j_details = cl.get_job_status(job_id, workspace_id, verify_ssl)
    except BadRequestException as e:
        if '403' in str(e) or 'Forbidden' in str(e):
            raise ValueError("API can only show job details of your own jobs, cannot see other user's job details.")
        else:
            raise ValueError(f"Job '{job_id}' not found or not accessible. {str(e)}")
    except Exception as e:
        raise ValueError(f"Failed to retrieve details for job '{job_id}'. {str(e)}")
    create_job_details(json.loads(j_details.content), job_id, output_format, output_basename, parameters, cloudos_url)


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
              help='The desired output format. For json option --all-fields will be automatically set to True. Default=stdout.',
              type=click.Choice(['stdout', 'csv', 'json'], case_sensitive=False),
              default='stdout')
@click.option('--table-columns',
              help=('Comma-separated list of columns to display in the table. Only applicable when --output-format=stdout. ' +
                    'Available columns: status,name,project,owner,pipeline,id,submit_time,end_time,run_time,commit,cost,resources,storage_type. ' +
                    'Default: responsive (auto-selects columns based on terminal width)'),
              default=None)
@click.option('--all-fields',
              help=('Whether to collect all available fields from jobs or ' +
                    'just the preconfigured selected fields. Only applicable ' +
                    'when --output-format=csv. Automatically enabled for json output.'),
              is_flag=True)
@click.option('--last-n-jobs',
              help=("The number of last workspace jobs to retrieve. You can use 'all' to " +
                    "retrieve all workspace jobs. When adding this option, options " +
                    "'--page' and '--page-size' are ignored."))
@click.option('--page',
              help=('Page number to fetch from the API. Used with --page-size to control jobs ' +
                    'per page (e.g. --page=4 --page-size=20). Default=1.'),
              type=int,
              default=1)
@click.option('--page-size',
              help=('Page size to retrieve from API, corresponds to the number of jobs per page. ' +
                    'Maximum allowed integer is 100. Default=10.'),
              type=int,
              default=10)
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
@click.option('--filter-owner',
              help='Filter jobs by owner username.')
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
@with_profile_config(required_params=['apikey', 'workspace_id'])
def list_jobs(ctx,
              apikey,
              cloudos_url,
              workspace_id,
              output_basename,
              output_format,
              table_columns,
              all_fields,
              last_n_jobs,
              page,
              page_size,
              archived,
              filter_status,
              filter_job_name,
              filter_project,
              filter_workflow,
              last,
              filter_job_id,
              filter_only_mine,
              filter_owner,
              filter_queue,
              verbose,
              disable_ssl_verification,
              ssl_cert,
              profile):
    """Collect and display workspace jobs from a CloudOS workspace."""
    # apikey, cloudos_url, and workspace_id are now automatically resolved by the decorator

    verify_ssl = ssl_selector(disable_ssl_verification, ssl_cert)
    
    # Pass table_columns directly to create_job_list_table for validation and processing
    selected_columns = table_columns
    # Only set outfile if not using stdout
    if output_format != 'stdout':
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

    if not isinstance(page_size, int) or page_size < 1:
        raise ValueError('Please, use a positive integer (>= 1) for the --page-size parameter')
    
    # Validate page_size limit - must be done before API call
    if page_size > 100:
        click.secho('Error: Page size cannot exceed 100. Please use --page-size with a value <= 100', fg='red', err=True)
        raise SystemExit(1)

    result = cl.get_job_list(workspace_id, last_n_jobs, page, page_size, archived, verify_ssl,
                             filter_status=filter_status,
                             filter_job_name=filter_job_name,
                             filter_project=filter_project,
                             filter_workflow=filter_workflow,
                             filter_job_id=filter_job_id,
                             filter_only_mine=filter_only_mine,
                             filter_owner=filter_owner,
                             filter_queue=filter_queue,
                             last=last)
    
    # Extract jobs and pagination metadata from result
    my_jobs_r = result['jobs']
    pagination_metadata = result['pagination_metadata']
    
    # Validate requested page exists
    if pagination_metadata:
        total_jobs = pagination_metadata.get('Pagination-Count', 0)
        current_page_size = pagination_metadata.get('Pagination-Limit', page_size)
        
        if total_jobs > 0:
            total_pages = (total_jobs + current_page_size - 1) // current_page_size
            if page > total_pages:
                click.secho(f'Error: Page {page} does not exist. There are only {total_pages} page(s) available with {total_jobs} total job(s). '
                           f'Please use --page with a value between 1 and {total_pages}', fg='red', err=True)
                raise SystemExit(1)
    
    if len(my_jobs_r) == 0:
        # Check if any filtering options are being used
        filters_used = any([
            filter_status,
            filter_job_name,
            filter_project,
            filter_workflow,
            filter_job_id,
            filter_only_mine,
            filter_owner,
            filter_queue
        ])
        if output_format == 'stdout':
            # For stdout, always show a user-friendly message
            create_job_list_table([], cloudos_url, pagination_metadata, selected_columns)
        else:
            if filters_used:
                print('A total of 0 jobs collected.')
            elif ctx.get_parameter_source('page') == click.core.ParameterSource.DEFAULT:
                print('A total of 0 jobs collected. This is likely because your workspace ' +
                      'has no jobs created yet.')
            else:
                print('A total of 0 jobs collected. This is likely because the --page you requested ' +
                      'does not exist. Please, try a smaller number for --page or collect all the jobs by not ' +
                      'using --page parameter.')
    elif output_format == 'stdout':
        # Display as table
        create_job_list_table(my_jobs_r, cloudos_url, pagination_metadata, selected_columns)
    elif output_format == 'csv':
        my_jobs = cl.process_job_list(my_jobs_r, all_fields)
        cl.save_job_list_to_csv(my_jobs, outfile)
    elif output_format == 'json':
        with open(outfile, 'w') as o:
            o.write(json.dumps(my_jobs_r))
        print(f'\tJob list collected with a total of {len(my_jobs_r)} jobs.')
        print(f'\tJob list saved to {outfile}')
    else:
        raise ValueError('Unrecognised output format. Please use one of [stdout|csv|json]')


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
@with_profile_config(required_params=['apikey', 'workspace_id'])
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
    # apikey, cloudos_url, and workspace_id are now automatically resolved by the decorator

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
            j_status = cl.get_job_status(job, workspace_id, verify_ssl)
        except Exception as e:
            click.secho(f"Failed to get status for job {job}, please make sure it exists in the workspace: {e}", fg='yellow', bold=True)
            continue
        j_status_content = json.loads(j_status.content)
        # check if job id is valid & is in working state (initial, running)
        if j_status_content['status'] not in ABORT_JOB_STATES:
            click.secho(f"Job {job} is not in a state that can be aborted and is ignored. " +
                  f"Current status: {j_status_content['status']}", fg='yellow', bold=True)
        else:
            cl.abort_job(job, workspace_id, verify_ssl)
            click.secho(f"Job '{job}' aborted successfully.", fg='green', bold=True)


@job.command('cost')
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
              help='The job id in CloudOS to get costs for.',
              required=True)
@click.option('--output-format',
              help='The desired file format (file extension) for the output. For json option --all-fields will be automatically set to True. Default=csv.',
              type=click.Choice(['stdout', 'csv', 'json'], case_sensitive=False),
              default='stdout')
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
@with_profile_config(required_params=['apikey', 'workspace_id'])
def job_cost(ctx,
             apikey,
             cloudos_url,
             workspace_id,
             job_id,
             output_format,
             verbose,
             disable_ssl_verification,
             ssl_cert,
             profile):
    """Retrieve job cost information in CloudOS."""
    # apikey, cloudos_url, and workspace_id are now automatically resolved by the decorator

    print('Retrieving cost information...')
    verify_ssl = ssl_selector(disable_ssl_verification, ssl_cert)
    if verbose:
        print('\t...Preparing objects')
    cost_viewer = CostViewer(cloudos_url, apikey)
    if verbose:
        print(f'\tSearching for cost data for job id: {job_id}')
    # Display costs with pagination
    cost_viewer.display_costs(job_id, workspace_id, output_format, verify_ssl)


@job.command('related')
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
              help='The job id in CloudOS to get costs for.',
              required=True)
@click.option('--output-format',
              help='The desired output format. Default=stdout.',
              type=click.Choice(['stdout', 'json'], case_sensitive=False),
              default='stdout')
@click.option('--disable-ssl-verification',
              help=('Disable SSL certificate verification. Please, remember that this option is ' +
                    'not generally recommended for security reasons.'),
              is_flag=True)
@click.option('--ssl-cert',
              help='Path to your SSL certificate file.')
@click.option('--profile', help='Profile to use from the config file', default=None)
@click.pass_context
@with_profile_config(required_params=['apikey', 'workspace_id'])
def related(ctx,
            apikey,
            cloudos_url,
            workspace_id,
            job_id,
            output_format,
            disable_ssl_verification,
            ssl_cert,
            profile):
    """Retrieve related job analyses in CloudOS."""
    verify_ssl = ssl_selector(disable_ssl_verification, ssl_cert)
    related_analyses(cloudos_url, apikey, job_id, workspace_id, output_format, verify_ssl)


@click.command(help='Clone or resume a job with modified parameters')
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
@click.option('--repository-platform', type=click.Choice(["github", "gitlab", "bitbucketServer"]),
              help='Name of the repository platform of the workflow. Default=github.',
              default='github')
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
@click.option('--accelerate-saving-results',
              help='Enables saving results directly to cloud storage bypassing the master node.',
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
@with_profile_config(required_params=['apikey', 'workspace_id'])
def clone_resume(ctx,
                 apikey,
                 cloudos_url,
                 workspace_id,
                 project_name,
                 parameter,
                 nextflow_profile,
                 nextflow_version,
                 git_branch,
                 repository_platform,
                 job_name,
                 do_not_save_logs,
                 job_queue,
                 instance_type,
                 cost_limit,
                 job_id,
                 accelerate_file_staging,
                 accelerate_saving_results,
                 resumable,
                 verbose,
                 disable_ssl_verification,
                 ssl_cert,
                 profile):

    # apikey, cloudos_url, and workspace_id are now automatically resolved by the decorator
    if ctx.info_name == "clone":
        mode, action = "clone", "cloning"
    elif ctx.info_name == "resume":
        mode, action = "resume", "resuming"

    verify_ssl = ssl_selector(disable_ssl_verification, ssl_cert)

    print(f'{action.capitalize()} job...')
    if verbose:
        print('\t...Preparing objects')

    # Create Job object (set dummy values for project_name and workflow_name, since they come from the cloned job)
    job_obj = jb.Job(cloudos_url, apikey, None, workspace_id, None, None, workflow_id=1234, project_id="None",
                     mainfile=None, importsfile=None, verify=verify_ssl)

    if verbose:
        print('\tThe following Job object was created:')
        print('\t' + str(job_obj) + '\n')
        print(f'\t{action.capitalize()} job {job_id} in workspace: {workspace_id}')

    try:

        # Clone/resume the job with provided overrides
        cloned_resumed_job_id = job_obj.clone_or_resume_job(
            source_job_id=job_id,
            queue_name=job_queue,
            cost_limit=cost_limit,
            master_instance=instance_type,
            job_name=job_name,
            nextflow_version=nextflow_version,
            branch=git_branch,
            repository_platform=repository_platform,
            profile=nextflow_profile,
            do_not_save_logs=do_not_save_logs,
            use_fusion=accelerate_file_staging,
            accelerate_saving_results=accelerate_saving_results,
            resumable=resumable,
            # only when explicitly setting --project-name will be overridden, else using the original project
            project_name=project_name if ctx.get_parameter_source("project_name") == click.core.ParameterSource.COMMANDLINE else None,
            parameters=list(parameter) if parameter else None,
            verify=verify_ssl,
            mode=mode
        )

        if verbose:
            print(f'\t{mode.capitalize()}d job ID: {cloned_resumed_job_id}')

        print(f"Job successfully {mode}d. New job ID: {cloned_resumed_job_id}")

    except BadRequestException as e:
        raise ValueError(f"Failed to {mode} job. Job '{job_id}' not found or not accessible. {str(e)}")
    except Exception as e:
        raise ValueError(f"Failed to {mode} job. Failed to {action} job '{job_id}'. {str(e)}")


# Apply the best Click solution: Set specific help text for each command registration
clone_resume.help = 'Clone a job with modified parameters'
job.add_command(clone_resume, "clone")

# Create a copy with different help text for resume
import copy
clone_resume_copy = copy.deepcopy(clone_resume)
clone_resume_copy.help = 'Resume a job with modified parameters'
job.add_command(clone_resume_copy, "resume")


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
@with_profile_config(required_params=['apikey', 'workspace_id'])
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
    # apikey, cloudos_url, and workspace_id are now automatically resolved by the decorator

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
@with_profile_config(required_params=['apikey', 'workspace_id', 'workflow_name'])
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
    # apikey, cloudos_url, and workspace_id are now automatically resolved by the decorator

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
@with_profile_config(required_params=['apikey', 'workspace_id'])
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
    # apikey, cloudos_url, and workspace_id are now automatically resolved by the decorator

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
            print('A total of 0 projects collected. This is likely because your workspace ' +
                  'has no projects created yet.')
        else:
            print('A total of 0 projects collected. This is likely because the --page you ' +
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
@with_profile_config(required_params=['apikey', 'workspace_id'])
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
    # apikey, cloudos_url, and workspace_id are now automatically resolved by the decorator

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
@with_profile_config(required_params=['cloudos_url', 'workspace_id'])
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
    # apikey, cloudos_url, and workspace_id are now automatically resolved by the decorator

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
@with_profile_config(required_params=['cloudos_url', 'workspace_id'])
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
    # apikey, cloudos_url, and workspace_id are now automatically resolved by the decorator

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
@with_profile_config(required_params=['cloudos_url', 'workspace_id'])
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
    # apikey, cloudos_url, and workspace_id are now automatically resolved by the decorator

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
@with_profile_config(required_params=['apikey', 'workspace_id'])
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
    # apikey, cloudos_url, and workspace_id are now automatically resolved by the decorator

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
    update_command_context_from_click(ctx)
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
@click.option('--accelerate-saving-results',
              help='Enables saving results directly to cloud storage bypassing the master node.',
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
@with_profile_config(required_params=['apikey', 'workspace_id', 'workflow_name', 'project_name'])
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
                 accelerate_saving_results,
                 request_interval,
                 disable_ssl_verification,
                 ssl_cert,
                 profile):
    """Run a bash job in CloudOS."""
    # apikey, cloudos_url, and workspace_id are now automatically resolved by the decorator

    verify_ssl = ssl_selector(disable_ssl_verification, ssl_cert)

    if instance_type == 'NONE_SELECTED':
        if execution_platform == 'aws':
            instance_type = 'c5.xlarge'
        elif execution_platform == 'azure':
            instance_type = 'Standard_D4as_v4'
        else:
            instance_type = None

    if do_not_save_logs:
        save_logs = False
    else:
        save_logs = True

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
                      accelerate_saving_results=accelerate_saving_results,
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
                                         workspace_id=workspace_id,
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
        j_status = j.get_job_status(j_id, workspace_id, verify_ssl)
        j_status_h = json.loads(j_status.content)["status"]
        print(f'\tYour current job status is: {j_status_h}')
        print('\tTo further check your job status you can either go to ' +
              f'{j_url} or use the following command:\n' +
              '\tcloudos job status \\\n' +
              f'\t\t--profile my_profile \\\n' +
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
@click.option('--accelerate-saving-results',
              help='Enables saving results directly to cloud storage bypassing the master node.',
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
              help=('A single parameter to pass to the job call only for specifying array columns. ' +
                    'It should be in the following form: parameter_name=array_file_column_name. E.g.: ' +
                    '-a --test=value or -a -test=value or -a test=value or -a =value (for no prefix). ' +
                    'You can use this option as many times as parameters you want to include.'))
@click.option('--custom-script-path',
              help=('Path of a custom script to run in the bash array job instead of a command.'),
              default=None)
@click.option('--custom-script-project',
              help=('Name of the project to use when running the custom command script, if ' +
                    'different than --project-name.'),
              default=None)
@click.pass_context
@with_profile_config(required_params=['apikey', 'workspace_id', 'workflow_name', 'project_name'])
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
                       accelerate_saving_results,
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
        ",": {"api": ",", "file": ","},
        ";": {"api": "%3B", "file": ";"},
        "space": {"api": "+", "file": " "},
        "tab": {"api": "tab", "file": "tab"},
        "|": {"api": "%7C", "file": "|"}
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
                raise ValueError(f"Column '{ap_value}' not found in the array file. " + \
                                 f"Columns in array-file: {separator.join([col['name'] for col in columns])}")

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
                      accelerate_saving_results=accelerate_saving_results,
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
                                         workspace_id=workspace_id,
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
        j_status = j.get_job_status(j_id, workspace_id, verify_ssl)
        j_status_h = json.loads(j_status.content)["status"]
        print(f'\tYour current job status is: {j_status_h}')
        print('\tTo further check your job status you can either go to ' +
              f'{j_url} or use the following command:\n' +
              '\tcloudos job status \\\n' +
              f'\t\t--profile my_profile \\\n' +
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
              help='The name of a CloudOS project.',
              required=True)
@click.option('--profile', help='Profile to use from the config file', default=None)
@click.option('--details',
              help=('When selected, it prints the details of the listed files. ' +
                    'Details contains "Type", "Owner", "Size", "Last Updated", ' +
                    '"Virtual Name", "Storage Path".'),
              is_flag=True)
@click.option('--output-format',
              help=('The desired display for the output, either directly in standard output or saved as file. ' +
                    'Default=stdout.'),
              type=click.Choice(['stdout', 'csv'], case_sensitive=False),
              default='stdout')
@click.option('--output-basename',
              help=('Output file base name to save jobs details. ' +
                    'Default=datasets_ls'),
              default='datasets_ls',
              required=False)
@click.pass_context
@with_profile_config(required_params=['apikey', 'workspace_id', 'project_name'])
def list_files(ctx,
               apikey,
               cloudos_url,
               workspace_id,
               disable_ssl_verification,
               ssl_cert,
               project_name,
               profile,
               path,
               details,
               output_format,
               output_basename):
    """List contents of a path within a CloudOS workspace dataset."""
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

        # Process items to extract data
        processed_items = []
        for item in contents:
            is_folder = "folderType" in item or item.get("isDir", False)
            type_ = "folder" if is_folder else "file"

            # Enhanced type information
            if is_folder:
                folder_type = item.get("folderType")
                if folder_type == "VirtualFolder":
                    type_ = "virtual folder"
                elif folder_type == "S3Folder":
                    type_ = "s3 folder"
                elif folder_type == "AzureBlobFolder":
                    type_ = "azure folder"
                else:
                    type_ = "folder"
            else:
                # Check if file is managed by Lifebit (user uploaded)
                is_managed_by_lifebit = item.get("isManagedByLifebit", False)
                if is_managed_by_lifebit:
                    type_ = "file (user uploaded)"
                else:
                    type_ = "file (virtual copy)"
                    
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
                storage_path = f"s3://{bucket}/{key}" if bucket and key else "-"
            elif item.get("fileType") == "AzureBlobFile" or item.get("folderType") == "AzureBlobFolder":
                account = item.get("blobStorageAccountName")
                container = item.get("blobContainerName")
                key = item.get("blobName") if item.get("fileType") == "AzureBlobFile" else item.get("blobPrefix")
                storage_path = f"az://{account}.blob.core.windows.net/{container}/{key}" if account and container and key else "-"
            else:
                storage_path = "-"

            processed_items.append({
                'type': type_,
                'owner': owner,
                'size': size,
                'raw_size': raw_size,
                'updated': updated,
                'name': filepath,
                'storage_path': storage_path,
                'is_folder': is_folder
            })

        # Output handling
        if output_format == 'csv':
            import csv

            csv_filename = f'{output_basename}.csv'

            if details:
                # CSV with all details
                with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
                    fieldnames = ['Type', 'Owner', 'Size', 'Size (bytes)', 'Last Updated', 'Virtual Name', 'Storage Path']
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()

                    for item in processed_items:
                        writer.writerow({
                            'Type': item['type'],
                            'Owner': item['owner'],
                            'Size': item['size'],
                            'Size (bytes)': item['raw_size'] if item['raw_size'] is not None else '',
                            'Last Updated': item['updated'],
                            'Virtual Name': item['name'],
                            'Storage Path': item['storage_path']
                        })
            else:
                # CSV with just names
                with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(['Name', 'Storage Path'])
                    for item in processed_items:
                        writer.writerow([item['name'], item['storage_path']])

            click.secho(f'\nDatasets list saved to: {csv_filename}', fg='green', bold=True)

        else:  # stdout
            if details:
                console = Console(width=None)
                table = Table(show_header=True, header_style="bold white")
                table.add_column("Type", style="cyan", no_wrap=True)
                table.add_column("Owner", style="white")
                table.add_column("Size", style="magenta")
                table.add_column("Last Updated", style="green")
                table.add_column("Virtual Name", style="bold", overflow="fold")
                table.add_column("Storage Path", style="dim", no_wrap=False, overflow="fold", ratio=2)

                for item in processed_items:
                    style = Style(color="blue", underline=True) if item['is_folder'] else None
                    table.add_row(
                        item['type'],
                        item['owner'],
                        item['size'],
                        item['updated'],
                        item['name'],
                        item['storage_path'],
                        style=style
                    )

                console.print(table)

            else:
                console = Console()
                for item in processed_items:
                    if item['is_folder']:
                        console.print(f"[blue underline]{item['name']}[/]")
                    else:
                        console.print(item['name'])

    except Exception as e:
        raise ValueError(f"Failed to list files for project '{project_name}'. {str(e)}")


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
@with_profile_config(required_params=['apikey', 'workspace_id', 'project_name'])
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
    # Validate destination constraint
    if not destination_path.strip("/").startswith("Data/") and destination_path.strip("/") != "Data":
        raise ValueError("Destination path must begin with 'Data/' or be 'Data'.")
    if not source_path.strip("/").startswith("Data/") and source_path.strip("/") != "Data":
        raise ValueError("SOURCE_PATH must start with  'Data/' or be 'Data'.")

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
    print('Checking source path')
    # === Resolve Source Item ===
    source_parts = source_path.strip("/").split("/")
    source_parent_path = "/".join(source_parts[:-1]) if len(source_parts) > 1 else None
    source_item_name = source_parts[-1]

    try:
        source_contents = source_client.list_folder_content(source_parent_path)
    except Exception as e:
        raise ValueError(f"Could not resolve source path '{source_path}'. {str(e)}")

    found_source = None
    for collection in ["files", "folders"]:
        for item in source_contents.get(collection, []):
            if item.get("name") == source_item_name:
                found_source = item
                break
        if found_source:
            break
    if not found_source:
        raise ValueError(f"Item '{source_item_name}' not found in '{source_parent_path or '[project root]'}'")

    source_id = found_source["_id"]
    source_kind = "Folder" if "folderType" in found_source else "File"
    print("Checking destination path")
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
        elif folder_type == "S3Folder":
            raise ValueError(f"Unable to move item '{source_item_name}' to '{destination_path}'. " +
                       "The destination is an S3 folder, and only virtual folders can be selected as valid move destinations.")
        elif isinstance(folder_type, bool) and folder_type:  # legacy dataset structure
            target_kind = "Dataset"
        else:
            raise ValueError(f"Unrecognized folderType '{folder_type}' for destination '{destination_path}'")

    except Exception as e:
        raise ValueError(f"Could not resolve destination path '{destination_path}'. {str(e)}")
    print(f"Moving {source_kind} '{source_item_name}' to '{destination_path}' " +
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
            click.secho(f"{source_kind} '{source_item_name}' moved to '{destination_path}' " +
                        f"in project '{destination_project_name}'.", fg="green", bold=True)
        else:
            raise ValueError(f"Move failed. {response.status_code} - {response.text}")
    except Exception as e:
        raise ValueError(f"Move operation failed. {str(e)}")


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
@with_profile_config(required_params=['apikey', 'workspace_id', 'project_name'])
def renaming_item(ctx,
                  source_path,
                  new_name,
                  apikey,
                  cloudos_url,
                  workspace_id,
                  project_name,
                  disable_ssl_verification,
                  ssl_cert,
                  profile):
    """
    Rename a file or folder in a CloudOS project.

    SOURCE_PATH [path]: the full path to the file or folder to rename. It must be a 'Data' folder path.
     E.g.: 'Data/folderA/old_name.txt'\n
    NEW_NAME [name]: the new name to assign to the file or folder. E.g.: 'new_name.txt'
    """
    if not source_path.strip("/").startswith("Data/"):
        raise ValueError("SOURCE_PATH must start with 'Data/', pointing to a file or folder in that dataset.")

    verify_ssl = ssl_selector(disable_ssl_verification, ssl_cert)
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
        raise ValueError(f"Could not list contents at '{parent_path or '[project root]'}'. {str(e)}")

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
        raise ValueError(f"Item '{target_name}' not found in '{parent_path or '[project root]'}'")

    item_id = found_item["_id"]
    kind = "Folder" if "folderType" in found_item else "File"

    print(f"Renaming {kind} '{target_name}' to '{new_name}'...")
    try:
        response = client.rename_item(item_id=item_id, new_name=new_name, kind=kind)
        if response.ok:
            click.secho(
                f"{kind} '{target_name}' renamed to '{new_name}' in folder '{parent_path}'.",
                fg="green",
                bold=True
            )
        else:
            raise ValueError(f"Rename failed. {response.status_code} - {response.text}")
    except Exception as e:
        raise ValueError(f"Rename operation failed. {str(e)}")


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
@with_profile_config(required_params=['apikey', 'workspace_id', 'project_name'])
def copy_item_cli(ctx,
                  source_path,
                  destination_path,
                  apikey,
                  cloudos_url,
                  workspace_id,
                  project_name,
                  destination_project_name,
                  disable_ssl_verification,
                  ssl_cert,
                  profile):
    """
    Copy a file or folder (S3 or virtual) from SOURCE_PATH to DESTINATION_PATH.

    SOURCE_PATH [path]: the full path to the file or folder to copy.
     E.g.: AnalysesResults/my_analysis/results/my_plot.png\n
    DESTINATION_PATH [path]: the full path to the destination folder. It must be a 'Data' folder path.
     E.g.: Data/plots
    """
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
        raise ValueError("DESTINATION_PATH must start with 'Data/'.")
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
        raise ValueError(f"Could not access paths. {str(e)}")
    # Find the source item
    source_item = None
    for item in source_content.get('files', []) + source_content.get('folders', []):
        if item.get("name") == source_name:
            source_item = item
            break
    if not source_item:
        raise ValueError(f"Item '{source_name}' not found in '{source_parent or '[project root]'}'")
    # Find the destination folder
    destination_folder = None
    for folder in dest_content.get("folders", []):
        if folder.get("name") == dest_folder_name:
            destination_folder = folder
            break
    if not destination_folder:
        raise ValueError(f"Destination folder '{destination_path}' not found.")
    try:
        # Determine item type
        if "fileType" in source_item:
            item_type = "file"
        elif source_item.get("folderType") == "VirtualFolder":
            item_type = "virtual_folder"
        elif "s3BucketName" in source_item and source_item.get("folderType") == "S3Folder":
            item_type = "s3_folder"
        else:
            raise ValueError("Could not determine item type.")
        print(f"Copying {item_type.replace('_', ' ')} '{source_name}' to '{destination_path}'...")
        if destination_folder.get("folderType") is True and destination_folder.get("kind") in ("Data", "Cohorts", "AnalysesResults"):
            destination_kind = "Dataset"
        elif destination_folder.get("folderType") == "S3Folder":
            raise ValueError(f"Unable to copy item '{source_name}' to '{destination_path}'. The destination is an S3 folder, and only virtual folders can be selected as valid copy destinations.")
        else:
            destination_kind = "Folder"
        response = source_client.copy_item(
            item=source_item,
            destination_id=destination_folder["_id"],
            destination_kind=destination_kind
        )
        if response.ok:
            click.secho("Item copied successfully.", fg="green", bold=True)
        else:
            raise ValueError(f"Copy failed. {response.status_code} - {response.text}")
    except Exception as e:
        raise ValueError(f"Copy operation failed. {str(e)}")


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
@with_profile_config(required_params=['apikey', 'workspace_id', 'project_name'])
def mkdir_item(ctx,
               new_folder_path,
               apikey,
               cloudos_url,
               workspace_id,
               project_name,
               disable_ssl_verification,
               ssl_cert,
               profile):
    """
    Create a virtual folder in a CloudOS project.

    NEW_FOLDER_PATH [path]: Full path to the new folder including its name. Must start with 'Data'.
    """
    new_folder_path = new_folder_path.strip("/")
    if not new_folder_path.startswith("Data"):
        raise ValueError("NEW_FOLDER_PATH must start with 'Data'.")

    path_parts = new_folder_path.split("/")
    if len(path_parts) < 2:
        raise ValueError("NEW_FOLDER_PATH must include at least a parent folder and the new folder name.")

    parent_path = "/".join(path_parts[:-1])
    folder_name = path_parts[-1]

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
        raise ValueError(f"Could not list contents at '{parent_of_parent_path}'. {str(e)}")

    # Find the parent folder in the contents
    folder_info = next(
        (f for f in contents.get("folders", []) if f.get("name") == parent_name),
        None
    )

    if not folder_info:
        raise ValueError(f"Could not find folder '{parent_name}' in '{parent_of_parent_path}'.")

    parent_id = folder_info.get("_id")
    folder_type = folder_info.get("folderType")

    if folder_type is True:
        parent_kind = "Dataset"
    elif isinstance(folder_type, str):
        parent_kind = "Folder"
    else:
        raise ValueError(f"Unrecognized folderType for '{parent_path}'.")

    # Create the folder
    print(f"Creating folder '{folder_name}' under '{parent_path}' ({parent_kind})...")
    try:
        response = client.create_virtual_folder(name=folder_name, parent_id=parent_id, parent_kind=parent_kind)
        if response.ok:
            click.secho(f"Folder '{folder_name}' created under '{parent_path}'", fg="green", bold=True)
        else:
            raise ValueError(f"Folder creation failed. {response.status_code} - {response.text}")
    except Exception as e:
        raise ValueError(f"Folder creation failed. {str(e)}")


@datasets.command(name="rm")
@click.argument("target_path", required=True)
@click.option('-k', '--apikey', required=True, help='Your CloudOS API key.')
@click.option('-c', '--cloudos-url', default=CLOUDOS_URL, required=True, help='The CloudOS URL.')
@click.option('--workspace-id', required=True, help='The CloudOS workspace ID.')
@click.option('--project-name', required=True, help='The project name.')
@click.option('--disable-ssl-verification', is_flag=True, help='Disable SSL certificate verification.')
@click.option('--ssl-cert', help='Path to your SSL certificate file.')
@click.option('--profile', default=None, help='Profile to use from the config file.')
@click.option('--force', is_flag=True, help='Force delete files. Required when deleting user uploaded files. This may also delete the file from the cloud provider storage.')
@click.pass_context
@with_profile_config(required_params=['apikey', 'workspace_id', 'project_name'])
def rm_item(ctx,
            target_path,
            apikey,
            cloudos_url,
            workspace_id,
            project_name,
            disable_ssl_verification,
            ssl_cert,
            profile,
            force):
    """
    Delete a file or folder in a CloudOS project.

    TARGET_PATH [path]: the full path to the file or folder to delete. Must start with 'Data'. \n
    E.g.: 'Data/folderA/file.txt' or 'Data/my_analysis/results/folderB'
    """
    if not target_path.strip("/").startswith("Data/"):
        raise ValueError("TARGET_PATH must start with 'Data/', pointing to a file or folder.")

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
        raise ValueError(f"Could not list contents at '{parent_path or '[project root]'}'. {str(e)}")

    found_item = None
    for item in contents.get('files', []) + contents.get('folders', []):
        if item.get("name") == item_name:
            found_item = item
            break

    if not found_item:
        raise ValueError(f"Item '{item_name}' not found in '{parent_path or '[project root]'}'")

    item_id = found_item.get("_id", '')
    kind = "Folder" if "folderType" in found_item else "File"
    if item_id == '':
        raise ValueError(f"Item '{item_name}' could not be removed as the parent folder is an s3 folder and their content cannot be modified.")
    # Check if the item is managed by Lifebit
    is_managed_by_lifebit = found_item.get("isManagedByLifebit", False)
    if is_managed_by_lifebit and not force:
        raise ValueError("By removing this file, it will be permanently deleted. If you want to go forward, please use the --force flag.")
    print(f"Removing {kind} '{item_name}' from '{parent_path or '[root]'}'...")
    try:
        response = client.delete_item(item_id=item_id, kind=kind)
        if response.ok:
            if is_managed_by_lifebit:
                click.secho(
                    f"{kind} '{item_name}' was permanently deleted from '{parent_path or '[root]'}'.",
                    fg="green", bold=True
                )
            else:
                click.secho(
                    f"{kind} '{item_name}' was removed from '{parent_path or '[root]'}'.",
                    fg="green", bold=True
                )
                click.secho("This item will still be available on your Cloud Provider.", fg="yellow")
        else:
            raise ValueError(f"Removal failed. {response.status_code} - {response.text}")
    except Exception as e:
        raise ValueError(f"Remove operation failed. {str(e)}")


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
@with_profile_config(required_params=['apikey', 'workspace_id', 'session_id'])
def link(ctx,
         path,
         apikey,
         cloudos_url,
         project_name,
         workspace_id,
         session_id,
         disable_ssl_verification,
         ssl_cert,
         profile):
    """
    Link a folder (S3 or File Explorer) to an active interactive analysis.

    PATH [path]: the full path to the S3 folder to link or relative to File Explorer.
    E.g.: 's3://bucket-name/folder/subfolder', 'Data/Downloads' or 'Data'.
    """
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

    # Minimal folder validation and improved error messages
    is_s3 = path.startswith("s3://")
    is_folder = True
    if is_s3:
        # S3 path validation - use heuristics to determine if it's likely a folder
        try:
            # If path ends with '/', it's likely a folder
            if path.endswith('/'):
                is_folder = True
            else:
                # Check the last part of the path
                path_parts = path.rstrip("/").split("/")
                if path_parts:
                    last_part = path_parts[-1]
                    # If the last part has no dot, it's likely a folder
                    if '.' not in last_part:
                        is_folder = True
                    else:
                        # If it has a dot, it might be a file - set to None for warning
                        is_folder = None
                else:
                    # Empty path parts, set to None for uncertainty
                    is_folder = None
        except Exception:
            # If we can't parse the S3 path, set to None for uncertainty
            is_folder = None
    else:
        # File Explorer path validation (existing logic)
        try:
            datasets = Datasets(
                cloudos_url=cloudos_url,
                apikey=apikey,
                workspace_id=workspace_id,
                project_name=project_name,
                verify=verify_ssl,
                cromwell_token=None
            )
            parts = path.strip("/").split("/")
            parent_path = "/".join(parts[:-1]) if len(parts) > 1 else ""
            item_name = parts[-1]
            contents = datasets.list_folder_content(parent_path)
            found = None
            for item in contents.get("folders", []):
                if item.get("name") == item_name:
                    found = item
                    break
            if not found:
                for item in contents.get("files", []):
                    if item.get("name") == item_name:
                        found = item
                        break
            if found and ("folderType" not in found):
                is_folder = False
        except Exception:
            is_folder = None

    if is_folder is False:
        if is_s3:
            raise ValueError("The S3 path appears to point to a file, not a folder. You can only link folders. Please link the parent folder instead.")
        else:
            raise ValueError("Linking files or virtual folders is not supported. Link the S3 parent folder instead.", err=True)
        return
    elif is_folder is None and is_s3:
        click.secho("Unable to verify whether the S3 path is a folder. Proceeding with linking; " +
                   "however, if the operation fails, please confirm that you are linking a folder rather than a file.", fg='yellow', bold=True)

    try:
        link_p.link_folder(path, session_id)
    except Exception as e:
        if is_s3:
            print("If you are linking an S3 path, please ensure it is a folder.")
        raise ValueError(f"Could not link folder. {e}")


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
@with_profile_config(required_params=['apikey', 'procurement_id'])
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
        raise ValueError(f"{str(e)}")


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
              type=click.Choice([
                  'RegularInteractiveSessions',
                  'SparkInteractiveSessions',
                  'RStudioInteractiveSessions',
                  'JupyterInteractiveSessions',
                  'JobDefault',
                  'NextflowBatchComputeEnvironment']))
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
@with_profile_config(required_params=['apikey', 'procurement_id'])
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
        raise ValueError(f"{str(e)}")


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
              type=click.Choice([
                  'RegularInteractiveSessions',
                  'SparkInteractiveSessions',
                  'RStudioInteractiveSessions',
                  'JupyterInteractiveSessions',
                  'JobDefault',
                  'NextflowBatchComputeEnvironment']))
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
@with_profile_config(required_params=['apikey', 'procurement_id'])
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
        raise ValueError(f"{str(e)}")

@run_cloudos_cli.command('link')
@click.argument('path', required=False)
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
@click.option('--session-id',
              help='The specific CloudOS interactive session id.',
              required=True)
@click.option('--job-id',
              help='The job id in CloudOS. When provided, links results, workdir and logs by default.',
              required=False)
@click.option('--project-name',
              help='The name of a CloudOS project. Required for File Explorer paths.',
              required=False)
@click.option('--results',
              help='Link only results folder (only works with --job-id).',
              is_flag=True)
@click.option('--workdir',
              help='Link only working directory (only works with --job-id).',
              is_flag=True)
@click.option('--logs',
              help='Link only logs folder (only works with --job-id).',
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
@with_profile_config(required_params=['apikey', 'workspace_id', 'session_id'])
def link_command(ctx,
                 path,
                 apikey,
                 cloudos_url,
                 workspace_id,
                 session_id,
                 job_id,
                 project_name,
                 results,
                 workdir,
                 logs,
                 verbose,
                 disable_ssl_verification,
                 ssl_cert,
                 profile):
    """
    Link folders to an interactive analysis session.
    
    This command is used to link folders
    to an active interactive analysis session for direct access to data.
    
    PATH: Optional path to link (S3). 
          Required if --job-id is not provided.
    
    Two modes of operation:
    
    1. Job-based linking (--job-id): Links job-related folders.
       By default, links results, workdir, and logs folders.
       Use --results, --workdir, or --logs flags to link only specific folders.
    
    2. Direct path linking (PATH argument): Links a specific S3 path.
    
    Examples:
    
        # Link all job folders (results, workdir, logs)
        cloudos link --job-id 12345 --session-id abc123
        
        # Link only results from a job
        cloudos link --job-id 12345 --session-id abc123 --results
        
        # Link a specific S3 path
        cloudos link s3://bucket/folder --session-id abc123
        
    """
    print('CloudOS link functionality: link s3 folders to interactive analysis sessions.\n')
    
    verify_ssl = ssl_selector(disable_ssl_verification, ssl_cert)
    
    # Validate input parameters
    if not job_id and not path:
        raise click.UsageError("Either --job-id or PATH argument must be provided.")
    
    if job_id and path:
        raise click.UsageError("Cannot use both --job-id and PATH argument. Please provide only one.")
    
    # Validate folder-specific flags only work with --job-id
    if (results or workdir or logs) and not job_id:
        raise click.UsageError("--results, --workdir, and --logs flags can only be used with --job-id.")
    
    # If no specific folders are selected with job-id, link all by default
    if job_id and not (results or workdir or logs):
        results = True
        workdir = True
        logs = True
    
    if verbose:
        print('Using the following parameters:')
        print(f'\tCloudOS url: {cloudos_url}')
        print(f'\tWorkspace ID: {workspace_id}')
        print(f'\tSession ID: {session_id}')
        if job_id:
            print(f'\tJob ID: {job_id}')
            print(f'\tLink results: {results}')
            print(f'\tLink workdir: {workdir}')
            print(f'\tLink logs: {logs}')
        else:
            print(f'\tPath: {path}')
    
    # Initialize Link client
    link_client = Link(
        cloudos_url=cloudos_url,
        apikey=apikey,
        cromwell_token=None,
        workspace_id=workspace_id,
        project_name=project_name,
        verify=verify_ssl
    )
    
    try:
        if job_id:
            # Job-based linking
            print(f'Linking folders from job {job_id} to interactive session {session_id}...\n')
            
            # Link results
            if results:
                link_client.link_job_results(job_id, workspace_id, session_id, verify_ssl, verbose)
            
            # Link workdir
            if workdir:
                link_client.link_job_workdir(job_id, workspace_id, session_id, verify_ssl, verbose)
            
            # Link logs
            if logs:
                link_client.link_job_logs(job_id, workspace_id, session_id, verify_ssl, verbose)
            
            
        else:
            # Direct path linking
            print(f'Linking path to interactive session {session_id}...\n')
            
            # Link path with validation
            link_client.link_path_with_validation(path, session_id, verify_ssl, project_name, verbose)
            
            print('\nLinking operation completed.')
            
    except BadRequestException as e:
        raise ValueError(f"Request failed: {str(e)}")
    except Exception as e:
        raise ValueError(f"Failed to link folder(s): {str(e)}")

if __name__ == "__main__":
    # Setup logging
    debug_mode = '--debug' in sys.argv
    setup_logging(debug_mode)
    logger = logging.getLogger("CloudOS")
    # Check if debug flag was passed (fallback for cases where Click doesn't handle it)
    try:
        run_cloudos_cli()
    except Exception as e:
        if debug_mode:
            logger.error(e, exc_info=True)
            traceback.print_exc()
        else:
            logger.error(e)
            click.echo(click.style(f"Error: {e}", fg='red'), err=True)
        sys.exit(1)
"""CLI commands for CloudOS job management."""

import rich_click as click
import cloudos_cli.jobs.job as jb
from cloudos_cli.clos import Cloudos
from cloudos_cli.utils.errors import BadRequestException
from cloudos_cli.utils.resources import ssl_selector
from cloudos_cli.utils.details import create_job_details, create_job_list_table
from cloudos_cli.cost.cost import CostViewer
from cloudos_cli.related_analyses.related_analyses import related_analyses
from cloudos_cli.configure.configure import with_profile_config, CLOUDOS_URL
from cloudos_cli.link import Link
from cloudos_cli.constants import (
    JOB_COMPLETED,
    REQUEST_INTERVAL_CROMWELL,
    AWS_NEXTFLOW_VERSIONS,
    AZURE_NEXTFLOW_VERSIONS,
    HPC_NEXTFLOW_VERSIONS,
    AWS_NEXTFLOW_LATEST,
    AZURE_NEXTFLOW_LATEST,
    HPC_NEXTFLOW_LATEST,
    ABORT_JOB_STATES
)
import json
import copy
import time
from cloudos_cli.queue.queue import Queue
import sys
from rich.console import Console
from cloudos_cli.utils.cli_helpers import pass_debug_to_subcommands




# Create the job group
@click.group(cls=pass_debug_to_subcommands())
def job():
    """CloudOS job functionality: run, clone, resume, check and abort jobs in CloudOS."""
    print(job.__doc__ + '\n')


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
    """Run a CloudOS workflow."""    
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
              '\t\t--profile my_profile \\\n' +
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
    """Get the status of a CloudOS job."""
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
                console.print('\n[bold]Additional information:[/bold]')
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
                console.print('\n[bold]Additional information:[/bold]')
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
                print('\nDeleting result directories from CloudOS...')
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
@click.option('--force',
              help='Force abort the job even if it is not in a running or initializing state.',
              is_flag=True)
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
               profile,
               force):
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

    # Issue warning if using --force flag
    if force:
        click.secho(f"Warning: Using --force to abort jobs. Some data might be lost.", fg='yellow', bold=True)

    for job in jobs:
        try:
            j_status = cl.get_job_status(job, workspace_id, verify_ssl)
        except Exception as e:
            click.secho(f"Failed to get status for job {job}, please make sure it exists in the workspace: {e}", fg='yellow', bold=True)
            continue

        j_status_content = json.loads(j_status.content)
        job_status = j_status_content['status']

        # Check if job is in a state that normally allows abortion
        is_abortable = job_status in ABORT_JOB_STATES

        # Issue warning if job is in initializing state and not using force
        if job_status == 'initializing' and not force:
            click.secho(f"Warning: Job {job} is in initializing state.", fg='yellow', bold=True)

        # Check if job can be aborted
        if not is_abortable:
            click.secho(f"Job {job} is not in a state that can be aborted and is ignored. " +
                  f"Current status: {job_status}", fg='yellow', bold=True)
        else:
            try:
                cl.abort_job(job, workspace_id, verify_ssl, force)
                click.secho(f"Job '{job}' aborted successfully.", fg='green', bold=True)
            except Exception as e:
                click.secho(f"Failed to abort job {job}. Error: {e}", fg='red', bold=True)


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


@click.command()
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
              help=('One or more job ids to archive/unarchive. If more than ' +
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
def archive_unarchive_jobs(ctx,
                           apikey,
                           cloudos_url,
                           workspace_id,
                           job_ids,
                           verbose,
                           disable_ssl_verification,
                           ssl_cert,
                           profile):
    """Archive or unarchive specified jobs in a CloudOS workspace."""
    # Determine operation based on the command name used
    target_archived_state = ctx.info_name == "archive"
    action = "archive" if target_archived_state else "unarchive"
    action_past = "archived" if target_archived_state else "unarchived"
    action_ing = "archiving" if target_archived_state else "unarchiving"

    verify_ssl = ssl_selector(disable_ssl_verification, ssl_cert)
    print(f'{action_ing.capitalize()} jobs...')

    if verbose:
        print('\t...Preparing objects')

    cl = Cloudos(cloudos_url, apikey, None)

    if verbose:
        print('\tThe following Cloudos object was created:')
        print('\t' + str(cl) + '\n')
        print(f'\t{action_ing.capitalize()} jobs in the following workspace: {workspace_id}')

    # check if the user provided an empty job list
    jobs = job_ids.replace(' ', '')
    if not jobs:
        raise ValueError(f'No job IDs provided. Please specify at least one job ID to {action}.')
    jobs_list = [job for job in jobs.split(',') if job]  # Filter out empty strings

    # Check for duplicate job IDs
    duplicates = [job_id for job_id in set(jobs_list) if jobs_list.count(job_id) > 1]
    if duplicates:
        dup_str = ', '.join(duplicates)
        click.secho(f'Warning: Duplicate job IDs detected and will be processed only once: {dup_str}', fg='yellow', bold=True)
        # Remove duplicates while preserving order
        jobs_list = list(dict.fromkeys(jobs_list))
        if verbose:
            print(f'\tDuplicate job IDs removed. Processing {len(jobs_list)} unique job(s).')

    # Check archive status for all jobs
    status_check = cl.check_jobs_archive_status(jobs_list, workspace_id, target_archived_state=target_archived_state, verify=verify_ssl, verbose=verbose)
    valid_jobs = status_check['valid_jobs']
    already_processed = status_check['already_processed']
    invalid_jobs = status_check['invalid_jobs']

    # Report invalid jobs (but continue processing valid ones)
    for job_id, error_msg in invalid_jobs.items():
        click.secho(f"Failed to get status for job {job_id}, please make sure it exists in the workspace: {error_msg}", fg='yellow', bold=True)

    if not valid_jobs and not already_processed:
        # All jobs were invalid - exit gracefully
        click.secho('No valid job IDs found. Please check that the job IDs exist and are accessible.', fg='yellow', bold=True)
        return

    if not valid_jobs:
        if len(already_processed) == 1:
            click.secho(f"Job '{already_processed[0]}' is already {action_past}. No action needed.", fg='cyan', bold=True)
        else:
            click.secho(f"All {len(already_processed)} jobs are already {action_past}. No action needed.", fg='cyan', bold=True)
        return

    try:
        # Call the appropriate action method
        if target_archived_state:
            cl.archive_jobs(valid_jobs, workspace_id, verify_ssl)
        else:
            cl.unarchive_jobs(valid_jobs, workspace_id, verify_ssl)

        success_msg = []
        if len(valid_jobs) == 1:
            success_msg.append(f"Job '{valid_jobs[0]}' {action_past} successfully.")
        else:
            success_msg.append(f"{len(valid_jobs)} jobs {action_past} successfully: {', '.join(valid_jobs)}")

        if already_processed:
            if len(already_processed) == 1:
                success_msg.append(f"Job '{already_processed[0]}' was already {action_past}.")
            else:
                success_msg.append(f"{len(already_processed)} jobs were already {action_past}: {', '.join(already_processed)}")

        click.secho('\n'.join(success_msg), fg='green', bold=True)
    except Exception as e:
        raise ValueError(f"Failed to {action} jobs: {str(e)}")


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
                 wait_completion,
                 wait_time,
                 request_interval,
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

    j_url = f'{cloudos_url}/app/advanced-analytics/analyses/{cloned_resumed_job_id}'
    if wait_completion:
        print('\tPlease, wait until job completion (max wait time of ' +
              f'{wait_time} seconds).\n')
        j_status = job_obj.wait_job_completion(job_id=cloned_resumed_job_id,
                                               workspace_id=workspace_id,
                                               wait_time=wait_time,
                                               request_interval=request_interval,
                                               verbose=verbose,
                                               verify=verify_ssl)
        j_name = j_status['name']
        j_final_s = j_status['status']
        if j_final_s == JOB_COMPLETED:
            print(f'\nJob status for job "{j_name}" (ID: {cloned_resumed_job_id}): {j_final_s}')
            sys.exit(0)
        else:
            print(f'\nJob status for job "{j_name}" (ID: {cloned_resumed_job_id}): {j_final_s}')
            sys.exit(1)
    else:
        j_status = job_obj.get_job_status(cloned_resumed_job_id, workspace_id, verify_ssl)
        j_status_h = json.loads(j_status.content)["status"]
        print(f'\tYour current job status is: {j_status_h}')
        print('\tTo further check your job status you can either go to ' +
              f'{j_url} or use the following command:\n' +
              '\tcloudos job status \\\n' +
              '\t\t--profile my_profile \\\n' +
              f'\t\t--job-id {cloned_resumed_job_id}\n')


# Register archive_unarchive_jobs with both command names using aliases (same pattern as clone/resume)
archive_unarchive_jobs.help = 'Archive specified jobs in a CloudOS workspace.'
job.add_command(archive_unarchive_jobs, "archive")

# Create a copy with different help text for unarchive
archive_unarchive_jobs_copy = copy.deepcopy(archive_unarchive_jobs)
archive_unarchive_jobs_copy.help = 'Unarchive specified jobs in a CloudOS workspace.'
job.add_command(archive_unarchive_jobs_copy, "unarchive")


# Apply the best Click solution: Set specific help text for each command registration
clone_resume.help = 'Clone a job with modified parameters'
job.add_command(clone_resume, "clone")

# Create a copy with different help text for resume
clone_resume_copy = copy.deepcopy(clone_resume)
clone_resume_copy.help = 'Resume a job with modified parameters'
job.add_command(clone_resume_copy, "resume")

"""CLI commands for CloudOS bash job management."""

import rich_click as click
import cloudos_cli.jobs.job as jb
from cloudos_cli.clos import Cloudos
from cloudos_cli.utils.resources import ssl_selector
from cloudos_cli.configure.configure import with_profile_config, CLOUDOS_URL
from cloudos_cli.utils.array_job import generate_datasets_for_project
import sys


@click.group()
def bash():
    """CloudOS bash-specific job functionality."""
    print(bash.__doc__ + '\n')


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

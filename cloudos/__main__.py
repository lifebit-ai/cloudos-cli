#!/usr/bin/env python3

import click
import cloudos.jobs.job as job
from cloudos.clos import Cloudos
import json


@click.group()
def run_cloudos_cli():
    """CloudOS python package: a package for interacting with CloudOS."""
    print(run_cloudos_cli.__doc__ + '\n')


@run_cloudos_cli.command()
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
@click.option('--job-params',
              help=('A nextflow.config file or similar, with the ' +
                    'parameters to use with your job.'),
              required=True)
@click.option('--job-name',
              help='The name of the job. Default=new_job.',
              default='new_job')
@click.option('--resumable',
              help='Whether to make the job able to be resumed or not.',
              is_flag=True)
@click.option('--instance-type',
              help='The type of AMI to use. Default=c5.xlarge.',
              default='c5.xlarge')
@click.option('--instance-disk',
              help='The amount of disk storage to configure. Default=500.',
              type=int,
              default=500)
@click.option('--spot',
              help='Whether to make a spot instance.',
              is_flag=True)
@click.option('--verbose',
              help='Whether to print information messages or not.',
              is_flag=True)
def runjob(apikey,
           cloudos_url,
           workspace_id,
           project_name,
           workflow_name,
           job_params,
           job_name,
           resumable,
           instance_type,
           instance_disk,
           spot,
           verbose):
    if verbose:
        print('Executing runjob...')
        print('\t...Preparing objects')
    j = job.Job(apikey, cloudos_url, workspace_id, project_name, workflow_name)
    if verbose:
        print('\tThe following Job object was created:')
        print('\t' + str(j))
        print('\t...Sending job to CloudOS\n')
    j_id = j.send_job(job_params,
                      job_name,
                      resumable,
                      instance_type,
                      instance_disk,
                      spot)
    print(f'Your assigned job id is: {j_id}')
    j_status = j.get_job_status(j_id)
    j_status_h = json.loads(j_status.content)["status"]
    print(f'Your current job status is: {j_status_h}')
    j_url = f'{cloudos_url}/app/jobs/{j_id}'
    print(f'To further check your job status you can either go to {j_url} ' +
          'or use the following command:\n' +
          'cloudos jobstatus \\\n' +
          '    --apikey $MY_API_KEY \\\n' +
          f'    --cloudos-url {cloudos_url} \\\n' +
          f'    --job-id {j_id}')


@run_cloudos_cli.command()
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
def jobstatus(apikey,
              cloudos_url,
              job_id,
              verbose):
    if verbose:
        print('Executing jobstatus...')
        print('\t...Preparing objects')
    cl = Cloudos(apikey, cloudos_url)
    if verbose:
        print('\tThe following Cloudos object was created:')
        print('\t' + str(cl) + '\n')
        print(f'\tSearching for job id: {job_id}')
    j_status = cl.get_job_status(job_id)
    j_status_h = json.loads(j_status.content)["status"]
    print(f'Your current job status is: {j_status_h}\n')
    j_url = f'{cloudos_url}/app/jobs/{job_id}'
    print(f'To further check your job status you can either go to {j_url} ' +
          'or repeat the command you just used.')


if __name__ == "__main__":
    run_cloudos_cli()

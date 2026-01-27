"""CLI commands for CloudOS Cromwell server management."""

import rich_click as click
import json
import time
import sys
from cloudos_cli.clos import Cloudos
from cloudos_cli.utils.resources import ssl_selector
from cloudos_cli.configure.configure import with_profile_config, CLOUDOS_URL

# Constants
REQUEST_INTERVAL_CROMWELL = 5


@click.group()
def cromwell():
    """CloudOS Cromwell server functionality."""
    print(cromwell.__doc__ + '\n')


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

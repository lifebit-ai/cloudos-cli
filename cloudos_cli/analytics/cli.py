"""CLI commands for Lifebit Platform analytics."""

import rich_click as click
import json
from cloudos_cli.analytics.analytics import Analytics
from cloudos_cli.utils.resources import ssl_selector
from cloudos_cli.configure.configure import with_profile_config, CLOUDOS_URL
from cloudos_cli.utils.cli_helpers import pass_debug_to_subcommands


# Create the analytics group
@click.group(cls=pass_debug_to_subcommands())
def analytics():
    """Lifebit Platform analytics functionality."""
    print(analytics.__doc__ + '\n')


@analytics.command('team-summary')
@click.option('-k',
              '--apikey',
              help='Your Lifebit Platform API key',
              required=True)
@click.option('-c',
              '--cloudos-url',
              help=(f'The Lifebit Platform url you are trying to access to. Default={CLOUDOS_URL}.'),
              default=CLOUDOS_URL,
              required=True)
@click.option('--team-id',
              help='The Lifebit Platform team (workspace) id.',
              required=True)
@click.option('--start-date',
              help='The start date for the analytics range (e.g. 2024-01-01).',
              required=False,
              default=None)
@click.option('--end-date',
              help='The end date for the analytics range (e.g. 2024-12-31).',
              required=False,
              default=None)
@click.option('--granularity',
              help='The time granularity for the analytics (e.g. daily, weekly, monthly).',
              required=False,
              default=None)
@click.option('--output-format',
              help=('The desired display for the output, either directly in standard output or saved as file. '
                    'Default=stdout.'),
              type=click.Choice(['stdout', 'json'], case_sensitive=False),
              default='stdout')
@click.option('--output-basename',
              help=('Output file base name to save team summary. '
                    'Default=team_summary'),
              default='team_summary',
              required=False)
@click.option('--disable-ssl-verification',
              help=('Disable SSL certificate verification. Please, remember that this option is '
                    'not generally recommended for security reasons.'),
              is_flag=True)
@click.option('--ssl-cert',
              help='Path to your SSL certificate file.')
@click.option('--profile', help='Profile to use from the config file', default=None)
@click.pass_context
@with_profile_config(required_params=['apikey', 'team_id'])
def team_summary(ctx,
                 apikey,
                 cloudos_url,
                 team_id,
                 start_date,
                 end_date,
                 granularity,
                 output_format,
                 output_basename,
                 disable_ssl_verification,
                 ssl_cert,
                 profile):
    """Retrieve aggregated team usage analytics (compute hours, job counts, spend) over a date range."""
    verify_ssl = ssl_selector(disable_ssl_verification, ssl_cert)
    print('Executing team-summary...')
    a = Analytics(cloudos_url, apikey, None, verify=verify_ssl)
    result = a.get_team_summary(
        team_id=team_id,
        start_date=start_date,
        end_date=end_date,
        granularity=granularity
    )
    if output_format == 'stdout':
        print(json.dumps(result, indent=2))
    elif output_format == 'json':
        outfile = output_basename + '.json'
        with open(outfile, 'w') as o:
            o.write(json.dumps(result))
        print(f'\tTeam summary saved to {outfile}')

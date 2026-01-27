"""CLI commands for CloudOS procurement management."""

import rich_click as click
from cloudos_cli.procurement.images import Images
from cloudos_cli.utils.resources import ssl_selector
from cloudos_cli.configure.configure import with_profile_config, CLOUDOS_URL
from rich.console import Console


@click.group()
def procurement():
    """CloudOS procurement functionality."""
    print(procurement.__doc__ + '\n')


@procurement.group()
def images():
    """CloudOS procurement images functionality."""


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

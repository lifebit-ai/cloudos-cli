import os
import urllib3

def format_bytes(size):
    """Convert bytes to human-readable format (e.g., 1.2 MB)."""
    if size is None:
        return "-"
    power = 1024
    n = 0
    labels = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    while size >= power and n < len(labels) - 1:
        size /= power
        n += 1
    return f"{size:.1f} {labels[n]}"


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

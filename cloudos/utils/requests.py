"""
Specific functions to wrapp error strategy for requests
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry


def retry_requests_get(url, total=5, status_forcelist=[429, 500, 502, 503, 504], **kwargs):
    """Wrap normal requests get with an error strategy.

    Parameters
    ----------
    url : string
        The request URL
    total : int
        Total number of retries
    status_forcelist : list
        A list of ints with the status codes to trigger the retries

    Return
    ------
    response : requests.Response
        The Response object returned by the API server
    """
    retry_strategy = Retry(
        total=total,
        status_forcelist=status_forcelist
    )
    # Create an HTTP adapter with the retry strategy and mount it to session
    adapter = HTTPAdapter(max_retries=retry_strategy)

    # Create a new session object
    session = requests.Session()
    session.mount('http://', adapter)
    session.mount('https://', adapter)

    # Make a request using the session object
    response = session.get(url, **kwargs)
    return response


def retry_requests_post(url, total=5, status_forcelist=[429, 500, 502, 503, 504], **kwargs):
    """Wrap normal requests post with an error strategy.

    Parameters
    ----------
    url : string
        The request URL
    total : int
        Total number of retries
    status_forcelist : list
        A list of ints with the status codes to trigger the retries

    Return
    ------
    response : requests.Response
        The Response object returned by the API server
    """
    retry_strategy = Retry(
        total=total,
        status_forcelist=status_forcelist
    )
    # Create an HTTP adapter with the retry strategy and mount it to session
    adapter = HTTPAdapter(max_retries=retry_strategy)

    # Create a new session object
    session = requests.Session()
    session.mount('http://', adapter)
    session.mount('https://', adapter)

    # Make a request using the session object
    response = session.post(url, **kwargs)
    return response

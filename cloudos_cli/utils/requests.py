"""
Specific functions to wrapp error strategy for requests
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry


def create_retry_session(total=5, status_forcelist=[429, 500, 502, 503, 504],
                         allowed_methods=None):
    """Create a requests.Session with a retry strategy mounted.

    Reusing the returned session across several requests to the same host
    avoids re-establishing a TCP/TLS connection for every request.

    Parameters
    ----------
    total : int
        Total number of retries
    status_forcelist : list
        A list of ints with the status codes to trigger the retries
    allowed_methods : list, optional
        HTTP methods allowed to be retried. When None, the urllib3
        default set of idempotent methods is used.

    Return
    ------
    session : requests.Session
        A session object with the retry strategy mounted.
    """
    retry_kwargs = dict(total=total, status_forcelist=status_forcelist)
    if allowed_methods is not None:
        retry_kwargs['allowed_methods'] = allowed_methods
    retry_strategy = Retry(**retry_kwargs)
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session = requests.Session()
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session


def retry_requests_get(url, total=5, status_forcelist=[429, 500, 502, 503, 504],
                       session=None, **kwargs):
    """Wrap normal requests get with an error strategy.

    Parameters
    ----------
    url : string
        The request URL
    total : int
        Total number of retries
    status_forcelist : list
        A list of ints with the status codes to trigger the retries
    session : requests.Session, optional
        An existing session to reuse (e.g. created with
        `create_retry_session`). When None, a new session is created
        for this single request.

    Return
    ------
    response : requests.Response
        The Response object returned by the API server
    """
    if session is None:
        session = create_retry_session(total, status_forcelist)
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
    session = create_retry_session(total, status_forcelist)
    response = session.post(url, **kwargs)
    return response


def retry_requests_put(url, total=5, status_forcelist=[429, 500, 502, 503, 504], **kwargs):
    """Wrap normal requests put with an error strategy.

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
    session = create_retry_session(total, status_forcelist)
    response = session.put(url, **kwargs)
    return response


def retry_requests_delete(url, total=5, status_forcelist=[429, 500, 502, 503, 504], **kwargs):
    """
    Wrap normal requests DELETE with an error retry strategy.

    Parameters
    ----------
    url : str
        The request URL.
    total : int
        Total number of retry attempts.
    status_forcelist : list of int
        HTTP status codes that should trigger a retry.
    **kwargs :
        Additional keyword arguments passed to `requests.delete`.

    Returns
    -------
    requests.Response
        The Response object returned by the API server.
    """
    session = create_retry_session(total, status_forcelist, allowed_methods=["DELETE"])
    response = session.delete(url, **kwargs)
    return response

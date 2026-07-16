import mock
import requests
from requests.adapters import HTTPAdapter

from cloudos_cli.utils.requests import create_retry_session, retry_requests_get


def test_create_retry_session_mounts_retry_adapters():
    session = create_retry_session(total=3, status_forcelist=[500])
    assert isinstance(session, requests.Session)
    for prefix in ('http://', 'https://'):
        adapter = session.get_adapter(f'{prefix}example.com')
        assert isinstance(adapter, HTTPAdapter)
        assert adapter.max_retries.total == 3
        assert adapter.max_retries.status_forcelist == [500]


def test_create_retry_session_allowed_methods():
    session = create_retry_session(allowed_methods=["DELETE"])
    adapter = session.get_adapter('https://example.com')
    assert adapter.max_retries.allowed_methods == ["DELETE"]


def test_retry_requests_get_reuses_given_session():
    session = mock.Mock()
    session.get.return_value = 'response'
    response = retry_requests_get('https://example.com', session=session, timeout=5)
    assert response == 'response'
    session.get.assert_called_once_with('https://example.com', timeout=5)

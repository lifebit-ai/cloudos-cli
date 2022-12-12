"""Pytest added to test ssl_selector function"""
import os
import sys
from io import StringIO
import warnings
from cloudos.__main__ import ssl_selector


DUMMY_SSL_CERT_FILE = "tests/test_data/process_job_list_initial_json.json"


def test_ssl_selector_disable_ssl_verification_without_ssl_cert():
    """testing disable ssl_verification"""
    output = StringIO()
    sys.stdout = output
    result = ssl_selector(disable_ssl_verification=True, ssl_cert=None)
    result_string = output.getvalue().rstrip()
    assert result is False
    assert result_string == '[WARNING] Disabling SSL verification'
    assert warnings.filters[0][0] == 'ignore'


def test_ssl_selector_not_disable_verification():
    """testing not disabling ssl verification"""
    result = ssl_selector(disable_ssl_verification=False, ssl_cert=None)
    assert result


def test_ssl_selector_not_disable_verification_ssl_cert_provided():
    """testing not disabling ssl verification and providing the ssl_cert"""
    result = ssl_selector(disable_ssl_verification=False, ssl_cert=DUMMY_SSL_CERT_FILE)
    assert isinstance(result, str) and len(result) > 0
    assert os.path.isfile(result)

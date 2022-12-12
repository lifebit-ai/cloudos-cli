"""Pytest added to test ssl_selector function"""
import os
import sys
from io import StringIO
from cloudos.__main__ import ssl_selector
import warnings


DUMMY_SSL_CERT_FILE = "tests/test_data/process_job_list_initial_json.json"


def supress_stdout(func):
    """supress the print output so that outputs are clear while checking Unit Test Status"""
    def wrapper(*a, **ka):
        with open(os.devnull, 'w', encoding="utf-8") as devnull:
            with contextlib.redirect_stdout(devnull):
                return func(*a, **ka)
    return wrapper


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


def test_ssl_selector_not_disable_verification_ssl_cert_provided:
    """testing not disabling ssl verification and providing the ssl_cert"""
    result = ssl_selector(disable_ssl_verification=False, ssl_cert=DUMMY_SSL_CERT_FILE)
    assert isinstance(result, str) and len(result) > 0
    assert os.path.isfile(result)
"""Pytest added to test ssl_selector function"""
import contextlib
import os
import sys
from io import StringIO
from cloudos.__main__ import ssl_selector


DUMMY_SSL_CERT_FILE = "tests/test_data/process_job_list_initial_json.json"

def supress_stdout(func):
    """supress the print output so that outputs are clear while checking Unit Test Status"""
    def wrapper(*a, **ka):
        with open(os.devnull, 'w', encoding="utf-8") as devnull:
            with contextlib.redirect_stdout(devnull):
                return func(*a, **ka)
    return wrapper

@supress_stdout
def test_ssl_selector_disable_ssl_verification_without_ssl_cert():
    """testing without ssl_verification and ssl_certification"""
    output = StringIO()
    sys.stdout = output
    result_string = output.getvalue()
    result = ssl_selector(disable_ssl_verification=True, ssl_cert=None)
    if result is False and result_string == '[WARNING] Disabling SSL verification':
        assert True

def test_ssl_selector_without_ssl_cert():
    """testing without ssl certification"""
    result = ssl_selector(disable_ssl_verification=False, ssl_cert=None)
    assert result

def test_ssl_selector_with_ssl_cert():
    """testing with ssl certification"""
    result = ssl_selector(disable_ssl_verification=False, ssl_cert=DUMMY_SSL_CERT_FILE)
    assert isinstance(result, str) and len(result) > 0

def test_ssl_selector_no_ssl_cert():
    """testing if ssl certification is a file"""
    result = ssl_selector(disable_ssl_verification=False, ssl_cert=DUMMY_SSL_CERT_FILE)
    assert os.path.isfile(result)
    
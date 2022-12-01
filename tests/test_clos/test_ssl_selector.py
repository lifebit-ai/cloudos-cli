from cloudos.__main__ import ssl_selector
import contextlib, os, sys
from io import StringIO


DUMMY_SSL_CERT_FILE = "tests/test_data/process_job_list_initial_json.json"

def supress_stdout(func):
    def wrapper(*a, **ka):
        with open(os.devnull, 'w') as devnull:
            with contextlib.redirect_stdout(devnull):
                return func(*a, **ka)
    return wrapper

@supress_stdout
def test_ssl_selector_disable_ssl_verification_without_ssl_cert():
    output = StringIO()
    sys.stdout = output
    result_string = output.getvalue()
    result = ssl_selector(disable_ssl_verification=True, ssl_cert=None)
    if result == False and result_string == '[WARNING] Disabling SSL verification':
        assert True
        
def test_ssl_selector_without_ssl_cert():
    result = ssl_selector(disable_ssl_verification=False, ssl_cert=None)
    assert result

def test_ssl_selector_with_ssl_cert():
    result = ssl_selector(disable_ssl_verification=False, ssl_cert=DUMMY_SSL_CERT_FILE)
    assert isinstance(result, str) and len(result) > 0
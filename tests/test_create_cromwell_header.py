import pytest
from cloudos.clos import Cloudos

TOKEN = "lifebit_test_token"
URL = "lifebit.ai"

EXPECTED_OUTPUT_APIKEY = {
                "Accept": "application/json",
                "apikey": TOKEN
            }

EXPECTED_OUTPUT_CROMWELL_TOKEN = {
                "Accept": "application/json",
                "Authorization": f'Bearer {TOKEN}'
            }

def test_create_cromwell_header_apikey():
    clos = Cloudos(apikey=TOKEN, cromwell_token=None, cloudos_url=URL)
    output = clos._create_cromwell_header()
    assert output == EXPECTED_OUTPUT_APIKEY

def test_create_cromwell_header_cromwell_token():
    clos = Cloudos(apikey=None, cromwell_token=TOKEN, cloudos_url=URL)
    output = clos._create_cromwell_header()
    assert output == EXPECTED_OUTPUT_CROMWELL_TOKEN

def test_create_cromwell_header_both():
    clos = Cloudos(apikey=TOKEN, cromwell_token=TOKEN, cloudos_url=URL)
    output = clos._create_cromwell_header()
    assert output == EXPECTED_OUTPUT_CROMWELL_TOKEN
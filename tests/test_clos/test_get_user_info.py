import mock
import json
import pytest
import responses
from cloudos.clos import Cloudos
from cloudos.utils.errors import BadRequestException

APIKEY = 'vnoiweur89u2ongs'
CLOUDOS_URL = 'http://cloudos.lifebit.ai'


@mock.patch('cloudos.clos', mock.MagicMock())
@responses.activate
def test_get_user_info_correct_response():
    """
    Test 'get_user_info' to work as intended
    """
    body = json.dumps({"dockerRegistriesCredentials": []})
    header = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json;charset=UTF-8",
        "apikey": APIKEY
    }
    # mock GET method with the .json
    responses.add(
            responses.GET,
            body=body,
            url=f"{CLOUDOS_URL}/api/v1/users/me",
            headers=header,
            status=200)
    # start cloudOS service
    clos = Cloudos(apikey=APIKEY, cromwell_token=None,
                   cloudos_url=CLOUDOS_URL)
    # get mock response
    response = clos.get_user_info()
    # check the response
    assert response['dockerRegistriesCredentials'] == []


@mock.patch('cloudos.clos', mock.MagicMock())
@responses.activate
def test_get_user_info_incorrect_response():
    """
    Test 'get_user_info' to fail with '400' response
    """
    # prepare error message
    error_message = {"statusCode": 400, "code": "BadRequest",
                     "message": "Bad Request.", "time": "2022-11-23_17:31:07"}
    error_json = json.dumps(error_message)
    header = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json;charset=UTF-8",
        "apikey": APIKEY
    }
    # mock GET method with the .json
    responses.add(
            responses.GET,
            url=f"{CLOUDOS_URL}/api/v1/users/me",
            body=error_json,
            headers=header,
            status=400)
    # raise 400 error
    with pytest.raises(BadRequestException) as error:
        # check if it failed
        clos = Cloudos(apikey=APIKEY, cromwell_token=None,
                       cloudos_url=CLOUDOS_URL)
        clos.get_user_info()
    assert "Server returned status 400." in (str(error))

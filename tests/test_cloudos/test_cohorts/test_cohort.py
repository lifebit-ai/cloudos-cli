import json

import mock
import pytest
import responses
from cloudos.cohorts import Cohort
from cloudos.utils.errors import BadRequestException
from responses import matchers
from tests.functions_for_pytest import load_json_file

apikey = "1"
workspace_id = '5f7c8696d6ea46288645a89f'
cloudos_url = "http://test"
cohort_id='test_cohort_id'
path = "tests/test_data/load_create/"

@mock.patch('cloudos.cohorts', mock.MagicMock())
@responses.activate
def test_load_correct_details():
    """
    Test that a cloudos cohort loads works as expected with correct information.
    API request is mocked and replicated with json files.
    """
    create_file = f"{path}update_responce_r_json_with_desc.json"
    create_json = load_json_file(create_file)
    params = {"teamId": workspace_id}
    cohort_name = 'testing cohort 2022'
    data = {"name": cohort_name,
            "description": ""}
    header = {"apikey": apikey,
              "Accept": "application/json, text/plain, */*",
              "Content-Type": "application/json;charset=UTF-8"}
    params = {"teamId": workspace_id}
    responses.add(
            responses.POST,
            url=f"{cloudos_url}/cohort-browser/v2/cohort/{cohort_id}?teamId={workspace_id}",
            body=data,
            headers=header,
            match=[matchers.query_param_matcher(params)],
            status=201)
    responses.add(
            responses.GET,
            url=f"{cloudos_url}/cohort-browser/v2/cohort/{cohort_id}?teamId={workspace_id}",
            body=create_json,
            headers=header,
            match=[matchers.query_param_matcher(params)],
            status=201)
    my_old_cohort = Cohort.load(apikey, cloudos_url, workspace_id,cohort_id)
    name = my_old_cohort.cohort_name
    assert name == cohort_name

@mock.patch('cloudos.cohorts', mock.MagicMock())
@responses.activate
def test_load_errors_with_fake_cohort():
    """
    Test that cloudos load failes with a new cohort.
    """
    params = {"teamId": workspace_id}
    cohort_name = 'new_cohort'
    data = {"name": cohort_name,
            "description": ""}
    error_message = {"statusCode": 500, "code": "InternalServerError",
                     "message": "Internal server error.", "time": "2022-06-29T16:31:07.924Z"}
    error_json = json.dumps(error_message)
    header = {"apikey": apikey,
              "Accept": "application/json, text/plain, */*",
              "Content-Type": "application/json;charset=UTF-8"}
    params = {"teamId": workspace_id}
    responses.add(
            responses.POST,
            url=f"{cloudos_url}/cohort-browser/v2/cohort/{cohort_id}?teamId={workspace_id}",
            body=data,
            headers=header,
            match=[matchers.query_param_matcher(params)],
            status=200)
    responses.add(
            responses.GET,
            url=f"{cloudos_url}/cohort-browser/v2/cohort/{cohort_id}?teamId={workspace_id}",
            body=error_json,
            headers=header,
            match=[matchers.query_param_matcher(params)],
            status=500)
    with pytest.raises(BadRequestException) as excinfo:
        my_old_cohort = Cohort.load(apikey, cloudos_url, workspace_id,cohort_id)
    assert "Internal server error." in (str(excinfo))

@mock.patch('cloudos.cohorts', mock.MagicMock())
@responses.activate
def test_cohort_errors_with_none_cohort():
    """
    Test that cloudos load raises the correct error message with no cohort.
    """
    with pytest.raises(ValueError) as excinfo:
        my_old_cohort = Cohort.load(apikey, cloudos_url, workspace_id,cohort_id=None)
    assert "One of cohort_id or cohort_name must be set." in str(excinfo.value)

@mock.patch('cloudos.cohorts', mock.MagicMock())
@responses.activate
def test_create_name_and_desc():
    """
    Test that a cloudos cohort create works as expected with name and description.
    API request is mocked and replicated with json files.
    """
    create_file = f"{path}update_responce_r_json_with_desc.json"
    create_json = load_json_file(create_file)
    create_post_file = f"{path}create_responce_r_json_with_desc.json"
    create_post_json  = load_json_file(create_post_file)

    params = {"teamId": workspace_id}
    cohort_name = "testing cohort 2022"
    cohort_desc = "Cohort made for unit testing"
    header = {"apikey": apikey,
              "Accept": "application/json, text/plain, */*",
              "Content-Type": "application/json;charset=UTF-8"}
    params = {"teamId": workspace_id}
    responses.add(
            responses.POST,
            url=f"{cloudos_url}/cohort-browser/v2/cohort?teamId={workspace_id}",
            body=create_post_json,
            headers=header,
            match=[matchers.query_param_matcher(params)],
            status=200)
    responses.add(
            responses.GET,
            url=f"{cloudos_url}/cohort-browser/v2/cohort/{cohort_id}?teamId={workspace_id}",
            body=create_json,
            headers=header,
            match=[matchers.query_param_matcher(params)],
            status=200)
    new_c = Cohort.create(apikey, cloudos_url, workspace_id,
                          cohort_name="testing cohort 2022",
                          cohort_desc="Cohort made for unit testing")
    name = new_c.cohort_name
    desc = new_c.cohort_desc
    assert [name, desc] == [cohort_name, cohort_desc]

@mock.patch('cloudos.cohorts', mock.MagicMock())
@responses.activate
def test_create_name_no_desc():
    """
    Test that a cloudos cohort create works as expected with a cohort_name.
    API request is mocked and replicated with json files.
    """
    create_no_desc_file = f"{path}update_responce_r_json_no_desc.json"
    create_no_desc_json = load_json_file(create_no_desc_file)
    create_post_no_desc_file = f"{path}create_responce_r_json_no_desc.json"
    create_post_no_desc_json = load_json_file(create_post_no_desc_file)

    params = {"teamId": workspace_id}
    cohort_name = "testing cohort 2022"
    cohort_desc = ""
    header = {"apikey": apikey,
              "Accept": "application/json, text/plain, */*",
              "Content-Type": "application/json;charset=UTF-8"}
    params = {"teamId": workspace_id}
    responses.add(
            responses.POST,
            url=f"{cloudos_url}/cohort-browser/v2/cohort?teamId={workspace_id}",
            body=create_post_no_desc_json,
            headers=header,
            match=[matchers.query_param_matcher(params)],
            status=200)
    responses.add(
            responses.GET,
            url=f"{cloudos_url}/cohort-browser/v2/cohort/{cohort_id}?teamId={workspace_id}",
            body=create_no_desc_json,
            headers=header,
            match=[matchers.query_param_matcher(params)],
            status=200)
    new_c = Cohort.create(apikey, cloudos_url, workspace_id, cohort_name="testing cohort 2022")
    name = new_c.cohort_name
    desc = new_c.cohort_desc
    assert [name, desc] == [cohort_name, cohort_desc]

@mock.patch('cloudos.cohorts', mock.MagicMock())
@responses.activate
def test_create_desc_no_name_error():
    """
    Test that cloudos load raises the correct error message with no cohort_name.
    """
    with pytest.raises(TypeError) as excinfo:
        new_c = Cohort.create(apikey, cloudos_url, workspace_id,
                              cohort_desc="Cohort made for unit testing")
    assert "missing 1 required positional argument: 'cohort_name'" in str(excinfo.value)

@mock.patch('cloudos.cohorts', mock.MagicMock())
@responses.activate
def test_create_no_desc_no_name():
    """
    Test that cloudos load raises the correct error message with no information.
    """
    with pytest.raises(TypeError) as excinfo:
        new_c = Cohort.create(apikey, cloudos_url, workspace_id)
    assert "missing 1 required positional argument: 'cohort_name'" in str(excinfo.value)
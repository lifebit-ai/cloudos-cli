import json

import mock
import pytest
import responses
from cloudos.cohorts import CohortBrowser
from responses import matchers
from tests.functions_for_pytest import load_json_file

apikey = "1"
workspace_id = '5f7c8696d6ea46288645a89f'
cloudos_url = "http://test"
cohort_id='test_cohort_id'
path = "tests/test_data/load_create/"

@mock.patch('cloudos.cohorts', mock.MagicMock())
@responses.activate
def test_load_cohort():
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
    cb = CohortBrowser(apikey, cloudos_url, workspace_id)
    cohort = cb.load_cohort(cohort_id)
    name = cohort.cohort_name
    assert name == cohort_name

@mock.patch('cloudos.cohorts', mock.MagicMock())
@responses.activate
def test_load_errors_with_no_cohort():
    """
    Test that cloudos load raises the correct error message with no cohort.
    """
    with pytest.raises(ValueError) as excinfo:
        cb = CohortBrowser(apikey, cloudos_url, workspace_id)
        cohort = cb.load_cohort()
    assert "One of cohort_id or cohort_name must be set." in str(excinfo.value)

@mock.patch('cloudos.cohorts', mock.MagicMock())
@responses.activate
def test_create_cohort():
    """
    Test that a cloudos cohort create works as expected with name and description.
    API request is mocked and replicated with json files.
    """
    create_file = f"{path}update_responce_r_json_with_desc.json"
    create_json = load_json_file(create_file)
    create_post_file = f"{path}create_responce_r_json_with_desc.json"
    create_post_json = load_json_file(create_post_file)

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
    cb = CohortBrowser(apikey, cloudos_url, workspace_id)
    new_c = cb.create_cohort(cohort_name="testing cohort 2022",
                             cohort_desc="Cohort made for unit testing")
    name = new_c.cohort_name
    desc = new_c.cohort_desc
    assert [name, desc] == [cohort_name, cohort_desc]

@mock.patch('cloudos.cohorts', mock.MagicMock())
@responses.activate
def test_create_no_name_errors():
    """
    Test that cloudos load raises the correct error message with no information.
    """
    with pytest.raises(TypeError) as excinfo:
        cb = CohortBrowser(apikey, cloudos_url, workspace_id)
        new_c = cb.create_cohort()
    assert "missing 1 required positional argument: 'cohort_name'" in str(excinfo.value)
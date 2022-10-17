import json
import mock
import pytest
import responses
from responses import matchers

def load_json_file(file_and_path):
    with open(file_and_path) as json_data:
        dict = json.load(json_data)
        json_data = json.dumps(dict)
    return(json_data)

details_dict = {
    "apikey" : "1",
    "workspace_id" : '5f7c8696d6ea46288645a89f',
    "cloudos_url" : "http://test",
    "cohort_id" : 'test_cohort_id',
    "path" : "tests/test_data/"
}

apikey = details_dict["apikey"]
workspace_id = details_dict["workspace_id"]
cloudos_url = details_dict["cloudos_url"]
cohort_id= details_dict["cohort_id"]
path = details_dict["path"]

@pytest.fixture
def load_cohort():
    create_file = f"{path}load_create/update_responce_r_json_with_desc.json"
    create_json = load_json_file(create_file)
    params = {"teamId": workspace_id}
    cohort_name = 'testing cohort 2022'
    data = {"name": cohort_name,
            "description": ""}
    header = {"apikey": details_dict["apikey"],
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
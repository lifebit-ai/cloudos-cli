import requests, json
from cloudos.clos import Cloudos
import pytest
import requests_mock

import pandas as pd

INPUT_JSON = "tests/test_data/process_workflow_list_initial_request.json"
output_df = pd.read_csv("tests/test_data/process_workflow_list_results.csv")
output_df_full = pd.read_csv("tests/test_data/process_workflow_list_results_FULL.csv")


@pytest.fixture()
def mocked_requests_get():
    test_workspace_id = 1
    with open(INPUT_JSON) as json_data:
        d = json.load(json_data)
    with requests_mock.Mocker() as mock:
        mock.get(f"http://test_cloud_os/api/v1/jobs?teamId={test_workspace_id}",
                 json=d)
        r = requests.get(f"http://test_cloud_os/api/v1/jobs?teamId={test_workspace_id}")
    return r

def test_process_workflow_list(mocked_requests_get):
    df = Cloudos.process_workflow_list(mocked_requests_get, all_fields=False)
    assert df.equals(output_df)

def test_process_workflow_list_all_fields(mocked_requests_get):
    df = Cloudos.process_workflow_list(mocked_requests_get, all_fields=True)
    assert df.equals(output_df_full)
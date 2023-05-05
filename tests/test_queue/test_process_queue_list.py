"""pytest for method Queue.process_queue_list"""
import json
import requests
import pytest
import requests_mock
import pandas as pd
from cloudos.queue import Queue

INPUT_JSON = "tests/test_data/queue/queues.json"
output_df = pd.read_csv("tests/test_data/queue/process_queue_list_results.csv")
output_df_full = pd.read_csv("tests/test_data/queue/process_queue_list_results_FULL.csv")


@pytest.fixture(name="mocked_requests_get")
def fixture_mocked_requests_get():
    """Creating a mock request"""
    test_workspace_id = 1
    with open(INPUT_JSON, encoding="utf-8") as json_data:
        data_d = json.load(json_data)
    with requests_mock.Mocker() as mock:
        mock.get(f"http://test_cloud_os/api/v1/teams/aws/v2/job-queues?teamId={test_workspace_id}",
                 json=data_d)
        r_get = requests.get(f"http://test_cloud_os/api/v1/teams/aws/v2/job-queues?teamId={test_workspace_id}")
    return json.loads(r_get.content)


def test_process_queue_list_all_fields_false(mocked_requests_get):
    """Test function parameter 'all_fields=False'"""
    df_ = Queue.process_queue_list(mocked_requests_get, all_fields=False)
    assert (df_.columns == output_df.columns).any()


def test_process_queue_list_all_fields_true(mocked_requests_get):
    """Test function parameter 'all_fields=True'"""
    df_ = Queue.process_queue_list(mocked_requests_get, all_fields=True)
    assert (df_.columns == output_df_full.columns).any()

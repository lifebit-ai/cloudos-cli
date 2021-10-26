import json
import pytest
import requests_mock
import requests
import pandas as pd
import numpy as np
from cloudos.clos import Cloudos

input_json = "tests/test_data/process_job_list_initial_json.json"
output_df = pd.read_csv("tests/test_data/output_df_of_results.csv",
                        index_col=0)
output_df_full = pd.read_csv("tests/test_data/output_df_of_results_FULL.csv", 
                                index_col=0)

@pytest.fixture()
def mocked_requests_get():
    test_workspace_id = 1
    with open(input_json) as json_data:
        d = json.load(json_data)
    with requests_mock.Mocker() as mock:
        mock.get(f"http://test_cloud_os/api/v1/jobs?teamId={test_workspace_id}", 
                json= d)
        r = requests.get(f"http://test_cloud_os/api/v1/jobs?teamId={test_workspace_id}")
    return r


def test_process_job_list_output_correct_shape(mocked_requests_get,):
    df = Cloudos.process_job_list(mocked_requests_get, full_data=False)
    assert df.shape == output_df.shape


def test_process_job_list_output_correct_headers(mocked_requests_get):
    df = Cloudos.process_job_list(mocked_requests_get, full_data=False)
    correct_headers = list(output_df.columns)
    actual_headers = list(df.columns)
    assert correct_headers == actual_headers


def test_process_job_list_df_values_equal(mocked_requests_get,):
    """
    Testing to check the values are the same. 3 columns (parameters, workflow.description and masterInstanceStorageCost)
    have been removed. Parameters has" added during making the csv, masterInstanceStorageCost there is a rounding error
    and workflow.description has nan.
    """
    df = Cloudos.process_job_list(mocked_requests_get)
    columns_to_compare = ['_id', 'team', 'name', 'status',
    'startTime', 'endTime', 'createdAt', 'updatedAt',
    'computeCostSpent',     'resumeWorkDir', 'user.id',
    'workflow._id', 'workflow.name', 'workflow.createdAt',
    'workflow.updatedAt', 'workflow.workflowType', 'project._id',
    'project.name', 'project.user', 'project.team', 'project.createdAt', 
    'project.updatedAt', 'masterInstance.usedInstance.type', 
    'spotInstances.usedInstance.asSpot']
    assert np.all(df[columns_to_compare] == output_df[columns_to_compare])


def test_process_job_list_full_has_correct_columns(mocked_requests_get):
    df = Cloudos.process_job_list(mocked_requests_get, full_data=True)
    correct_headers = list(output_df_full.columns)
    actual_headers = list(df.columns)
    assert correct_headers == actual_headers


def test_process_job_list_empty_json():
    test_workspace_id = 1
    empty_json = {"a": {"b": ""}}
    with requests_mock.Mocker() as mock:
        mock.get(f"http://test_cloud_os/api/v1/jobs?teamId={test_workspace_id}", 
                json= empty_json)
        r = requests.get(f"http://test_cloud_os/api/v1/jobs?teamId={test_workspace_id}")
    with pytest.raises(KeyError) as excinfo:
        df = Cloudos.process_job_list(r)
    assert "jobs" in str(excinfo.value)

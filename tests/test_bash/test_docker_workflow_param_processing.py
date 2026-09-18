"""Regression coverage for resolving Bash parameters to File Explorer items."""
import json
from unittest.mock import Mock

import pytest
import responses

from cloudos_cli.jobs import Job


@pytest.fixture
def job():
    return Job(
        cloudos_url="https://cloudos.example.com",
        apikey="test-key",
        cromwell_token=None,
        workspace_id="workspace-id",
        project_name="current-project",
        workflow_name="ubuntu",
        project_id="project-id",
        workflow_id="workflow-id",
    )


@pytest.fixture
def datasets(monkeypatch):
    factory = Mock()
    monkeypatch.setattr("cloudos_cli.utils.array_job.generate_datasets_for_project", factory)
    factory.return_value.list_folder_content.return_value = {
        "files": [{"name": "no_extension_file", "_id": "file-id"}]
    }
    return factory


@pytest.mark.parametrize("path, project, directory", [
    ("Data/no_extension_file", "current-project", "Data"),
    ("/Data/no_extension_file", "current-project", "Data"),
    ("Data/subfolder/no_extension_file", "current-project", "Data/subfolder"),
    ("/Data/subfolder/nested/no_extension_file", "current-project", "Data/subfolder/nested"),
    ("other-project/Data/no_extension_file", "other-project", "Data"),
    ("/other-project/Data/subfolder/no_extension_file", "other-project", "Data/subfolder"),
])
def test_extensionless_file(job, datasets, path, project, directory):
    result = job.docker_workflow_param_processing(f"--f1={path}", job.project_name)

    assert result == {
        "name": "f1", "prefix": "--", "parameterKind": "dataItem",
        "dataItem": {"kind": "File", "item": "file-id"},
    }
    datasets.assert_called_once_with(
        job.cloudos_url, job.apikey, job.workspace_id, project, job.verify
    )
    datasets.return_value.list_folder_content.assert_called_once_with(directory)


@pytest.mark.parametrize("filename", ["input.csv", "archive.tar.gz", ".hidden"])
@pytest.mark.parametrize("prefix", ["--", "-", ""])
def test_file_names_and_parameter_prefixes(job, datasets, filename, prefix):
    datasets.return_value.list_folder_content.return_value = {
        "files": [{"name": filename, "_id": "file-id"}]
    }
    result = job.docker_workflow_param_processing(f"{prefix}f1=Data/{filename}", job.project_name)

    assert result == {
        "name": "f1", "prefix": prefix, "parameterKind": "dataItem",
        "dataItem": {"kind": "File", "item": "file-id"},
    }


@pytest.mark.parametrize("value", ["plain_text", "no_extension_file", "", "key=value", "Data", "Database/value"])
def test_literal_text(job, datasets, value):
    assert job.docker_workflow_param_processing(f"--label={value}", job.project_name) == {
        "name": "label", "prefix": "--", "parameterKind": "textValue", "textValue": value,
    }
    datasets.assert_not_called()


@pytest.mark.parametrize("pattern", ["*", "*.csv", "file[0-9]", "file.*"])
def test_glob_and_regex_parameters(job, datasets, pattern):
    datasets.return_value.list_project_content.return_value = {
        "folders": [{"name": "Data", "_id": "folder-id"}]
    }
    assert job.docker_workflow_param_processing(f"--f1=Data/{pattern}", job.project_name) == {
        "name": "f1", "prefix": "--", "parameterKind": "globPattern",
        "globPattern": pattern, "folder": "folder-id",
    }


@responses.activate
def test_missing_extensionless_file_fails_before_submission(job, datasets):
    datasets.return_value.list_folder_content.return_value = {"files": []}
    with pytest.raises(ValueError, match="File 'missing' not found in directory 'Data'"):
        job.send_job(parameter=("--f1=Data/missing",), workflow_type="docker", command={"command": "cat"})
    assert len(responses.calls) == 0


@pytest.mark.parametrize("array_job", [False, True])
@responses.activate
def test_submission_payload_contains_file_reference(job, datasets, array_job):
    responses.post(f"{job.cloudos_url}/api/v2/jobs", json={"jobId": "job-id"})
    array_options = {}
    if array_job:
        array_options = {
            "array_parameter": ("--sample=sample",),
            "array_file_header": [{"index": 0, "name": "sample"}],
        }
    job.send_job(
        parameter=("--f1=Data/no_extension_file",),
        workflow_type="docker", command={"command": "cat"}, **array_options
    )

    payload = json.loads(responses.calls[0].request.body)
    assert payload["parameters"][-1] == {
        "name": "f1", "prefix": "--", "parameterKind": "dataItem",
        "dataItem": {"kind": "File", "item": "file-id"},
    }


def test_override_existing_file_parameter(job, datasets):
    parameters = [{
        "name": "f1", "prefix": "--", "parameterKind": "dataItem",
        "dataItem": {"kind": "File", "item": "old-file-id"},
    }]
    assert job.update_parameter_value(parameters, "f1", "Data/no_extension_file")
    assert parameters[0] == {
        "name": "f1", "prefix": "--", "parameterKind": "dataItem",
        "dataItem": {"kind": "File", "item": "file-id"},
    }

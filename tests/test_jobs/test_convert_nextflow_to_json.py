import pytest
import json

from cloudos_cli.jobs.job import Job

actual_json_file = "tests/test_data/convert_nextflow_to_json_params.json"

param_dict = {
    "config": "cloudos_cli/examples/rnatoy.config",
    "parameter": (),
    "params_file": None,
    "array_parameter": (),
    "array_file_header": None,
    "is_module": False,
    "example_parameters": [],
    "git_commit": None,
    "git_tag": None,
    "git_branch": None,
    "project_id": "6054754029b82f0112762b9c",
    "workflow_id": "60b0ca54303ee601a69b42d1",
    "job_name": "new_job",
    "resumable": True,
    "save_logs": True,
    "batch": False,
    "job_queue_id": None,
    "nextflow_profile": None,
    "nextflow_version": '22.10.8',
    "instance_type": "c5.xlarge",
    "instance_disk": 500,
    "execution_platform": "aws",
    "hpc_id": None,
    "workflow_type": 'nextflow',
    "cromwell_id": None,
    "azure_worker_instance_type":'Standard_D4as_v4',
    "azure_worker_instance_disk":100,
    "azure_worker_instance_spot":False,
    "cost_limit": -1,
    "use_mountpoints": False,
    "accelerate_saving_results": False,
    "docker_login": False,
    "command": None,
    "cpus": 1,
    "memory": 4
}


def test_convert_nextflow_to_json_output_correct():
    job = Job(
        "https://cloudos.example",
        "test_api_key",
        None,
        "workspace_id",
        "project",
        "workflow",
        project_id=param_dict["project_id"],
        workflow_id=param_dict["workflow_id"]
    )
    job_json = job.convert_nextflow_to_json(
        param_dict["config"],
        param_dict["params_file"],
        parameter=param_dict["parameter"],
        array_parameter=param_dict["array_parameter"],
        array_file_header=param_dict["array_file_header"],
        is_module=param_dict["is_module"],
        example_parameters=param_dict["example_parameters"],
        git_commit=param_dict["git_commit"],
        git_tag=param_dict["git_tag"],
        git_branch=param_dict["git_branch"],
        project_id=param_dict["project_id"],
        workflow_id=param_dict["workflow_id"],
        job_name=param_dict["job_name"],
        resumable=param_dict["resumable"],
        save_logs=param_dict["save_logs"],
        batch=param_dict["batch"],
        job_queue_id=param_dict["job_queue_id"],
        nextflow_profile=param_dict["nextflow_profile"],
        nextflow_version=param_dict["nextflow_version"],
        instance_type=param_dict["instance_type"],
        instance_disk=param_dict["instance_disk"],
        execution_platform=param_dict["execution_platform"],
        hpc_id=param_dict["hpc_id"],
        workflow_type=param_dict["workflow_type"],
        cromwell_id=param_dict["cromwell_id"],
        azure_worker_instance_type=param_dict["azure_worker_instance_type"],
        azure_worker_instance_disk=param_dict["azure_worker_instance_disk"],
        azure_worker_instance_spot=param_dict["azure_worker_instance_spot"],
        cost_limit=param_dict["cost_limit"],
        use_mountpoints=param_dict["use_mountpoints"],
        accelerate_saving_results=param_dict["accelerate_saving_results"],
        docker_login=param_dict["docker_login"],
        command=param_dict["command"],
        cpus=param_dict["cpus"],
        memory=param_dict["memory"]
        )
    with open(actual_json_file) as json_data:
        correct_json = json.load(json_data)
    assert job_json == correct_json


def test_convert_nextflow_to_json_badly_formed_config():
    no_equals_config = "tests/test_data/wrong_params.config"
    with pytest.raises(ValueError) as excinfo:
        job = Job(
            "https://cloudos.example",
            "test_api_key",
            None,
            "workspace_id",
            "project",
            "workflow",
            project_id=param_dict["project_id"],
            workflow_id=param_dict["workflow_id"]
        )
        job.convert_nextflow_to_json(
            no_equals_config,
            param_dict["params_file"],
            parameter=param_dict["parameter"],
            array_parameter=param_dict["array_parameter"],
            array_file_header=param_dict["array_file_header"],
            is_module=param_dict["is_module"],
            example_parameters=param_dict["example_parameters"],
            git_commit=param_dict["git_commit"],
            git_tag=param_dict["git_tag"],
            git_branch=param_dict["git_branch"],
            project_id=param_dict["project_id"],
            workflow_id=param_dict["workflow_id"],
            job_name=param_dict["job_name"],
            resumable=param_dict["resumable"],
            save_logs=param_dict["save_logs"],
            batch=param_dict["batch"],
            job_queue_id=param_dict["job_queue_id"],
            nextflow_profile=param_dict["nextflow_profile"],
            nextflow_version=param_dict["nextflow_version"],
            instance_type=param_dict["instance_type"],
            instance_disk=param_dict["instance_disk"],
            execution_platform=param_dict["execution_platform"],
            hpc_id=param_dict["hpc_id"],
            workflow_type=param_dict["workflow_type"],
            cromwell_id=param_dict["cromwell_id"],
            azure_worker_instance_type=param_dict["azure_worker_instance_type"],
            azure_worker_instance_disk=param_dict["azure_worker_instance_disk"],
            azure_worker_instance_spot=param_dict["azure_worker_instance_spot"],
            cost_limit=param_dict["cost_limit"],
            use_mountpoints=param_dict["use_mountpoints"],
            accelerate_saving_results=param_dict["accelerate_saving_results"],
            docker_login=param_dict["docker_login"],
            command=param_dict["command"],
            cpus=param_dict["cpus"],
            memory=param_dict["memory"]
            )
        print(str(excinfo.value))
    assert "Could not parse line 2 of tests/test_data/wrong_params.config" in str(excinfo.value)
    assert "reads    s3://lifebit-featured-datasets/pipelines/rnatoy-data" in str(excinfo.value)


def test_parse_job_config_params_reports_offending_line():
    """A line that is not 'name = value' names the line number and its content."""
    with pytest.raises(ValueError) as excinfo:
        Job.parse_job_config_params("tests/test_data/wrong_params.config")
    message = str(excinfo.value)
    assert "line 2" in message
    assert "tests/test_data/wrong_params.config" in message
    assert "reads    s3://lifebit-featured-datasets/pipelines/rnatoy-data" in message


def test_parse_job_config_params_rejects_multiline_value():
    """A value spanning several lines fails with a message naming the cause."""
    with pytest.raises(ValueError) as excinfo:
        Job.parse_job_config_params("tests/test_data/multiline_params.config")
    message = str(excinfo.value)
    assert "line 2" in message
    assert "acceleratedFileSystems=[" in message
    assert "several lines" in message
    assert "single line" in message


def test_parse_job_config_params_strips_inline_comments():
    """Trailing comments are removed instead of being absorbed into the value."""
    parsed = Job.parse_job_config_params("tests/test_data/inline_comment_params.config")
    assert parsed == [("reads", "s3://my-bucket/reads"),
                      ("coloc_window", "0.5"),
                      ("genome", "s3://my-bucket/genome.fa")]


def test_strip_inline_comment_preserves_urls():
    """The '//' of a URL scheme is not mistaken for a comment."""
    assert Job.strip_inline_comment("reads = s3://bucket/key") == "reads = s3://bucket/key"
    assert Job.strip_inline_comment("reads = s3://bucket/key  // note") == "reads = s3://bucket/key"
    assert Job.strip_inline_comment("reads = s3://bucket/key  # note") == "reads = s3://bucket/key"


def test_parse_job_config_params_keeps_names_containing_params():
    """A parameter whose name contains 'params' is not dropped."""
    assert Job.parse_job_config_params("tests/test_data/params_in_name.config") == [
        ("input_params", "s3://bucket/a"),
        ("reads", "s3://bucket/b"),
        ("extra_params_file", "foo.json")]


def test_parse_job_config_params_rejects_empty_value():
    """A parameter with no value fails instead of being sent as empty."""
    with pytest.raises(ValueError) as excinfo:
        Job.parse_job_config_params("tests/test_data/no_value_params.config")
    message = str(excinfo.value)
    assert "line 3" in message
    assert "'empty' has no value" in message


def test_parse_job_config_params_keeps_single_line_lists():
    """A single-line list literal is passed through as text."""
    parsed = dict(Job.parse_job_config_params("tests/test_data/inline_comment_params.config"))
    assert parsed["coloc_window"] == "0.5"


def test_list_literal_warning_reports_count_and_received_value():
    """A list literal warns, naming the elements and the string actually sent."""
    warning = Job.list_literal_warning("tools", "[fastqc,multiqc,star]")
    assert "3 elements" in warning
    assert "'fastqc', 'multiqc', 'star'" in warning
    assert "--tools '[fastqc,multiqc,star]'" in warning
    assert "--params-file" in warning


def test_list_literal_warning_singular_element():
    """A single-element list is described in the singular."""
    warning = Job.list_literal_warning("coloc_prior", "[1e-5]")
    assert "1 element ('1e-5')" in warning


def test_list_literal_warning_none_for_scalars():
    """Plain values, including paths and numbers, are not warned about."""
    assert Job.list_literal_warning("reads", "s3://bucket/key") is None
    assert Job.list_literal_warning("chunk_size", "50") is None
    assert Job.list_literal_warning("pattern", "sample[1].txt") is None


def test_parse_job_config_params_examples_unchanged():
    """The shipped example configs keep parsing exactly as before."""
    assert Job.parse_job_config_params("cloudos_cli/examples/rnatoy.config") == [
        ("reads", "s3://lifebit-featured-datasets/pipelines/rnatoy-data"),
        ("genome", "s3://lifebit-featured-datasets/pipelines/rnatoy-data/"
                   "ggal_1_48850000_49020000.Ggal71.500bpflank.fa"),
        ("annot", "s3://lifebit-featured-datasets/pipelines/rnatoy-data/"
                  "ggal_1_48850000_49020000.bed.gff")]
    # WDL keeps quotes, so arrays and maps survive as text
    wdl = dict(Job.parse_job_config_params("cloudos_cli/examples/wdl.config", "wdl"))
    assert wdl["test.arrayTest"] == '["lala"]'
    assert wdl["test.mapTest"] == '{"some":"props"}'


def test_params_file_payload_s3():
    job = Job(
        "https://cloudos.example",
        "test_api_key",
        None,
        "workspace_id",
        "project",
        "workflow",
        project_id=param_dict["project_id"],
        workflow_id=param_dict["workflow_id"]
    )
    payload = job.build_parameters_file_payload("s3://my-bucket/path/to/params.json")
    assert payload == {
        "parametersFile": {
            "dataItemEmbedded": {
                "data": {
                    "name": "params.json",
                    "s3BucketName": "my-bucket",
                    "s3ObjectKey": "path/to/params.json"
                },
                "type": "S3File"
            }
        }
    }


def test_params_file_payload_azure_blob():
    job = Job(
        "https://cloudos.example",
        "test_api_key",
        None,
        "workspace_id",
        "project",
        "workflow",
        project_id=param_dict["project_id"],
        workflow_id=param_dict["workflow_id"]
    )
    payload = job.build_parameters_file_payload(
        "az://6480f3db916489d248956a5f.blob.core.windows.net/"
        "cloudos-66607e71e8cffa9985592c10/dataset/697b7341c69bacdd8b0b700d/"
        "rnatoy_params.json_137531fe-c19a-44c6-9e30-2d6dcb371072"
    )
    assert payload == {
        "parametersFile": {
            "dataItemEmbedded": {
                "data": {
                    "name": "rnatoy_params.json",
                    "blobStorageAccountName": "6480f3db916489d248956a5f",
                    "blobContainerName": "cloudos-66607e71e8cffa9985592c10",
                    "blobName": "dataset/697b7341c69bacdd8b0b700d/rnatoy_params.json_137531fe-c19a-44c6-9e30-2d6dcb371072"
                },
                "type": "AzureBlobFile"
            }
        }
    }


def test_params_file_payload_azure_blob_with_query_not_supported():
    job = Job(
        "https://cloudos.example",
        "test_api_key",
        None,
        "workspace_id",
        "project",
        "workflow",
        project_id=param_dict["project_id"],
        workflow_id=param_dict["workflow_id"]
    )
    with pytest.raises(ValueError) as excinfo:
        job.build_parameters_file_payload(
            "az://6480f3db916489d248956a5f.blob.core.windows.net/"
            "cloudos-66607e71e8cffa9985592c10/dataset/697b7341c69bacdd8b0b700d/"
            "rnatoy_params.json_137531fe-c19a-44c6-9e30-2d6dcb371072?sv=token"
        )
    assert "query parameters is not supported" in str(excinfo.value)


def test_params_file_payload_file_explorer(monkeypatch):
    job = Job(
        "https://cloudos.example",
        "test_api_key",
        None,
        "workspace_id",
        "project",
        "workflow",
        project_id=param_dict["project_id"],
        workflow_id=param_dict["workflow_id"]
    )

    def fake_get_file_or_folder_id(*args, **kwargs):
        return "file-123"

    monkeypatch.setattr(
        "cloudos_cli.jobs.job.get_file_or_folder_id",
        fake_get_file_or_folder_id
    )
    payload = job.build_parameters_file_payload("Data/params-files/run160226.json")
    assert payload == {
        "parametersFile": {
            "dataItem": {
                "kind": "File",
                "item": "file-123"
            }
        }
    }

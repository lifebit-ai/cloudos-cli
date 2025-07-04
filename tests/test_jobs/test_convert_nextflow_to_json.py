import pytest
import json

from cloudos_cli.jobs.job import Job

actual_json_file = "tests/test_data/convert_nextflow_to_json_params.json"

param_dict = {
    "config": "cloudos_cli/examples/rnatoy.config",
    "parameter": (),
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
    "storage_mode": 'regular',
    "lustre_size": 1200,
    "execution_platform": "aws",
    "hpc_id": None,
    "workflow_type": 'nextflow',
    "cromwell_id": None,
    "azure_worker_instance_type":'Standard_D4as_v4',
    "azure_worker_instance_disk":100,
    "azure_worker_instance_spot":False,
    "cost_limit": -1,
    "use_mountpoints": False,
    "docker_login": False,
    "command": None,
    "cpus": 1,
    "memory": 4
}


def test_convert_nextflow_to_json_output_correct():
    job_json = Job.convert_nextflow_to_json(
        1, param_dict["config"],
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
        storage_mode=param_dict["storage_mode"],
        lustre_size=param_dict["lustre_size"],
        execution_platform=param_dict["execution_platform"],
        hpc_id=param_dict["hpc_id"],
        workflow_type=param_dict["workflow_type"],
        cromwell_id=param_dict["cromwell_id"],
        azure_worker_instance_type=param_dict["azure_worker_instance_type"],
        azure_worker_instance_disk=param_dict["azure_worker_instance_disk"],
        azure_worker_instance_spot=param_dict["azure_worker_instance_spot"],
        cost_limit=param_dict["cost_limit"],
        use_mountpoints=param_dict["use_mountpoints"],
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
        Job.convert_nextflow_to_json(
            1, no_equals_config,
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
            storage_mode=param_dict["storage_mode"],
            lustre_size=param_dict["lustre_size"],
            execution_platform=param_dict["execution_platform"],
            hpc_id=param_dict["hpc_id"],
            workflow_type=param_dict["workflow_type"],
            cromwell_id=param_dict["cromwell_id"],
            azure_worker_instance_type=param_dict["azure_worker_instance_type"],
            azure_worker_instance_disk=param_dict["azure_worker_instance_disk"],
            azure_worker_instance_spot=param_dict["azure_worker_instance_spot"],
            cost_limit=param_dict["cost_limit"],
            use_mountpoints=param_dict["use_mountpoints"],
            docker_login=param_dict["docker_login"],
            command=param_dict["command"],
            cpus=param_dict["cpus"],
            memory=param_dict["memory"]
            )
        print(str(excinfo.value))
    assert "Please, specify your parameters in\
            tests/test_data/wrong_params.config\
            using the \'=\' as spacer.\
            E.g: name = my_name".replace("           ", "") in str(excinfo.value)

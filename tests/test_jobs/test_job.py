import pytest 
import json

from cloudos.jobs.job import Job

actual_json_file = "tests/test_data/convert_nextflow_to_json_params.json"

param_dict = {
    "config" : "cloudos/examples/rnatoy.config",
    "project_id" : "614b181e31de9201a5c3fab4",
    "workflow_id" : "616edcf11b866a01d69f9480",
    "job_name" : "new_job",
    "resumable" : True,
    "instance_type" : "c5.xlarge",
    "instance_disk" : 500,
    "spot" : True
}

def test_output_correct():
    job_json = Job.convert_nextflow_to_json(1,param_dict["config"],
project_id=param_dict["project_id"], workflow_id=param_dict["workflow_id"],
job_name=param_dict["job_name"],resumable=param_dict["resumable"],instance_type=param_dict["instance_type"],
instance_disk=param_dict["instance_disk"],spot=param_dict["spot"]
)
    with open(actual_json_file) as json_data:
        correct_json = json.load(json_data)
    assert job_json == correct_json

def test_badly_formed_config():
    no_equals_config = "tests/test_data/wrong_params.config"
    with pytest.raises(ValueError) as excinfo:
        job_json = Job.convert_nextflow_to_json(1,no_equals_config,
        project_id=param_dict["project_id"], workflow_id=param_dict["workflow_id"],
        job_name=param_dict["job_name"],resumable=param_dict["resumable"],instance_type=param_dict["instance_type"],
        instance_disk=param_dict["instance_disk"],spot=param_dict["spot"]
        )
        print(str(excinfo.value))
    assert 'Please, specify your parameters in tests/test_data/wrong_params.config using the \'=\' char as spacer. E.g: name = my_name' in str(excinfo.value)



"""pytest tests for --custom-script-path in 'cloudos bash job'"""
import json
import click
import mock
import pytest
from click.testing import CliRunner
from cloudos_cli.__main__ import run_cloudos_cli
from cloudos_cli.jobs import Job

APIKEY = 'vnoiweur89u2ongs'
CLOUDOS_URL = 'http://cloudos.lifebit.ai'
WORKSPACE_ID = 'lv89ufc838sdig'
PROJECT_NAME = "lifebit-testing"
WORKFLOW_NAME = "ubuntu"
SCRIPT_ID = "12345"
custom_cmd = {"command": 'command.sh', "customScriptFile": {"dataItem": {"kind": "File", "item": SCRIPT_ID}}}
base_args = [
    'bash', 'job',
    '--apikey', APIKEY,
    '--cloudos-url', CLOUDOS_URL,
    '--workspace-id', WORKSPACE_ID,
    '--project-name', PROJECT_NAME,
    '--workflow-name', WORKFLOW_NAME
]


def _ds_with_files(files):
    ds = mock.MagicMock()
    ds.list_folder_content.return_value = {"files": files}
    return ds


def _job_without_init():
    # setup_custom_script_command does not depend on instance state
    return Job.__new__(Job)


def test_setup_custom_script_command_found():
    ds = _ds_with_files([{"name": "other.sh", "_id": "000"}, {"name": "command.sh", "_id": SCRIPT_ID}])
    cmd = _job_without_init().setup_custom_script_command("Data/scripts/command.sh", ds)
    assert cmd == custom_cmd
    ds.list_folder_content.assert_called_once_with("Data/scripts")


def test_setup_custom_script_command_not_found():
    ds = _ds_with_files([{"name": "other.sh", "_id": "000"}])
    with pytest.raises(ValueError, match='Custom script "command.sh" not found'):
        _job_without_init().setup_custom_script_command("Data/command.sh", ds)


def test_setup_params_array_file_uses_custom_script():
    job = _job_without_init()
    job.array_file_id = "9876"
    ds = _ds_with_files([{"name": "command.sh", "_id": SCRIPT_ID}])
    cmd = job.setup_params_array_file("Data/command.sh", ds, None, ",")
    assert cmd == custom_cmd | {
        "arrayFile": {"dataItem": {"kind": "File", "item": "9876"}, "separator": ","}
    }


def test_bash_job_requires_command_or_custom_script():
    result = CliRunner().invoke(run_cloudos_cli, base_args)
    assert result.exit_code == 2
    # rich-click colours option names when colour is forced (e.g. GitHub Actions)
    assert "Must provide --command or --custom-script-path" in click.unstyle(result.output)


@pytest.mark.parametrize("extra_args, expected_project", [
    (['--custom-script-path', 'Data/command.sh'], PROJECT_NAME),
    (['--custom-script-path', 'Data/command.sh', '--custom-script-project', 'other'], 'other'),
])
def test_bash_job_sends_custom_script(extra_args, expected_project):
    with mock.patch('cloudos_cli.bash.cli.jb.Job') as job_cls, \
            mock.patch('cloudos_cli.bash.cli.generate_datasets_for_project') as gen_ds:
        job = job_cls.return_value
        job.setup_custom_script_command.return_value = custom_cmd
        job.send_job.return_value = "job123"
        job.get_job_status.return_value.content = json.dumps({"status": "initializing"})
        result = CliRunner().invoke(run_cloudos_cli, base_args + extra_args)

    assert result.exit_code == 0, result.output
    assert gen_ds.call_args.args[3] == expected_project
    job.setup_custom_script_command.assert_called_once_with('Data/command.sh', gen_ds.return_value)
    assert job.send_job.call_args.kwargs["command"] == custom_cmd


def test_bash_job_sends_text_command():
    with mock.patch('cloudos_cli.bash.cli.jb.Job') as job_cls, \
            mock.patch('cloudos_cli.bash.cli.generate_datasets_for_project') as gen_ds:
        job = job_cls.return_value
        job.send_job.return_value = "job123"
        job.get_job_status.return_value.content = json.dumps({"status": "initializing"})
        result = CliRunner().invoke(run_cloudos_cli, base_args + ['--command', 'echo hi'])

    assert result.exit_code == 0, result.output
    gen_ds.assert_not_called()
    job.setup_custom_script_command.assert_not_called()
    assert job.send_job.call_args.kwargs["command"] == {"command": "echo hi"}

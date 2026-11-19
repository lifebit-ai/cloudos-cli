"""pytest for --environment-variable in 'cloudos job run', 'job clone' and 'job resume' (LP-112224).

The API classes are mocked: the tests check that valid variables reach the job submission
and that invalid ones fail fast with a clear message, before any job is submitted.
"""
import mock
import pytest
from click.testing import CliRunner
from cloudos_cli.jobs.cli import run, job

BASE_ARGS = ['--apikey', 'xxx', '--cloudos-url', 'http://cloudos.lifebit.ai',
             '--workspace-id', 'ws', '--project-name', 'proj', '--workflow-name', 'wf']


@pytest.fixture(autouse=True)
def no_profile_config():
    """Skip profile loading: every option is given on the command line."""
    with mock.patch('cloudos_cli.configure.configure.ConfigurationProfile.load_profile_and_validate_data',
                    return_value={}):
        yield


def invoke_run(extra_args, is_module=False, workflow_type='nextflow'):
    """Invoke 'job run' with mocked API classes; returns (result, mocked Job class)."""
    with mock.patch('cloudos_cli.jobs.cli.Cloudos') as cloudos_cls, \
            mock.patch('cloudos_cli.jobs.cli.jb.Job') as job_cls, \
            mock.patch('cloudos_cli.jobs.cli.Queue'):
        cloudos_cls.return_value.detect_workflow.return_value = workflow_type
        cloudos_cls.return_value.is_module.return_value = is_module
        job_cls.return_value.send_job.return_value = 'job123'
        job_cls.return_value.get_job_status.return_value.content = b'{"status": "initializing"}'
        result = CliRunner().invoke(run, BASE_ARGS + extra_args)
    return result, job_cls


@pytest.mark.parametrize('value', ['v1', 'v2'])
def test_run_passes_environment_variable_to_send_job(value):
    result, job_cls = invoke_run(['--nextflow-version', '25.10.4',
                                  '--environment-variable', f'NXF_SYNTAX_PARSER={value}'])
    assert result.exit_code == 0, result.output
    assert f'Environment variable: NXF_SYNTAX_PARSER={value}' in result.output
    send_kwargs = job_cls.return_value.send_job.call_args.kwargs
    assert send_kwargs['environment_variable'] == (f'NXF_SYNTAX_PARSER={value}',)
    assert send_kwargs['nextflow_version'] == '25.10.4'


def test_run_without_environment_variable_sends_empty_tuple():
    result, job_cls = invoke_run(['--nextflow-version', '25.10.4'])
    assert result.exit_code == 0, result.output
    assert job_cls.return_value.send_job.call_args.kwargs['environment_variable'] == ()


@pytest.mark.parametrize('extra_args, error', [
    (['--nextflow-version', '24.04.4', '--environment-variable', 'NXF_SYNTAX_PARSER=v2'],
     'requires Nextflow 25.04.0 or later'),
    (['--nextflow-version', '25.10.4', '--environment-variable', 'NXF_OTHER=v2'],
     "'NXF_OTHER' is not supported"),
    (['--nextflow-version', '25.10.4', '--environment-variable', 'NXF_SYNTAX_PARSER=v3'],
     'Allowed values: v1, v2'),
    (['--nextflow-version', '25.10.4', '--environment-variable', 'NXF_SYNTAX_PARSER'],
     'Use the form NAME=VALUE'),
])
def test_run_fails_fast_without_submitting(extra_args, error):
    result, job_cls = invoke_run(extra_args)
    assert result.exit_code != 0
    assert error in str(result.exception)
    job_cls.assert_not_called()


def test_run_default_version_explains_missing_nextflow_version():
    """Without --nextflow-version, user workflows default to 24.04.4: the error says so."""
    result, job_cls = invoke_run(['--environment-variable', 'NXF_SYNTAX_PARSER=v2'])
    assert result.exit_code != 0
    message = str(result.exception)
    assert 'Nextflow 24.04.4 is the default because --nextflow-version was not set' in message
    assert 'Use one of these Nextflow versions: 25.04.8, 25.10.4' in message
    job_cls.assert_not_called()


def test_run_azure_is_rejected():
    result, job_cls = invoke_run(['--execution-platform', 'azure',
                                  '--environment-variable', 'NXF_SYNTAX_PARSER=v2'])
    assert result.exit_code != 0
    assert 'azure execution platform only supports Nextflow 22.11.1-edge' in str(result.exception)
    job_cls.assert_not_called()


def test_run_platform_workflow_is_rejected():
    result, job_cls = invoke_run(['--nextflow-version', '25.10.4',
                                  '--environment-variable', 'NXF_SYNTAX_PARSER=v2'], is_module=True)
    assert result.exit_code != 0
    assert "can't be used with Platform Workflows" in str(result.exception)
    job_cls.assert_not_called()


def test_run_non_nextflow_workflow_is_rejected():
    result, job_cls = invoke_run(['--environment-variable', 'NXF_SYNTAX_PARSER=v2'], workflow_type='docker')
    assert result.exit_code != 0
    assert 'only supported for Nextflow workflows' in str(result.exception)
    job_cls.assert_not_called()


@pytest.mark.parametrize('command', ['clone', 'resume'])
def test_clone_resume_pass_environment_variable(command):
    with mock.patch('cloudos_cli.jobs.cli.jb.Job') as job_cls:
        job_cls.return_value.clone_or_resume_job.return_value = 'job456'
        job_cls.return_value.get_job_status.return_value.content = b'{"status": "initializing"}'
        result = CliRunner().invoke(job, [command, '--apikey', 'xxx', '--workspace-id', 'ws',
                                          '--job-id', 'job123',
                                          '--environment-variable', 'NXF_SYNTAX_PARSER=v2'])
    assert result.exit_code == 0, result.output
    clone_kwargs = job_cls.return_value.clone_or_resume_job.call_args.kwargs
    assert clone_kwargs['environment_variable'] == ('NXF_SYNTAX_PARSER=v2',)
    assert clone_kwargs['mode'] == command

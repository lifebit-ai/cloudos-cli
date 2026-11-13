"""pytest for Nextflow runtime environment variables (e.g. NXF_SYNTAX_PARSER) in the Python SDK.

Covers Job.send_job (LP-112225) and Job.clone_or_resume_job: the variables are sent as
'environmentVariables' in the job payload, and invalid ones raise a clear error without
submitting the job.
"""
import json
import mock
import pytest
import responses
from cloudos_cli.jobs import Job
from tests.functions_for_pytest import load_json_file

APIKEY = 'vnoiweur89u2ongs'
CLOUDOS_URL = 'http://cloudos.lifebit.ai'
WORKSPACE_ID = 'lv89ufc838sdig'
PROJECT_ID = '6054754029b82f0112762b9c'
WORKFLOW_ID = '60b0ca54303ee601a69b42d1'
SOURCE_JOB_ID = '616ee9681b866a01d69fa1cd'
JOB_CONFIG = 'cloudos_cli/examples/rnatoy.config'
JOBS_URL = f'{CLOUDOS_URL}/api/v2/jobs?teamId={WORKSPACE_ID}'
PAYLOAD_URL = f'{CLOUDOS_URL}/api/v1/jobs/{SOURCE_JOB_ID}/request-payload?teamId={WORKSPACE_ID}'
JOB_URL = f'{CLOUDOS_URL}/api/v1/jobs/{SOURCE_JOB_ID}?teamId={WORKSPACE_ID}'
JOB_PAYLOAD_INPUT = 'tests/test_data/job_request_payload.json'
JOB_DETAILS_INPUT = 'tests/test_data/get_job_details.json'
SEND_JOB_RESPONSE = 'tests/test_data/send_job.json'
CLONE_RESPONSE_INPUT = 'tests/test_data/clone_job_response.json'


def make_job():
    """Job with explicit project and workflow ids, so no lookups are made."""
    return Job(cloudos_url=CLOUDOS_URL, apikey=APIKEY, cromwell_token=None,
               workspace_id=WORKSPACE_ID, project_name=None, workflow_name=None,
               project_id=PROJECT_ID, workflow_id=WORKFLOW_ID)


def sent_payload():
    """The JSON body of the job POST request."""
    posts = [call for call in responses.calls if call.request.method == 'POST']
    assert len(posts) == 1
    return json.loads(posts[0].request.body)


def add_job_post(body_file=SEND_JOB_RESPONSE):
    responses.add(responses.POST, url=JOBS_URL, body=load_json_file(body_file), status=200)


def add_source_job(payload_overrides=None):
    payload = json.loads(load_json_file(JOB_PAYLOAD_INPUT))
    payload.update(payload_overrides or {})
    responses.add(responses.GET, url=PAYLOAD_URL, body=json.dumps(payload), status=200)
    responses.add(responses.GET, url=JOB_URL, body=load_json_file(JOB_DETAILS_INPUT), status=200)


# --- send_job ---------------------------------------------------------------

@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
@pytest.mark.parametrize('value', ['v1', 'v2'])
def test_send_job_with_syntax_parser(value):
    """A supported variable on a supported version is sent as environmentVariables."""
    add_job_post()
    make_job().send_job(job_config=JOB_CONFIG, nextflow_version='25.10.4',
                        environment_variable=(f'NXF_SYNTAX_PARSER={value}',))
    assert sent_payload()['environmentVariables'] == [{'name': 'NXF_SYNTAX_PARSER', 'value': value}]


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
def test_send_job_without_environment_variables_has_no_field():
    """Jobs without environment variables don't send the field (unchanged payload)."""
    add_job_post()
    make_job().send_job(job_config=JOB_CONFIG, nextflow_version='25.10.4')
    assert 'environmentVariables' not in sent_payload()


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
@pytest.mark.parametrize('env_var, nextflow_version, error', [
    ('NXF_SYNTAX_PARSER=v2', '24.04.4', 'requires Nextflow 25.04.0 or later'),
    ('NXF_OTHER=v2', '25.10.4', "'NXF_OTHER' is not supported"),
    ('NXF_SYNTAX_PARSER=v3', '25.10.4', 'Allowed values: v1, v2'),
])
def test_send_job_rejects_without_submitting(env_var, nextflow_version, error):
    """Unsupported version, name or value raise a clear error and nothing is submitted."""
    with pytest.raises(ValueError, match=error):
        make_job().send_job(job_config=JOB_CONFIG, nextflow_version=nextflow_version,
                            environment_variable=(env_var,))
    assert len(responses.calls) == 0


# --- clone / resume ---------------------------------------------------------

@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
def test_clone_keeps_original_environment_variables():
    """Cloning without overrides keeps the variables of the original job, as strings."""
    add_source_job({'nextflowVersion': '25.10.4',
                    'environmentVariables': [{'name': 'NXF_SYNTAX_PARSER', 'value': 'v2'}]})
    add_job_post(CLONE_RESPONSE_INPUT)
    make_job().clone_or_resume_job(source_job_id=SOURCE_JOB_ID, mode='clone')
    assert sent_payload()['environmentVariables'] == [{'name': 'NXF_SYNTAX_PARSER', 'value': 'v2'}]


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
@pytest.mark.parametrize('mode', ['clone', 'resume'])
def test_clone_resume_override_environment_variable(mode):
    """An override replaces the original value."""
    add_source_job({'nextflowVersion': '25.10.4',
                    'environmentVariables': [{'name': 'NXF_SYNTAX_PARSER', 'value': 'v1'}]})
    add_job_post(CLONE_RESPONSE_INPUT)
    make_job().clone_or_resume_job(source_job_id=SOURCE_JOB_ID, mode=mode,
                                   environment_variable=('NXF_SYNTAX_PARSER=v2',))
    assert sent_payload()['environmentVariables'] == [{'name': 'NXF_SYNTAX_PARSER', 'value': 'v2'}]


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
def test_clone_adds_environment_variable_with_new_version():
    """A variable can be added together with a compatible --nextflow-version."""
    add_source_job()  # original job: Nextflow 22.10.8, no variables
    add_job_post(CLONE_RESPONSE_INPUT)
    make_job().clone_or_resume_job(source_job_id=SOURCE_JOB_ID, mode='clone', nextflow_version='25.04.8',
                                   environment_variable=('NXF_SYNTAX_PARSER=v2',))
    payload = sent_payload()
    assert payload['nextflowVersion'] == '25.04.8'
    assert payload['environmentVariables'] == [{'name': 'NXF_SYNTAX_PARSER', 'value': 'v2'}]


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
def test_clone_rejects_variable_on_original_old_version():
    """Adding a variable to a job that ran on an unsupported version fails without submitting."""
    add_source_job()  # original job: Nextflow 22.10.8
    with pytest.raises(ValueError, match='uses Nextflow 22.10.8'):
        make_job().clone_or_resume_job(source_job_id=SOURCE_JOB_ID, mode='clone',
                                       environment_variable=('NXF_SYNTAX_PARSER=v2',))
    assert not [call for call in responses.calls if call.request.method == 'POST']


@mock.patch('cloudos_cli.clos', mock.MagicMock())
@responses.activate
def test_clone_rejects_inherited_variable_on_downgraded_version():
    """Downgrading the version of a job that has a variable fails without submitting."""
    add_source_job({'nextflowVersion': '25.10.4',
                    'environmentVariables': [{'name': 'NXF_SYNTAX_PARSER', 'value': 'v2'}]})
    with pytest.raises(ValueError, match='uses Nextflow 24.04.4'):
        make_job().clone_or_resume_job(source_job_id=SOURCE_JOB_ID, mode='clone', nextflow_version='24.04.4')
    assert not [call for call in responses.calls if call.request.method == 'POST']


@mock.patch('cloudos_cli.clos', mock.MagicMock())
def test_clone_malformed_variable_fails_before_any_request():
    """A malformed override fails before the original job is fetched."""
    with responses.RequestsMock() as rsps:
        with pytest.raises(ValueError, match='Use the form NAME=VALUE'):
            make_job().clone_or_resume_job(source_job_id=SOURCE_JOB_ID, mode='clone',
                                           environment_variable=('NXF_SYNTAX_PARSER',))
        assert len(rsps.calls) == 0


def test_fix_boolean_strings_keeps_environment_variable_values():
    """'true'/'false' values of environment variables must stay strings."""
    payload = {'resumable': 'true', 'environmentVariables': [{'name': 'SOME_FLAG', 'value': 'true'}]}
    fixed = make_job().fix_boolean_strings(payload)
    assert fixed['resumable'] is True
    assert fixed['environmentVariables'] == [{'name': 'SOME_FLAG', 'value': 'true'}]

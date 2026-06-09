"""Tests for the queue create command and Queue.create_job_queue() method."""

import json
import pytest
import responses
import requests_mock as requests_mock_module
from click.testing import CliRunner

from cloudos_cli.queue.queue import Queue, QUEUE_PRESETS
from cloudos_cli.utils.errors import BadRequestException
from cloudos_cli.__main__ import run_cloudos_cli
from tests.functions_for_pytest import load_json_file

# ---------------------------------------------------------------------------
# Constants shared across tests
# ---------------------------------------------------------------------------

APIKEY = 'vnoiweur89u2ongs'
CLOUDOS_URL = 'https://cloudos.lifebit.ai'
WORKSPACE_ID = 'lv89ufc838sdig'
CREATE_RESPONSE_FILE = 'tests/test_data/queue/create_queue_response.json'
QUEUES_FILE = 'tests/test_data/queue/queues.json'
SYSTEM_QUEUES_FILE = 'tests/test_data/queue/system_queues.json'

with open(CREATE_RESPONSE_FILE) as f:
    CREATE_RESPONSE_JSON_STR = f.read()
    CREATE_RESPONSE_JSON_DICT = json.loads(CREATE_RESPONSE_JSON_STR)


# ===========================================================================
# Unit tests – Queue.get_preset_template()
# ===========================================================================

class TestGetPresetTemplate:
    def test_returns_dict_for_each_known_preset(self):
        for preset_name in QUEUE_PRESETS:
            result = Queue.get_preset_template(preset_name)
            assert isinstance(result, dict)
            assert 'computeEnvironmentName' in result
            assert 'computeResources' in result
            assert 'templateName' in result
            assert 'templateDescription' in result

    def test_standard_stable_preset_uses_ec2(self):
        preset = Queue.get_preset_template('standard-stable')
        assert preset['computeResources']['type'] == 'EC2'
        assert preset['computeResources']['allocationStrategy'] == 'BEST_FIT_PROGRESSIVE'

    def test_standard_cost_saving_preset_uses_spot(self):
        preset = Queue.get_preset_template('standard-cost-saving')
        assert preset['computeResources']['type'] == 'SPOT'
        assert preset['computeResources']['allocationStrategy'] == 'SPOT_CAPACITY_OPTIMIZED'
        assert preset['computeResources']['bidPercentage'] == 100

    def test_read_write_optimised_has_volume(self):
        preset = Queue.get_preset_template('read-write-optimised')
        assert 'volume' in preset['computeResources']
        assert preset['computeResources']['volume']['type'] == 'gp3'

    def test_standard_gpu_includes_gpu_instances(self):
        preset = Queue.get_preset_template('standard-gpu')
        instance_types = preset['computeResources']['instanceTypes']
        gpu_instances = [i for i in instance_types if i.startswith(('g4dn', 'p3'))]
        assert len(gpu_instances) > 0

    def test_raises_value_error_for_unknown_preset(self):
        with pytest.raises(ValueError, match="Unknown preset"):
            Queue.get_preset_template('nonexistent-preset')

    def test_all_presets_have_optimal_instance_type(self):
        for preset_name in QUEUE_PRESETS:
            preset = Queue.get_preset_template(preset_name)
            assert 'optimal' in preset['computeResources']['instanceTypes']

    def test_all_presets_have_max_vcpus(self):
        for preset_name in QUEUE_PRESETS:
            preset = Queue.get_preset_template(preset_name)
            assert preset['computeResources']['maxvCpus'] > 0


# ===========================================================================
# Unit tests – Queue.create_job_queue() (API mocked via responses)
# ===========================================================================

class TestCreateJobQueue:
    def _make_queue(self):
        return Queue(
            cloudos_url=CLOUDOS_URL,
            apikey=APIKEY,
            cromwell_token=None,
            workspace_id=WORKSPACE_ID,
        )

    @responses.activate
    def test_create_job_queue_success_returns_id(self):
        responses.add(
            responses.POST,
            url=f"{CLOUDOS_URL}/api/v1/teams/aws/v2/job-queue?teamId={WORKSPACE_ID}",
            body=CREATE_RESPONSE_JSON_STR,
            status=200,
            content_type='application/json',
        )
        q = self._make_queue()
        queue_id = q.create_job_queue(
            label='Test Queue',
            description='A test queue',
            preset_name='standard-stable',
        )
        assert queue_id == CREATE_RESPONSE_JSON_DICT['_id']

    @responses.activate
    def test_create_job_queue_posts_correct_payload(self):
        responses.add(
            responses.POST,
            url=f"{CLOUDOS_URL}/api/v1/teams/aws/v2/job-queue?teamId={WORKSPACE_ID}",
            body=CREATE_RESPONSE_JSON_STR,
            status=200,
            content_type='application/json',
        )
        q = self._make_queue()
        q.create_job_queue(
            label='My Queue',
            description='desc',
            preset_name='standard-cost-saving',
            executor='nextflow',
        )
        # Inspect what was sent
        sent_payload = json.loads(responses.calls[0].request.body)
        assert sent_payload['label'] == 'My Queue'
        assert sent_payload['description'] == 'desc'
        assert sent_payload['executor'] == 'nextflow'
        assert sent_payload['status'] == 'ToCreate'
        assert sent_payload['isDefault'] is False
        assert sent_payload['id'] == ''
        assert sent_payload['environment']['computeResources']['type'] == 'SPOT'

    @responses.activate
    def test_create_job_queue_raises_on_400(self):
        error_body = json.dumps({
            'statusCode': 400,
            'code': 'BadRequest',
            'message': 'Bad Request.',
        })
        responses.add(
            responses.POST,
            url=f"{CLOUDOS_URL}/api/v1/teams/aws/v2/job-queue?teamId={WORKSPACE_ID}",
            body=error_body,
            status=400,
            content_type='application/json',
        )
        q = self._make_queue()
        with pytest.raises(BadRequestException):
            q.create_job_queue(
                label='Bad Queue',
                description='',
                preset_name='standard-stable',
            )

    @responses.activate
    def test_create_job_queue_all_presets_succeed(self):
        for preset_name in QUEUE_PRESETS:
            responses.add(
                responses.POST,
                url=f"{CLOUDOS_URL}/api/v1/teams/aws/v2/job-queue?teamId={WORKSPACE_ID}",
                body=CREATE_RESPONSE_JSON_STR,
                status=200,
                content_type='application/json',
            )
        q = self._make_queue()
        for preset_name in QUEUE_PRESETS:
            queue_id = q.create_job_queue(
                label=f'queue-{preset_name}',
                description='test',
                preset_name=preset_name,
            )
            assert queue_id != ''

    def test_create_job_queue_raises_on_invalid_preset(self):
        q = self._make_queue()
        with pytest.raises(ValueError, match='Unknown preset'):
            q.create_job_queue(
                label='Queue',
                description='',
                preset_name='not-a-preset',
            )


# ===========================================================================
# CLI integration tests – `cloudos queue create`
# ===========================================================================

class TestCreateQueueCLI:
    def _base_args(self, extra=None):
        args = [
            'queue', 'create',
            '--apikey', APIKEY,
            '--cloudos-url', CLOUDOS_URL,
            '--workspace-id', WORKSPACE_ID,
            '--label', 'Test Queue',
            '--description', 'A test queue',
            '--preset', 'standard-stable',
            '--yes',
        ]
        if extra:
            args.extend(extra)
        return args

    def test_create_command_exists_in_help(self):
        runner = CliRunner()
        result = runner.invoke(run_cloudos_cli, ['queue', '--help'])
        assert result.exit_code == 0
        assert 'create' in result.output

    def test_create_command_help(self):
        runner = CliRunner()
        result = runner.invoke(run_cloudos_cli, ['queue', 'create', '--help'])
        assert result.exit_code == 0
        assert '--label' in result.output
        assert '--preset' in result.output
        assert '--yes' in result.output
        assert '--description' in result.output

    def test_create_command_all_presets_in_help(self):
        runner = CliRunner()
        result = runner.invoke(run_cloudos_cli, ['queue', 'create', '--help'])
        for preset_name in QUEUE_PRESETS:
            assert preset_name in result.output

    def test_create_queue_success_with_yes_flag(self):
        runner = CliRunner()
        with requests_mock_module.Mocker() as m:
            m.post(
                f"{CLOUDOS_URL}/api/v1/teams/aws/v2/job-queue?teamId={WORKSPACE_ID}",
                text=CREATE_RESPONSE_JSON_STR,
                status_code=200,
            )
            result = runner.invoke(run_cloudos_cli, self._base_args())
        assert result.exit_code == 0
        assert 'created successfully' in result.output
        assert CREATE_RESPONSE_JSON_DICT['_id'] in result.output

    def test_create_queue_shows_url_on_success(self):
        runner = CliRunner()
        with requests_mock_module.Mocker() as m:
            m.post(
                f"{CLOUDOS_URL}/api/v1/teams/aws/v2/job-queue?teamId={WORKSPACE_ID}",
                text=CREATE_RESPONSE_JSON_STR,
                status_code=200,
            )
            result = runner.invoke(run_cloudos_cli, self._base_args())
        assert CLOUDOS_URL in result.output
        assert 'job-queues' in result.output

    def test_create_queue_aborted_on_confirmation_decline(self):
        runner = CliRunner()
        # Do NOT pass --yes; answer 'n' to the prompt
        args = [
            'queue', 'create',
            '--apikey', APIKEY,
            '--cloudos-url', CLOUDOS_URL,
            '--workspace-id', WORKSPACE_ID,
            '--label', 'Test Queue',
            '--preset', 'standard-stable',
        ]
        result = runner.invoke(run_cloudos_cli, args, input='n\n')
        assert result.exit_code == 0
        assert 'Aborted' in result.output

    def test_create_queue_proceeds_on_confirmation_accept(self):
        runner = CliRunner()
        args = [
            'queue', 'create',
            '--apikey', APIKEY,
            '--cloudos-url', CLOUDOS_URL,
            '--workspace-id', WORKSPACE_ID,
            '--label', 'Test Queue',
            '--preset', 'standard-stable',
        ]
        with requests_mock_module.Mocker() as m:
            m.post(
                f"{CLOUDOS_URL}/api/v1/teams/aws/v2/job-queue?teamId={WORKSPACE_ID}",
                text=CREATE_RESPONSE_JSON_STR,
                status_code=200,
            )
            result = runner.invoke(run_cloudos_cli, args, input='y\n')
        assert result.exit_code == 0
        assert 'created successfully' in result.output

    def test_create_queue_api_error_exits_nonzero(self):
        runner = CliRunner()
        error_body = json.dumps({'statusCode': 400, 'message': 'Bad Request.'})
        with requests_mock_module.Mocker() as m:
            m.post(
                f"{CLOUDOS_URL}/api/v1/teams/aws/v2/job-queue?teamId={WORKSPACE_ID}",
                text=error_body,
                status_code=400,
            )
            result = runner.invoke(run_cloudos_cli, self._base_args())
        assert result.exit_code == 1
        assert 'Error' in result.output

    def test_create_queue_invalid_preset_rejected(self):
        runner = CliRunner()
        args = [
            'queue', 'create',
            '--apikey', APIKEY,
            '--cloudos-url', CLOUDOS_URL,
            '--workspace-id', WORKSPACE_ID,
            '--label', 'Test Queue',
            '--preset', 'not-a-real-preset',
            '--yes',
        ]
        result = runner.invoke(run_cloudos_cli, args)
        assert result.exit_code != 0

    def test_create_queue_missing_label_fails(self):
        runner = CliRunner()
        args = [
            'queue', 'create',
            '--apikey', APIKEY,
            '--cloudos-url', CLOUDOS_URL,
            '--workspace-id', WORKSPACE_ID,
            '--yes',
        ]
        result = runner.invoke(run_cloudos_cli, args)
        assert result.exit_code != 0

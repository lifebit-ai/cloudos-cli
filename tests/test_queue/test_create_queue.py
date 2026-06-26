"""Tests for the queue create command and Queue.create_job_queue() method."""

import json
import re
import pytest
import responses
import requests_mock as requests_mock_module
from click.testing import CliRunner

from cloudos_cli.queue.queue import Queue, QUEUE_PRESETS
from cloudos_cli.utils.errors import (
    BadRequestException,
)
from cloudos_cli.__main__ import run_cloudos_cli

# rich_click renders usage errors in a styled panel and highlights option
# tokens (e.g. ``--description``) with ANSI escape codes. When colour output is
# enabled (as in CI), those escape codes are inserted between the surrounding
# text and the option token, breaking naive substring assertions. Strip ANSI
# escape sequences before asserting on the human-readable message.
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _plain(text):
    """Return ``text`` with ANSI escape sequences removed."""
    return _ANSI_RE.sub("", text)

# ---------------------------------------------------------------------------
# Constants shared across tests
# ---------------------------------------------------------------------------

APIKEY = 'vnoiweur89u2ongs'
CLOUDOS_URL = 'https://cloudos.lifebit.ai'
WORKSPACE_ID = 'lv89ufc838sdig'
CREATE_RESPONSE_FILE = 'tests/test_data/queue/create_queue_response.json'

with open(CREATE_RESPONSE_FILE) as f:
    CREATE_RESPONSE_JSON_STR = f.read()
    CREATE_RESPONSE_JSON_DICT = json.loads(CREATE_RESPONSE_JSON_STR)


def _mock_get_queues_with_total_ces(m, total_ces, n_queues=1):
    """Mock the GET job-queues endpoints with queues totalling ``total_ces`` CEs.

    The compute environments are spread across ``n_queues`` team queues. The
    system-job-queues endpoint is mocked with an empty list.
    """
    per_queue = []
    remaining = total_ces
    for i in range(n_queues):
        count = remaining if i == n_queues - 1 else remaining // (n_queues - i)
        remaining -= count
        per_queue.append(count)
    queues = [
        {
            'id': f'q{i}',
            'name': f'queue-{i}',
            'label': f'queue-{i}',
            'description': '',
            'isDefault': False,
            'resourceType': '',
            'executor': 'nextflow',
            'computeEnvironments': [
                {'label': f'CE-{i}-{j}', 'environment': {}, 'status': 'Ready'}
                for j in range(count)
            ],
            'status': 'Ready',
        }
        for i, count in enumerate(per_queue)
    ]
    m.get(
        f"{CLOUDOS_URL}/api/v1/teams/aws/v2/job-queues?teamId={WORKSPACE_ID}",
        text=json.dumps(queues),
        status_code=200,
    )
    m.get(
        f"{CLOUDOS_URL}/api/v1/teams/aws/v2/system-job-queues?teamId={WORKSPACE_ID}",
        text='[]',
        status_code=200,
    )


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
            _mock_get_queues_with_total_ces(m, 1)
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
            _mock_get_queues_with_total_ces(m, 1)
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
            '--description', 'A test queue',
            '--preset', 'standard-stable',
        ]
        with requests_mock_module.Mocker() as m:
            _mock_get_queues_with_total_ces(m, 1)
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
            '--description', 'A test queue',
            '--preset', 'standard-stable',
        ]
        with requests_mock_module.Mocker() as m:
            _mock_get_queues_with_total_ces(m, 1)
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
            _mock_get_queues_with_total_ces(m, 1)
            m.post(
                f"{CLOUDOS_URL}/api/v1/teams/aws/v2/job-queue?teamId={WORKSPACE_ID}",
                text=error_body,
                status_code=400,
            )
            result = runner.invoke(run_cloudos_cli, self._base_args())
        assert result.exit_code == 1
        assert 'Error' in result.output

    def test_create_queue_workspace_limit_reached_exits(self):
        runner = CliRunner()
        with requests_mock_module.Mocker() as m:
            _mock_get_queues_with_total_ces(m, 10, n_queues=4)
            result = runner.invoke(run_cloudos_cli, self._base_args())
        assert result.exit_code == 0
        assert 'reached the limit for compute environments in your workspace' \
            in result.output

    def test_create_queue_invalid_preset_rejected(self):
        runner = CliRunner()
        args = [
            'queue', 'create',
            '--apikey', APIKEY,
            '--cloudos-url', CLOUDOS_URL,
            '--workspace-id', WORKSPACE_ID,
            '--label', 'Test Queue',
            '--description', 'A test queue',
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
            '--description', 'A test queue',
            '--yes',
        ]
        result = runner.invoke(run_cloudos_cli, args)
        assert result.exit_code != 0

    def test_create_queue_missing_description_fails(self):
        runner = CliRunner()
        args = [
            'queue', 'create',
            '--apikey', APIKEY,
            '--cloudos-url', CLOUDOS_URL,
            '--workspace-id', WORKSPACE_ID,
            '--label', 'Test Queue',
            '--preset', 'standard-stable',
            '--yes',
        ]
        result = runner.invoke(run_cloudos_cli, args)
        assert result.exit_code != 0
        assert 'Missing option --description' in _plain(result.output)


# ===========================================================================
# Unit tests – Queue.create_job_queue_from_scratch() (API mocked)
# ===========================================================================

class TestCreateJobQueueFromScratch:
    def _make_queue(self):
        return Queue(
            cloudos_url=CLOUDOS_URL,
            apikey=APIKEY,
            cromwell_token=None,
            workspace_id=WORKSPACE_ID,
        )

    def _add_post(self):
        responses.add(
            responses.POST,
            url=f"{CLOUDOS_URL}/api/v1/teams/aws/v2/job-queue?teamId={WORKSPACE_ID}",
            body=CREATE_RESPONSE_JSON_STR,
            status=200,
            content_type='application/json',
        )

    @responses.activate
    def test_on_demand_gp3_payload(self):
        self._add_post()
        q = self._make_queue()
        queue_id = q.create_job_queue_from_scratch(
            label='Custom',
            description='d',
            provisioning_type='on-demand',
            allocation_strategy='BEST_FIT_PROGRESSIVE',
            max_vcpus=512,
            min_vcpus=0,
            instance_types=['optimal'],
            volume_type='gp3',
            size=1000,
            iops=3000,
            throughput=125,
        )
        assert queue_id == CREATE_RESPONSE_JSON_DICT['_id']
        payload = json.loads(responses.calls[0].request.body)
        cr = payload['environment']['computeResources']
        assert payload['environment']['computeEnvironmentName'] == 'Custom'
        assert payload['templateName'] == ''
        assert cr['type'] == 'EC2'
        assert 'bidPercentage' not in cr
        assert cr['allocationStrategy'] == 'BEST_FIT_PROGRESSIVE'
        assert cr['maxvCpus'] == 512
        assert cr['minvCpus'] == 0
        assert cr['instanceTypes'] == ['optimal']
        assert cr['volume']['type'] == 'gp3'
        assert cr['volume']['size'] == {'usageQuantity': 1000, 'usageUnit': 'Gb'}
        assert cr['volume']['iops'] == 3000
        assert cr['volume']['throughput'] == 125

    @responses.activate
    def test_spot_io2_payload_has_bid_and_no_throughput(self):
        self._add_post()
        q = self._make_queue()
        q.create_job_queue_from_scratch(
            label='Custom',
            description='d',
            provisioning_type='spot',
            allocation_strategy='SPOT_CAPACITY_OPTIMIZED',
            max_vcpus=256,
            min_vcpus=0,
            instance_types=['c5.xlarge', 'm5.xlarge'],
            volume_type='io2',
            size=200,
            iops=5000,
            throughput=125,
        )
        payload = json.loads(responses.calls[0].request.body)
        cr = payload['environment']['computeResources']
        assert cr['type'] == 'SPOT'
        assert cr['bidPercentage'] == 100
        assert 'throughput' not in cr['volume']
        assert cr['volume']['type'] == 'io2'

    def test_invalid_provisioning_type_raises(self):
        q = self._make_queue()
        with pytest.raises(ValueError, match='Unknown provisioning type'):
            q.create_job_queue_from_scratch(
                label='C', description='', provisioning_type='nope',
                allocation_strategy='BEST_FIT', max_vcpus=512, min_vcpus=0,
                instance_types=['optimal'], volume_type='gp3', size=1000,
                iops=3000, throughput=125,
            )

    def test_incompatible_allocation_strategy_raises(self):
        q = self._make_queue()
        with pytest.raises(ValueError, match='not valid'):
            q.create_job_queue_from_scratch(
                label='C', description='', provisioning_type='on-demand',
                allocation_strategy='SPOT_CAPACITY_OPTIMIZED', max_vcpus=512,
                min_vcpus=0, instance_types=['optimal'], volume_type='gp3',
                size=1000, iops=3000, throughput=125,
            )

    def test_invalid_volume_type_raises(self):
        q = self._make_queue()
        with pytest.raises(ValueError, match='Unknown volume type'):
            q.create_job_queue_from_scratch(
                label='C', description='', provisioning_type='on-demand',
                allocation_strategy='BEST_FIT', max_vcpus=512, min_vcpus=0,
                instance_types=['optimal'], volume_type='ssd', size=1000,
                iops=3000, throughput=125,
            )


# ===========================================================================
# CLI integration tests – `cloudos queue create --from-scratch`
# ===========================================================================
#
# DISABLED: the --from-scratch CLI flow is hidden until the per-workspace
# instance-types API endpoint is opened (the CLI options were commented out in
# cloudos_cli/queue/cli.py). These integration tests are commented out together
# with that feature and should be restored when it is re-enabled.
#
# class TestCreateQueueFromScratchCLI:
#     def test_from_scratch_options_in_help(self):
#         runner = CliRunner()
#         result = runner.invoke(run_cloudos_cli, ['queue', 'create', '--help'])
#         assert result.exit_code == 0
#         for opt in ['--from-scratch', '--provisioning-type', '--allocation-strategy',
#                     '--max-vcpus', '--min-vcpus', '--instance-types', '--volume-type',
#                     '--size', '--iops', '--throughput']:
#             assert opt in result.output
#
#     def test_from_scratch_yes_success(self):
#         runner = CliRunner()
#         args = [
#             'queue', 'create',
#             '--apikey', APIKEY,
#             '--cloudos-url', CLOUDOS_URL,
#             '--workspace-id', WORKSPACE_ID,
#             '--label', 'Custom Queue',
#             '--description', 'A custom queue',
#             '--from-scratch', '--yes',
#         ]
#         with requests_mock_module.Mocker() as m:
#             _mock_get_queues_with_total_ces(m, 1)
#             m.post(
#                 f"{CLOUDOS_URL}/api/v1/teams/aws/v2/job-queue?teamId={WORKSPACE_ID}",
#                 text=CREATE_RESPONSE_JSON_STR,
#                 status_code=200,
#             )
#             result = runner.invoke(run_cloudos_cli, args)
#         assert result.exit_code == 0
#         assert 'created successfully' in result.output
#
#     def test_from_scratch_workspace_limit_reached_exits(self):
#         runner = CliRunner()
#         args = [
#             'queue', 'create',
#             '--apikey', APIKEY,
#             '--cloudos-url', CLOUDOS_URL,
#             '--workspace-id', WORKSPACE_ID,
#             '--label', 'Custom Queue',
#             '--description', 'A custom queue',
#             '--from-scratch', '--yes',
#         ]
#         with requests_mock_module.Mocker() as m:
#             _mock_get_queues_with_total_ces(m, 10, n_queues=3)
#             result = runner.invoke(run_cloudos_cli, args)
#         assert result.exit_code == 0
#         assert 'reached the limit for compute environments in your workspace' \
#             in result.output
#
#     def test_from_scratch_mutually_exclusive_with_preset(self):
#         runner = CliRunner()
#         args = [
#             'queue', 'create',
#             '--apikey', APIKEY,
#             '--cloudos-url', CLOUDOS_URL,
#             '--workspace-id', WORKSPACE_ID,
#             '--label', 'Custom Queue',
#             '--description', 'A custom queue',
#             '--from-scratch', '--preset', 'standard-gpu', '--yes',
#         ]
#         result = runner.invoke(run_cloudos_cli, args)
#         assert result.exit_code != 0
#         assert 'cannot be combined with --preset' in _plain(result.output)
#
#     def test_from_scratch_incompatible_strategy_rejected(self):
#         runner = CliRunner()
#         args = [
#             'queue', 'create',
#             '--apikey', APIKEY,
#             '--cloudos-url', CLOUDOS_URL,
#             '--workspace-id', WORKSPACE_ID,
#             '--label', 'Custom Queue',
#             '--description', 'A custom queue',
#             '--from-scratch', '--yes',
#             '--provisioning-type', 'on-demand',
#             '--allocation-strategy', 'SPOT_CAPACITY_OPTIMIZED',
#         ]
#         result = runner.invoke(run_cloudos_cli, args)
#         assert result.exit_code != 0
#
#     def test_from_scratch_gp3_iops_out_of_range_rejected(self):
#         runner = CliRunner()
#         args = [
#             'queue', 'create',
#             '--apikey', APIKEY,
#             '--cloudos-url', CLOUDOS_URL,
#             '--workspace-id', WORKSPACE_ID,
#             '--label', 'Custom Queue',
#             '--description', 'A custom queue',
#             '--from-scratch', '--yes',
#             '--volume-type', 'gp3',
#             '--iops', '100',
#         ]
#         result = runner.invoke(run_cloudos_cli, args)
#         assert result.exit_code != 0
#
#     def test_from_scratch_invalid_instance_type_rejected(self):
#         runner = CliRunner()
#         args = [
#             'queue', 'create',
#             '--apikey', APIKEY,
#             '--cloudos-url', CLOUDOS_URL,
#             '--workspace-id', WORKSPACE_ID,
#             '--label', 'Custom Queue',
#             '--description', 'A custom queue',
#             '--from-scratch', '--yes',
#             '--instance-types', 'not-an-instance',
#         ]
#         result = runner.invoke(run_cloudos_cli, args)
#         assert result.exit_code != 0
#
#     def test_from_scratch_interactive_wizard_success(self):
#         runner = CliRunner()
#         args = [
#             'queue', 'create',
#             '--apikey', APIKEY,
#             '--cloudos-url', CLOUDOS_URL,
#             '--workspace-id', WORKSPACE_ID,
#             '--description', 'A wizard queue',
#             '--from-scratch',
#         ]
#         # Wizard answers: name, provisioning, strategy, max, min, instances,
#         # volume type, size, iops, throughput.
#         wizard_input = '\n'.join([
#             'My Wizard Queue',
#             'on-demand',
#             'BEST_FIT_PROGRESSIVE',
#             '512',
#             '0',
#             'optimal',
#             'gp3',
#             '1000',
#             '3000',
#             '125',
#         ]) + '\n'
#         with requests_mock_module.Mocker() as m:
#             _mock_get_queues_with_total_ces(m, 1)
#             m.post(
#                 f"{CLOUDOS_URL}/api/v1/teams/aws/v2/job-queue?teamId={WORKSPACE_ID}",
#                 text=CREATE_RESPONSE_JSON_STR,
#                 status_code=200,
#             )
#             result = runner.invoke(run_cloudos_cli, args, input=wizard_input)
#         assert result.exit_code == 0
#         assert 'created successfully' in result.output


# ===========================================================================
# Unit tests – Queue.count_workspace_compute_environments()
# ===========================================================================

QUEUES_LIST_FILE = 'tests/test_data/queue/queues.json'

with open(QUEUES_LIST_FILE) as f:
    QUEUES_LIST_STR = f.read()


class TestCountWorkspaceComputeEnvironments:
    def _make_queue(self):
        return Queue(
            cloudos_url=CLOUDOS_URL,
            apikey=APIKEY,
            cromwell_token=None,
            workspace_id=WORKSPACE_ID,
        )

    def test_count_workspace_compute_environments_from_list(self):
        q = self._make_queue()
        queues = [
            {'computeEnvironments': [{}, {}]},
            {'computeEnvironments': [{}]},
            {},
        ]
        assert q.count_workspace_compute_environments(queues=queues) == 3

    @responses.activate
    def test_count_workspace_compute_environments_fetches_queues(self):
        # System queues are excluded from the workspace CE count, so only the
        # team job-queues endpoint contributes.
        responses.add(
            responses.GET,
            url=f"{CLOUDOS_URL}/api/v1/teams/aws/v2/job-queues?teamId={WORKSPACE_ID}",
            body=QUEUES_LIST_STR,
            status=200,
            content_type='application/json',
        )
        q = self._make_queue()
        team_queues = json.loads(QUEUES_LIST_STR)
        expected = sum(
            len(x.get('computeEnvironments', [])) for x in team_queues
        )
        assert q.count_workspace_compute_environments() == expected


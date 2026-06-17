"""Test the CLI project members command functionality."""

import json
import os
import tempfile
from click.testing import CliRunner
from cloudos_cli.__main__ import run_cloudos_cli
import requests_mock

APIKEY = 'test_api_key_12345'
CLOUDOS_URL = 'https://cloudos.lifebit.ai'
PROJECT_ID = 'project-123'
PROJECT_MEMBERS = [
    {"id": "member-1", "email": "member1@example.com", "role": "owner"},
    {"id": "member-2", "email": "member2@example.com", "role": "editor"}
]


def test_project_members_command_exists():
    """Test that the project members command exists in the project group."""
    runner = CliRunner()
    result = runner.invoke(run_cloudos_cli, ['project', '--help'])
    assert result.exit_code == 0
    assert 'members' in result.output
    assert 'Collect and display all members from a Lifebit Platform project.' in result.output


def test_project_members_json_output():
    """Test project members with JSON output format."""
    runner = CliRunner()

    with requests_mock.Mocker() as m:
        m.get(
            f"{CLOUDOS_URL}/api/v1/projects/{PROJECT_ID}/members",
            json=PROJECT_MEMBERS,
            status_code=200
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, 'project_members.json')
            result = runner.invoke(run_cloudos_cli, [
                'project', 'members',
                '--apikey', APIKEY,
                '--cloudos-url', CLOUDOS_URL,
                '--project-id', PROJECT_ID,
                '--output-format', 'json',
                '--output-basename', output_file.replace('.json', '')
            ])

            assert result.exit_code == 0
            assert 'Executing members...' in result.output
            assert os.path.exists(output_file)

            with open(output_file, 'r') as f:
                assert json.load(f) == PROJECT_MEMBERS


def test_project_members_stdout_output():
    """Test project members with stdout output format."""
    runner = CliRunner()

    with requests_mock.Mocker() as m:
        m.get(
            f"{CLOUDOS_URL}/api/v1/projects/{PROJECT_ID}/members",
            json=PROJECT_MEMBERS,
            status_code=200
        )

        result = runner.invoke(run_cloudos_cli, [
            'project', 'members',
            '--apikey', APIKEY,
            '--cloudos-url', CLOUDOS_URL,
            '--project-id', PROJECT_ID
        ])

        assert result.exit_code == 0
        assert 'Executing members...' in result.output
        assert 'member1@example.com' in result.output
        assert 'member2@example.com' in result.output

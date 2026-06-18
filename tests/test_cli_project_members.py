import pytest
import json
import responses
from click.testing import CliRunner
from cloudos_cli.__main__ import run_cloudos_cli

APIKEY = 'vnoiweur89u2ongs'
CLOUDOS_URL = 'http://cloudos.lifebit.ai'
PROJECT_ID = '64a7b1c2f8d9e1a2b3c4d5e6'

MEMBERS_RESPONSE = [
    {
        "_id": "60bf3b9b303ee601a69e4856",
        "name": "Test",
        "surname": "User",
        "email": "test.user@lifebit.ai",
        "role": "owner"
    },
    {
        "_id": "71cf4c0c414ff712b7af5967",
        "name": "Jane",
        "surname": "Smith",
        "email": "jane.smith@lifebit.ai",
        "role": "member"
    }
]


def test_project_members_command_exists():
    """Test that the project members command exists in the project group."""
    runner = CliRunner()
    result = runner.invoke(run_cloudos_cli, ['project', '--help'])
    assert result.exit_code == 0
    assert 'members' in result.output


def test_project_members_help():
    """Test that the project members command help works."""
    runner = CliRunner()
    result = runner.invoke(run_cloudos_cli, ['project', 'members', '--help'])
    assert result.exit_code == 0
    assert '--project-id' in result.output
    assert '--apikey' in result.output
    assert '--cloudos-url' in result.output
    assert 'List members of a Lifebit Platform project.' in result.output


@responses.activate
def test_project_members_correct_response():
    """Test that the project members command works with a valid API response."""
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/projects/{PROJECT_ID}/members",
        json=MEMBERS_RESPONSE,
        status=200)

    runner = CliRunner()
    result = runner.invoke(run_cloudos_cli, [
        'project', 'members',
        '--apikey', APIKEY,
        '--cloudos-url', CLOUDOS_URL,
        '--project-id', PROJECT_ID
    ])

    assert result.exit_code == 0
    assert 'test.user@lifebit.ai' in result.output
    assert 'owner' in result.output


@responses.activate
def test_project_members_api_error():
    """Test that the project members command handles API errors gracefully."""
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/projects/{PROJECT_ID}/members",
        json={"statusCode": 400, "message": "Project not found."},
        status=400)

    runner = CliRunner()
    result = runner.invoke(run_cloudos_cli, [
        'project', 'members',
        '--apikey', APIKEY,
        '--cloudos-url', CLOUDOS_URL,
        '--project-id', PROJECT_ID
    ])

    assert result.exit_code != 0
    assert 'Error' in result.output


def test_project_members_missing_project_id():
    """Test that the command fails when --project-id is missing."""
    runner = CliRunner()
    result = runner.invoke(run_cloudos_cli, [
        'project', 'members',
        '--apikey', APIKEY,
        '--cloudos-url', CLOUDOS_URL
    ])
    assert result.exit_code != 0
    assert 'project-id' in result.output or 'Missing' in result.output or 'Error' in result.output

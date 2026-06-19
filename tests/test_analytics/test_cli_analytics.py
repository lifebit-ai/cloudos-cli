"""Test the CLI analytics team-summary command functionality."""

import pytest
import json
import requests_mock
from click.testing import CliRunner
from cloudos_cli.__main__ import run_cloudos_cli

# Test data
APIKEY = 'test_api_key_12345'
CLOUDOS_URL = 'https://cloudos.lifebit.ai'
TEAM_ID = 'test_team_id_123'

# Load test analytics data
with open("tests/test_data/analytics/team_summary.json") as f:
    TEAM_SUMMARY_JSON_STR = f.read()
    TEAM_SUMMARY_JSON_DICT = json.loads(TEAM_SUMMARY_JSON_STR)


def test_analytics_group_exists():
    """Test that the analytics group exists in the CLI."""
    runner = CliRunner()
    result = runner.invoke(run_cloudos_cli, ['analytics', '--help'])
    assert result.exit_code == 0
    assert 'analytics' in result.output.lower() or 'Lifebit Platform' in result.output


def test_analytics_team_summary_help():
    """Test that the analytics team-summary command help works."""
    runner = CliRunner()
    result = runner.invoke(run_cloudos_cli, ['analytics', 'team-summary', '--help'])
    assert result.exit_code == 0
    assert '--team-id' in result.output
    assert '--apikey' in result.output
    assert '--start-date' in result.output
    assert '--end-date' in result.output
    assert '--granularity' in result.output
    assert '--output-format' in result.output


def test_analytics_team_summary_stdout():
    """Test analytics team-summary with stdout output format."""
    runner = CliRunner()

    with requests_mock.Mocker() as m:
        m.get(
            f"{CLOUDOS_URL}/api/v1/analytics/team/summary",
            text=TEAM_SUMMARY_JSON_STR,
            status_code=200
        )
        result = runner.invoke(run_cloudos_cli, [
            'analytics', 'team-summary',
            '--apikey', APIKEY,
            '--cloudos-url', CLOUDOS_URL,
            '--team-id', TEAM_ID,
        ])
    assert result.exit_code == 0
    assert 'computeHours' in result.output or 'jobCount' in result.output or 'spend' in result.output


def test_analytics_team_summary_with_optional_params():
    """Test analytics team-summary with all optional parameters."""
    runner = CliRunner()

    with requests_mock.Mocker() as m:
        m.get(
            f"{CLOUDOS_URL}/api/v1/analytics/team/summary",
            text=TEAM_SUMMARY_JSON_STR,
            status_code=200
        )
        result = runner.invoke(run_cloudos_cli, [
            'analytics', 'team-summary',
            '--apikey', APIKEY,
            '--cloudos-url', CLOUDOS_URL,
            '--team-id', TEAM_ID,
            '--start-date', '2024-01-01',
            '--end-date', '2024-12-31',
            '--granularity', 'monthly',
        ])
    assert result.exit_code == 0
    # Verify optional params were passed in the request
    assert len(m.request_history) == 1
    request_url = m.request_history[0].url
    assert 'startDate=2024-01-01' in request_url
    assert 'endDate=2024-12-31' in request_url
    assert 'granularity=monthly' in request_url


def test_analytics_team_summary_api_error():
    """Test analytics team-summary raises an error on API failure."""
    runner = CliRunner()
    error_body = json.dumps({"statusCode": 401, "message": "Unauthorized"})

    with requests_mock.Mocker() as m:
        m.get(
            f"{CLOUDOS_URL}/api/v1/analytics/team/summary",
            text=error_body,
            status_code=401
        )
        result = runner.invoke(run_cloudos_cli, [
            'analytics', 'team-summary',
            '--apikey', 'bad_key',
            '--cloudos-url', CLOUDOS_URL,
            '--team-id', TEAM_ID,
        ])
    assert result.exit_code != 0

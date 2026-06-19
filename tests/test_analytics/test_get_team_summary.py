"""Tests for Analytics.get_team_summary."""

import json
import pytest
import responses
from cloudos_cli.analytics import Analytics
from cloudos_cli.utils.errors import BadRequestException
from tests.functions_for_pytest import load_json_file

INPUT = "tests/test_data/analytics/team_summary.json"
APIKEY = 'vnoiweur89u2ongs'
CLOUDOS_URL = 'http://cloudos.lifebit.ai'
TEAM_ID = 'lv89ufc838sdig'


@responses.activate
def test_get_team_summary_correct_response():
    """
    Test 'get_team_summary' to work as intended.
    API request is mocked and replicated with a json file.
    """
    body = load_json_file(INPUT)
    header = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json;charset=UTF-8",
        "apikey": APIKEY
    }
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/analytics/team/summary",
        body=body,
        headers=header,
        status=200,
        match_querystring=False
    )
    a = Analytics(cloudos_url=CLOUDOS_URL, apikey=APIKEY, cromwell_token=None)
    result = a.get_team_summary(
        team_id=TEAM_ID,
        start_date='2024-01-01',
        end_date='2024-12-31',
        granularity='monthly'
    )
    assert isinstance(result, dict)
    assert result['teamId'] == TEAM_ID
    assert result['computeHours'] == 1234.56
    assert result['jobCount'] == 42
    assert result['spend'] == 987.65
    # Verify query params were sent
    assert len(responses.calls) == 1
    request_url = responses.calls[0].request.url
    assert 'teamId=' in request_url
    assert 'startDate=' in request_url
    assert 'endDate=' in request_url
    assert 'granularity=' in request_url


@responses.activate
def test_get_team_summary_minimal_params():
    """
    Test 'get_team_summary' with only the required teamId parameter.
    Optional params (startDate, endDate, granularity) should be omitted.
    """
    body = load_json_file(INPUT)
    header = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json;charset=UTF-8",
        "apikey": APIKEY
    }
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/analytics/team/summary",
        body=body,
        headers=header,
        status=200,
        match_querystring=False
    )
    a = Analytics(cloudos_url=CLOUDOS_URL, apikey=APIKEY, cromwell_token=None)
    result = a.get_team_summary(team_id=TEAM_ID)
    assert isinstance(result, dict)
    # Verify only teamId was sent (no optional params)
    request_url = responses.calls[0].request.url
    assert 'teamId=' in request_url
    assert 'startDate=' not in request_url
    assert 'endDate=' not in request_url
    assert 'granularity=' not in request_url


@responses.activate
def test_get_team_summary_bad_request():
    """
    Test 'get_team_summary' raises BadRequestException on a 400 response.
    """
    error_message = {"statusCode": 400, "code": "BadRequest",
                     "message": "Bad Request.", "time": "2024-01-01_00:00:00"}
    error_json = json.dumps(error_message)
    header = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json;charset=UTF-8",
        "apikey": APIKEY
    }
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/analytics/team/summary",
        body=error_json,
        headers=header,
        status=400,
        match_querystring=False
    )
    with pytest.raises(BadRequestException) as error:
        a = Analytics(cloudos_url=CLOUDOS_URL, apikey=APIKEY, cromwell_token=None)
        a.get_team_summary(team_id=TEAM_ID)
    assert "Server returned status 400." in str(error)

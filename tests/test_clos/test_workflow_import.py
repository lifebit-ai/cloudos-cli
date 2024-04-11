import mock
import json
import pytest
import responses
from cloudos.clos import Cloudos
from cloudos.utils.errors import BadRequestException
from tests.functions_for_pytest import load_json_file

OUTPUT = "tests/test_data/workflows/workflow_import.json"
APIKEY = 'vnoiweur89u2ongs'
CLOUDOS_URL = 'http://cloudos.lifebit.ai'
WORKSPACE_ID = 'lv89ufc838sdig'
WORKFLOW_URL = 'https://github.com/lifebit-ai/repo'
WORKFLOW_NAME = 'test-repo'
WORKFLOW_DOCS_LINK = ''
REPOSITORY_PROJECT_ID = 1234
REPOSITORY_ID = 567


@mock.patch('cloudos.clos', mock.MagicMock())
@responses.activate
def test_workflow_import_correct():
    """
    Test 'import_workflows' to work as intended
    API request is mocked and replicated with json files
    """
    create_json = load_json_file(OUTPUT)
    search_str = f"teamId={WORKSPACE_ID}"
    # mock POST method with the .json
    responses.add(
            responses.POST,
            url=f"{CLOUDOS_URL}/api/v1/workflows?{search_str}",
            body=create_json,
            status=200)
    # start cloudOS service
    clos = Cloudos(apikey=APIKEY, cromwell_token=None, cloudos_url=CLOUDOS_URL)
    # get mock response
    workflow_id = clos.workflow_import(WORKSPACE_ID,
                                       WORKFLOW_URL,
                                       WORKFLOW_NAME,
                                       REPOSITORY_PROJECT_ID,
                                       WORKFLOW_DOCS_LINK,
                                       REPOSITORY_ID)
    # check the response
    assert isinstance(workflow_id, str)
    assert workflow_id == '66156ba61d5f06a39b1da573'


@mock.patch('cloudos.clos', mock.MagicMock())
@responses.activate
def test_workflow_import_incorrect():
    """
    Test 'workflow_import' to fail with '400' response
    """
    # prepare error message
    error_message = {"statusCode": 400, "code": "BadRequest",
                     "message": "Bad Request.", "time": "2022-11-23_17:31:07"}
    error_json = json.dumps(error_message)
    search_str = f"teamId={WORKSPACE_ID}"
    # mock POST method with the .json
    responses.add(
            responses.POST,
            url=f"{CLOUDOS_URL}/api/v1/workflows?{search_str}",
            body=error_json,
            status=400)
    # raise 400 error
    with pytest.raises(BadRequestException) as error:
        # check if it failed
        clos = Cloudos(apikey=APIKEY, cromwell_token=None,
                       cloudos_url=CLOUDOS_URL)
        clos.workflow_import(WORKSPACE_ID,
                             WORKFLOW_URL,
                             WORKFLOW_NAME,
                             REPOSITORY_PROJECT_ID,
                             WORKFLOW_DOCS_LINK,
                             REPOSITORY_ID)
    assert "Server returned status 400." in (str(error))

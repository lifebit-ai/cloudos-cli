import mock
import json
import pytest
import requests
import responses
import requests_mock
from responses import matchers
from cloudos.clos import Cloudos
from cloudos.utils.errors import BadRequestException
from tests.functions_for_pytest import load_json_file
from cloudos.jobs.job import Job

INPUT = "tests/test_data/jobs/fetch_cloudos_id.json"
APIKEY = 'vnoiweur89u2ongs'
CLOUDOS_URL = 'http://cloudos.test.ai'
WORKSPACE_ID = 'lv89ufc838sdig'


@mock.patch('cloudos.jobs', mock.MagicMock())
@responses.activate
def test_fetch_cloudos_id_incorrect_response():
    """
    Test 'get_workflow_list' to fail with '400' response
    """
    # prepare error message
    error_message = {"statusCode": 400, "code": "BadRequest",
                     "message": "Bad Request.", "time": "2022-11-23_17:31:07"}
    error_json = json.dumps(error_message)
    params = {"teamId": WORKSPACE_ID, "apikey": APIKEY}
    header = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json;charset=UTF-8"
    }
    search_str = f"teamId={WORKSPACE_ID}&apikey={APIKEY}"
    # mock GET method with the .json
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/workflows?{search_str}",
        body=error_json,
        headers=header,
        match=[matchers.query_param_matcher(params)],
        status=400)
    # raise 400 error
    with pytest.raises(BadRequestException) as error:
        # check if it failed
        clos = Cloudos(apikey=APIKEY, cromwell_token=None, cloudos_url=CLOUDOS_URL)
        clos.get_workflow_list(WORKSPACE_ID)
    assert "Bad Request." in (str(error))


def test_fetch_cloudos_id_incorrect_resource():
    """
    Test 'fetch_cloudos_id' to fail with incorrect resource
    API request is mocked and replicated with json files
    """
    allowed_resources = ['projects', 'workflows']
    with pytest.raises(ValueError) as excinfo:
        Job.fetch_cloudos_id(
            1, # self
            apikey=APIKEY,
            cloudos_url=CLOUDOS_URL,
            resource='mock_resource',
            workspace_id=WORKSPACE_ID,
            name='rnatoy',
            mainfile=None,
            importsfile=None,
            repository_platform='github',
            verify=True
        )
    assert f'Your specified resource is not supported. ' + \
           f'Use one of the following: {allowed_resources}' in str(excinfo.value)


def create_response(resource):
    """
    Creates the response to be retrieved in the call
    """
    create_json = load_json_file(INPUT)
    params = {"teamId": WORKSPACE_ID, "apikey": APIKEY}
    header = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json;charset=UTF-8"
    }
    search_str = f"teamId={WORKSPACE_ID}&apikey={APIKEY}"
    # mock GET method with the .json
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/{resource}?{search_str}",
        body=create_json,
        headers=header,
        match=[matchers.query_param_matcher(params)],
        status=200
    )


@responses.activate
def test_fetch_cloudos_id_workflows_resource_no_mainfile():
    """
    Use:
    
    resource='workflows'
    name='pipeline1'
    repository_platform='github'
    mainfile=None
    importsfile=None

    The result should be '1234'
    """
    create_response('workflows')
    # call the function
    element_id = Job.fetch_cloudos_id(
        1, # self
        apikey=APIKEY,
        cloudos_url=CLOUDOS_URL,
        resource='workflows',
        workspace_id=WORKSPACE_ID,
        name='pipeline1',
        mainfile=None,
        importsfile=None,
        repository_platform='github',
        verify=True
    )
    assert element_id == '1234'


@responses.activate
def test_fetch_cloudos_id_workflows_with_mainfile_no_importsfile():
    """
    Use:
    
    resource='workflows'
    name='pipeline2'
    repository_platform='github'
    mainfile="main.nf"
    importsfile=None

    The result should be '5678'
    """
    create_response('workflows')
    # call the function
    element_id = Job.fetch_cloudos_id(
        1, # self
        apikey=APIKEY,
        cloudos_url=CLOUDOS_URL,
        resource='workflows',
        workspace_id=WORKSPACE_ID,
        name='pipeline2',
        mainfile="main.nf",
        importsfile=None,
        repository_platform='github',
        verify=True
    )
    assert element_id == '5678'


@responses.activate
def test_fetch_cloudos_id_workflows_with_mainfile_and_importsfile():
    """
    Use:
    
    resource='workflows'
    name='pipeline3'
    repository_platform='github'
    mainfile="main.nf"
    importsfile="importsfile.txt"

    The result should be '8910'
    """
    create_response('workflows')
    # call the function
    element_id = Job.fetch_cloudos_id(
        1, # self
        apikey=APIKEY,
        cloudos_url=CLOUDOS_URL,
        resource='workflows',
        workspace_id=WORKSPACE_ID,
        name='pipeline3',
        mainfile='main.nf',
        importsfile='importsfile.txt',
        repository_platform='github',
        verify=True
    )
    assert element_id == '8910'


@responses.activate
def test_fetch_cloudos_id_projects_with_name():
    """
    Use:
    
    resource='projects'
    name='pipeline4'
    repository_platform='github'
    mainfile="main.nf"
    importsfile="importsfile.txt"

    The result should be '8911'
    """
    create_response('projects')
    # call the function
    element_id = Job.fetch_cloudos_id(
        1, # self
        apikey=APIKEY,
        cloudos_url=CLOUDOS_URL,
        resource='projects',
        workspace_id=WORKSPACE_ID,
        name='pipeline4',
        mainfile='main.nf',
        importsfile='importsfile.txt',
        repository_platform='github',
        verify=True
    )
    assert element_id == '8911'


@responses.activate
def test_fetch_cloudos_id_with_mainfile_value_error():
    """
    Use:
    
    resource='projects'
    name='pipeline7'
    repository_platform='github'
    mainfile="main.nf"
    importsfile="importsfile.txt"

    The result should be an error message
    """
    create_response('projects')
    # call the function
    with pytest.raises(ValueError) as excinfo:
        message = Job.fetch_cloudos_id(
            1, # self
            apikey=APIKEY,
            cloudos_url=CLOUDOS_URL,
            resource='projects',
            workspace_id=WORKSPACE_ID,
            name='pipeline7',
            mainfile='main.nf',
            importsfile='importsfile.txt',
            repository_platform='github',
            verify=True
        )
    assert "[ERROR] A workflow named 'pipeline7' with a mainFile 'main.nf'" + \
            " and an importsFile 'importsfile.txt' was not found" in str(excinfo.value)


@responses.activate
def test_fetch_cloudos_id_without_mainfile_value_error():
    """
    Use:
    
    resource='projects'
    name='pipeline7'
    repository_platform='github'
    mainfile=Nonew
    importsfile=None

    The result should be an error message
    """
    create_response('projects')
    # call the function
    with pytest.raises(ValueError) as excinfo:
        message = Job.fetch_cloudos_id(
            1, # self
            apikey=APIKEY,
            cloudos_url=CLOUDOS_URL,
            resource='projects',
            workspace_id=WORKSPACE_ID,
            name='pipeline7',
            mainfile=None,
            importsfile=None,
            repository_platform=None,
            verify=True
        )
    assert "[ERROR] No pipeline7 element in projects was found" in str(excinfo.value)

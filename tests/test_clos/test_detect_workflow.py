import mock
import json
import responses
from responses import matchers
from cloudos.clos import Cloudos

INPUT = "tests/test_data/process_workflow_list_initial_request.json"
APIKEY = 'vnoiweur89u2ongs'
CLOUDOS_URL = 'http://cloudos.lifebit.ai'
WORKSPACE_ID = 'lv89ufc838sdig'

@mock.patch('cloudos.clos', mock.MagicMock())
@responses.activate
def test_detect_workflow():
    """
    Test 'get_workflow_list' to work as intended
    API request is mocked and replicated with json files
    """
    with open(INPUT) as json_data:
        data = json.load(json_data)
        json_data = json.dumps(data)


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
            body=json_data,
            headers=header,
            match=[matchers.query_param_matcher(params)],
            status=200)
    # start cloudOS service 
    clos = Cloudos(apikey=APIKEY, cromwell_token=None, cloudos_url=CLOUDOS_URL)
    # get mock response
    response_2 = clos.detect_workflow(workspace_id=WORKSPACE_ID, workflow_name="nf-core-deepvariant")
    print("------")

    print(response_2)

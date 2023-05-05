"""pytest added for function TimeOutException"""
import mock
import responses
from cloudos.clos import Cloudos
from cloudos.utils.errors import TimeOutException

APIKEY = 'vnoiweur89u2ongs'
CLOUDOS_URL = 'http://cloudos.lifebit.ai'
WORKSPACE_ID = 'lv89ufc838sdig'
STATUS_CODE = 200
REASON = "OK"
JOB_ID = "fgsdgsdahashgy325cc"


@mock.patch('cloudos.clos', mock.MagicMock())
@responses.activate
def test_time_out_exception():
    """
    Test 'TimeOutException' to work as intended
    API request is mocked and replicated with json files
    """
    header = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json;charset=UTF-8",
        "apikey": APIKEY
    }
    # mock GET method with the .json
    responses.add(
            responses.GET,
            url=f"{CLOUDOS_URL}/api/v1/jobs/{JOB_ID}",
            headers=header,
            status=STATUS_CODE)
    # start cloudOS service
    clos = Cloudos(apikey=APIKEY, cromwell_token=None, cloudos_url=CLOUDOS_URL)
    response = clos.get_job_status(j_id=JOB_ID)
    timeout_ex = TimeOutException(response)

    assert timeout_ex.rv.status_code == STATUS_CODE
    assert timeout_ex.rv.reason == REASON

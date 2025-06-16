from urllib.parse import urlsplit
from cloudos_cli.import_wf.import_wf import ImportWorflow
import pytest
import responses
from responses import matchers

CLOUDOS_URL = "https://cloudos.lifebit.ai"
CLOUDOS_TOKEN = "cloudos_token"
WORKSPACE_ID = "some_ws_id"
WF_URL_BASEGROUP = "https://gitlab.com/lb-ortiz/spammer-nf"
WF_URL_SUBGROUP = "https://gitlab.com/lb-ortiz/sample_subgroup/spammer-nf"
WF_URL_NESTEDGROUP = "https://gitlab.com/lb-ortiz/sample_subgroup/nested-subgroup/spammer-nf"
REPO_NAME = "from-gitlab-spammer-nf"
WF_NAME = "spammer-nf"
repo_expected_data = [
        [WF_URL_BASEGROUP, None, (1, REPO_NAME, 100, "lb-ortiz")],
        [WF_URL_SUBGROUP,  None, (2, REPO_NAME, 100, "lb-ortiz/sample_subgroup")],
        [WF_URL_NESTEDGROUP, "custom.nf", (3, REPO_NAME, 100, "lb-ortiz/sample_subgroup/nested-subgroup")]
]


@pytest.mark.parametrize("repo_url,main_file,expected", repo_expected_data)
@responses.activate
def test_fetch_correct_repo_data(repo_url, main_file, expected):
    ex_repo_id, ex_repo_name, ex_group_id, ex_group_name = expected
    parsed_url = urlsplit(repo_url)
    repo_name = parsed_url.path.split("/")[-1]
    repo_owner = "/".join(parsed_url.path.split("/")[1:-1])
    repo_host = f"{parsed_url.scheme}://{parsed_url.netloc}"
    get_repo_params = dict(repoName=repo_name, repoOwner=repo_owner, host=repo_host, teamId=WORKSPACE_ID)
    repo_owner_urlencode = repo_owner.replace("/", "%2F")
    get_repo_main_file_url = f"{CLOUDOS_URL}/api/v1/git/gitlab/getWorkflowConfig/{repo_name}/{repo_owner_urlencode}"
    get_repo_main_file_params = dict(host=repo_host, teamId=WORKSPACE_ID)
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/git/gitlab/getPublicRepo",
        match=[matchers.query_param_matcher(get_repo_params)],
        json={
            "id": ex_repo_id,
            "name": WF_NAME,
            "namespace": {
                "id": ex_group_id,
                "full_path": ex_group_name
            }
        }
    )
    responses.add(
        responses.GET,
        url=get_repo_main_file_url,
        match=[matchers.query_param_matcher(get_repo_main_file_params)],
        json={"mainFile": main_file}

    )

    GitlabImport = ImportWorflow(cloudos_url=CLOUDOS_URL, cloudos_apikey=CLOUDOS_TOKEN, workspace_id=WORKSPACE_ID,
                                platform="gitlab", workflow_url=repo_url, workflow_name=REPO_NAME, main_file=main_file,
                                workflow_docs_link="", verify=True)
    GitlabImport.get_repo()
    assert GitlabImport.payload["repository"]["repositoryId"] == ex_repo_id
    assert GitlabImport.payload["repository"]["name"] == WF_NAME
    assert GitlabImport.payload["repository"]["owner"]["id"] == ex_group_id
    assert GitlabImport.payload["repository"]["owner"]["login"] == ex_group_name
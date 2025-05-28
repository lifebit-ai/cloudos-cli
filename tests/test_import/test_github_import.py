from urllib.parse import urlsplit
import responses
from cloudos_cli.clos import ImportGithub
from responses import matchers

CLOUDOS_URL = "https://cloudos.lifebit.ai"
CLOUDOS_TOKEN = "some_token"
WORKSPACE_ID = "5c6d3e9bd954e800b23f8c62"
WF_MAIN_URL = "https://github.com/lifebit-ai/post-gwas-target-identification"
REPO_NAME = "post-gwas-target-identification"

EXPECTED = (930401807, REPO_NAME, 30871219, 'lifebit-ai', None)

@responses.activate
def test_fetch_correct_repo_data():
    ex_repo_id, ex_repo_name, ex_group_id, ex_group_name, main_file = EXPECTED
    parsed_url = urlsplit(WF_MAIN_URL)
    repo_name = parsed_url.path.split("/")[-1]
    repo_owner = "/".join(parsed_url.path.split("/")[1:-1])
    repo_host = f"{parsed_url.scheme}://{parsed_url.netloc}"
    get_repo_params = dict(repoName=repo_name, repoOwner=repo_owner, host=repo_host, teamId=WORKSPACE_ID)
    repo_owner_urlencode = repo_owner.replace("/", "%2F")
    get_repo_main_file_url = f"{CLOUDOS_URL}/api/v1/git/github/getWorkflowConfig/{repo_name}/{repo_owner_urlencode}"
    get_repo_main_file_params = dict(host=repo_host, teamId=WORKSPACE_ID)
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/git/github/getPublicRepo",
        match=[matchers.query_param_matcher(get_repo_params)],
        json={
            "id": ex_repo_id,
            "name": REPO_NAME,
            "owner": {
                "id": ex_group_id,
                "login": ex_group_name

        }}
    )
    responses.add(
        responses.GET,
        url=get_repo_main_file_url,
        match=[matchers.query_param_matcher(get_repo_main_file_params)],
        json={"mainFile": main_file}

    )
    gh = ImportGithub(cloudos_url="https://cloudos.lifebit.ai", cloudos_apikey=CLOUDOS_TOKEN, workspace_id=WORKSPACE_ID, platform="github", workflow_name=REPO_NAME, workflow_url=WF_MAIN_URL)
    gh.get_repo()
    assert gh.payload["repository"]["repositoryId"] == ex_repo_id
    assert gh.payload["repository"]["name"] == REPO_NAME
    assert gh.payload["repository"]["owner"]["id"] == ex_group_id
    assert gh.payload["repository"]["owner"]["login"] == ex_group_name
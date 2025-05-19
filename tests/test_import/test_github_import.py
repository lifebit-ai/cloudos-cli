from urllib.parse import urlsplit
import responses
from cloudos_cli.clos import ImportGithub

CLOUDOS_URL = "https://cloudos.lifebit.ai"
CLOUDOS_TOKEN = "some_token"
WORKSPACE_ID = "5c6d3e9bd954e800b23f8c62"
GITHUB_TOKEN = "another_token"
GITHUB_BAD_TOKEN = "bad_token"
WF_MAIN_URL = "https://github.com/lifebit-ai/post-gwas-target-identification"
WF_BAD_URL = "https://github.com/something-that-should-not-work/repo"
REPO_NAME = "post-gwas-target-identification"
WF_NAME = "pgta-from-github"

EXPECTED = (930401807, REPO_NAME, 30871219, 'lifebit-ai')

@responses.activate
def test_fetch_correct_repo_data():
    ex_repo_id, ex_repo_name, ex_group_id, ex_group_name = EXPECTED
    parsed_url = urlsplit(WF_MAIN_URL)
    github_base_url = f"{parsed_url.scheme}://api.{parsed_url.netloc}"
    url_endpoint = f"{github_base_url}/repos{parsed_url.path}"
    responses.add(
        responses.GET,
        url=url_endpoint,
        json={
            "id": ex_repo_id,
            "name": REPO_NAME,
            "owner": {
                "login": ex_group_name,
                "id": ex_group_id
            }
        }
    )
    gh = ImportGithub(cloudos_url="https://cloudos.lifebit.ai", cloudos_apikey=CLOUDOS_TOKEN, workspace_id=WORKSPACE_ID, platform="github", workflow_name=REPO_NAME, workflow_url=WF_MAIN_URL)
    gh.fill_payload(github_apikey=GITHUB_TOKEN)
    assert gh.payload["repository"]["repositoryId"] == ex_repo_id
    assert gh.payload["repository"]["name"] == REPO_NAME
    assert gh.payload["repository"]["owner"]["id"] == ex_group_id
    assert gh.payload["repository"]["owner"]["login"] == ex_group_name
from cloudos_cli.clos import ImportGithub
from os import environ

CLOUDOS_URL = "https://cloudos.lifebit.ai"
CLOUDOS_TOKEN = environ["CLOUDOS_TOKEN"]
WORKSPACE_ID = "5c6d3e9bd954e800b23f8c62"
GITHUB_TOKEN = environ["GITHUB_TOKEN"]
GITHUB_BAD_TOKEN = "bad_token"
WF_MAIN_URL = "https://github.com/lifebit-ai/post-gwas-target-identification"
WF_NAME = "post-gwas-target-identification"

EXPECTED = (930401807, WF_NAME, 30871219, 'lifebit-ai')
def test_fetch_correct_repo_data():
    ex_repo_id, ex_repo_name, ex_group_id, ex_group_name = EXPECTED
    gh = ImportGithub(cloudos_url="https://cloudos.lifebit.ai", cloudos_apikey=CLOUDOS_TOKEN, workspace_id=WORKSPACE_ID,platform="github", workflow_name=WF_NAME, workflow_url=WF_MAIN_URL)
    gh.fill_payload(github_apikey=GITHUB_TOKEN)
    assert gh.payload["repository"]["repositoryId"] == ex_repo_id
    assert gh.payload["repository"]["name"] == WF_NAME
    assert gh.payload["repository"]["owner"]["id"] == ex_group_id
    assert gh.payload["repository"]["owner"]["login"] == ex_group_name

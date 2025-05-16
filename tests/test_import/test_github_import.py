import pytest

from cloudos_cli.clos import ImportGithub
from os import environ
from cloudos_cli.utils.errors import GithubRepositoryError

CLOUDOS_URL = "https://cloudos.lifebit.ai"
CLOUDOS_TOKEN = environ["CLOUDOS_TOKEN"]
WORKSPACE_ID = "5c6d3e9bd954e800b23f8c62"
GITHUB_TOKEN = environ["GITHUB_TOKEN"]
GITHUB_BAD_TOKEN = "bad_token"
WF_MAIN_URL = "https://github.com/lifebit-ai/post-gwas-target-identification"
WF_BAD_URL = "https://github.com/something-that-should-not-work/repo"
REPO_NAME = "post-gwas-target-identification"
WF_NAME = "pgta-from-github"

EXPECTED = (930401807, REPO_NAME, 30871219, 'lifebit-ai')
def test_fetch_correct_repo_data():
    ex_repo_id, ex_repo_name, ex_group_id, ex_group_name = EXPECTED
    gh = ImportGithub(cloudos_url="https://cloudos.lifebit.ai", cloudos_apikey=CLOUDOS_TOKEN, workspace_id=WORKSPACE_ID, platform="github", workflow_name=REPO_NAME, workflow_url=WF_MAIN_URL)
    gh.fill_payload(github_apikey=GITHUB_TOKEN)
    assert gh.payload["repository"]["repositoryId"] == ex_repo_id
    assert gh.payload["repository"]["name"] == REPO_NAME
    assert gh.payload["repository"]["owner"]["id"] == ex_group_id
    assert gh.payload["repository"]["owner"]["login"] == ex_group_name

def test_unauthorised_user():
    with pytest.raises(GithubRepositoryError) as excinfo:
        gh = ImportGithub(cloudos_url="https://cloudos.lifebit.ai", cloudos_apikey=CLOUDOS_TOKEN, workspace_id=WORKSPACE_ID,
                          platform="github", workflow_name=WF_NAME, workflow_url=WF_MAIN_URL)
        gh.fill_payload(github_apikey=GITHUB_BAD_TOKEN)
    assert "The user is not authorized to access this resource or resource not found (Error code: 401)." in str(excinfo.value)

def test_repo_not_found():
    with pytest.raises(GithubRepositoryError) as excinfo:
        gh = ImportGithub(cloudos_url="https://cloudos.lifebit.ai", cloudos_apikey=CLOUDOS_TOKEN, workspace_id=WORKSPACE_ID,
                          platform="github", workflow_name=WF_NAME, workflow_url=WF_BAD_URL)
        gh.fill_payload(github_apikey=GITHUB_TOKEN)
    assert "The requested resource does not exist (Error code: 404)" in str(excinfo.value)

def test_full_github_import():
    gh = ImportGithub(cloudos_url="https://cloudos.lifebit.ai", cloudos_apikey=CLOUDOS_TOKEN, workspace_id=WORKSPACE_ID,
                      platform="github", workflow_name=WF_NAME, workflow_url=WF_MAIN_URL)
    gh.fill_payload(github_apikey=GITHUB_TOKEN)
    wf_id = gh.import_workflow()
    print(f"Pipeline {WF_NAME} was imported with id {wf_id}")
import pytest
from gitlab import GitlabAuthenticationError
from os import environ
from cloudos_cli.clos import ImportGitlab
import pytest


CLOUDOS_URL = environ["CLOUDOS_URL"]
CLOUDOS_TOKEN = environ["CLOUDOS_TOKEN"]
WORKSPACE_ID = environ["WORKSPACE_ID"]
GITLAB_TOKEN = environ["GITLAB_TOKEN"]
GITLAB_BAD_TOKEN = environ["GITLAB_BAD_TOKEN"]
WF_URL_BASEGROUP = environ["WF_URL_BASEGROUP"]
WF_URL_SUBGROUP = environ["WF_URL_SUBGROUP"]
WF_URL_NESTEDGROUP = environ["WF_URL_NESTEDGROUP"]
REPO_NAME = "from-gitlab-spammer-nf"
repo_expected_data = [
        [WF_URL_BASEGROUP, (69676121, REPO_NAME, 89592167, "lb-ortiz")],
        [WF_URL_SUBGROUP, (69676104, REPO_NAME, 107145926, "lb-ortiz/sample_subgroup")],
        [WF_URL_NESTEDGROUP, (69676266, REPO_NAME, 107146238, "lb-ortiz/sample_subgroup/nested-subgroup")]
]


@pytest.mark.parametrize("repo_url,expected", repo_expected_data)
def test_fetch_correct_repo_data(repo_url, expected):
    ex_repo_id, ex_repo_name, ex_group_id, ex_group_name = expected
    GitlabImport = ImportGitlab(cloudos_url=CLOUDOS_URL, cloudos_apikey=CLOUDOS_TOKEN, workspace_id=WORKSPACE_ID, platform="gitlab", workflow_url=repo_url, workflow_name=REPO_NAME)
    GitlabImport.fill_payload(gitlab_apikey=GITLAB_TOKEN)
    assert GitlabImport.payload["repository"]["repositoryId"] == ex_repo_id
    assert GitlabImport.payload["repository"]["name"] == REPO_NAME
    assert GitlabImport.payload["repository"]["owner"]["id"] == ex_group_id
    assert GitlabImport.payload["repository"]["owner"]["login"] == ex_group_name

def test_failed_login(repo_url=repo_expected_data[0][0], args=repo_expected_data[0][1]):
    ex_repo_id, ex_repo_name, ex_group_id, ex_group_name = args
    with pytest.raises(GitlabAuthenticationError) as excinfo:
        GitlabImport = ImportGitlab(cloudos_url=CLOUDOS_URL, cloudos_apikey=CLOUDOS_TOKEN, workspace_id=WORKSPACE_ID, platform="gitlab", workflow_url=repo_url, workflow_name=REPO_NAME)
        GitlabImport.fill_payload(gitlab_apikey=GITLAB_BAD_TOKEN)
        assert GitlabImport.payload["repository"]["repositoryId"] == ex_repo_id
        assert GitlabImport.payload["repository"]["name"] == REPO_NAME
        assert GitlabImport.payload["repository"]["owner"]["id"] == ex_group_id
        assert GitlabImport.payload["repository"]["owner"]["login"] == ex_group_name
    assert "Could not login to Gitlab. Check Gitlab URL and Gitlab API key" in str(excinfo.value)

def test_full_import():
    GitlabImport = ImportGitlab(cloudos_url=CLOUDOS_URL, cloudos_apikey=CLOUDOS_TOKEN, workspace_id=WORKSPACE_ID,
                                platform="gitlab", workflow_url=WF_URL_BASEGROUP, workflow_name=REPO_NAME)
    GitlabImport.fill_payload(gitlab_apikey=GITLAB_TOKEN)
    wf_id = GitlabImport.import_workflow()
    print(f"Pipeline {REPO_NAME} was imported with id {wf_id}")
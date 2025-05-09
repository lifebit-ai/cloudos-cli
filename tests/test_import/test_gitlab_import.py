import pytest
from gitlab import GitlabAuthenticationError

from cloudos_cli.clos import ImportGitlab
from cloudos_cli.clos import ImportGitlab

CLOUDOS_URL = "http://cloudos.lifebit.ai"
WF_URL_BASEGROUP = "https://gitlab.com/lb-ortiz/spammer-nf"
WF_URL_SUBGROUP = "https://gitlab.com/lb-ortiz/sample_subgroup/spammer-nf"
WF_URL_NESTEDGROUP = (
    "https://gitlab.com/lb-ortiz/sample_subgroup/nested-subgroup/spammer-nf"
)
repo_name = "spammer-nf"
repo_expected_data = [
    [WF_URL_BASEGROUP, (69676121, repo_name, 89592167, "lb-ortiz")],
    [WF_URL_SUBGROUP, (69676104, repo_name, 107145926, "lb-ortiz/sample_subgroup")],
    [
        WF_URL_NESTEDGROUP,
        (69676266, repo_name, 107146238, "lb-ortiz/sample_subgroup/nested-subgroup"),
    ],
]


@pytest.mark.parametrize("repo_url,expected", repo_expected_data)
def test_fetch_correct_repo_data(repo_url, expected):
    ex_repo_id, ex_repo_name, ex_group_id, ex_group_name = expected
    GitlabImport = ImportGitlab(
        cloudos_url=CLOUDOS_URL,
        cloudos_apikey="CLOUDOS_TOKEN",
        workspace_id="WORKSPACE_ID",
        platform="gitlab",
        workflow_url=repo_url,
        workflow_name=repo_name,
    )
    GitlabImport.fill_payload(gitlab_apikey="GITLAB_TOKEN")
    assert GitlabImport.payload["repository"]["repositoryId"] == ex_repo_id
    assert GitlabImport.payload["repository"]["name"] == repo_name
    assert GitlabImport.payload["repository"]["owner"]["id"] == ex_group_id
    assert GitlabImport.payload["repository"]["owner"]["login"] == ex_group_name

def test_failed_login(repo_url=repo_expected_data[0][0], args=repo_expected_data[0][1]):
    ex_repo_id, ex_repo_name, ex_group_id, ex_group_name = args
    with pytest.raises(GitlabAuthenticationError) as excinfo:
        GitlabImport = ImportGitlab(cloudos_url=CLOUDOS_URL, cloudos_apikey="CLOUDOS_TOKEN", workspace_id="WORKSPACE_ID", platform="gitlab", workflow_url=repo_url, workflow_name=repo_name)
        GitlabImport.fill_payload(gitlab_apikey="GITLAB_BAD_TOKEN")
        assert GitlabImport.payload["repository"]["repositoryId"] == ex_repo_id
        assert GitlabImport.payload["repository"]["name"] == repo_name
        assert GitlabImport.payload["repository"]["owner"]["id"] == ex_group_id
        assert GitlabImport.payload["repository"]["owner"]["login"] == ex_group_name
    assert "Could not login to Gitlab. Check Gitlab URL and Gitlab API key" in str(excinfo.value)
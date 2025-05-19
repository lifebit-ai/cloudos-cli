import json
from urllib.parse import urlsplit
from cloudos_cli.clos import ImportGitlab
import pytest
import responses

CLOUDOS_URL = "https://cloudos.lifebit.ai"
CLOUDOS_TOKEN = "cloudos_token"
WORKSPACE_ID = "some_ws_id"
GITLAB_TOKEN = "gitlab_token"
WF_URL_BASEGROUP = "https://gitlab.com/lb-ortiz/spammer-nf"
WF_URL_SUBGROUP = "https://gitlab.com/lb-ortiz/sample_subgroup/spammer-nf"
WF_URL_NESTEDGROUP = "https://gitlab.com/lb-ortiz/sample_subgroup/nested-subgroup/spammer-nf"
REPO_NAME = "from-gitlab-spammer-nf"
WF_NAME = "spammer-nf"
repo_expected_data = [
        [WF_URL_BASEGROUP, "tests/test_import/data/lb-ortiz_spammer-nf.json", (69676121, REPO_NAME, 21882195, "lb-ortiz")],
        [WF_URL_SUBGROUP, "tests/test_import/data/lb-ortiz_subgroup_spammer-nf.json", (69676104, REPO_NAME, 21882195, "lb-ortiz/sample_subgroup")],
        [WF_URL_NESTEDGROUP, "tests/test_import/data/lb-ortiz_subgroup_nested-subgroup_spammer-nf.json", (69676266, REPO_NAME, 21882195, "lb-ortiz/sample_subgroup/nested-subgroup")]
]


@pytest.mark.parametrize("repo_url,fixture_path,expected", repo_expected_data)
@responses.activate
def test_fetch_correct_repo_data(repo_url, fixture_path, expected):
    ex_repo_id, ex_repo_name, ex_group_id, ex_group_name = expected
    parsed_url = urlsplit(repo_url)
    project_with_namespace = parsed_url.path[1:].replace("/", "%2F")
    fixture = json.load(open(fixture_path))
    user = json.load(open("data/user.json"))

    responses.add(
        responses.GET,
        url=f"https://gitlab.com/api/v4/projects/{project_with_namespace}",
        json=fixture
    )
    responses.add(
        responses.GET,
        url="https://gitlab.com/api/v4/user",
        json=user
    )
    GitlabImport = ImportGitlab(cloudos_url=CLOUDOS_URL, cloudos_apikey=CLOUDOS_TOKEN, workspace_id=WORKSPACE_ID, platform="gitlab", workflow_url=repo_url, workflow_name=REPO_NAME)
    GitlabImport.fill_payload(gitlab_apikey=GITLAB_TOKEN)
    assert GitlabImport.payload["repository"]["repositoryId"] == ex_repo_id
    assert GitlabImport.payload["repository"]["name"] == WF_NAME
    assert GitlabImport.payload["repository"]["owner"]["id"] == ex_group_id
    assert GitlabImport.payload["repository"]["owner"]["login"] == ex_group_name
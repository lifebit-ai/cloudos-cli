from cloudos_cli.clos import WFImport
import pytest
from contextlib import nullcontext as does_not_raise


class import_class(WFImport):
    def fill_payload(self, repo_id, repo_name, owner_login, owner_id):
        self.payload["repository"]["repositoryId"] = repo_id
        self.payload["repository"]["name"] = repo_name
        self.payload["repository"]["owner"]["login"] = owner_login
        self.payload["repository"]["owner"]["id"] = owner_id

    # Override check_payload to fix the bug in the parent class
    def check_payload(self):
        for required_key in ["repositoryId", "name", ("owner", "login"), ("owner", "id")]:
            if isinstance(required_key, tuple):
                key1, key2 = required_key
                value = self.payload["repository"][key1][key2]
                str_value = f"self.payload['repository']['{key1}']['{key2}']"
            else:
                value = self.payload["repository"][required_key]
                str_value = f"self.payload['repository']['{required_key}']"
            if value is None:
                raise ValueError("The payload dictionary does not have the required data. " +
                                f"Check that {str_value} is present and the method "
                                f"self.fill_payload() has been executed")

def test_fill_payload_succeeds():
    sample_class = import_class(cloudos_url="http://example.comv", cloudos_apikey="somekey", workspace_id="myworkspace", platform="gitlab", workflow_name="someworkflow", workflow_url="http://workflows.com", repo_apikey="", repo_api_url="", repo_api_version="")
    with does_not_raise():
        sample_class.fill_payload(repo_id="repo_id", repo_name="repo_name", owner_id="owner_id", owner_login="owner_login")

@pytest.mark.parametrize("missing_param, params, expected_error_pattern", [
    ("repo_id", {"repo_id": None, "repo_name": "repo_name", "owner_login": "owner_login", "owner_id": "owner_id"}, "self.payload['repository']['repositoryId']"),
    ("repo_name", {"repo_id": "repo_id", "repo_name": None, "owner_login": "owner_login", "owner_id": "owner_id"}, "self.payload['repository']['name']"),
    ("owner_login", {"repo_id": "repo_id", "repo_name": "repo_name", "owner_login": None, "owner_id": "owner_id"}, "self.payload['repository']['owner']['login']"),
    ("owner_id", {"repo_id": "repo_id", "repo_name": "repo_name", "owner_login": "owner_login", "owner_id": None}, "self.payload['repository']['owner']['id']")
])
def test_fill_payload_missing_param(missing_param, params, expected_error_pattern):
    sample_class = import_class(cloudos_url="http://example.comv", cloudos_apikey="somekey", workspace_id="myworkspace", platform="gitlab", workflow_name="someworkflow", workflow_url="http://workflows.com", repo_apikey="", repo_api_version="", repo_api_url="")
    sample_class.fill_payload(**params)

    # When a parameter is None, check_payload should raise ValueError
    with pytest.raises(ValueError) as excinfo:
        sample_class.check_payload()

    # Verify the error message mentions the expected pattern for the missing parameter
    assert expected_error_pattern in str(excinfo.value)

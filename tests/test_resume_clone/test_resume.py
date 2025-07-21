from cloudos_cli.jobs.job import Job, JobSetup
import responses
from responses import matchers
import pytest

PROJECT_NAME = "lifebit-testing"

CLOS_URL = "https://cloudos.lifebit.ai"
WS_ID = "workspace1"
PROJECT = "project_name"
PROJECT_ID = "p1234"
GIT_PROVIDER = "github"
REPO_ID = "repo1"
REPO_OWNER = "alice"
REPO_OWNER_ID = "abc1"
WF_ID = "wf123"
WF_NAME = "a_workflow"
WF_OWNER = "wfalice"
PROFILE = "nx_profile",
BRANCH = "prod"
COMMIT = "123456"
TAG = "tag1"
VERIFY = True

APIKEY = "somekey"
HEADERS = {"apikey": APIKEY}
BASE_PARAMS = {"teamId": WS_ID}

BASE_JOB = Job(
    cloudos_url=CLOS_URL,
    apikey=APIKEY,
    cromwell_token="",
    workspace_id=WS_ID,
    workflow_id=WF_ID,
    workflow_name=WF_NAME,
    project_name=PROJECT,
    project_id=PROJECT_ID
)

# Branch check assets
CHECK_BRANCH_RESPONSE = {
    "branches": [
        {"commit": {"sha": COMMIT}}
    ]
}
BAD_BRANCH_RESPONSE = {"branches": []}


@pytest.mark.parametrize("branch,reponse_json", [
    (BRANCH, CHECK_BRANCH_RESPONSE),
    ("bad_branch", BAD_BRANCH_RESPONSE)])
@responses.activate
def test_check_branch(branch, reponse_json):
    params = BASE_PARAMS | {
        "repositoryIdentifier": REPO_ID,
        "owner": REPO_OWNER,
        "workflowOwnerId": WF_OWNER,
        "branchName": branch
    }
    responses.add(
        responses.GET,
        url=f"{CLOS_URL}/api/v1/git/{GIT_PROVIDER}/getBranches/",
        match=[matchers.query_param_matcher(params), matchers.header_matcher(HEADERS)],
        json=reponse_json
    )
    branch_exists = BASE_JOB.check_branch(WS_ID, GIT_PROVIDER, REPO_ID, REPO_OWNER, WF_OWNER, branch, verify=VERIFY)
    if branch == BRANCH:
        assert branch_exists
    else:
        assert not branch_exists


COMMIT_RESPONSE = dict(commits=[{"commit": 1}])
BAD_COMMIT_RESPONSE = dict(commits=[])


@pytest.mark.parametrize("commit,commit_response",
                         [(COMMIT, COMMIT_RESPONSE),
                          ("bad_commit", BAD_COMMIT_RESPONSE)])
@responses.activate
def test_check_commit(commit, commit_response):
    params = BASE_PARAMS | {
        "repositoryIdentifier": REPO_ID,
        "owner": REPO_OWNER,
        "workflowOwnerId": WF_OWNER,
        "commitName": commit
    }
    responses.add(
        responses.GET,
        url=f"{CLOS_URL}/api/v1/git/{GIT_PROVIDER}/getCommits/",
        match=[matchers.query_param_matcher(params), matchers.header_matcher(HEADERS)],
        json=commit_response
    )
    commit_exists = BASE_JOB.check_commit(WS_ID, GIT_PROVIDER, REPO_ID, REPO_OWNER, WF_OWNER, commit, VERIFY)
    if commit == COMMIT:
        assert commit_exists
    else:
        assert not commit_exists


VALID_PROFILES = ["good_profile", "another_profile"]


@pytest.mark.parametrize("profile", ["good_profile", "bad_profile"])
@responses.activate
def test_check_profile(profile):
    params = BASE_PARAMS | {
        "workflowId": WF_ID,
        "revisionHash": COMMIT
    }
    responses.add(
        responses.GET,
        url=f"{CLOS_URL}/api/v2/workflows/parsers/nf-config-profiles",
        match=[matchers.query_param_matcher(params), matchers.header_matcher(HEADERS)],
        json=VALID_PROFILES
    )
    profile_exists = BASE_JOB.check_profile(WF_ID, COMMIT, WS_ID, profile, VERIFY)
    if profile in VALID_PROFILES:
        assert profile_exists
    else:
        assert not profile_exists


VALID_PROJECTS = {
    "total": 1,
    "projects": [
        {
            "_id": PROJECT,
            "name": PROJECT_NAME,
            "user": {
                "name": "Alice",
                "surname": "Smith",
                "email": "alice.smith@example.com"
            }
        }
    ]
}
INVALID_PROJECTS = {
    "total": 0
}


@responses.activate
@pytest.mark.parametrize("project,project_response", [(PROJECT, VALID_PROJECTS), ("bad_project", INVALID_PROJECTS)])
def check_projects(project, project_response):
    params = BASE_PARAMS | {"search": project}
    responses.add(
        responses.GET,
        url=f"{CLOS_URL}/api/v2/projects",
        match=[matchers.query_param_matcher(params), matchers.header_matcher(HEADERS)],
        json=project_response
    )
    BASE_JOB.check_project(WS_ID, project, VERIFY)


JOB_NAME = "job1"
JOB_ID = "jobid1234"
NEW_JOB_ID = "jobid5678"
INSTANCE_TYPE = "c5.xlarge"
PAYLOAD_BRANCH_AWS = {
    "name": JOB_NAME,
    "resumable": True,
    "revision": {
        "revisionType": "branch",
        "branch": BRANCH
    },
    "profile": PROFILE,
    "workflow": WF_ID,
    "project": PROJECT,
    "parameters": [
        {
            "name": "param1",
            "textValue": "val1"
        },
        {
            "name": "param2",
            "textValue": "val2"
        }
    ],
    "usesFusionFileSystem": False,
    "masterInstance": {
        "requestedInstance": {
            "type": INSTANCE_TYPE
        }
    },
    "execution": {
        "computeCostLimit": 10,
    },
    "batch": {"enabled": True},
    "nextflowVersion": "22.10.8",
    "storageSizeInGb": 500,
    "storageMode": "regular",
    "executionPlatform": "aws",
    "saveProcessLogs": True
}
PAYLOAD_BRANCH_AZURE = {
    "name": JOB_NAME,
    "resumable": True,
    "revision": {
        "revisionType": "branch",
        "branch": BRANCH
    },
    "profile": PROFILE,
    "workflow": WF_ID,
    "project": PROJECT,
    "parameters": [
        {
            "name": "param1",
            "textValue": "val1"
        },
        {
            "name": "param2",
            "textValue": "val2"
        }
    ],
    "usesFusionFileSystem": False,
    "masterInstance": {
        "requestedInstance": {
            "type": "Standard_D4as_v4"
        }
    },
    "execution": {
        "computeCostLimit": 10,
    },
    "batch": {"enabled": True},
    "nextflowVersion": "22.11.1-edge",
    "storageSizeInGb": 500,
    "storageMode": "regular",
    "executionPlatform": "azure",
    "saveProcessLogs": True
}
FINISHED_JOB_BRNACH = {
    "name": WF_NAME,
    "status": "completed",
    "resumeWorkDir": "s3://some/path/to/results",
    "revision": {
        "revisionType": "branch",
        "branch": BRANCH,
        "commit": COMMIT,
        "tag": TAG
    },
    "workflow": {
        "name": WF_NAME,
        "isModule": True,
        "workflowType": "nextflow",
        "repository": {
            "repositoryId": REPO_ID,
            "owner": {
                "id": REPO_OWNER_ID,
                "login": REPO_OWNER
            },
            "platform": GIT_PROVIDER
        }
    },
    "saveProcessLogs": True,
    "azureBatch": {"vmType": "Standard_D4as_v4"}
}


@responses.activate
@pytest.mark.parametrize("payload,job_id,job_params,resume",
                         [
                            (PAYLOAD_BRANCH_AWS, JOB_ID, None, False),
                            (PAYLOAD_BRANCH_AWS, JOB_ID, ["param1=val1", "param2=val2"], False),
                            (PAYLOAD_BRANCH_AZURE, JOB_ID, None, False),
                            (PAYLOAD_BRANCH_AWS, JOB_ID, None, True),
                            (PAYLOAD_BRANCH_AWS, JOB_ID, ["param1=val1", "param2=val2"], True),
                            (PAYLOAD_BRANCH_AZURE, JOB_ID, None, True),
                         ])
def test_clone(payload, job_id, job_params, resume):
    params = dict(teamId=WS_ID)
    responses.add(
        responses.GET,
        url=f"{CLOS_URL}/api/v1/git/{GIT_PROVIDER}/getBranches/",
        match=[matchers.query_param_matcher(params), matchers.header_matcher(HEADERS)],
        json=CHECK_BRANCH_RESPONSE
    )
    responses.add(
            responses.GET,
            url=f"{CLOS_URL}/api/v1/git/{GIT_PROVIDER}/getCommits/",
            match=[matchers.query_param_matcher(params), matchers.header_matcher(HEADERS)],
            json=COMMIT_RESPONSE
        )
    responses.add(
        responses.GET,
        url=f"{CLOS_URL}/api/v2/workflows/parsers/nf-config-profiles",
        match=[matchers.query_param_matcher(params), matchers.header_matcher(HEADERS)],
        json=VALID_PROFILES
    )
    responses.add(
        responses.GET,
        url=f"{CLOS_URL}/api/v2/projects",
        match=[matchers.query_param_matcher(params), matchers.header_matcher(HEADERS)],
        json=VALID_PROJECTS
    )
    responses.add(
        responses.GET,
        url=f"{CLOS_URL}/api/v1/jobs/{job_id}/request-payload",
        match=[matchers.query_param_matcher(params), matchers.header_matcher(HEADERS)],
        json=payload
    )
    responses.add(
        responses.GET,
        url=f"{CLOS_URL}/api/v1/jobs/{job_id}",
        match=[matchers.query_param_matcher(params), matchers.header_matcher(HEADERS)],
        json=FINISHED_JOB_BRNACH
    )
    responses.add(
        responses.POST,
        url=f"{CLOS_URL}/api/v2/jobs",
        match=[matchers.query_param_matcher(params), matchers.header_matcher(HEADERS)],
        json=dict(jobId=NEW_JOB_ID)

    )

    new_job_id = BASE_JOB.clone_or_resume_job(job_id, parameters=job_params, resume_job=resume)
    assert new_job_id == NEW_JOB_ID


@pytest.mark.parametrize("payload", [(PAYLOAD_BRANCH_AWS)])
@responses.activate
def test_job_setup(payload):
    params = dict(teamId=WS_ID)
    responses.add(
        responses.GET,
        url=f"{CLOS_URL}/api/v1/jobs/{JOB_ID}/request-payload",
        match=[matchers.query_param_matcher(params), matchers.header_matcher(HEADERS)],
        json=payload
    )
    responses.add(
        responses.GET,
        url=f"{CLOS_URL}/api/v1/jobs/{JOB_ID}",
        match=[matchers.query_param_matcher(params), matchers.header_matcher(HEADERS)],
        json=FINISHED_JOB_BRNACH
    )
    headers = HEADERS | {"Content-type": "application/json"}
    wf_list_response = {
        "paginationMetadata": {
            "Pagination-Count": 1
        },
        "workflows": [
            {
                "_id": WF_ID,
                "name": WF_NAME,
                "archived": {
                    "status": False
                },
                "mainFile": "main.nf",
                "workflowType": "nextflow",
                "group": "drug-discovery",
                "repository": {
                    "platform": GIT_PROVIDER,
                    "name": REPO_ID,
                    "url": "https://somegit.com",
                    "isPrivate": True
                }
            }
        ]
    }
    responses.add(
        responses.GET,
        url=f"{CLOS_URL}/api/v3/workflows",
        match=[matchers.query_param_matcher({"search": WF_NAME, "teamId": WS_ID}), matchers.header_matcher(headers)],
        status=200,
        json=wf_list_response
    )
    responses.add(
            responses.GET,
            url=f"{CLOS_URL}/api/v2/projects?teamId={WS_ID}&search={PROJECT_NAME}",
            headers=headers,
            status=200,
            json=VALID_PROJECTS
    )
    responses.add(
        responses.GET,
        url=f"{CLOS_URL}/api/v1/cloud/aws",
        match=[matchers.query_param_matcher({"teamId": "workspace1"})],
        json={"withValue": 1}
    )
    job_setup = JobSetup(APIKEY, WS_ID, PROJECT_NAME, job_id=JOB_ID)
    assert job_setup.job_id == JOB_ID

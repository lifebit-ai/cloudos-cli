from cloudos_cli.clos import ImportGitlab, ImportGithub

CLOS_URL = "https://dev.sdlc.lifebit.ai"
CLOS_TOKEN = "68369cec859e81fe43867aee:nqja8Q6Xdr1lMWUxNs0FdTia7l78tvW9ff7FDpst"
WS_ID = "5ca489a630020c00b2fe7609"
GL_URL = "https://gitlab.com/lb-ortiz/sample_subgroup/spammer-nf"
GL_NAME = "spammer-gl"
GH_URL = "https://github.com/lifebit-ai/spammer-nf"
GH_NAME = "spammer-gh"

def test_gitlab():
    gl = ImportGitlab(cloudos_url=CLOS_URL, cloudos_apikey=CLOS_TOKEN, workspace_id=WS_ID, workflow_url=GL_URL, workflow_name=GL_NAME, workflow_docs_link="", platform="gitlab", main_file=None, verify=True)
    gl.import_workflow()

def test_github():
    gl = ImportGithub(cloudos_url=CLOS_URL, cloudos_apikey=CLOS_TOKEN, workspace_id=WS_ID, workflow_url=GH_URL, workflow_name=GH_NAME, workflow_docs_link="", platform="github", main_file=None, verify=True)
    gl.import_workflow()
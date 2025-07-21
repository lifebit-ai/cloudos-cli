from cloudos_cli.jobs.job import JobSetup

cloudos_url = "https://cloudos.lifebit.ai"

# Azure
# apikey = "686e5447273110ef5f20a086:a7GdkuV2mRprtbIyGIgA1RGMy7tHGJNzOKeUkiJC"
# workspace_id = "67d97c06d5f03da2eee9ca8b"
# project_name = "target-id--juan-cli-tests"
# job_id = "685e9607beaf05a2d205292c"

# AWS
apikey = "687475479e7fe38ec6dff418:o5Is6prtqwN8xgRHmcdRqILGMbwQ7rsGl9Y0rGfd"
workspace_id = "5c6d3e9bd954e800b23f8c62"
project_name = "davidp_testing1"
# job_id = "684b1d66a8344509de758261"
job_id = "686ebc5e45064980403a0d35" # bash array

job = JobSetup(
    cloudos_url=cloudos_url,
    apikey=apikey,
    workspace_id=workspace_id,
    job_id=job_id,
    run_type="clone",
    resumable=True
)
job.run_again(resume=False)

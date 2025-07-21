from cloudos_cli.__main__ import run

clos = Job(
    cloudos_url="https://cloudos.lifebit.ai",
    apikey="6875dfeeea34967c728ddc7a:2PjPNQZ6MjaJnOsvN7rHPvyqaloEZqrkQXlRCOsq",
    cromwell_token="",
    workspace_id="67d97c06d5f03da2eee9ca8b",
    project_name="target-id--juan-cli-tests",
    workflow_name="Target identification from GWAS summary statistics",
)
sent = clos.send_job(
    git_branch="prod",
    nextflow_profile="test_ci_wisemapper_magma_twas_sancfm",
    nextflow_version="22.11.1-edge",
    execution_platform="azure",
)
# d = clos.clone_or_resume_job(
#     job_id="685e20debeaf05a2d201ab13",
#     commit="567da1533d54040bd9471eeb988ea4d7b405a5d9",
#     profile="test_ci_wisemapper_magma_twas_sancfm",
#     name="resumed_from_cli",
#     project="",
#     parameters=["param1=val1", "param2=val67"],
#     resume_job=True,
# )


r = run(
    ctx=None,
    profile="azure",
    apikey="6875dfeeea34967c728ddc7a:2PjPNQZ6MjaJnOsvN7rHPvyqaloEZqrkQXlRCOsq",
    cloudos_cli="https://cloudos.lifebit.ai",
    cromwell_token="",
    workspace_id="67d97c06d5f03da2eee9ca8b",
    project_name="target-id--juan-cli-tests",
    workflow_name="Target identification from GWAS summary statistics",
    git_branch="prod",
    nextflow_profile="test_ci_wisemapper_magma_twas_sancfm",
    nextflow_version="22.11.1-edge",
    execution_platform="azure",
    job_name="new_job",
    instance_disk=500,
    storage_mode="regular",
    lustre_size=1200,
    wait_time=3600,
    repository_platform="github",
    hpc_id="660fae20f93358ad61e0104b",
    azure_worker_instance_type="Standard_D4as_v4",
    azure_worker_instance_disk=100,
    cost_limit=30.0,
    request_interval=30,
    instance_type="NONE_SELECTED",
    # Flag parameters defaulting to False
    resumable=False,
    do_not_save_logs=False,
    wait_completion=False,
    azure_worker_instance_spot=False,
    accelerate_file_staging=False,
    use_private_docker_repository=False,
    verbose=False,
    disable_ssl_verification=False
)

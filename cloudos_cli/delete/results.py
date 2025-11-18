import click
import cloudos_cli.jobs.job as jb


def delete_job_results(cloudos_url, apikey, job_id, workspace_id, mode="analysisResults", verify=True):

    if mode not in ["analysisResults", "workDirectory"]:
        raise ValueError(f"Invalid mode '{mode}'. Supported modes are 'analysisResults' and 'workDirectory'.")

    job = jb.Job(cloudos_url, apikey, None, workspace_id, None, None, workflow_id=1234, project_id="None",
                 mainfile=None, importsfile=None, verify=verify)

    job.delete_job_results(job_id, mode, verify=verify)
import click
import cloudos_cli.jobs.job as jb


def delete_job_results(cloudos_url, apikey, j_id, workspace_id, verify=True):
    job = jb.Job(cloudos_url, apikey, None, workspace_id, None, None, workflow_id=1234, project_id="None",
                 mainfile=None, importsfile=None, verify=verify)

    # Get job results directory
    try:
        j_results_dir = job.get_field_from_jobs_endpoint(j_id, field='analysisResults', verify=verify)
    except Exception as e:
        if "Field 'analysisResults' not found in endpoint 'jobs'" in str(e):
            click.secho("Selected job does not have 'Results' information.", fg="yellow", bold=True)
            return
        else:
            raise e

    # Get folder ID
    folder_id = j_results_dir.get('folderId')
    if not folder_id:
        raise ValueError("The job does not have a results directory associated.")

    job.delete_job_results(folder_id, verify=verify)
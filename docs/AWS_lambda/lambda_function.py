import cloudos.jobs.job as jb
import json
import os

# AWS Lambda function handler
def lambda_handler(event, context):
    apikey = os.environ.get('CLOUDOS_API_KEY')
    cloudos_url = os.environ.get('CLOUDOS_URL')
    workspace_id = os.environ.get('WORKSPACE_ID')
    project_name = os.environ.get('PROJECT_NAME')
    workflow_name = os.environ.get('WORKFLOW_NAME')

    bucket_name = event['Records'][0]['s3']['bucket']['name']
    object_key = event['Records'][0]['s3']['object']['key']
    input_file_path = f"s3://{bucket_name}/{object_key}"

    try:
        cloudos_workflow = jb.Job(cloudos_url, apikey, None, workspace_id, project_name, workflow_name)
        job_id = cloudos_workflow.send_job(
            parameter=(f'input={input_file_path}', 'outdir=results'),
            nextflow_profile='test,docker'
            )
        job_status = cloudos_workflow.get_job_status(job_id)
        job_status_h = json.loads(job_status.content)["status"]

        # Return success response
        return {
            "statusCode": 200,
            "body": json.dumps(job_status_h)
        }
    except Exception as e:
        # Handle any exceptions
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }

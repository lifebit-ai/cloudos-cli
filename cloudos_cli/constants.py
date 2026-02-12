"""Global constants for CloudOS CLI."""

# Job status constants
JOB_COMPLETED = 'completed'
JOB_FAILED = 'failed'
JOB_ABORTED = 'aborted'

# Nextflow version constants
AWS_NEXTFLOW_VERSIONS = ['22.10.8', '24.04.4']
AZURE_NEXTFLOW_VERSIONS = ['22.11.1-edge']
HPC_NEXTFLOW_VERSIONS = ['22.10.8']
AWS_NEXTFLOW_LATEST = '24.04.4'
AZURE_NEXTFLOW_LATEST = '22.11.1-edge'
HPC_NEXTFLOW_LATEST = '22.10.8'

# Job abort states
ABORT_JOB_STATES = ['running', 'initializing']

# Request interval for Cromwell
REQUEST_INTERVAL_CROMWELL = 30

# Global constants for CloudOS CLI
CLOUDOS_URL = 'https://cloudos.lifebit.ai'
INIT_PROFILE = 'initialisingProfile'

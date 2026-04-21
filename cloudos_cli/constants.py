"""Global constants for CloudOS CLI."""

# Job status constants
JOB_COMPLETED = 'completed'
JOB_FAILED = 'failed'
JOB_ABORTED = 'aborted'

# Nextflow version constants
AWS_NEXTFLOW_VERSIONS = ['22.10.8', '24.04.4', '25.04.8', '25.10.4']
AZURE_NEXTFLOW_VERSIONS = ['22.11.1-edge']
HPC_NEXTFLOW_VERSIONS = ['22.10.8']
AWS_NEXTFLOW_LATEST = '25.10.4'
AZURE_NEXTFLOW_LATEST = '22.11.1-edge'
HPC_NEXTFLOW_LATEST = '22.10.8'

# Nextflow version defaults by workflow type
PLATFORM_WORKFLOW_NEXTFLOW_VERSION = '22.10.8'  # For Lifebit Platform workflows (modules)
USER_WORKFLOW_NEXTFLOW_VERSION = '24.04.4'  # For user-imported workflows

# Job abort states
ABORT_JOB_STATES = ['running', 'initializing']

# Request interval for Cromwell
REQUEST_INTERVAL_CROMWELL = 30

# Global constants for CloudOS CLI
CLOUDOS_URL = 'https://cloudos.lifebit.ai'
INIT_PROFILE = 'initialisingProfile'

# Job status symbol mapping
JOB_STATUS_SYMBOLS = {
    "completed": "[bold green]✓[/bold green]",
    "running": "[bold bright_black]◐[/bold bright_black]",
    "failed": "[bold red]✗[/bold red]",
    "aborted": "[bold orange3]■[/bold orange3]",
    "aborting": "[bold orange3]⊡[/bold orange3]",
    "initialising": "[bold bright_black]○[/bold bright_black]",
    "scheduled": "[bold cyan]◷[/bold cyan]",
    "n/a": "[bold bright_black]?[/bold bright_black]"
}

# Column priority groups for responsive table display
COLUMN_PRIORITY_GROUPS = {
    'minimal': ['status', 'id', 'name'],
    'essential': ['status', 'id', 'name', 'pipeline'],
    'important': ['project', 'owner', 'run_time', 'cost'],
    'useful': ['submit_time', 'end_time', 'commit'],
    'extended': ['resources', 'storage_type']
}

# Essential columns priority order for auto-selection
ESSENTIAL_COLUMN_PRIORITY = ['status', 'id', 'name', 'pipeline']

# Additional columns priority order for auto-selection
ADDITIONAL_COLUMN_PRIORITY = [
    'project', 'owner', 'run_time', 'cost',
    'submit_time', 'end_time', 'commit', 'resources', 'storage_type'
]

# Column configurations for job list table
COLUMN_CONFIGS = {
    'status': {"header": "Status", "style": "cyan", "no_wrap": True, "min_width": 6, "max_width": 6},
    'name': {"header": "Name", "style": "green", "overflow": "fold", "no_wrap": False, "min_width": 6, "max_width": 14},
    'project': {"header": "Project", "style": "magenta", "overflow": "fold", "no_wrap": False, "min_width": 6, "max_width": 18},
    'owner': {"header": "Owner", "style": "blue", "overflow": "fold", "no_wrap": False, "min_width": 4, "max_width": 14},
    'pipeline': {"header": "Pipeline", "style": "yellow", "overflow": "fold", "no_wrap": False, "min_width": 8, "max_width": 14},
    'id': {"header": "ID", "style": "white", "overflow": "ellipsis", "no_wrap": True, "min_width": 24, "max_width": 24},
    'submit_time': {"header": "Submit", "style": "cyan", "no_wrap": True, "min_width": 12, "max_width": 16},
    'end_time': {"header": "End", "style": "cyan", "no_wrap": True, "min_width": 12, "max_width": 16},
    'run_time': {"header": "Runtime", "style": "green", "no_wrap": True, "min_width": 8, "max_width": 12},
    'commit': {"header": "Commit", "style": "magenta", "no_wrap": True, "min_width": 9, "max_width": 10},
    'cost': {"header": "Cost", "style": "yellow", "no_wrap": True, "min_width": 8, "max_width": 12},
    'resources': {"header": "Resources", "style": "blue", "overflow": "ellipsis", "no_wrap": True, "min_width": 8, "max_width": 16},
    'storage_type': {"header": "Storage", "style": "white", "no_wrap": True, "min_width": 8, "max_width": 10}
}

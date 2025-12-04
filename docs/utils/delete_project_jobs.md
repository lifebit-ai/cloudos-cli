# Delete Project Jobs Script

A bash utility script for bulk deletion of job results and/or working directories for all jobs within a CloudOS project.

## Overview

The `delete_project_jobs.sh` script provides a safe and efficient way to clean up storage by deleting results and working directories for multiple jobs at once. It includes built-in safety features like confirmation prompts, dry-run mode, and detailed progress reporting.

## Location

```
utils/delete_project_jobs.sh
```

## Features

- **Bulk deletion**: Process multiple jobs in a single operation
- **Flexible targeting**: Delete results, workdir, or both
- **Project filtering**: Target all jobs within a specific project
- **Status filtering**: Optionally filter by job status (completed, failed, etc.)
- **Safety controls**: 
  - Confirmation prompts before deletion
  - Dry-run mode to preview actions
  - Status validation
- **Progress tracking**: Real-time feedback with counters and colored output
- **Comprehensive reporting**: Detailed summary of operations

## Usage

### Basic Syntax

```bash
./utils/delete_project_jobs.sh --profile <profile> --project-name <project> [OPTIONS]
```

### Required Arguments

| Argument | Description |
|----------|-------------|
| `--profile PROFILE` | CloudOS profile to use for authentication |
| `--project-name PROJECT` | Project name to filter jobs (must match exactly) |

### Deletion Options

At least one of the following must be specified:

| Option | Description |
|--------|-------------|
| `--results` | Delete results directories only |
| `--workdir` | Delete working directories only |
| `--both` | Delete both results and working directories |

### Additional Options

| Option | Description |
|--------|-------------|
| `--dry-run` | Show what would be deleted without actually deleting |
| `--filter-status STATUS` | Additional filter by job status |
| `--help` | Display help message |

### Valid Status Values

When using `--filter-status`, the following values are accepted:
- `completed`
- `running`
- `failed`
- `aborted`
- `queued`
- `pending`
- `initializing`

## Examples

### Delete Results for All Jobs in a Project

```bash
./utils/delete_project_jobs.sh \
  --profile my_profile \
  --project-name "My Research Project" \
  --results
```

### Delete Both Results and Workdir for Completed Jobs

```bash
./utils/delete_project_jobs.sh \
  --profile my_profile \
  --project-name "Analysis Project" \
  --both \
  --filter-status completed
```

### Dry Run to Preview Deletions

```bash
./utils/delete_project_jobs.sh \
  --profile my_profile \
  --project-name "Test Project" \
  --both \
  --dry-run
```

### Delete Workdir Only for Failed Jobs

```bash
./utils/delete_project_jobs.sh \
  --profile my_profile \
  --project-name "Experimental Runs" \
  --workdir \
  --filter-status failed
```

## Output

### Configuration Display

The script displays the configuration before proceeding:

```
=== CloudOS Bulk Deletion Script ===
Profile: my_profile
Project: My Research Project
Delete results: true
Delete workdir: true
Dry run: false
Status filter: completed

WARNING: This will permanently delete data. This action cannot be undone.
Are you sure you want to proceed? (yes/no):
```

### Progress Output

During execution, the script shows real-time progress:

```
Fetching job list...
Found 15 job(s) in project "My Research Project"

[1/15] Processing job: genome_analysis_v1 (ID: 62c83a1191fe06013b7ef355, Status: completed)
  Deleting results...
  ✓ Results deleted successfully
  Deleting workdir...
  ✓ Workdir deleted successfully

[2/15] Processing job: variant_calling_test (ID: 62c83b2291fe06013b7ef456, Status: completed)
  Deleting results...
  ⚠ Failed to delete results (may not exist or already deleted)
  Deleting workdir...
  ✓ Workdir deleted successfully
```

### Summary Report

After processing all jobs, a summary is displayed:

```
=== Summary ===
Total jobs processed: 15

Results deletion:
  Successful: 13
  Failed/Skipped: 2

Workdir deletion:
  Successful: 14
  Failed/Skipped: 1

Done!
```

## How It Works

1. **Validation**: Validates all input parameters and checks status values
2. **Confirmation**: Prompts for user confirmation (unless in dry-run mode)
3. **Job List Retrieval**: Uses `cloudos job list` to fetch all jobs matching the criteria
4. **Extraction**: Extracts job IDs, names, and statuses from the CSV output
5. **Processing**: Iterates through each job and executes deletion commands
6. **Reporting**: Tracks success/failure for each operation and displays a summary

## Technical Details

### Dependencies

- **CloudOS CLI**: Must be installed and accessible in PATH
- **Standard Unix tools**: `awk`, `cut`, `tail`, `wc`
- **Bash**: Version 4.0 or higher

### CSV Column Structure

The script expects the following CSV column order from `cloudos job list`:
1. Status
2. Name
3. Project
4. Owner
5. Pipeline
6. ID

### Error Handling

- **Failed deletions**: Logged as warnings but don't stop execution
- **Missing job list**: Exits with error if CSV cannot be generated
- **Empty results**: Gracefully handles projects with no matching jobs
- **Invalid status**: Validates status values before execution

### Exit Codes

| Code | Description |
|------|-------------|
| 0 | Successful completion |
| 1 | Error (missing arguments, invalid status, failed job list retrieval, etc.) |

## Safety Features

### Confirmation Prompt

Before any deletion occurs, the script displays a warning and requires explicit confirmation:

```
WARNING: This will permanently delete data. This action cannot be undone.
Are you sure you want to proceed? (yes/no):
```

Type `yes` to proceed or `no` to cancel.

### Dry Run Mode

Use `--dry-run` to preview what would be deleted without making any changes:

```bash
./utils/delete_project_jobs.sh \
  --profile my_profile \
  --project-name "Test Project" \
  --both \
  --dry-run
```

Output will show:
```
[1/5] Processing job: test_analysis (ID: 62c83a1191fe06013b7ef355, Status: completed)
  [DRY RUN] Would delete results for job 62c83a1191fe06013b7ef355
  [DRY RUN] Would delete workdir for job 62c83a1191fe06013b7ef355
```

### Silent Failures

If a deletion fails (e.g., resource already deleted, no permissions), the script:
- Logs a warning with a yellow indicator
- Continues processing remaining jobs
- Includes the failure in the summary report

## Best Practices

1. **Always test with dry-run first**: Preview the operations before executing
   ```bash
   ./utils/delete_project_jobs.sh --profile my_profile --project-name "Project" --both --dry-run
   ```

2. **Start with completed jobs**: Initially target only completed jobs to avoid interfering with running analyses
   ```bash
   ./utils/delete_project_jobs.sh --profile my_profile --project-name "Project" --both --filter-status completed
   ```

3. **Delete in stages**: Consider deleting results first, then workdir separately
   ```bash
   # First delete results
   ./utils/delete_project_jobs.sh --profile my_profile --project-name "Project" --results
   
   # Then delete workdir
   ./utils/delete_project_jobs.sh --profile my_profile --project-name "Project" --workdir
   ```

4. **Review the summary**: Always check the summary report to ensure expected results

5. **Back up critical data**: Before bulk deletion, ensure any critical results are backed up elsewhere

## Troubleshooting

### "Failed to retrieve job list"

**Cause**: The `cloudos job list` command failed

**Solutions**:
- Verify your profile configuration: `cloudos configure list-profiles`
- Check project name spelling (case-sensitive)
- Ensure you have access to the workspace and project
- Test the job list command manually:
  ```bash
  cloudos job list --profile my_profile --filter-project "Project Name"
  ```

### "No jobs found for project"

**Cause**: No jobs match the specified criteria

**Solutions**:
- Verify the project name is correct (case-sensitive)
- Remove status filter to see all jobs
- Check if jobs exist using CloudOS web interface

### Permission Errors

**Cause**: API key lacks permission to delete resources

**Solutions**:
- Ensure you own the jobs you're trying to delete
- Verify your API key has appropriate permissions
- Contact your workspace administrator

### "Invalid status"

**Cause**: Status value not in the allowed list

**Solution**: Use one of the valid statuses: completed, running, failed, aborted, queued, pending, initializing

## Limitations

1. **Project-wide only**: Cannot target individual jobs (use CloudOS CLI directly for that)
2. **No undo**: Deletions are permanent and cannot be reversed
3. **Single workspace**: Processes one workspace at a time (determined by profile)
4. **No parallel execution**: Jobs are processed sequentially

## Related Commands

- `cloudos job list`: List jobs in a workspace
- `cloudos job results --delete`: Delete results for a single job
- `cloudos job workdir --delete`: Delete workdir for a single job
- `cloudos job status`: Check status of a job

## See Also

- [CloudOS CLI Documentation](../../README.md)
- [Job Management](../../README.md#nextflow-jobs)
- [Delete Job Results](../../README.md#delete-job-results)

# CloudOS Job Archive Command Examples

This document shows examples of using the new `cloudos job archive` command.

## Basic Usage

### Archive a Single Job
```bash
cloudos job archive \
    --apikey YOUR_API_KEY \
    --workspace-id YOUR_WORKSPACE_ID \
    --job-ids 69413101b07d5f5bb46891b4
```

### Archive Multiple Jobs
```bash
cloudos job archive \
    --apikey YOUR_API_KEY \
    --workspace-id YOUR_WORKSPACE_ID \
    --job-ids "job1,job2,job3"
```

### Archive Jobs with Verbose Output
```bash
cloudos job archive \
    --apikey YOUR_API_KEY \
    --workspace-id YOUR_WORKSPACE_ID \
    --job-ids 69413101b07d5f5bb46891b4 \
    --verbose
```

### Using Profile Configuration
```bash
# First configure your profile
cloudos configure

# Then use the profile
cloudos job archive \
    --job-ids 69413101b07d5f5bb46891b4 \
    --profile my-profile
```

## What the Command Does

The `archive` command:

1. **Validates Job IDs**: Checks that each job ID exists and is accessible in the specified workspace
2. **Archives Jobs**: Makes a PUT request to `/api/v1/jobs?teamId=WORKSPACE_ID` with the archive payload
3. **Provides Feedback**: Shows success or error messages for each job

## API Details

The command sends this payload structure:
```json
{
  "jobIds": ["69413101b07d5f5bb46891b4"],
  "update": {
    "archived": {
      "status": true,
      "archivalTimestamp": "2025-12-17T09:59:10.497Z"
    }
  }
}
```

## Error Handling

- **Invalid Job IDs**: Jobs that don't exist are skipped with a warning message
- **No Valid Jobs**: If no valid jobs are found, the command exits with an error
- **Empty Job List**: Providing an empty job list results in an error
- **API Errors**: HTTP errors are handled and reported appropriately

## Exit Codes

- **0**: Success - all valid jobs were archived
- **Non-zero**: Error occurred (invalid jobs, API errors, etc.)
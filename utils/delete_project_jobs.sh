#!/bin/bash

# Script to delete results and/or working directories for all jobs in a CloudOS project
# Usage: ./delete_project_jobs.sh --profile <profile> --project-name <project> [--results] [--workdir] [--both]

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to display usage
usage() {
    echo "Usage: $0 --profile <profile> --project-name <project> [OPTIONS]"
    echo ""
    echo "Required arguments:"
    echo "  --profile PROFILE         CloudOS profile to use"
    echo "  --project-name PROJECT    Project name to filter jobs"
    echo ""
    echo "Deletion options (at least one required):"
    echo "  --results                 Delete results directories only"
    echo "  --workdir                 Delete working directories only"
    echo "  --both                    Delete both results and working directories"
    echo ""
    echo "Additional options:"
    echo "  --dry-run                 Show what would be deleted without actually deleting"
    echo "  --filter-status STATUS    Additional filter by job status (e.g., completed)"
    echo "  --help                    Display this help message"
    echo ""
    echo "Examples:"
    echo "  # Delete results for all jobs in a project"
    echo "  $0 --profile my_profile --project-name \"My Project\" --results"
    echo ""
    echo "  # Delete both results and workdir for completed jobs only"
    echo "  $0 --profile my_profile --project-name \"My Project\" --both --filter-status completed"
    echo ""
    echo "  # Dry run to see what would be deleted"
    echo "  $0 --profile my_profile --project-name \"My Project\" --both --dry-run"
    exit 1
}

# Initialize variables
PROFILE="default"
PROJECT_NAME=""
DELETE_RESULTS=false
DELETE_WORKDIR=false
DRY_RUN=false
FILTER_STATUS=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --profile)
            PROFILE="$2"
            shift 2
            ;;
        --project-name)
            PROJECT_NAME="$2"
            shift 2
            ;;
        --results)
            DELETE_RESULTS=true
            shift
            ;;
        --workdir)
            DELETE_WORKDIR=true
            shift
            ;;
        --both)
            DELETE_RESULTS=true
            DELETE_WORKDIR=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --filter-status)
            FILTER_STATUS="$2"
            shift 2
            ;;
        --help)
            usage
            ;;
        *)
            echo -e "${RED}Error: Unknown option $1${NC}"
            usage
            ;;
    esac
done

# Validate required arguments
if [[ -z "$PROFILE" ]]; then
    echo -e "${RED}Error: --profile is required${NC}"
    usage
fi

if [[ -z "$PROJECT_NAME" ]]; then
    echo -e "${RED}Error: --project-name is required${NC}"
    usage
fi

if [[ "$DELETE_RESULTS" == false && "$DELETE_WORKDIR" == false ]]; then
    echo -e "${RED}Error: At least one deletion option (--results, --workdir, or --both) is required${NC}"
    usage
fi

# Validate FILTER_STATUS if provided
if [[ -n "$FILTER_STATUS" ]]; then
    VALID_STATUSES=("completed" "running" "failed" "aborted" "queued" "pending" "initializing")
    STATUS_VALID=false
    for valid_status in "${VALID_STATUSES[@]}"; do
        if [[ "$FILTER_STATUS" == "$valid_status" ]]; then
            STATUS_VALID=true
            break
        fi
    done
    
    if [[ "$STATUS_VALID" == false ]]; then
        echo -e "${RED}Error: Invalid status '$FILTER_STATUS'. Valid statuses are: $(IFS=','; echo "${VALID_STATUSES[*]}")${NC}"
    fi
fi

# Display configuration
echo -e "${GREEN}=== CloudOS Bulk Deletion Script ===${NC}"
echo "Profile: $PROFILE"
echo "Project: $PROJECT_NAME"
echo "Delete results: $DELETE_RESULTS"
echo "Delete workdir: $DELETE_WORKDIR"
echo "Dry run: $DRY_RUN"
if [[ -n "$FILTER_STATUS" ]]; then
    echo "Status filter: $FILTER_STATUS"
fi
echo ""

# Confirm before proceeding
if [[ "$DRY_RUN" == false ]]; then
    echo -e "${YELLOW}WARNING: This will permanently delete data. This action cannot be undone.${NC}"
    read -p "Are you sure you want to proceed? (yes/no): " CONFIRM
    if [[ "$CONFIRM" != "yes" ]]; then
        echo "Operation cancelled."
        exit 0
    fi
    echo ""
fi

# Create temporary file for job list
TEMP_FILE=$(mktemp)
trap "rm -f $TEMP_FILE" EXIT

# Build cloudos job list command
LIST_CMD="cloudos job list --profile \"$PROFILE\" --filter-project \"$PROJECT_NAME\" --output-format csv --last-n-jobs all"

if [[ -n "$FILTER_STATUS" ]]; then
    LIST_CMD="$LIST_CMD --filter-status \"$FILTER_STATUS\""
fi

echo -e "${GREEN}Fetching job list...${NC}"
eval "$LIST_CMD" > /dev/null 2>&1

# Check if joblist.csv was created
if [[ ! -f "joblist.csv" ]]; then
    echo -e "${RED}Error: Failed to retrieve job list${NC}"
    exit 1
fi

# Extract job IDs from CSV (skip header, get first column)
tail -n +2 joblist.csv | cut -d',' -f1 > "$TEMP_FILE"

JOB_COUNT=$(wc -l < "$TEMP_FILE" | tr -d ' ')

if [[ "$JOB_COUNT" -eq 0 ]]; then
    echo -e "${YELLOW}No jobs found for project \"$PROJECT_NAME\"${NC}"
    rm -f joblist.csv
    exit 0
fi

echo -e "${GREEN}Found $JOB_COUNT job(s) in project \"$PROJECT_NAME\"${NC}"
echo ""

# Initialize counters
SUCCESS_RESULTS=0
SUCCESS_WORKDIR=0
FAILED_RESULTS=0
FAILED_WORKDIR=0
SKIPPED_RESULTS=0
SKIPPED_WORKDIR=0

# Process each job
COUNTER=0
while IFS= read -r JOB_ID; do
    COUNTER=$((COUNTER + 1))
    echo -e "${GREEN}[$COUNTER/$JOB_COUNT] Processing job: $JOB_ID${NC}"

    # Delete results if requested
    if [[ "$DELETE_RESULTS" == true ]]; then
        if [[ "$DRY_RUN" == true ]]; then
            echo "  [DRY RUN] Would delete results for job $JOB_ID"
            SKIPPED_RESULTS=$((SKIPPED_RESULTS + 1))
        else
            echo "  Deleting results..."
            if cloudos job results --profile "$PROFILE" --job-id "$JOB_ID" --delete --yes > /dev/null 2>&1; then
                echo -e "  ${GREEN}✓ Results deleted successfully${NC}"
                SUCCESS_RESULTS=$((SUCCESS_RESULTS + 1))
            else
                echo -e "  ${YELLOW}⚠ Failed to delete results (may not exist or already deleted)${NC}"
                FAILED_RESULTS=$((FAILED_RESULTS + 1))
            fi
        fi
    fi

    # Delete workdir if requested
    if [[ "$DELETE_WORKDIR" == true ]]; then
        if [[ "$DRY_RUN" == true ]]; then
            echo "  [DRY RUN] Would delete workdir for job $JOB_ID"
            SKIPPED_WORKDIR=$((SKIPPED_WORKDIR + 1))
        else
            echo "  Deleting workdir..."
            if cloudos job workdir --profile "$PROFILE" --job-id "$JOB_ID" --delete --yes > /dev/null 2>&1; then
                echo -e "  ${GREEN}✓ Workdir deleted successfully${NC}"
                SUCCESS_WORKDIR=$((SUCCESS_WORKDIR + 1))
            else
                echo -e "  ${YELLOW}⚠ Failed to delete workdir (may not exist or already deleted)${NC}"
                FAILED_WORKDIR=$((FAILED_WORKDIR + 1))
            fi
        fi
    fi

    echo ""
done < "$TEMP_FILE"

# Display summary
echo -e "${GREEN}=== Summary ===${NC}"
echo "Total jobs processed: $JOB_COUNT"
echo ""

if [[ "$DELETE_RESULTS" == true ]]; then
    echo "Results deletion:"
    if [[ "$DRY_RUN" == true ]]; then
        echo "  Would delete: $SKIPPED_RESULTS"
    else
        echo "  Successful: $SUCCESS_RESULTS"
        echo "  Failed/Skipped: $FAILED_RESULTS"
    fi
fi

if [[ "$DELETE_WORKDIR" == true ]]; then
    echo "Workdir deletion:"
    if [[ "$DRY_RUN" == true ]]; then
        echo "  Would delete: $SKIPPED_WORKDIR"
    else
        echo "  Successful: $SUCCESS_WORKDIR"
        echo "  Failed/Skipped: $FAILED_WORKDIR"
    fi
fi

# Clean up
rm -f joblist.csv

echo ""
echo -e "${GREEN}Done!${NC}"

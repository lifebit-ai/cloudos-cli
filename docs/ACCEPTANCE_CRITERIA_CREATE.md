# Interactive Session Create - Acceptance Criteria

## Basic Session Type Creation

<details>
<summary>Scenario 1: Successfully create a new Jupyter IA session</summary>

```bash
cloudos interactive-session create --session-type jupyter --name test_jupyter
```

**Verify output includes:**
- Session ID
- Current status (scheduled or initialising)
- Backend type (Jupyter)
- Confirmation of successful creation

</details>

<details>
<summary>Scenario 2: Successfully create a new VSCode IA session</summary>

```bash
cloudos interactive-session create --session-type vscode --name test_vs
```

**Verify output includes:**
- Session ID
- Current status (scheduled or initialising)
- Backend type (VSCode)
- Confirmation of successful creation

</details>

<details>
<summary>Scenario 3: Successfully create a new RStudio IA session</summary>

```bash
cloudos interactive-session create --session-type rstudio --name test_rstudio
```

**Verify output includes:**
- Session ID
- Current status (scheduled or initialising)
- Backend type (RStudio)
- Confirmation of successful creation

</details>

<details>
<summary>Scenario 4: Successfully create a new Spark IA session</summary>

```bash
cloudos interactive-session create --session-type spark --name test_spark
```

**Verify output includes:**
- Session ID
- Current status (scheduled or initialising)
- Backend type (Spark)
- Confirmation of successful creation

</details>

## Session Configuration Options

<details>
<summary>Scenario 5: Create a new IA session with custom instance type</summary>

```bash
cloudos interactive-session create --session-type jupyter --name test_instance --instance c5.2xlarge
```

**Verify output includes:**
- Session ID
- Instance type reflects specified configuration (c5.2xlarge)
- Confirmation of successful creation with custom instance

</details>

<details>
<summary>Scenario 6: Create a new IA session with custom storage size</summary>

```bash
cloudos interactive-session create --session-type jupyter --name test_storage --storage 1000
```

**Verify output includes:**
- Session ID
- Storage allocation reflects specified size (1000 GB)
- Confirmation of successful creation with custom storage

</details>

<details>
<summary>Scenario 7: Create a new IA session with spot instance flag</summary>

```bash
cloudos interactive-session create --session-type jupyter --name test_spot --spot
```

**Verify output includes:**
- Session ID
- Spot instance flag enabled
- Confirmation of successful creation with spot instance enabled

</details>

<details>
<summary>Scenario 8: Create a new IA session with shutdown timeout</summary>

```bash
cloudos interactive-session create --session-type jupyter --name test_time --shutdown-in 10m
```

**Verify output includes:**
- Session ID
- Shutdown configuration set to 10 minutes
- Confirmation of successful creation with timeout configured

</details>

<details>
<summary>Scenario 9: Create a new IA session with cost limit</summary>

```bash
cloudos interactive-session create --session-type jupyter --name test_cost --cost-limit 0.05
```

**Verify output includes:**
- Session ID
- Cost limit configured to $0.05
- Confirmation of successful creation with cost limit set

</details>

<details>
<summary>Scenario 10: Create a new IA session with shared flag</summary>

```bash
cloudos interactive-session create --session-type jupyter --name test_public --shared
```

**Verify output includes:**
- Session ID
- Shared/workspace visibility enabled
- Confirmation of successful creation with shared flag enabled

</details>

## Backend-Specific Configuration

<details>
<summary>Scenario 11: Create a new RStudio IA session with specific R version</summary>

```bash
cloudos interactive-session create --session-type rstudio --name test_rstudio --r-version 4.4.2
```

**Verify output includes:**
- Session ID
- Backend type (RStudio)
- R version set to 4.4.2
- Confirmation of successful creation with custom R version

</details>

<details>
<summary>Scenario 12: Create a new Spark IA session with custom master and worker configuration</summary>

```bash
cloudos interactive-session create --session-type spark --name test_spark --spark-master c5.xlarge --spark-workers 2 --spark-core c5.xlarge
```

**Verify output includes:**
- Session ID
- Master node instance type (c5.xlarge)
- Worker count (2)
- Core node instance type (c5.xlarge)
- Confirmation of successful creation with custom Spark configuration

</details>

## Data Mounting and Linking

<details>
<summary>Scenario 13: Create a new IA session with linked file explorer data</summary>

```bash
cloudos interactive-session create --session-type jupyter --name test_link_fe --link leila-test/AnalysesResults/JG_1shard_chr15-68f210f9e2fdcb612f8e6fe8/results/pipeline_info
```

**Verify output includes:**
- Session ID
- Data link configured for file explorer path
- Confirmation of successful creation with data linked
- Data should be accessible within the session

</details>

<details>
<summary>Scenario 14: Create a new IA session with linked S3 data</summary>

```bash
cloudos interactive-session create --session-type jupyter --name test_link_s3 --link s3://lifebit-featured-datasets/pipelines/phewas/example-data/
```

**Verify output includes:**
- Session ID
- Data link configured for S3 bucket
- Confirmation of successful creation with S3 data linked
- Data should be accessible within the session

</details>

<details>
<summary>Scenario 15: Create a new IA session with mounted S3 data</summary>

```bash
cloudos interactive-session create --session-type jupyter --name test_mount_s3 --mount s3://lifebit-featured-datasets/pipelines/phewas/100_binary_pheno.phe
```

**Verify output includes:**
- Session ID
- S3 mount configured
- Confirmation of successful creation with S3 data mounted
- Data should be mounted and accessible within the session

</details>

<details>
<summary>Scenario 16: Create a new IA session with mounted file explorer data</summary>

```bash
cloudos interactive-session create --session-type jupyter --name test_mount_fe --mount leila-test/Data/benchmark_test.txt
```

**Verify output includes:**
- Session ID
- File explorer mount configured
- Confirmation of successful creation with file explorer data mounted
- Data should be mounted and accessible within the session

</details>

## Error Handling

<details>
<summary>Scenario 17: Attempt to create a session with an unsupported session type</summary>

```bash
cloudos interactive-session create --session-type invalid_type --name test_invalid
```

**Verify output includes:**
- Error message indicating invalid session type
- List of supported session types (jupyter, vscode, rstudio, spark)
- No session is created

</details>

<details>
<summary>Scenario 18: Attempt to create a session with invalid credentials</summary>

```bash
cloudos interactive-session create --session-type jupyter --name test_auth --apikey invalid_key --cloudos-url https://test.com
```

**Verify output includes:**
- Authentication error message
- "Please check your credentials" or similar helpful message
- No session is created

</details>

<details>
<summary>Scenario 19: Attempt to create a session with missing required parameters</summary>

```bash
cloudos interactive-session create --session-type jupyter
```

**Verify output includes:**
- Error message about missing required parameters (session name)
- Help text showing required parameters
- No session is created

</details>

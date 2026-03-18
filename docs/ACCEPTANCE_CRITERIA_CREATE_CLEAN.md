<details>
<summary>Scenario 1: Successfully create a new Jupyter IA session</summary>

```bash
cloudos interactive-session create --session-type jupyter --name test_jupyter
```

</details>

<details>
<summary>Scenario 2: Successfully create a new VSCode IA session</summary>

```bash
cloudos interactive-session create --session-type vscode --name test_vs
```

</details>

<details>
<summary>Scenario 3: Successfully create a new RStudio IA session</summary>

```bash
cloudos interactive-session create --session-type rstudio --name test_rstudio
```

</details>

<details>
<summary>Scenario 4: Successfully create a new Spark IA session</summary>

```bash
cloudos interactive-session create --session-type spark --name test_spark
```

</details>

<details>
<summary>Scenario 5: Create a new IA session with custom instance type</summary>

```bash
cloudos interactive-session create --session-type jupyter --name test_instance --instance c5.2xlarge
```

</details>

<details>
<summary>Scenario 6: Create a new IA session with custom storage size</summary>

```bash
cloudos interactive-session create --session-type jupyter --name test_storage --storage 1000
```

</details>

<details>
<summary>Scenario 7: Create a new IA session with spot instance flag</summary>

```bash
cloudos interactive-session create --session-type jupyter --name test_spot --spot
```

</details>

<details>
<summary>Scenario 8: Create a new IA session with shutdown timeout</summary>

```bash
cloudos interactive-session create --session-type jupyter --name test_time --shutdown-in 10m
```

</details>

<details>
<summary>Scenario 9: Create a new IA session with cost limit</summary>

```bash
cloudos interactive-session create --session-type jupyter --name test_cost --cost-limit 0.05
```

</details>

<details>
<summary>Scenario 10: Create a new IA session with shared flag</summary>

```bash
cloudos interactive-session create --session-type jupyter --name test_public --shared
```

</details>

<details>
<summary>Scenario 11: Create a new RStudio IA session with specific R version</summary>

```bash
cloudos interactive-session create --session-type rstudio --name test_rstudio --r-version 4.4.2
```

</details>

<details>
<summary>Scenario 12: Create a new Spark IA session with custom master and worker configuration</summary>

```bash
cloudos interactive-session create --session-type spark --name test_spark --spark-master c5.xlarge --spark-workers 2 --spark-core c5.xlarge
```

</details>

<details>
<summary>Scenario 13: Create a new IA session with linked file explorer data</summary>

```bash
cloudos interactive-session create --session-type jupyter --name test_link_fe --link leila-test/AnalysesResults/JG_1shard_chr15-68f210f9e2fdcb612f8e6fe8/results/pipeline_info
```

</details>

<details>
<summary>Scenario 14: Create a new IA session with linked S3 data</summary>

```bash
cloudos interactive-session create --session-type jupyter --name test_link_s3 --link s3://lifebit-featured-datasets/pipelines/phewas/example-data/
```

</details>

<details>
<summary>Scenario 15: Create a new IA session with mounted S3 data</summary>

```bash
cloudos interactive-session create --session-type jupyter --name test_mount_s3 --mount s3://lifebit-featured-datasets/pipelines/phewas/100_binary_pheno.phe
```

</details>

<details>
<summary>Scenario 16: Create a new IA session with mounted file explorer data</summary>

```bash
cloudos interactive-session create --session-type jupyter --name test_mount_fe --mount leila-test/Data/benchmark_test.txt
```

</details>

<details>
<summary>Scenario 17: Attempt to create a session with an unsupported session type</summary>

```bash
cloudos interactive-session create --session-type invalid_type --name test_invalid
```

</details>

<details>
<summary>Scenario 18: Attempt to create a session with invalid credentials</summary>

```bash
cloudos interactive-session create --session-type jupyter --name test_auth --apikey invalid_key --cloudos-url https://test.com
```

</details>

<details>
<summary>Scenario 19: Attempt to create a session with missing required parameters</summary>

```bash
cloudos interactive-session create --session-type jupyter
```

</details>

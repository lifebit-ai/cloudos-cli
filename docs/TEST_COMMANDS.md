# Test Commands - Interactive Session Create

cloudos interactive-session create --session-type jupyter --name test_jupyter
cloudos interactive-session create --session-type vscode --name test_vs
cloudos interactive-session create --session-type rstudio --name test_rstudio
cloudos interactive-session create --session-type spark --name test_spark
cloudos interactive-session create --session-type jupyter --name test_instance --instance c5.2xlarge
cloudos interactive-session create --session-type jupyter --name test_storage --storage 1000
cloudos interactive-session create --session-type jupyter --name test_spot --spot
cloudos interactive-session create --session-type jupyter --name test_time --shutdown-in 10m
cloudos interactive-session create --session-type jupyter --name test_cost --cost-limit 0.05
cloudos interactive-session create --session-type jupyter --name test_public --shared
cloudos interactive-session create --session-type rstudio --name test_rstudio --r-version 4.4.2
cloudos interactive-session create --session-type spark --name test_spark --spark-master c5.xlarge --spark-workers 2 --spark-core c5.xlarge
cloudos interactive-session create --session-type jupyter --name test_link_fe --link leila-test/AnalysesResults/JG_1shard_chr15-68f210f9e2fdcb612f8e6fe8/results/pipeline_info
cloudos interactive-session create --session-type jupyter --name test_link_s3 --link s3://lifebit-featured-datasets/pipelines/phewas/example-data/
cloudos interactive-session create --session-type jupyter --name test_mount_s3 --mount s3://lifebit-featured-datasets/pipelines/phewas/100_binary_pheno.phe
cloudos interactive-session create --session-type jupyter --name test_mount_fe --mount leila-test/Data/benchmark_test.txt
cloudos interactive-session create --session-type invalid_type --name test_invalid
cloudos interactive-session create --session-type jupyter --name test_auth --apikey invalid_key --cloudos-url https://test.com
cloudos interactive-session create --session-type jupyter

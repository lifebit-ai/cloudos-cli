# Interactive Session Create - Acceptance Criteria (Gherkin Format)

## Scenario 1: Successfully create a new Jupyter IA session

Given a user has valid cloudos-cli credentials and access to the Lifebit Platform

When the user runs the cloudos-cli command to create a new IA session specifying Jupyter as the session type

Then a new Jupyter IA session is launched successfully

And the session ID and its current status are returned in the command output

---

## Scenario 2: Successfully create a new VSCode IA session

Given a user has valid cloudos-cli credentials and access to the Lifebit Platform

When the user runs the cloudos-cli command to create a new IA session specifying VSCode as the session type

Then a new VSCode IA session is launched successfully

And the session ID and its current status are returned in the command output

---

## Scenario 3: Successfully create a new RStudio IA session

Given a user has valid cloudos-cli credentials and access to the Lifebit Platform

When the user runs the cloudos-cli command to create a new IA session specifying RStudio as the session type

Then a new RStudio IA session is launched successfully

And the session ID and its current status are returned in the command output

---

## Scenario 4: Successfully create a new Spark IA session

Given a user has valid cloudos-cli credentials and access to the Lifebit Platform

When the user runs the cloudos-cli command to create a new IA session specifying Spark as the session type

Then a new Spark IA session is launched successfully

And the session ID and its current status are returned in the command output

---

## Scenario 5: Create a new IA session with custom instance type

Given a user has valid cloudos-cli credentials and access to the Lifebit Platform

When the user runs the create session command specifying an instance type (e.g., c5.2xlarge)

Then the IA session is launched with the specified instance type

And the instance configuration is reflected in the command output

---

## Scenario 6: Create a new IA session with custom storage size

Given a user has valid cloudos-cli credentials and access to the Lifebit Platform

When the user runs the create session command specifying a storage size (e.g., 1000 GB)

Then the IA session is launched with the specified storage allocation

And the storage configuration is reflected in the command output

---

## Scenario 7: Create a new IA session with spot instance flag

Given a user has valid cloudos-cli credentials and access to the Lifebit Platform

When the user runs the create session command with the spot instance flag enabled

Then the IA session is launched using spot instances

And the spot instance configuration is reflected in the command output

---

## Scenario 8: Create a new IA session with shutdown timeout

Given a user has valid cloudos-cli credentials and access to the Lifebit Platform

When the user runs the create session command specifying a shutdown timeout (e.g., 10 minutes)

Then the IA session is launched with the specified shutdown timeout configured

And the session will automatically shut down after the specified time period

---

## Scenario 9: Create a new IA session with cost limit

Given a user has valid cloudos-cli credentials and access to the Lifebit Platform

When the user runs the create session command specifying a cost limit (e.g., $0.05)

Then the IA session is launched with the cost limit configured

And the session will stop if the cost limit is exceeded

---

## Scenario 10: Create a new IA session with shared flag

Given a user has valid cloudos-cli credentials and access to the Lifebit Platform

When the user runs the create session command with the shared flag enabled

Then the IA session is launched with workspace visibility enabled

And other workspace members can access the session

---

## Scenario 11: Create a new RStudio IA session with specific R version

Given a user has valid cloudos-cli credentials and access to the Lifebit Platform

When the user runs the create session command specifying RStudio as the backend with a specific R version (e.g., 4.4.2)

Then the RStudio IA session is launched with the specified R version

And the R version is reflected in the command output and session details

---

## Scenario 12: Create a new Spark IA session with custom master and worker configuration

Given a user has valid cloudos-cli credentials and access to the Lifebit Platform

When the user runs the create session command specifying Spark as the backend with custom master and worker instance types and worker count

Then the Spark IA session is launched with the specified Spark cluster configuration

And the master, core, and worker node types are reflected in the command output

---

## Scenario 13: Create a new IA session with linked file explorer data

Given a user has valid cloudos-cli credentials and data assets are available on the platform

When the user runs the create session command specifying a file explorer path to link

Then the IA session is launched with the data asset linked from file explorer

And the data is accessible within the newly launched IA session

---

## Scenario 14: Create a new IA session with linked S3 data

Given a user has valid cloudos-cli credentials and data assets are available in S3

When the user runs the create session command specifying an S3 path to link

Then the IA session is launched with the S3 data linked

And the data is accessible within the newly launched IA session

---

## Scenario 15: Create a new IA session with mounted S3 data

Given a user has valid cloudos-cli credentials and data assets are available in S3

When the user runs the create session command specifying an S3 path to mount

Then the IA session is launched with the S3 data mounted

And the data is accessible within the newly launched IA session

---

## Scenario 16: Create a new IA session with mounted file explorer data

Given a user has valid cloudos-cli credentials and data assets are available on the platform

When the user runs the create session command specifying a file explorer path to mount

Then the IA session is launched with the data asset mounted from file explorer

And the data is accessible within the newly launched IA session

---

## Scenario 17: Attempt to create a session with an unsupported session type

Given a user has valid cloudos-cli credentials

When the user runs the create session command with an unsupported session type

Then an error message is returned indicating the valid session types (jupyter, vscode, rstudio, spark)

And no session is created

---

## Scenario 18: Attempt to create a session with invalid credentials

Given a user attempts to use cloudos-cli with invalid credentials

When the user runs the create session command

Then an authentication error message is returned

And no session is created

---

## Scenario 19: Attempt to create a session with missing required parameters

Given a user has valid cloudos-cli credentials

When the user runs the create session command without specifying required parameters (e.g., session name)

Then an error message is returned indicating the missing required parameters

And no session is created

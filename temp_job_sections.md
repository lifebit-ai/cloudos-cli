# Temporary file for reorganizing job sections

## Logical order we want:
1. Submit a Job (line 472)
2. Check Job Status (line 765) 
3. List Jobs (line 918)
4. Get Job Details (line 782)
5. Get Job Logs (line 592)
6. Get Job Results (line 617)
7. Get Job Workdir (line 854)
8. Get Job Costs (line 1106)
9. Get Job Related Analyses (line 1253)
10. Clone or Resume Job (line 672)
11. Abort Jobs (line 751)
12. Delete Job Results (line 1361)

## Section boundaries:
- Submit a Job: 472 -> 591 (before Get Job Logs)
- Get Job Logs: 592 -> 616 (before Get Job Results)  
- Get Job Results: 617 -> 671 (before Clone or Resume Job)
- Clone or Resume Job: 672 -> 750 (before Abort Jobs)
- Abort Jobs: 751 -> 764 (before Check Job Status)
- Check Job Status: 765 -> 781 (before Get Job Details)
- Get Job Details: 782 -> 853 (before Get Job Workdir)
- Get Job Workdir: 854 -> 917 (before List Jobs)
- List Jobs: 918 -> 1105 (before Get Job Costs)
- Get Job Costs: 1106 -> 1252 (before Get Job Related Analyses)
- Get Job Related Analyses: 1253 -> 1360 (before Delete Job Results)
- Delete Job Results: 1361 -> 1436 (before Bash Jobs)
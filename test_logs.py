from cloudos_cli.clos import Cloudos

print("Azure job logs")
cl = Cloudos(
    "https://dev.sdlc.lifebit.ai",
    "684ac0474b0f858a350066e7:wGLDQGpg4XFTOOER8DPPy0oo58VGuvWLre4Dey61",
    None,
)
azure_jobs = cl.get_job_logs("6846bed4dcefb8dc983349a1", "6480f3db916489d248956a5f")
print(azure_jobs)
print("AWS job logs")
cl1 = Cloudos(
    "https://cloudos.lifebit.ai",
    "6849518bcd5396cf0d3164dc:VqMqQ58ATcydCDruFMYcvFOCjX8ROwiOgswWw8VW",
    None,
)
aws_job = cl1.get_job_logs("684302047fa0203cbcff45cb", "5c6d3e9bd954e800b23f8c62")
print(aws_job)

from cloudos_cli.clos import Cloudos

print("Azure job results")
azure_jobs = cl.get_job_results("6846bed4dcefb8dc983349a1", "6480f3db916489d248956a5f")
print(azure_jobs)
print("AWS job results")
aws_job = cl1.get_job_results("684302047fa0203cbcff45cb", "5c6d3e9bd954e800b23f8c62")
print(aws_job)

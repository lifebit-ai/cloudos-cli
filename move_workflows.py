from cloudos_cli.import_wf import ImportWorflow
import yaml
import subprocess
from pathlib import Path
from shlex import split as cmd
apikey = "68747b049e7fe38ec6e0204a:QMq2zB91JHw9M5CUWGAQYqfTr2bvyKcOP0u062oL"
clos_url = "https://cloudos.lifebit.ai"
ws = "6863d338fa98499e1e2a1c85"

gits = [
    # ("git@github.com:lifebit-ai/lifebit-platform-liftover-nf.git","https://github.com/lifebit-ai/lifebit-platform-liftover-nf"),
    # ("git@github.com:lifebit-ai/lifebit-platform-genomic-data-qc.git", "https://github.com/lifebit-ai/lifebit-platform-genomic-data-qc"),
    # ("git@github.com:lifebit-ai/gwas-sumstats-imputation-nf.git", "https://github.com/lifebit-ai/gwas-sumstats-imputation-nf"),
    # ("git@github.com:lifebit-ai/lifebit-platform-burden-testing-helper.git", "https://github.com/lifebit-ai/lifebit-platform-burden-testing-helper"),
    # ("git@github.com:lifebit-ai/alternative-splicing-nf.git", "https://github.com/lifebit-ai/alternative-splicing-nf"),
    # ("git@github.com:lifebit-ai/variant-classification-nf.git", "https://github.com/lifebit-ai/variant-classification-nf"),
    # ("git@github.com:lifebit-ai/generate-in-sample-references-nf.git", "https://github.com/lifebit-ai/generate-in-sample-references-nf"),
    # ("git@github.com:lifebit-ai/variant-imputing-nf.git", "https://github.com/lifebit-ai/variant-imputing-nf"),
    # ("git@github.com:lifebit-ai/ancestry-inference-nf.git", "https://github.com/lifebit-ai/ancestry-inference-nf"),
    # ("git@github.com:lifebit-ai/lifebit-platform-exomiser-nf.git", "https://github.com/lifebit-ai/lifebit-platform-exomiser-nf"),
    # ("git@github.com:lifebit-ai/vcf-benchmarking-nf.git", "https://github.com/lifebit-ai/vcf-benchmarking-nf"),
    # ("git@github.com:lifebit-ai/omics-etl-somatic-variant-gen-nf.git", "https://github.com/lifebit-ai/omics-etl-somatic-variant-gen-nf"),
    # ("git@github.com:lifebit-ai/trio-joint-calling-analysis.git", "https://github.com/lifebit-ai/trio-joint-calling-analysis"),
    # ("git@github.com:lifebit-ai/joint-genotyping-nf.git", "https://github.com/lifebit-ai/joint-genotyping-nf"),
    # ("git@github.com:lifebit-ai/omics-etl-variant-files-gen-nf.git", "https://github.com/lifebit-ai/omics-etl-variant-files-gen-nf"),
    # ("git@github.com:lifebit-ai/pharmcat-nf.git", "https://github.com/lifebit-ai/pharmcat-nf"),
    # ("git@github.com:lifebit-ai/lifebit-platform-prs-nf.git", "https://github.com/lifebit-ai/lifebit-platform-prs-nf"),
    # ("git@github.com:lifebit-ai/omop-to-vep-protocol-orchestrator-nf.git", "https://github.com/lifebit-ai/omop-to-vep-protocol-orchestrator-nf"),
    # ("git@github.com:lifebit-ai/lifebit-platform-phewas-nf.git", "https://github.com/lifebit-ai/lifebit-platform-phewas-nf"),
    # ("git@github.com:lifebit-ai/rnaseq-workflow-nf.git", "https://github.com/lifebit-ai/rnaseq-workflow-nf"),
    # ("git@github.com:lifebit-ai/lifebit-platform-genetic-heritability-and-correlation-nf.git", "https://github.com/lifebit-ai/lifebit-platform-genetic-heritability-and-correlation-nf"),
    ("git@github.com:lifebit-ai/lifebit-platform-burden-testing.git", "https://github.com/lifebit-ai/lifebit-platform-burden-testing"),
    ("git@github.com:lifebit-ai/post-gwas-target-identification.git", "https://github.com/lifebit-ai/post-gwas-target-identification"),
    ("git@github.com:lifebit-ai/lifebit-platform-trans-ancestry-meta-analysis.git", "https://github.com/lifebit-ai/lifebit-platform-trans-ancestry-meta-analysis")
]

def download_repo(git, url):
    git_dir_name = Path(f"pipelines/{Path(git).stem}")
    if not git_dir_name.exists():
        subprocess.run(cmd(f"git clone {git} {git_dir_name}"))
    return git_dir_name, url

def parse_name(path, url):
    ci_loc = path / ".github/workflows/internal_lifebit_cloudos_ci.yml"
    if not ci_loc.exists():
        ci_loc = Path(str(ci_loc).replace(".yml", ".yaml"))
    with ci_loc.open() as o:
        parsed_ci = yaml.safe_load(o)
    return parsed_ci, url

names_wf = dict()
for repo, url in gits:
    ci_path, url = download_repo(repo, url)
    d, url = parse_name(ci_path, url)
    for job_data in d["jobs"].values():
        if "steps" in job_data:
            for step in job_data["steps"]:
                if "with" in step:
                    wf_name = step["with"]["workflow_name"]
                    if url not in names_wf:
                        names_wf[url] = wf_name
                    elif wf_name not in names_wf[url]:
                        names_wf[url] = wf_name

for url, name in names_wf.items():
    wf_import = ImportWorflow(
        cloudos_url=clos_url,
        cloudos_apikey=apikey,
        workspace_id=ws,
        platform="github",
        workflow_name=name,
        workflow_url=url
    )
    print(f"Importing {name}")
    wf_import.import_workflow()
    print(f"{name} imported")

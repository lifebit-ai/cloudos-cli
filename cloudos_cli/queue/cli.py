"""CLI commands for Lifebit Platform job queue management."""

import sys
import rich_click as click
import json
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from cloudos_cli.queue.queue import (
    Queue,
    QUEUE_PRESETS,
    PROVISIONING_TYPES,
    ALLOCATION_STRATEGIES,
    VOLUME_SPECS,
    MAX_VCPUS_LIMIT,
    DEFAULT_MAX_VCPUS,
    DEFAULT_MIN_VCPUS,
    MAX_COMPUTE_ENVS,
    CE_LIMIT_REACHED_MESSAGE,
    MAX_WORKSPACE_COMPUTE_ENVS,
    WORKSPACE_CE_LIMIT_REACHED_MESSAGE,
    _ALL_INSTANCE_TYPES,
)
from cloudos_cli.utils.resources import ssl_selector
from cloudos_cli.configure.configure import with_profile_config, CLOUDOS_URL
from cloudos_cli.utils.cli_helpers import pass_debug_to_subcommands
from cloudos_cli.utils.details import create_queue_list_table


# Union of all allocation strategies, used for the CLI option choices.
_ALL_ALLOCATION_STRATEGIES = ["BEST_FIT", "BEST_FIT_PROGRESSIVE", "SPOT_CAPACITY_OPTIMIZED"]

# Workflow executors supported for job queues.
_EXECUTORS = ["nextflow", "cromwell"]

# Default volume parameters for the non-interactive --from-scratch flags. These
# mirror the gp3 spec (the default volume type) in VOLUME_SPECS so the CLI
# defaults never drift from the validated specification.
_DEFAULT_SIZE = VOLUME_SPECS["gp3"]["size"][0]
_DEFAULT_IOPS = VOLUME_SPECS["gp3"]["iops"][0]
_DEFAULT_THROUGHPUT = VOLUME_SPECS["gp3"]["throughput"][0]

# ---------------------------------------------------------------------------
# Wizard styling helpers
# ---------------------------------------------------------------------------

# Colour theme for the interactive --from-scratch wizard.
_C_ACCENT = "cyan"
_C_STEP = "bold cyan"
_C_TITLE = "bold white"
_C_OPTION = "bold green"
_C_DESC = "grey62"
_C_HINT = "grey50"


def _print_section(console, step, total, title, subtitle=None, options=None, hint=None):
    """Print a styled wizard section: step badge, title, options and hint.

    Parameters
    ----------
    console : rich.console.Console
        The console used for rich output.
    step : int
        The current step number.
    total : int
        The total number of steps.
    title : str
        The section title.
    subtitle : str or None, optional
        A short clarifying line shown under the title.
    options : list[tuple[str, str]] or None, optional
        A list of ``(name, description)`` pairs. Names are highlighted and
        descriptions shown in a dimmed (grey) style, both indented.
    hint : str or None, optional
        A short hint (e.g. allowed range / default) shown just above the prompt.
    """
    console.print()
    console.rule(
        f"[{_C_STEP}]Step {step}/{total}[/{_C_STEP}]  [{_C_TITLE}]{title}[/{_C_TITLE}]",
        align="left",
        characters="─",
        style=_C_ACCENT,
    )
    if subtitle:
        console.print(f"  [{_C_DESC}]{subtitle}[/{_C_DESC}]")
    if options:
        console.print()
        for name, description in options:
            console.print(f"    [{_C_OPTION}]●[/{_C_OPTION}] [{_C_OPTION}]{name}[/{_C_OPTION}]")
            console.print(f"      [{_C_DESC}]{description}[/{_C_DESC}]")
    if hint:
        console.print()
        console.print(f"  [{_C_HINT}]{hint}[/{_C_HINT}]")
    console.print()


def _styled_prompt(label, **kwargs):
    """Issue a ``click.prompt`` with a consistent, coloured prompt line.

    Parameters
    ----------
    label : str
        The prompt label (without the leading arrow).
    **kwargs
        Forwarded to ``click.prompt`` (e.g. ``type``, ``default``).

    Returns
    -------
    The value returned by ``click.prompt``.
    """
    arrow = click.style("  ❯ ", fg="cyan", bold=True)
    text = arrow + click.style(label, fg="white", bold=True)
    return click.prompt(text, **kwargs)


def _from_scratch_wizard(console, for_compute_env=False, queue_label=None):
    """Interactively collect custom queue parameters, emulating the UI flow.

    Parameters
    ----------
    console : rich.console.Console
        The console used for rich output.
    for_compute_env : bool, optional
        When True, the wizard collects a compute environment to add to an
        existing queue (step 1 asks for the compute environment name) rather
        than a brand new queue.
    queue_label : str or None, optional
        The label of the target queue, shown in the intro when
        ``for_compute_env`` is True.

    Returns
    -------
    params : dict
        A dict with keys: ``label``, ``provisioning_type``,
        ``allocation_strategy``, ``max_vcpus``, ``min_vcpus``,
        ``instance_types``, ``volume_type``, ``size``, ``iops`` and
        ``throughput``. When ``for_compute_env`` is True, ``label`` holds the
        compute environment name.
    """
    total = 9
    console.print()
    if for_compute_env:
        intro = (
            "[bold cyan]Add a compute environment to a job queue[/bold cyan]\n"
            f"[grey62]Target queue: [white]{queue_label}[/white]. Answer the "
            "prompts below to configure the new compute environment.[/grey62]"
        )
    else:
        intro = (
            "[bold cyan]Create a job queue from scratch[/bold cyan]\n"
            "[grey62]Answer the prompts below to configure your custom "
            "compute environment.[/grey62]"
        )
    console.print(
        Panel.fit(intro, border_style="cyan", padding=(1, 4))
    )

    # 1. Name
    if for_compute_env:
        _print_section(
            console, 1, total, "Name",
            subtitle="A human-readable name for the new compute environment.",
        )
        label = _styled_prompt("Name of the compute environment", type=str)
    else:
        _print_section(
            console, 1, total, "Name",
            subtitle="A human-readable name for your job queue.",
        )
        label = _styled_prompt("Name of the queue", type=str)

    # 2. Provisioning type
    _print_section(
        console, 2, total, "Provisioning type",
        subtitle="Choose how your compute instances are provisioned.",
        options=[
            ("On demand",
             "EC2 usage and provisioned storage for EBS volumes are billed on "
             "one second increments, with a minimum of 60 seconds."),
            ("Spot",
             "Save money by using Spot instances but your instances can be "
             "interrupted with a two minute notification when EC2 needs the "
             "capacity back."),
        ],
    )
    provisioning_type = _styled_prompt(
        "Provisioning type",
        type=click.Choice(list(PROVISIONING_TYPES.keys()), case_sensitive=False),
        default="on-demand",
    )

    # 3. Allocation strategy
    allowed_strategies = ALLOCATION_STRATEGIES[provisioning_type]
    _print_section(
        console, 3, total, "Allocation strategy",
        subtitle="Choose how batch launches instances on your behalf.",
        hint="We recommend Best Fit Progressive for On-Demand CEs and "
             "Spot Capacity Optimised for Spot CEs.",
    )
    allocation_strategy = _styled_prompt(
        "Allocation strategy",
        type=click.Choice(allowed_strategies, case_sensitive=False),
        default="BEST_FIT_PROGRESSIVE",
    )

    # 4. Max vCPUs
    _print_section(
        console, 4, total, "Max vCPUs",
        subtitle="Maximum number of vCPUs the queue can scale up to.",
        hint=f"Max {MAX_VCPUS_LIMIT}. Default {DEFAULT_MAX_VCPUS}.",
    )
    max_vcpus = _styled_prompt(
        "Max vCPUs",
        type=click.IntRange(0, MAX_VCPUS_LIMIT),
        default=DEFAULT_MAX_VCPUS,
    )

    # 5. Min vCPUs
    _print_section(
        console, 5, total, "Min vCPUs",
        subtitle="Minimum number of vCPUs kept running (optional).",
        hint="Default 0.",
    )
    min_vcpus = _styled_prompt(
        "Min vCPUs",
        type=click.IntRange(0, MAX_VCPUS_LIMIT),
        default=DEFAULT_MIN_VCPUS,
    )

    # 6. Instance types
    _print_section(
        console, 6, total, "Instance types",
        subtitle="Optimal or a combination of instances.",
        hint="Enter 'optimal' or a comma-separated list of instance types "
             "from the standard (c5, r5, m5, c4, r4, m4) or GPU (p3, g4dn) "
             "families.",
    )
    instance_types = _prompt_instance_types(console)

    # 7. Volume type
    _print_section(
        console, 7, total, "Volume type",
        subtitle="Select your preferred volume type.",
        options=[
            ("General Purpose SSD (gp3)",
             "Balanced price and performance for a wide variety of workloads."),
            ("Provisioned IOPS SSD (io2)",
             "High-performance SSD for I/O-intensive workloads."),
        ],
    )
    volume_type = _styled_prompt(
        "Volume type",
        type=click.Choice(list(VOLUME_SPECS.keys()), case_sensitive=False),
        default="gp3",
    )
    if volume_type == "io2":
        console.print()
        console.print(
            Panel(
                "[bold yellow]⚠  Warning, high cost disk type.[/bold yellow]\n"
                "[grey62]Read more: "
                "https://lifebit.atlassian.net/wiki/spaces/CD/pages/316506431/"
                "Disk+types[/grey62]",
                border_style="yellow",
                padding=(0, 2),
            )
        )

    spec = VOLUME_SPECS[volume_type]

    # 8. Size (GiB)
    size_default, size_min, size_max = spec["size"]
    _print_section(
        console, 8, total, "Size (GiB)",
        subtitle="Volume size in GiB.",
        hint=f"Min {size_min}, max {size_max}. Default {size_default}.",
    )
    size = _styled_prompt(
        "Size (GiB)",
        type=click.IntRange(size_min, size_max),
        default=size_default,
    )

    # 9. IOPS
    iops_default, iops_min, iops_max = spec["iops"]
    _print_section(
        console, 9, total, "IOPS",
        subtitle="Input/output Operations per Second (IOPS).",
        hint="A high IOPS is needed for jobs with high throughput that need "
             f"many files to be written/read. Min {iops_min}, max {iops_max}. "
             f"Default {iops_default}.",
    )
    iops = _styled_prompt(
        "IOPS",
        type=click.IntRange(iops_min, iops_max),
        default=iops_default,
    )

    # Throughput (gp3 only)
    throughput = None
    if spec["throughput"] is not None:
        tp_default, tp_min, tp_max = spec["throughput"]
        _print_section(
            console, 10, total + 1, "Throughput (MB/s)",
            subtitle="Volume throughput in MB/s.",
            hint=f"Min {tp_min}, max {tp_max}. Default {tp_default}.",
        )
        throughput = _styled_prompt(
            "Throughput (MB/s)",
            type=click.IntRange(tp_min, tp_max),
            default=tp_default,
        )

    params = {
        "label": label,
        "provisioning_type": provisioning_type,
        "allocation_strategy": allocation_strategy,
        "max_vcpus": max_vcpus,
        "min_vcpus": min_vcpus,
        "instance_types": instance_types,
        "volume_type": volume_type,
        "size": size,
        "iops": iops,
        "throughput": throughput,
    }
    _print_summary(console, params, for_compute_env=for_compute_env)
    return params


def _print_summary(console, params, for_compute_env=False):
    """Print a styled summary table of the collected wizard parameters.

    Parameters
    ----------
    console : rich.console.Console
        The console used for rich output.
    params : dict
        The collected from-scratch parameters.
    """
    table = Table(
        title=(
            "[bold cyan]Compute environment configuration summary[/bold cyan]"
            if for_compute_env
            else "[bold cyan]Queue configuration summary[/bold cyan]"
        ),
        show_header=False,
        box=None,
        padding=(0, 2),
    )
    table.add_column(justify="right", style="grey62", no_wrap=True)
    table.add_column(style="white")

    instance_label = ", ".join(params["instance_types"])
    name_label = "Compute environment" if for_compute_env else "Name"
    rows = [
        (name_label, params["label"]),
        ("Provisioning type", params["provisioning_type"]),
        ("Allocation strategy", params["allocation_strategy"]),
        ("Max vCPUs", str(params["max_vcpus"])),
        ("Min vCPUs", str(params["min_vcpus"])),
        ("Instance types", instance_label),
        ("Volume type", params["volume_type"]),
        ("Size (GiB)", str(params["size"])),
        ("IOPS", str(params["iops"])),
    ]
    if params["throughput"] is not None:
        rows.append(("Throughput (MB/s)", str(params["throughput"])))

    for name, value in rows:
        table.add_row(name, value)

    console.print()
    console.print(table)
    console.print()


def _prompt_instance_types(console):
    """Prompt for instance types, validating them against the standard list.

    Parameters
    ----------
    console : rich.console.Console
        The console used for rich output.

    Returns
    -------
    instance_types : list[str]
        The validated list of instance types.
    """
    while True:
        raw = _styled_prompt("Instance types", type=str, default="optimal")
        instance_types = [item.strip() for item in raw.split(",") if item.strip()]
        invalid = [item for item in instance_types if item not in _ALL_INSTANCE_TYPES]
        if not instance_types:
            console.print("[red]Please provide at least one instance type.[/red]")
            continue
        if invalid:
            console.print(
                f"[red]Invalid instance type(s): {', '.join(invalid)}.[/red] "
                "[dim]Allowed values are 'optimal' or standard/GPU instance types.[/dim]"
            )
            continue
        return instance_types


def _parse_instance_types(raw):
    """Parse and validate a comma-separated instance types string.

    Parameters
    ----------
    raw : str
        Comma-separated instance types (e.g. ``'optimal'`` or ``'c5.xlarge,m5.xlarge'``).

    Returns
    -------
    instance_types : list[str]
        The parsed list of instance types.

    Raises
    ------
    click.BadParameter
        If the string is empty or contains unrecognised instance types.
    """
    instance_types = [item.strip() for item in raw.split(",") if item.strip()]
    if not instance_types:
        raise click.BadParameter("At least one instance type is required.")
    invalid = [item for item in instance_types if item not in _ALL_INSTANCE_TYPES]
    if invalid:
        raise click.BadParameter(
            f"Invalid instance type(s): {', '.join(invalid)}. "
            "Allowed values are 'optimal' or standard/GPU instance types."
        )
    return instance_types


def _validate_from_scratch_flags(params):
    """Validate non-interactive ``--from-scratch`` flag values.

    Parameters
    ----------
    params : dict
        A dict with the from-scratch parameters (same keys as produced by
        ``_from_scratch_wizard``).

    Raises
    ------
    click.BadParameter
        If the allocation strategy is incompatible with the provisioning type
        or the volume size/IOPS/throughput fall outside the allowed range.
    """
    provisioning_type = params["provisioning_type"]
    allowed_strategies = ALLOCATION_STRATEGIES[provisioning_type]
    if params["allocation_strategy"] not in allowed_strategies:
        raise click.BadParameter(
            f"Allocation strategy '{params['allocation_strategy']}' is not valid "
            f"for '{provisioning_type}' provisioning. Valid options are: "
            f"{', '.join(allowed_strategies)}."
        )

    if params["min_vcpus"] > params["max_vcpus"]:
        raise click.BadParameter(
            f"--min-vcpus cannot be greater than --max-vcpus (got {params['min_vcpus']} > {params['max_vcpus']})."
        )

    spec = VOLUME_SPECS[params["volume_type"]]
    _check_range("--size", params["size"], spec["size"])
    _check_range("--iops", params["iops"], spec["iops"])
    if spec["throughput"] is not None:
        if params["throughput"] is None:
            params["throughput"] = spec["throughput"][0]
        _check_range("--throughput", params["throughput"], spec["throughput"])
    else:
        params["throughput"] = None


def _check_range(name, value, spec):
    """Validate that ``value`` is within the ``(default, min, max)`` spec.

    Parameters
    ----------
    name : str
        The option name (for error messages).
    value : int
        The value to validate.
    spec : tuple[int, int, int]
        A ``(default, minimum, maximum)`` tuple.

    Raises
    ------
    click.BadParameter
        If ``value`` is outside ``[minimum, maximum]``.
    """
    _, minimum, maximum = spec
    if value < minimum or value > maximum:
        raise click.BadParameter(
            f"{name} must be between {minimum} and {maximum} for the selected "
            f"volume type (got {value})."
        )


def _check_workspace_ce_limit(console, j_queue, queues=None):
    """Exit with a warning if the workspace has reached its CE limit.

    Parameters
    ----------
    console : rich.console.Console
        The console used for rich output.
    j_queue : Queue
        The queue client used to count compute environments.
    queues : list or None, optional
        A pre-fetched list of job queue dicts. If ``None``, the queues are
        fetched.
    """
    count = j_queue.count_workspace_compute_environments(queues=queues)
    if count >= MAX_WORKSPACE_COMPUTE_ENVS:
        console.print(
            f"[yellow]Warning:[/yellow] {WORKSPACE_CE_LIMIT_REACHED_MESSAGE}"
        )
        sys.exit(0)




# Create the queue group
@click.group(cls=pass_debug_to_subcommands())
def queue():
    """Lifebit Platform job queue functionality."""
    print(queue.__doc__ + '\n')


@queue.command('list')
@click.option('-k',
              '--apikey',
              help='Your Lifebit Platform API key',
              required=True)
@click.option('-c',
              '--cloudos-url',
              help=(f'The Lifebit Platform url you are trying to access to. Default={CLOUDOS_URL}.'),
              default=CLOUDOS_URL,
              required=True)
@click.option('--workspace-id',
              help='The specific Lifebit Platform workspace id.',
              required=True)
@click.option('--output-basename',
              help=('Output file base name to save job queue list. ' +
                    'Default=job_queue_list'),
              default='job_queue_list',
              required=False)
@click.option('--output-format',
              help=('Output format for queue list. Options: '
                    'stdout (display as interactive table in terminal), '
                    'csv (save as comma-separated values file), '
                    'json (save as JSON file with full API response). '
                    'Default=stdout.'),
              type=click.Choice(['stdout', 'csv', 'json'], case_sensitive=False),
              default='stdout')
@click.option('--all-fields',
              help=('Whether to collect all available fields from queues or ' +
                    'just the preconfigured selected fields. Only applicable ' +
                    'when --output-format=csv'),
              is_flag=True)
@click.option('--exclude-system-queues',
              help='Exclude system job queues from the list.',
              is_flag=True)
@click.option('--execution-platform',
              help='Name of the execution platform implemented in your Lifebit Platform. Default=aws.',
              type=click.Choice(['aws', 'azure', 'hpc']),
              default='aws')
@click.option('--disable-ssl-verification',
              help=('Disable SSL certificate verification. Please, remember that this option is ' +
                    'not generally recommended for security reasons.'),
              is_flag=True)
@click.option('--ssl-cert',
              help='Path to your SSL certificate file.')
@click.option('--profile', help='Profile to use from the config file', default=None)
@click.pass_context
@with_profile_config(required_params=['apikey', 'workspace_id'])
def list_queues(ctx,
                apikey,
                cloudos_url,
                workspace_id,
                output_basename,
                output_format,
                all_fields,
                exclude_system_queues,
                execution_platform,
                disable_ssl_verification,
                ssl_cert,
                profile):
    """Collect and display all available job queues from a Lifebit Platform workspace."""
    # apikey, cloudos_url, and workspace_id are now automatically resolved by the decorator

    verify_ssl = ssl_selector(disable_ssl_verification, ssl_cert)

    # Batch job queues are an AWS-only feature; they are not available in
    # Azure or HPC workspaces.
    if execution_platform in ('azure', 'hpc'):
        Console().print(
            '[yellow]Warning:[/yellow] Batch job queues are not available in '
            f'{execution_platform.upper()} workspaces.'
        )
        sys.exit(0)

    print('Executing list...')
    j_queue = Queue(cloudos_url, apikey, None, workspace_id, verify=verify_ssl)
    my_queues = j_queue.get_job_queues(exclude_system_queues=exclude_system_queues)
    if len(my_queues) == 0:
        raise ValueError('No AWS batch queues found. Please, make sure that your Lifebit Platform supports AWS batch queues')
    if output_format == 'stdout':
        create_queue_list_table(my_queues, cloudos_url)
    elif output_format == 'csv':
        outfile = output_basename + '.' + output_format
        queues_processed = j_queue.process_queue_list(my_queues, all_fields)
        queues_processed.to_csv(outfile, index=False)
        print(f'\tJob queue list collected with a total of {queues_processed.shape[0]} queues.')
        print(f'\tJob queue list saved to {outfile}')
    elif output_format == 'json':
        outfile = output_basename + '.' + output_format
        with open(outfile, 'w') as o:
            o.write(json.dumps(my_queues))
        print(f'\tJob queue list collected with a total of {len(my_queues)} queues.')
        print(f'\tJob queue list saved to {outfile}')


@queue.command('create')
@click.option('-k',
              '--apikey',
              help='Your Lifebit Platform API key',
              required=True)
@click.option('-c',
              '--cloudos-url',
              help=(f'The Lifebit Platform url you are trying to access to. Default={CLOUDOS_URL}.'),
              default=CLOUDOS_URL,
              required=True)
@click.option('--workspace-id',
              help='The specific Lifebit Platform workspace id.',
              required=True)
@click.option('--label',
              help='Name (label) for the new job queue.',
              required=False,
              default=None)
@click.option('--description',
              help=('Short description of the new job queue. Required when '
                    'creating a queue (not used with --add-compute-env).'),
              default='',
              required=False)
@click.option('--preset',
              help=(
                  'Preset template to use. Choices: '
                  + ', '.join(QUEUE_PRESETS.keys())
                  + '. Default=standard-stable.'
              ),
              type=click.Choice(list(QUEUE_PRESETS.keys()), case_sensitive=False),
              default='standard-stable',
              show_default=True,
              required=False)
@click.option('--executor',
              help='Workflow executor for the queue. Default=nextflow.',
              type=click.Choice(_EXECUTORS, case_sensitive=False),
              default='nextflow',
              show_default=True,
              required=False)
@click.option('--from-scratch',
              help=('Create a custom job queue from scratch. By default this '
                    'launches an interactive wizard. Combine with -y/--yes to '
                    'create non-interactively using the options below. Mutually '
                    'exclusive with --preset.'),
              is_flag=True)
@click.option('--add-compute-env',
              help=('Add a compute environment to an existing job queue '
                    '(identified by --label, which is required). By default '
                    'this launches an interactive wizard; combine with -y/--yes '
                    'to add non-interactively using the options below. A queue '
                    f'can hold up to {MAX_COMPUTE_ENVS} compute environments.'),
              is_flag=True)
@click.option('--compute-env-name',
              help=('Name for the new compute environment when using '
                    '--add-compute-env with -y/--yes.'),
              default=None)
@click.option('--provisioning-type',
              help='Provisioning type for --from-scratch. Default=on-demand.',
              type=click.Choice(list(PROVISIONING_TYPES.keys()), case_sensitive=False),
              default='on-demand',
              show_default=True)
@click.option('--allocation-strategy',
              help=('Allocation strategy for --from-scratch. spot supports all '
                    'strategies; on-demand supports BEST_FIT and '
                    'BEST_FIT_PROGRESSIVE. Default=BEST_FIT_PROGRESSIVE.'),
              type=click.Choice(_ALL_ALLOCATION_STRATEGIES, case_sensitive=False),
              default='BEST_FIT_PROGRESSIVE',
              show_default=True)
@click.option('--max-vcpus',
              help=f'Max vCPUs for --from-scratch. Max {MAX_VCPUS_LIMIT}.',
              type=click.IntRange(0, MAX_VCPUS_LIMIT),
              default=DEFAULT_MAX_VCPUS,
              show_default=True)
@click.option('--min-vcpus',
              help='Min vCPUs for --from-scratch.',
              type=click.IntRange(0, MAX_VCPUS_LIMIT),
              default=DEFAULT_MIN_VCPUS,
              show_default=True)
@click.option('--instance-types',
              help=("Instance types for --from-scratch. 'optimal' or a "
                    'comma-separated list of standard or GPU instance types. '
                    'Default=optimal.'),
              default='optimal',
              show_default=True)
@click.option('--volume-type',
              help='Volume type for --from-scratch. Default=gp3.',
              type=click.Choice(list(VOLUME_SPECS.keys()), case_sensitive=False),
              default='gp3',
              show_default=True)
@click.option('--size',
              help=f'Volume size in GiB for --from-scratch. Default={_DEFAULT_SIZE}.',
              type=int,
              default=_DEFAULT_SIZE,
              show_default=True)
@click.option('--iops',
              help=f'Provisioned IOPS for --from-scratch. Default={_DEFAULT_IOPS}.',
              type=int,
              default=_DEFAULT_IOPS,
              show_default=True)
@click.option('--throughput',
              help=('Volume throughput in MB/s for --from-scratch (gp3 only). '
                    f'Default={_DEFAULT_THROUGHPUT}.'),
              type=int,
              default=_DEFAULT_THROUGHPUT,
              show_default=True)
@click.option('-y',
              '--yes',
              'skip_confirmation',
              help='Skip the confirmation prompt and proceed immediately.',
              is_flag=True)
@click.option('--set-default',
              help='Set the new job queue as the workspace default. Default=False.',
              is_flag=True)
@click.option('--execution-platform',
              help='Name of the execution platform implemented in your Lifebit Platform. Default=aws.',
              type=click.Choice(['aws', 'azure', 'hpc']),
              default='aws')
@click.option('--disable-ssl-verification',
              help=('Disable SSL certificate verification. Please, remember that this option is '
                    'not generally recommended for security reasons.'),
              is_flag=True)
@click.option('--ssl-cert',
              help='Path to your SSL certificate file.')
@click.option('--profile', help='Profile to use from the config file', default=None)
@click.pass_context
@with_profile_config(required_params=['apikey', 'workspace_id'])
def create_queue(ctx,
                 apikey,
                 cloudos_url,
                 workspace_id,
                 label,
                 description,
                 preset,
                 executor,
                 from_scratch,
                 add_compute_env,
                 compute_env_name,
                 provisioning_type,
                 allocation_strategy,
                 max_vcpus,
                 min_vcpus,
                 instance_types,
                 volume_type,
                 size,
                 iops,
                 throughput,
                 skip_confirmation,
                 set_default,
                 execution_platform,
                 disable_ssl_verification,
                 ssl_cert,
                 profile):
    """Create a new job queue in a Lifebit Platform workspace.

    By default a preset template is used. Pass --from-scratch to build a custom
    queue, either interactively (default) or non-interactively with -y/--yes.
    Pass --add-compute-env to add a compute environment to an existing queue.
    """

    verify_ssl = ssl_selector(disable_ssl_verification, ssl_cert)

    # Batch job queues are an AWS-only feature; they are not available in
    # Azure or HPC workspaces.
    if execution_platform in ('azure', 'hpc'):
        Console().print(
            '[yellow]Warning:[/yellow] Batch job queues are not available in '
            f'{execution_platform.upper()} workspaces.'
        )
        sys.exit(0)

    if from_scratch and add_compute_env:
        raise click.UsageError(
            '--from-scratch and --add-compute-env cannot be used together.'
        )

    if add_compute_env:
        _add_compute_environment(
            ctx=ctx,
            cloudos_url=cloudos_url,
            apikey=apikey,
            workspace_id=workspace_id,
            verify_ssl=verify_ssl,
            label=label,
            compute_env_name=compute_env_name,
            provisioning_type=provisioning_type,
            allocation_strategy=allocation_strategy,
            max_vcpus=max_vcpus,
            min_vcpus=min_vcpus,
            instance_types=instance_types,
            volume_type=volume_type,
            size=size,
            iops=iops,
            throughput=throughput,
            skip_confirmation=skip_confirmation,
        )
        return

    # --description is required when creating a queue (both preset and
    # from-scratch paths). It is not used when adding a compute environment.
    if not description:
        raise click.UsageError('Missing option --description.')

    if from_scratch:
        _create_queue_from_scratch(
            ctx=ctx,
            cloudos_url=cloudos_url,
            apikey=apikey,
            workspace_id=workspace_id,
            verify_ssl=verify_ssl,
            label=label,
            description=description,
            executor=executor,
            provisioning_type=provisioning_type,
            allocation_strategy=allocation_strategy,
            max_vcpus=max_vcpus,
            min_vcpus=min_vcpus,
            instance_types=instance_types,
            volume_type=volume_type,
            size=size,
            iops=iops,
            throughput=throughput,
            skip_confirmation=skip_confirmation,
            set_default=set_default,
        )
        return

    if label is None:
        raise click.UsageError('Missing option --label.')

    # Resolve the preset to show the user what will be created
    preset_info = QUEUE_PRESETS[preset]
    ce_name = preset_info['computeEnvironmentName']
    cr = preset_info['computeResources']
    resource_type = cr.get('type', 'EC2')
    max_vcpus_preset = cr.get('maxvCpus', 'N/A')
    instance_count = len(cr.get('instanceTypes', []))
    template_name = preset_info['templateName']

    j_queue = Queue(cloudos_url, apikey, None, workspace_id, verify=verify_ssl)

    # Creating a queue creates a compute environment; enforce the workspace limit.
    _check_workspace_ce_limit(Console(), j_queue)

    if not skip_confirmation:
        click.echo('\nYou are about to create the following job queue:')
        click.echo(f'  Label              : {label}')
        click.echo(f'  Description        : {description or "(none)"}')
        click.echo(f'  Preset             : {template_name}')
        click.echo(f'  Compute env name   : {ce_name}')
        click.echo(f'  Resource type      : {resource_type}')
        click.echo(f'  Max vCPUs          : {max_vcpus_preset}')
        click.echo(f'  Instance types     : {instance_count} types')
        click.echo(f'  Executor           : {executor}')
        click.echo(f'  Set as default     : {set_default}')
        click.echo(f'  Workspace          : {workspace_id}')
        click.echo('')
        if not click.confirm('Proceed with queue creation?'):
            click.echo('Aborted.')
            sys.exit(0)

    console = Console()
    print('Executing queue create...')

    try:
        queue_id = j_queue.create_job_queue(
            label=label,
            description=description,
            preset_name=preset,
            executor=executor,
            is_default=set_default,
        )
        console.print(f'\t[green]Queue "{label}" created successfully.[/green]')
        print(f'\tQueue ID : {queue_id}')
        print(f'\tView at  : {cloudos_url}/app/job-queues/{queue_id}')
    except Exception as e:
        console.print(f'\t[red]Error creating queue:[/red] {str(e)}')
        sys.exit(1)


def _create_queue_from_scratch(ctx,
                               cloudos_url,
                               apikey,
                               workspace_id,
                               verify_ssl,
                               label,
                               description,
                               executor,
                               provisioning_type,
                               allocation_strategy,
                               max_vcpus,
                               min_vcpus,
                               instance_types,
                               volume_type,
                               size,
                               iops,
                               throughput,
                               skip_confirmation,
                               set_default):
    """Handle the --from-scratch branch of ``cloudos queue create``.

    When ``skip_confirmation`` is False, an interactive wizard collects all the
    parameters. Otherwise the provided option flags are validated and used
    directly (non-interactive mode).
    """
    console = Console()

    # --from-scratch is mutually exclusive with an explicitly-set --preset.
    if ctx.get_parameter_source('preset') == click.core.ParameterSource.COMMANDLINE:
        raise click.UsageError('--from-scratch cannot be combined with --preset.')

    j_queue = Queue(cloudos_url, apikey, None, workspace_id, verify=verify_ssl)

    if skip_confirmation:
        params = {
            'label': label,
            'provisioning_type': provisioning_type,
            'allocation_strategy': allocation_strategy,
            'max_vcpus': max_vcpus,
            'min_vcpus': min_vcpus,
            'instance_types': _parse_instance_types(instance_types),
            'volume_type': volume_type,
            'size': size,
            'iops': iops,
            'throughput': throughput,
        }
        if params['label'] is None:
            raise click.UsageError('Missing option --label for --from-scratch -y.')
        _validate_from_scratch_flags(params)
        # Creating a queue creates a compute environment; enforce the limit.
        _check_workspace_ce_limit(console, j_queue)
    else:
        # Creating a queue creates a compute environment; enforce the limit.
        _check_workspace_ce_limit(console, j_queue)
        params = _from_scratch_wizard(console)

    print('Executing queue create...')

    try:
        queue_id = j_queue.create_job_queue_from_scratch(
            label=params['label'],
            description=description,
            provisioning_type=params['provisioning_type'],
            allocation_strategy=params['allocation_strategy'],
            max_vcpus=params['max_vcpus'],
            min_vcpus=params['min_vcpus'],
            instance_types=params['instance_types'],
            volume_type=params['volume_type'],
            size=params['size'],
            iops=params['iops'],
            throughput=params['throughput'],
            executor=executor,
            is_default=set_default,
        )
        console.print(
            f'\t[green]Queue "{params["label"]}" created successfully.[/green]'
        )
        print(f'\tQueue ID : {queue_id}')
        print(f'\tView at  : {cloudos_url}/app/job-queues/{queue_id}')
    except Exception as e:
        console.print(f'\t[red]Error creating queue:[/red] {str(e)}')
        sys.exit(1)


def _add_compute_environment(ctx,
                             cloudos_url,
                             apikey,
                             workspace_id,
                             verify_ssl,
                             label,
                             compute_env_name,
                             provisioning_type,
                             allocation_strategy,
                             max_vcpus,
                             min_vcpus,
                             instance_types,
                             volume_type,
                             size,
                             iops,
                             throughput,
                             skip_confirmation):
    """Handle the --add-compute-env branch of ``cloudos queue create``.

    Adds a compute environment to an existing queue (identified by ``label``).
    The queue must exist and have fewer than ``MAX_COMPUTE_ENVS`` compute
    environments. When ``skip_confirmation`` is False an interactive wizard
    collects the compute environment configuration.
    """
    console = Console()

    if label is None:
        raise click.UsageError('Missing option --label for --add-compute-env.')

    j_queue = Queue(cloudos_url, apikey, None, workspace_id, verify=verify_ssl)

    # The queue must already exist to add a compute environment to it. Compute
    # environments can only be added to created (non-system) queues, and system
    # queues do not count towards the workspace limit.
    team_queues = j_queue.get_job_queues(exclude_system_queues=True)
    target_queue = next(
        (q for q in team_queues if q.get('label') == label), None
    )
    if target_queue is None:
        console.print(
            f"[red]Error:[/red] No job queue with label '{label}' was found. "
            "Compute environments can only be added to existing queues."
        )
        sys.exit(1)

    queue_id = target_queue.get('id') or target_queue.get('_id', '')
    current_ce_count = len(target_queue.get('computeEnvironments', []))

    # A queue cannot exceed the compute environment limit.
    if current_ce_count >= MAX_COMPUTE_ENVS:
        console.print(
            f"[yellow]Warning:[/yellow] {CE_LIMIT_REACHED_MESSAGE}"
        )
        sys.exit(0)

    # Adding a compute environment must not exceed the workspace limit.
    _check_workspace_ce_limit(console, j_queue, queues=team_queues)

    if skip_confirmation:
        if compute_env_name is None:
            raise click.UsageError(
                'Missing option --compute-env-name for --add-compute-env -y.'
            )
        params = {
            'label': compute_env_name,
            'provisioning_type': provisioning_type,
            'allocation_strategy': allocation_strategy,
            'max_vcpus': max_vcpus,
            'min_vcpus': min_vcpus,
            'instance_types': _parse_instance_types(instance_types),
            'volume_type': volume_type,
            'size': size,
            'iops': iops,
            'throughput': throughput,
        }
        _validate_from_scratch_flags(params)
    else:
        params = _from_scratch_wizard(
            console, for_compute_env=True, queue_label=label
        )

    print('Executing add compute environment...')

    try:
        j_queue.add_compute_environment(
            queue_id=queue_id,
            queue_label=label,
            ce_name=params['label'],
            provisioning_type=params['provisioning_type'],
            allocation_strategy=params['allocation_strategy'],
            max_vcpus=params['max_vcpus'],
            min_vcpus=params['min_vcpus'],
            instance_types=params['instance_types'],
            volume_type=params['volume_type'],
            size=params['size'],
            iops=params['iops'],
            throughput=params['throughput'],
        )
        console.print(
            f'\t[green]Compute environment "{params["label"]}" added '
            f'successfully to queue "{label}".[/green]'
        )
        print(f'\tView at  : {cloudos_url}/app/job-queues/{queue_id}')
        # Inform the user if this addition reached the compute environment limit.
        if current_ce_count + 1 >= MAX_COMPUTE_ENVS:
            console.print(f'\t[yellow]Warning:[/yellow] {CE_LIMIT_REACHED_MESSAGE}')
    except Exception as e:
        console.print(f'\t[red]Error adding compute environment:[/red] {str(e)}')
        sys.exit(1)

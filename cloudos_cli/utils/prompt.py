import sys
import os
from rich.console import Console
from rich.prompt import Confirm


def smart_input(prompt="> ", use_confirm=False):
    """
    Prompt for user input using Rich Console in both terminal and Jupyter environments.
    
    This function handles different execution contexts:
    - Terminal: Uses Rich Console input with beautiful formatting
    - Jupyter Python cells: Uses Rich Console which displays styled input
    - Jupyter bash cells: Reads from environment variable set by user
    
    Parameters
    ----------
    prompt : str
        The prompt message to display to the user.
    use_confirm : bool
        If True, uses Rich Confirm for yes/no questions (returns bool).
        If False, uses standard console input (returns string).
        
    Returns
    -------
    str or bool
        The user's input string, or boolean if use_confirm=True.
        
    Notes
    -----
    For Jupyter bash cells, set the environment variable before running:
        import os
        os.environ['CLOUDOS_CONFIRM'] = 'y'
        !cloudos job results --delete --job-id YOUR_JOB_ID
    Or use the --yes flag to skip confirmation.
    """
    console = Console()
    
    # Check if we're in a non-interactive environment
    if not sys.stdin.isatty():
        # Check if answer was provided via environment variable
        env_answer = os.environ.get('CLOUDOS_CONFIRM', '').strip().lower()
        if env_answer:
            console.print(f"[yellow]{prompt}[/yellow][green]{env_answer}[/green]")
            if use_confirm:
                return env_answer in ('y', 'yes', 'true', '1')
            return env_answer
        
        # Try getpass as fallback (works in some terminal contexts)
        try:
            import getpass
            sys.stderr.write(prompt)
            sys.stderr.flush()
            result = getpass.getpass('')
            if use_confirm:
                return result.lower() in ('y', 'yes')
            return result
        except Exception:
            pass
        
        # If nothing works, provide helpful error
        console.print("\n[red bold]" + "="*70 + "[/red bold]")
        console.print("[red bold]❌ Cannot read input in non-interactive mode (Jupyter bash cell).[/red bold]\n")
        console.print("[yellow]Choose one of these solutions:[/yellow]\n")
        console.print("[cyan]1. Use Python cell instead of bash:[/cyan]")
        console.print("   [dim]import subprocess[/dim]")
        console.print("   [dim]subprocess.run(['cloudos', 'job', 'results', '--delete', ...])[/dim]\n")
        console.print("[cyan]2. Use the --yes flag to skip confirmation:[/cyan]")
        console.print("   [dim]!cloudos job results --delete --job-id ID --yes[/dim]\n")
        console.print("[cyan]3. Set environment variable before bash command:[/cyan]")
        console.print("   [dim]import os[/dim]")
        console.print("   [dim]os.environ['CLOUDOS_CONFIRM'] = 'y'[/dim]")
        console.print("   [dim]!cloudos job results --delete --job-id ID[/dim]")
        console.print("[red bold]" + "="*70 + "[/red bold]")
        raise RuntimeError("Cannot read input in non-interactive mode")
    
    # Interactive mode (terminal or Jupyter Python cell)
    if use_confirm:
        return Confirm.ask(prompt, default=False, console=console)
    else:
        return console.input(f"[bold cyan]{prompt}[/bold cyan]")



import sys
import os


def smart_input(prompt="> "):
    """
    Prompt for user input in both terminal and Jupyter environments.
    
    This function handles different execution contexts:
    - Terminal: Uses standard input() function
    - Jupyter Python cells: Uses standard input() which displays input widget
    - Jupyter bash cells: Reads from environment variable set by user
    
    Parameters
    ----------
    prompt : str
        The prompt message to display to the user.
        
    Returns
    -------
    str
        The user's input string.
        
    Notes
    -----
    For Jupyter bash cells, set the environment variable before running:
        export CLOUDOS_CONFIRM="y"
        !cloudos job results --delete --job-id YOUR_JOB_ID
    Or better yet, use the --yes flag to skip confirmation.
    """
    # Check if we're in a non-interactive environment
    if not sys.stdin.isatty():
        # Check if answer was provided via environment variable
        env_answer = os.environ.get('CLOUDOS_CONFIRM', '').strip().lower()
        if env_answer:
            sys.stderr.write(f"{prompt}{env_answer}\n")
            sys.stderr.flush()
            return env_answer
        
        # Try getpass as fallback (works in some terminal contexts)
        try:
            import getpass
            sys.stderr.write(prompt)
            sys.stderr.flush()
            return getpass.getpass('')
        except Exception:
            pass
        
        # If nothing works, provide helpful error
        raise RuntimeError(
            "\n" + "="*70 + "\n"
            "❌ Cannot read input in non-interactive mode (Jupyter bash cell).\n\n"
            "Choose one of these solutions:\n\n"
            "1. Use Python cell instead of bash:\n"
            "   import subprocess\n"
            "   subprocess.run(['cloudos', 'job', 'results', '--delete', ...])\n\n"
            "2. Use the --yes flag to skip confirmation:\n"
            "   !cloudos job results --delete --job-id ID --yes\n\n"
            "3. Set environment variable before bash command:\n"
            "   import os\n"
            "   os.environ['CLOUDOS_CONFIRM'] = 'y'\n"
            "   !cloudos job results --delete --job-id ID\n"
            + "="*70
        )
    
    # Interactive mode (terminal or Jupyter Python cell)
    return input(prompt)
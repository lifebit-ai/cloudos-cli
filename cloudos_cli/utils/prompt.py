import sys


def smart_input(prompt="> "):
    """
    Prompt for user input in both terminal and Jupyter environments.
    
    This function handles different execution contexts:
    - Terminal: Uses standard input() function
    - Jupyter Python cells: Uses standard input() which displays input widget
    - Jupyter bash cells: Detects non-interactive mode and uses getpass fallback
    
    Parameters
    ----------
    prompt : str
        The prompt message to display to the user.
        
    Returns
    -------
    str
        The user's input string.
    """
    # Check if stdin is available and interactive
    if not sys.stdin.isatty():
        # Non-interactive mode (e.g., piped input, subprocess from Jupyter bash)
        # Try to use getpass which can read from /dev/tty
        try:
            import getpass
            # Print prompt to stderr so it's visible
            sys.stderr.write(prompt)
            sys.stderr.flush()
            return getpass.getpass('')
        except:
            # If getpass fails, we're truly in a non-interactive environment
            # Return empty string or raise error
            raise RuntimeError(
                "Cannot read input in non-interactive mode. "
                "If running from Jupyter bash cell (!command), use Python cell instead, "
                "or provide --yes flag to skip confirmation."
            )
    
    # Interactive mode (terminal or Jupyter Python cell)
    return input(prompt)
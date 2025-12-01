import sys
import os


def smart_input(prompt=">>>"):

    try:
        # Try standard input()
        return input(prompt)
    except (EOFError, KeyboardInterrupt):
        # Fall back to readline from stdin (for some Bash Jupyter cases)
        try:
            print(prompt, end="", flush=True)
            return sys.stdin.readline().strip()
        except Exception:
            # If stdin is unavailable, return a default value
            print("\n[Input unavailable, using default value]")
            return "default_value"
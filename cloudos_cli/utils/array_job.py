import re


def is_valid_regex(s):
    try:
        re.compile(s)
        return True
    except re.error:
        return False

def is_glob_pattern(s):
    return any(char in s for char in "*?[")

def is_probably_regex(s):
    if not is_valid_regex(s):
        return False

    # Patterns that usually indicate actual regex use (not just file names)
    regex_indicators = [
        r"\.\*", r"\.\+", r"\\[dws]", r"\[[^\]]+\]", r"\([^\)]+\)",
        r"\{\d+(,\d*)?\}", r"\^", r"\$", r"\|"
    ]
    return any(re.search(pat, s) for pat in regex_indicators)

def classify_pattern(s):
    if is_probably_regex(s):
        return "regex"
    elif is_glob_pattern(s):
        return "glob"
    else:
        return "exact"

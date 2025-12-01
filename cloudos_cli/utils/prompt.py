def smart_input(prompt="> "):
    """
    Prompt for user input in both terminal and Jupyter environments.
    
    In Jupyter Notebook/Lab, the standard input() function works correctly
    when executed in an interactive cell. It displays a text box for input.
    
    Parameters
    ----------
    prompt : str
        The prompt message to display to the user.
        
    Returns
    -------
    str
        The user's input string.
    """
    return input(prompt)
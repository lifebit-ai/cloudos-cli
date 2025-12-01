def smart_input(prompt="> "):
    try:
        from IPython import get_ipython
        shell = get_ipython().__class__.__name__
        if shell == "ZMQInteractiveShell":  # Jupyter Notebook/Lab
            from ipywidgets import Text, Button
            from IPython.display import display

            result = {}

            text = Text(description=prompt)
            button = Button(description="Submit")

            def on_click(b):
                result["value"] = text.value

            button.on_click(on_click)
            display(text, button)

            # Wait until user submits
            while "value" not in result:
                import time
                time.sleep(0.1)

            return result["value"]
        else:
            # Terminal or other IPython shells
            return input(prompt)

    except:
        # Fallback for normal Python
        return input(prompt)
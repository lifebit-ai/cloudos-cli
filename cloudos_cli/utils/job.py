def param_to_json(param_str: str, prefix="--"):
    data = param_str.split("=")
    if len(data) != 2:
        raise ValueError(
            f"Parameter {param_str} should have the format param_name=param_value"
        )
    name, value = data
    if value == "false":
        value = False
    elif value == "true":
        value = True
    return {
        "name": name,
        "prefix": prefix,
        "parameterKind": "textValue",
        "textValue": value,
    }

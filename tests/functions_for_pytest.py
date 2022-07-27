import json

def load_json_file(file_and_path):
    with open(file_and_path) as json_data:
        dict = json.load(json_data)
        json_data = json.dumps(dict)
    return(json_data)
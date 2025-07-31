import yaml
def load_config(debug=False):
    if debug:
        return yaml.safe_load(open("config_debug.yml"))
    return yaml.safe_load(open("config.yml"))

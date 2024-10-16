from ..utils import get_function_container_config

def is_available(provider):
    containerConf = get_function_container_config()
    return containerConf['provider'] == provider
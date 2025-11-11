from pydantic import BaseModel
from typing import Literal
import os


def get_function_container_config():
    # Read the env from the environment
    env = os.environ

    config = {
        "provider": env.get("provider", "local-once"),
    }
    return config
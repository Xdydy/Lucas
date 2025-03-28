from .models import (
    localonce_durable
)
from ..utils import (
    config
)
from .result import (
    DurableWaitingResult
)

def createOrchestratorScopedId(orcheId:str):
    return f"orchestrator::__state__::{orcheId}"



def durable_helper(fn):
    conf = config.get_function_container_config()
    match conf['provider']:
        case 'local-once':
            return localonce_durable(fn)
        case 'local':
            return
        case _:
            raise Exception(f"Unsupported provider {conf['provider']}")

__all__ = [
    "durable_helper",
    "DurableWaitingResult",
]
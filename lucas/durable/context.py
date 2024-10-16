from .metadata import OrchestratorMetadata
from pydantic import BaseModel

class DurableCallbackContext(BaseModel):
    kind: str = "durable-orchestrator-callback"
    orchestrator: OrchestratorMetadata
    taskpc: int

def parseDurableCallbackContext(ctx) -> DurableCallbackContext | None:
    if ctx is None:
        return None
    try:
        ctx = DurableCallbackContext(**ctx)
    except Exception as e:
        return None
    if ctx.kind != "durable-orchestrator-callback":
        return None
    return ctx
from lucas.runtime import Runtime
from lucas.runtime import RuntimeMetadata
from typing import Any, Callable
from pydantic import BaseModel

class OrchestratorMetadata(BaseModel):
    class InitialData(BaseModel):
        input: Any
        metadata: RuntimeMetadata
    id: str
    initialData: InitialData

class DurableMetadata(BaseModel):
    orchestrator: OrchestratorMetadata = None
    runtimeData: RuntimeMetadata
    fn: Callable = None
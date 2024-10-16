from .config import get_function_container_config
from ..runtime import (
    RuntimeMetadata,
    TellParams,
    Runtime
)

def callback(result,frt:Runtime):
    metadata = frt.metadata()
    if len(metadata.stack) == 0:
        return result
    lastInvocation = metadata.stack.pop()
    if lastInvocation.callback == None:
        return result
    if lastInvocation.callback.ctx.get('kind') == 'durable-orchestrator-callback':
        callbackParams = TellParams(
            input=result,
            callback=None,
            responseCtx=lastInvocation.callback.ctx
        )
        result = frt.tell(lastInvocation.caller.funcName, callbackParams.dict())
        return result
    
async def popStack(result, metadata: RuntimeMetadata):
    if len(metadata.stack) == 0:
        return result
    lastInvocation = metadata.stack[-1]
    metadata.stack.pop()
    if lastInvocation.kind == 'tell':
        return result

__all__ = [
    "get_function_container_config",
    "callback",
    "popStack"
]
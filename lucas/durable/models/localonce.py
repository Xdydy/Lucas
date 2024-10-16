from lucas.runtime import (
    LocalOnceRuntime,
    RuntimeMetadata
)

from ..state import (
    DurableFunctionState,
    ScopedDurableStateClient
)

from ..metadata import (
    DurableMetadata,
    OrchestratorMetadata,
)

from ..context import (
    DurableCallbackContext,
    parseDurableCallbackContext
)

from ..runtime import (
    DurableRuntime,
    DurableException
)

from ..result import (
    DurableWaitingResult
)
from lucas.utils import (
    callback,
    popStack
)

import uuid

def createOrchestratorScopedId(orcheId:str):
    return f"orchestrator::__state__::{orcheId}"

def localonce_durable(fn):
    localonceClients : dict[str,ScopedDurableStateClient] = {}
    localonceResults : dict[str,DurableWaitingResult] = {}
    def getClient(scopeId:str):
        if scopeId not in localonceClients:
            localonceClients[scopeId] = ScopedDurableStateClient(scopeId)
        return localonceClients[scopeId]
    async def handler(event: dict,
                      workflow_runner = None,
                      metadata = None):
        frt = LocalOnceRuntime(event,workflow_runner,metadata)
        frt_metadata: RuntimeMetadata = frt.metadata()
        # print(f"[Debug] {frt_metadata.dict()}")
        callbackCtx : DurableCallbackContext = None

        # special judge
        last_invocation = frt_metadata.stack[-1]
        if last_invocation.kind == 'tell':
            # 拿到上一轮的callbackCtx并退栈
            callbackCtx = parseDurableCallbackContext(last_invocation.response.responseCtx)
            # frt_metadata.stack.pop()

        if callbackCtx is not None:
            # not first-call
            orchestratorMetadata = callbackCtx.orchestrator
            frt_metadata.stack.pop()
        else:
            # first-call
            orchestratorMetadata = OrchestratorMetadata(
                id=str(uuid.uuid4()),
                initialData=OrchestratorMetadata.InitialData(
                    input=frt.input(),
                    metadata=frt_metadata
                )
            )
        durableMetadata  = DurableMetadata(
            orchestrator=orchestratorMetadata,
            runtimeData=frt_metadata,
            fn=handler
        )
        
        orchestratorMetadataId = orchestratorMetadata.id
        scopeId = createOrchestratorScopedId(orchestratorMetadataId)
        client = getClient(scopeId)
        state, init = await DurableFunctionState.load(client)

        if callbackCtx is not None:
            result = frt.input()
            action = state._actions[callbackCtx.taskpc-1]
            action.status = 'completed'
            action.result = result
            await state.store(client)

        dfrt = DurableRuntime(frt,durableMetadata,state)
        
        try:
            result = await fn(dfrt)
            await state.saveResult(client,result)
            await callback(result,frt)
            # await popStack(result,frt_metadata)
            await localonceResults[orchestratorMetadataId].setResult(result)
            return result
        except DurableException as e:
            print(f"[Trace] {frt_metadata.funcName}::{orchestratorMetadataId} yield")
            await state.store(client)
            waitingResult = DurableWaitingResult()
            if localonceResults.get(orchestratorMetadataId) == None:
                localonceResults[orchestratorMetadataId] = waitingResult
            return localonceResults[orchestratorMetadataId]
    return handler
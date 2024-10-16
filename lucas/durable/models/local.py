from faasit_runtime.runtime import (
    FaasitRuntimeMetadata,
    LocalRuntime
)

from faasit_runtime.durable.state import (
    DurableFunctionState,
    ScopedDurableStateClient
)

from faasit_runtime.durable.metadata import (
    DurableMetadata,
    OrchestratorMetadata,
)

from faasit_runtime.durable.context import (
    DurableCallbackContext,
    parseDurableCallbackContext
)

from faasit_runtime.durable.runtime import (
    DurableRuntime,
    DurableException
)

from faasit_runtime.durable.result import (
    DurableWaitingResult
)

from faasit_runtime.utils import callback

import uuid

def createOrchestratorScopedId(orcheId:str,fnName:str):
    return f"orchestrator::__state__::{orcheId}::{fnName}"

async def loadStateByMetadata(metadata: FaasitRuntimeMetadata):
    functionId = metadata.invocation.id
    functionName = metadata.funcName
    key = createOrchestratorScopedId(functionId,functionName)
    return await DurableFunctionState.loads(key)

def local_durable(fn):
    # 要先在函数初始化的时候就恢复函数记忆
    async def handler(event: dict,
                      metadata = None):
        frt = LocalRuntime(event,metadata)
        frt_metadata: FaasitRuntimeMetadata = frt.metadata()

        callbackCtx: DurableCallbackContext = None

        # judge if one function is re-called
        if frt_metadata.invocation.kind == 'tell':
            callbackCtx = parseDurableCallbackContext(frt_metadata.invocation.callback)
        
        if callbackCtx is not None:
            # not first call
            orchestratorMetadata = callbackCtx.orchestrator
        else:
            # first call
            orchestratorMetadata = OrchestratorMetadata(
                id=str(uuid.uuid4()),
                initialData=OrchestratorMetadata.InitialData(
                    input=frt.input(),
                    metadata=frt_metadata
                )
            )
        
        durableMetadata = DurableMetadata(
            orchestrator=orchestratorMetadata,
            runtimeData=frt_metadata
        )

        state,client = await loadStateByMetadata(frt_metadata)
        print("[STATE] load state and client")
        if callbackCtx is not None:
            result = frt.input()
            action = state._actions[callbackCtx.taskpc-1]
            action.status = 'completed'
            action.result = result
            await state.store(client)

        dfrt = DurableRuntime(frt, durableMetadata, state)
        try:
            result = await fn(dfrt)
            await state.saveResult(client,result)
            state.to_redis(client)
            await callback(result,frt,frt_metadata)
            return result
        except DurableException as e:
            print(f"[Trace] {frt_metadata.funcName}::{orchestratorMetadata.id} yield")
            await state.store(client)
            state.to_redis(client)
            # return DurableWaitingResult(e.task,state,client)
            return {"status":"waiting","result":None}
        
    return handler
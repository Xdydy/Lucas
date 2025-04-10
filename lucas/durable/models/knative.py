from lucas.durable.runtime import DurableRuntime
from lucas.runtime.kn_runtime import KnativeRuntime
from ..state import (
    DurableStateClient,
    ScopedDurableStateClient,
    DurableFunctionState,
)
from lucas.serverless_function import Metadata

class ActorState(DurableStateClient):
    def __init__(self, instanceId, frt:KnativeRuntime):
        self._env = f"faasit-kn-{instanceId}"
        self._frt = frt

    def set(self,key:str,value):
        _state = self._frt._redis_db.get(self._env)
        if _state is None:
            _state = {}
        _state[key] = value
        self._frt._redis_db.set(self._env, _state)

    def get(self,key:str):
        _state = self._frt._redis_db.get(self._env)
        if _state is None:
            return None
        return _state.get(key, None)

def kn_durable(kn):
    def handler(md: Metadata):
        def getClient(scopeId:str):
            client = md._redis_db.get(scopeId)
            if client == None:
                return ScopedDurableStateClient.load(scopeId,{})
        params = md._params
        try:
            instanceId = params['instanceId']
        except KeyError as e:
            raise ValueError("Durable function `instanceId` is required")
        frt = KnativeRuntime(md)
        client = getClient(instanceId)
        state, init = DurableFunctionState.load(client)
        actorState = ActorState(instanceId, frt)
        df = DurableRuntime(
            frt=frt,
            durableMetadata=None,
            state=state,
            client=actorState
        )
        result = kn(df)
        # saveClient(client)
        return result
    return handler
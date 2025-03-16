from .check import is_available
from .runtime import (
    Runtime, 
    InputType,
    CallResult,
    StorageMethods,
    RuntimeMetadata,
    TellParams,
    CallParams
)
if is_available('local'):
    import requests
    import aiohttp
    import redis

import json
from typing import Any
from lucas.serverless_function import Metadata

class LocalRuntime(Runtime):
    name: str = 'local'
    def __init__(self, metadata: Metadata) -> None:
        super().__init__()
        self._input = metadata._params
        self._id = metadata._id
        self._storage = self.LocalStorage()
        self._metadata = metadata

    def input(self):
        result = None
        try:
            result = json.loads(self._input)
        except Exception as e:
            result = self._input
        return result

    def output(self, _out):
        return _out

    def metadata(self):
        return self._metadata

    def call(self, fnName: str, fnParams) -> CallResult:
        fnParams: CallParams
        try:
            fnParams = CallParams(**fnParams)
        except:
            fnParams = CallParams(input=fnParams)
        event = fnParams.input
        metadata = self.helperCollectMetadata('call',fnName, fnParams)

        callerName = self._metadata.funcName
        print(f"[function call] {callerName} -> {fnName}")
        print(f"[call params] {event}")

        url = f"http://{fnName}:9000"
        json_data = {
            "event": event,
            "metadata": metadata.json()
        }
        headers = {"Content-Type": "application/json"}
        resp = requests.post(url, json=json_data, headers=headers)
        result = resp.json()
        
        status = result.get('status')
        if status == "finished":
            return result.get('result')
        elif status == 'waiting':
            return result
        else:
            return None

    async def tell(self, fnName: str, fnParams: dict) -> Any:
        fnParams: TellParams 
        try:
            fnParams = TellParams(**fnParams)
        except:
            fnParams = TellParams(input=fnParams)
        event = fnParams.input
        metadata: RuntimeMetadata = self.helperCollectMetadata("tell", fnName, fnParams)
        callerName = self._metadata.funcName

        print(f"[function tell] {callerName} -> {fnName}")
        print(f"[tell params] {event}")

        url = f"http://{fnName}:9000"
        json_data = {
            "event": event,
            "metadata": metadata.json()
        }
        headers = {"Content-Type": "application/json"}
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=json_data,headers=headers) as resp:
                result = await resp.json()
                return result

    @property
    def storage(self) -> StorageMethods:
        return self._storage

    class LocalStorage(StorageMethods):
        def __init__(self) -> None:
            self.redis_client = redis.Redis(host='redis', port=6379, db=0)
            pass

        async def set(self, key: str, value: str) -> None:
            self.redis_client.set(key, value)
            pass

        async def get(self, key: str) -> str:
            return self.redis_client.get(key)

        async def delete(self, key: str) -> None:
            self.redis_client.delete(key)
            pass

        async def list(self) -> list:
            return [key.decode('utf-8') for key in self.redis_client.keys()]

        async def exists(self, key: str) -> bool:
            return self.redis_client.exists(key)


        
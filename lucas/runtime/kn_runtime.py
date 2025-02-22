from .runtime import (
    Runtime, 
    InputType,
    CallResult
)
import requests
import os
import json
import uuid
from lucas.serverless_function import Metadata
from lucas.utils.logging import log


class KnativeRuntime(Runtime):
    name: str = 'knative'
    def __init__(self,metadata: Metadata) -> None:
        super().__init__()
        self._input = metadata._params
        self._id = metadata._id
        self._redis_db = metadata._redis_db
        self._namespace = metadata._namespace
        self._router:dict = metadata._router
        self._type = metadata._type

    def input(self):
        result = None
        try:
            result = json.loads(self._input)
        except Exception as e:
            result = self._input
        return result
    def output(self, _out):
        return _out

    def _collect_metadata(self, params):
        id = str(uuid.uuid4())
        
        return {
            'id': id,
            'params': params,
            'namespace': self._namespace,
            'router': self._router,
            'type': 'invoke'
        }
    def call(self, fnName:str, fnParams: InputType) -> CallResult:
        call_url = self._router.get(fnName)
        if call_url is None:
            raise ValueError(f"Function {fnName} not found in router")
        
        metadata_dict = self._collect_metadata(params=fnParams)
        log.info(f"Calling function {fnName} with params metadata: {metadata_dict}")
        resp = requests.post(f"{call_url}", json=metadata_dict, headers={'Content-Type': 'application/json'}, proxies={'http': None, 'https': None})
        resp = resp.json()
        if resp['status'] == 'error':
            raise ValueError(f"Failed to call function {fnName}: {resp['error']}")
        return resp['data']
    
    def tell(self):
        pass
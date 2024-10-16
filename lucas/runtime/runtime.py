from abc import ABC, abstractmethod
from typing import Any, Tuple, Awaitable, Union, Callable, List
from pydantic import BaseModel, validator, ValidationError
import uuid

class InvocationMetadata(BaseModel):
    class Caller(BaseModel):
        funcName: str
        invocationId: str
    class Callback(BaseModel):
        ctx: Any
    class Response(BaseModel):
        responseCtx: Any = None
    id: str
    kind: str
    caller: Caller = None
    callback: Callback = None
    response: Response = None


    @validator('kind')
    def check_fields(cls, v, values, **kwargs):
        if v == 'call':
            return v
        elif v == 'tell':
            # if 'callback' not in values:
            #     raise ValidationError('callback is required for kind tell')
            # if 'response' not in values:
            #     raise ValidationError('response is required for kind tell')
            return v
        else:
            raise ValidationError('kind must be either call or tell')




class RuntimeMetadata(BaseModel):
    funcName: str
    stack: list[InvocationMetadata]



InputType = dict[str, Any]
OutputType = dict[str, Any]
MetadataInput = dict[str, Any]
class CallParams(BaseModel):
    input: InputType
    seq: int = 0
CallResult = OutputType
class TellParams(BaseModel):
    input: InputType
    class Callback(BaseModel):
        ctx: Any
    callback: Callback = None
    responseCtx: Any = None
TellResult = OutputType

FaasitResult = Any

def createRuntimeMetadata(fnName:str) -> RuntimeMetadata:
    id=uuid.uuid4().hex
    invocation = InvocationMetadata(
        id=id,
        kind='call',
    )
    return RuntimeMetadata(funcName=fnName, stack=[])

class StorageMethods(ABC):
    def put(self, filename: str, data: bytes) -> None:
        pass

    def get(self, filename: str, timeout = -1) -> bytes:
        pass

    def list(self) -> List:
        pass

    def exists(self, filename: str) -> bool:
        pass

    def delete(self, filename: str) -> None:
        pass

class Runtime(ABC):
    def __init__(self) -> None:
        super().__init__()
        self.event = None
    def metadata(self) -> RuntimeMetadata:
        return self._metadata
    
    @classmethod
    @abstractmethod
    def input(self) -> InputType:
        pass

    @classmethod
    @abstractmethod
    def output(self) -> OutputType:
        pass

    @classmethod
    @abstractmethod
    def call(self, fnName: str, fnParams: CallParams) -> CallResult:
        pass

    @classmethod
    @abstractmethod
    def tell(self, fnName:str, fnParams: TellParams) -> Awaitable[TellResult]:
        pass

    @property
    def storage(self) -> StorageMethods:
        pass

    async def waitResults(self, tasks: list[Awaitable[CallResult]]):
        results = []
        for t in tasks:
            results.append(await t)
        return results

    def helperCollectMetadata(self, 
                              kind: Union["call", "tell"], 
                              fnName: str, 
                              params: Union[CallParams, TellParams]
                              ) -> RuntimeMetadata:
        # 检查kind的值只能为call或tell
        if kind not in ["call", "tell"]:
            raise Exception("kind must be either call or tell")
        metadata: RuntimeMetadata = self.metadata()

        newMetadataStack = metadata.stack.copy()
        # lastInvocation = newMetadata.stack[-1]
        id=uuid.uuid4().hex
        caller=InvocationMetadata.Caller(
            funcName=metadata.funcName, 
            invocationId=id)
        
        if kind == 'call':
            invocation = InvocationMetadata(
                id=id,
                kind=kind,
                caller=caller
            )
            newMetadataStack.append(invocation)
        else:
            p : TellParams = params
            callback = p.callback
            response = InvocationMetadata.Response(responseCtx=p.responseCtx)
            invocation = InvocationMetadata(
                callback=callback,
                response=response,
                id=id,
                kind=kind,
                caller=caller,
            )
            # if response.responseCtx.get('kind') != 'durable-orchestrator-callback':
            #     newMetadataStack.append(invocation)
            # else:
            #     newMetadataStack[-1] = invocation
            newMetadataStack.append(invocation)


        return RuntimeMetadata(funcName=fnName, stack=newMetadataStack)
        # return newMetadata